/* KEYHOLE WebGL molecular renderer built on the vendored three.js build.
 *
 * Scientific contract: this module only ever *draws* coordinates that Python already
 * serialized. It never moves, idealizes, minimizes, docks, or interpolates an atom, and
 * it never implies dynamics, affinity simulation, or electron density. Bond lines are a
 * representation choice derived from the packaged interatomic distances and are labeled
 * as such. Camera framing is the only thing this file invents.
 */
(function (global) {
  "use strict";

  var UI = null;

  /* Chain-role colors are shared with the Canvas 2D fallback so both agree exactly. */
  var ROLE_COLORS = {
    "HLA heavy chain": 0x2f8fa3,
    "β2-microglobulin": 0x4d67b0,
    "peptide": 0xe3a72f,
    "TCR α chain": 0xcb6659,
    "TCR β chain": 0x9b5aa5,
    "candidate peptide schematic": 0xe3a72f
  };
  /* Conventional CPK-family element colors. */
  var ELEMENT_COLORS = {
    C: 0xb9c2c9, N: 0x4f7fd6, O: 0xe05561, S: 0xd9b53a, P: 0xe08b3a,
    SE: 0xd18f3a, CL: 0x4fbf6a, F: 0x63d6a4, BR: 0xa2603c, I: 0x9a6bb5,
    FE: 0xc9773c, ZN: 0x7d8fa6, MG: 0x69a86b, CA: 0x8f9a5c, NA: 0x8b7fd4,
    K: 0x8b7fd4, MN: 0x9c7bb0, CU: 0xc08457, HG: 0x8f9498
  };
  var ROLE_MARKER_COLORS = { mutation: 0xf85149, anchor: 0x4cc4d1 };
  /* Empirical covalent radii used only for relative visual sizing. */
  var VISUAL_RADII = {
    H: 0.31, C: 0.76, N: 0.71, O: 0.66, S: 1.05, P: 1.07, SE: 1.2, CL: 1.02,
    F: 0.57, FE: 1.32, ZN: 1.22, MG: 1.41, CA: 1.76, NA: 1.66, K: 2.03, HG: 1.32
  };
  var COVALENT_CUTOFF_ANGSTROM = 1.9;
  var IDLE_SPIN_RADIANS_PER_MS = 0.00011;
  var IDLE_DELAY_MS = 2200;
  var RESET_DURATION_MS = 520;
  var DAMPING = 0.86;

  var webglProbe = null;

  function webglSupported() {
    if (webglProbe !== null) { return webglProbe; }
    webglProbe = false;
    if (!global.THREE || !global.WebGLRenderingContext) { return webglProbe; }
    try {
      var probe = document.createElement("canvas");
      var context = probe.getContext("webgl2") ||
        probe.getContext("webgl") || probe.getContext("experimental-webgl");
      if (context) {
        webglProbe = true;
        var lose = context.getExtension("WEBGL_lose_context");
        if (lose) { lose.loseContext(); }
      }
    } catch (error) {
      webglProbe = false;
    }
    return webglProbe;
  }

  function roleOf(prepared, atom) {
    return prepared.chainRoles[atom.chain] || "";
  }

  function atomColor(prepared, atom, mode) {
    if (atom.role && ROLE_MARKER_COLORS[atom.role] !== undefined) {
      return ROLE_MARKER_COLORS[atom.role];
    }
    if (mode === "chain") {
      var role = roleOf(prepared, atom);
      if (ROLE_COLORS[role] !== undefined) { return ROLE_COLORS[role]; }
    }
    var element = ELEMENT_COLORS[atom.element];
    return element === undefined ? 0x8b949e : element;
  }

  function atomRadius(atom, scale) {
    var radius = VISUAL_RADII[atom.element];
    if (radius === undefined) { radius = VISUAL_RADII.C; }
    return radius * scale;
  }

  /* Deterministic same-chain, same-or-adjacent-residue distance bonding. */
  function distanceBonds(atoms) {
    var cell = COVALENT_CUTOFF_ANGSTROM;
    var buckets = new Map();
    var index;
    function key(x, y, z) { return x + "|" + y + "|" + z; }
    for (index = 0; index < atoms.length; index += 1) {
      var atom = atoms[index];
      var id = key(
        Math.floor(atom.x / cell), Math.floor(atom.y / cell), Math.floor(atom.z / cell)
      );
      var bucket = buckets.get(id);
      if (!bucket) { bucket = []; buckets.set(id, bucket); }
      bucket.push(index);
    }
    var pairs = [];
    var limit = COVALENT_CUTOFF_ANGSTROM * COVALENT_CUTOFF_ANGSTROM;
    for (index = 0; index < atoms.length; index += 1) {
      var current = atoms[index];
      var cx = Math.floor(current.x / cell);
      var cy = Math.floor(current.y / cell);
      var cz = Math.floor(current.z / cell);
      for (var dx = -1; dx <= 1; dx += 1) {
        for (var dy = -1; dy <= 1; dy += 1) {
          for (var dz = -1; dz <= 1; dz += 1) {
            var neighbours = buckets.get(key(cx + dx, cy + dy, cz + dz));
            if (!neighbours) { continue; }
            for (var slot = 0; slot < neighbours.length; slot += 1) {
              var other = neighbours[slot];
              if (other <= index) { continue; }
              var candidate = atoms[other];
              if (candidate.chain !== current.chain) { continue; }
              if (Math.abs(Number(candidate.res_seq) - Number(current.res_seq)) > 1) {
                continue;
              }
              var ox = candidate.x - current.x;
              var oy = candidate.y - current.y;
              var oz = candidate.z - current.z;
              var square = ox * ox + oy * oy + oz * oz;
              if (square > 0.36 && square <= limit) {
                pairs.push({ fromIndex: index, toIndex: other });
              }
            }
          }
        }
      }
    }
    pairs.sort(function (left, right) {
      return left.fromIndex - right.fromIndex || left.toIndex - right.toIndex;
    });
    return pairs;
  }

  /* Ordered Cα traces per chain, taken straight from the serialized atom order. */
  function backboneTraces(prepared) {
    var traces = new Map();
    prepared.atoms.forEach(function (atom) {
      if (atom.name !== "CA" && String(atom.name).indexOf("CA from PDB") !== 0) { return; }
      var list = traces.get(atom.chain);
      if (!list) { list = []; traces.set(atom.chain, list); }
      list.push(atom);
    });
    return traces;
  }

  function disposeObject(object) {
    object.traverse(function (child) {
      if (child.geometry && typeof child.geometry.dispose === "function") {
        child.geometry.dispose();
      }
      var material = child.material;
      if (!material) { return; }
      if (Array.isArray(material)) {
        material.forEach(function (item) { if (item.dispose) { item.dispose(); } });
      } else if (material.dispose) {
        material.dispose();
      }
    });
  }

  function qualityTier(atomCount) {
    var ratio = global.devicePixelRatio || 1;
    if (atomCount > 4200) {
      return { name: "balanced", sphereDetail: 1, bondSegments: 6, tubular: 220, radial: 8, pixelRatio: Math.min(1.5, ratio) };
    }
    if (atomCount > 1200) {
      return { name: "high", sphereDetail: 2, bondSegments: 8, tubular: 300, radial: 10, pixelRatio: Math.min(1.75, ratio) };
    }
    return { name: "maximum", sphereDetail: 3, bondSegments: 12, tubular: 260, radial: 14, pixelRatio: Math.min(2, ratio) };
  }

  function mount(container, data, options) {
    UI = global.KEYHOLE.ui;
    if (!container || typeof container.appendChild !== "function") {
      throw new Error("molecule mount requires a DOM container");
    }
    if (!webglSupported()) { throw new Error("WebGL is unavailable"); }
    var THREE = global.THREE;
    var settings = options || {};
    var prepared = global.KEYHOLE.scene.prepare(data);
    var label = global.KEYHOLE.scene.truthLabel(data);
    var isReal = data.kind === "pdb";
    var tier = qualityTier(prepared.atoms.length);
    var motion = UI.motionWatcher();
    var reduced = motion.reduced;

    var fig = UI.figure({
      className: "fig-molecule" + (settings.compact ? " fig-molecule-compact" : ""),
      label: settings.label || "",
      title: settings.title || String(data.title || data.sequence || ""),
      truth: label,
      truthKind: isReal ? "real" : "schematic",
      description: settings.description || (isReal ?
        [data.method, data.resolution_angstrom ? data.resolution_angstrom + " Å" : "", data.citation]
          .filter(Boolean).join(" · ") :
        String(data.geometry || "")),
      dataSummary: isReal ?
        "Coordinate provenance and displayed-chain accounting" :
        "Template provenance and illustrative geometry"
    });
    container.appendChild(fig.root);

    var stage = UI.node("div", "mol-stage");
    stage.tabIndex = 0;
    stage.setAttribute("role", "application");
    stage.setAttribute(
      "aria-label",
      label + ". Interactive molecular coordinate view. Use arrow keys to rotate, " +
        "plus and minus to zoom, Home to reset."
    );
    fig.viewport.appendChild(stage);

    var canvas = UI.node("canvas", "mol-canvas");
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.touchAction = "none";
    stage.appendChild(canvas);

    var overlay = UI.node("div", "mol-overlay");
    var overlayId = UI.node("span", "mol-overlay-id", isReal ? "PDB " + String(data.pdb_id) : "candidate");
    overlay.appendChild(overlayId);
    var overlayMode = UI.node("span", "mol-overlay-mode", "");
    overlay.appendChild(overlayMode);
    stage.appendChild(overlay);

    var renderer = null;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: tier.name !== "balanced",
        alpha: false,
        powerPreference: "high-performance",
        stencil: false
      });
    } catch (error) {
      motion.destroy();
      fig.root.remove();
      throw new Error("WebGL context creation failed");
    }
    renderer.setPixelRatio(tier.pixelRatio);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.04;

    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0d10);

    var content = new THREE.Group();
    scene.add(content);

    /* Three-point studio lighting: no effect obscures an atom position. */
    var hemisphere = new THREE.HemisphereLight(0xdfeaf2, 0x0a0f14, 0.85);
    scene.add(hemisphere);
    var keyLight = new THREE.DirectionalLight(0xffffff, 2.25);
    keyLight.position.set(1, 1.35, 1.1);
    scene.add(keyLight);
    var fillLight = new THREE.DirectionalLight(0x9fc4de, 0.85);
    fillLight.position.set(-1.2, -0.4, 0.6);
    scene.add(fillLight);
    var rimLight = new THREE.DirectionalLight(0x8fd6e2, 0.7);
    rimLight.position.set(-0.5, 0.6, -1.4);
    scene.add(rimLight);
    var ambient = new THREE.AmbientLight(0x24313d, 1);
    scene.add(ambient);

    var camera = new THREE.PerspectiveCamera(34, 16 / 10, 0.1, 4000);

    var bounds = { center: new THREE.Vector3(), radius: 1 };
    (function computeBounds() {
      var box = new THREE.Box3();
      var point = new THREE.Vector3();
      prepared.atoms.forEach(function (atom, index) {
        point.set(atom.x, atom.y, atom.z);
        if (index === 0) { box.set(point.clone(), point.clone()); } else { box.expandByPoint(point); }
      });
      if (prepared.atoms.length) {
        box.getCenter(bounds.center);
        var sphere = new THREE.Sphere();
        box.getBoundingSphere(sphere);
        bounds.radius = Math.max(1, sphere.radius);
      }
    })();
    content.position.set(-bounds.center.x, -bounds.center.y, -bounds.center.z);

    /*
     * Framing is the only thing this renderer chooses. The bounding sphere of the packaged
     * coordinates is fitted to the vertical field of view and then pulled in slightly, so
     * the subject fills the frame instead of floating in it. No coordinate is scaled.
     */
    var home = {
      theta: -0.62,
      phi: 1.24,
      distance: bounds.radius / Math.sin(THREE.MathUtils.degToRad(camera.fov) / 2) * 0.86
    };
    var view = { theta: home.theta, phi: home.phi, distance: home.distance };
    var velocity = { theta: 0, phi: 0 };
    var resetTween = null;

    /* ---------------- representation building ---------------- */
    var representations = {};
    var currentMode = "";
    var modeDefinitions = isReal ?
      [
        { id: "ribbon", label: "Backbone + peptide", note: "chain tubes through measured Cα positions with the displayed peptide as ball-and-stick" },
        { id: "atoms", label: "All displayed atoms", note: "every packaged display-chain atom position as ball-and-stick" }
      ] :
      [
        { id: "ribbon", label: "Template trace", note: "measured 1HHK chain-C Cα template with residue beads" }
      ];

    function material(color, options2) {
      var config = Object.assign({
        color: color,
        roughness: 0.42,
        metalness: 0.08,
        envMapIntensity: 0.4
      }, options2 || {});
      return new THREE.MeshStandardMaterial(config);
    }

    function instancedSpheres(atoms, colorMode, scale, extra) {
      var groups = new Map();
      atoms.forEach(function (atom, index) {
        var color = atomColor(prepared, atom, colorMode);
        var bucket = groups.get(color);
        if (!bucket) { bucket = []; groups.set(color, bucket); }
        bucket.push(index);
      });
      var meshes = [];
      var geometry = new THREE.IcosahedronGeometry(1, tier.sphereDetail);
      var matrix = new THREE.Matrix4();
      var ordered = Array.from(groups.keys()).sort(function (a, b) { return a - b; });
      ordered.forEach(function (color) {
        var indices = groups.get(color);
        var mesh = new THREE.InstancedMesh(geometry, material(color, extra), indices.length);
        indices.forEach(function (atomIndex, slot) {
          var atom = atoms[atomIndex];
          var radius = atomRadius(atom, scale) * (atom.role ? 1.55 : 1);
          matrix.makeScale(radius, radius, radius);
          matrix.setPosition(atom.x, atom.y, atom.z);
          mesh.setMatrixAt(slot, matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;
        mesh.frustumCulled = false;
        meshes.push(mesh);
      });
      return { meshes: meshes, geometry: geometry };
    }

    function instancedBonds(atoms, pairs, radius, color, extra) {
      if (!pairs.length) { return null; }
      var geometry = new THREE.CylinderGeometry(1, 1, 1, tier.bondSegments, 1, true);
      var mesh = new THREE.InstancedMesh(geometry, material(color, extra), pairs.length);
      var start = new THREE.Vector3();
      var end = new THREE.Vector3();
      var direction = new THREE.Vector3();
      var up = new THREE.Vector3(0, 1, 0);
      var quaternion = new THREE.Quaternion();
      var matrix = new THREE.Matrix4();
      var scaleVector = new THREE.Vector3();
      var position = new THREE.Vector3();
      pairs.forEach(function (pair, slot) {
        var from = atoms[pair.fromIndex];
        var to = atoms[pair.toIndex];
        start.set(from.x, from.y, from.z);
        end.set(to.x, to.y, to.z);
        direction.subVectors(end, start);
        var length = direction.length();
        if (length < 1e-6) { length = 1e-6; }
        quaternion.setFromUnitVectors(up, direction.clone().normalize());
        position.addVectors(start, end).multiplyScalar(0.5);
        scaleVector.set(radius, length, radius);
        matrix.compose(position, quaternion, scaleVector);
        mesh.setMatrixAt(slot, matrix);
      });
      mesh.instanceMatrix.needsUpdate = true;
      mesh.frustumCulled = false;
      return { meshes: [mesh], geometry: geometry };
    }

    function chainTubes(scale) {
      var traces = backboneTraces(prepared);
      var group = [];
      var geometries = [];
      Array.from(traces.keys()).sort().forEach(function (chain) {
        var points = traces.get(chain);
        if (points.length < 2) { return; }
        var curve = new THREE.CatmullRomCurve3(points.map(function (atom) {
          return new THREE.Vector3(atom.x, atom.y, atom.z);
        }), false, "catmullrom", 0.35);
        var segments = Math.max(24, Math.min(tier.tubular, points.length * 6));
        var geometry = new THREE.TubeGeometry(curve, segments, scale, tier.radial, false);
        var role = prepared.chainRoles[chain] || "";
        var color = ROLE_COLORS[role] === undefined ? 0x7d8b98 : ROLE_COLORS[role];
        var mesh = new THREE.Mesh(geometry, material(color, { roughness: 0.5 }));
        mesh.frustumCulled = false;
        group.push(mesh);
        geometries.push(geometry);
      });
      return { meshes: group, geometries: geometries };
    }

    function buildRibbon() {
      var group = new THREE.Group();
      var owned = [];
      if (isReal) {
        var tubes = chainTubes(Math.max(0.34, bounds.radius * 0.012));
        tubes.meshes.forEach(function (mesh) { group.add(mesh); });
        var peptideAtoms = prepared.atoms.filter(function (atom) {
          return roleOf(prepared, atom) === "peptide";
        });
        if (peptideAtoms.length) {
          /* The displayed peptide is the subject of the whole report, so it is the only
             chain drawn as ball-and-stick against the backbone tubes. */
          var spheres = instancedSpheres(peptideAtoms, "element", 0.42, {
            roughness: 0.26, metalness: 0.16
          });
          spheres.meshes.forEach(function (mesh) { group.add(mesh); });
          owned.push(spheres.geometry);
          var bonds = instancedBonds(
            peptideAtoms, distanceBonds(peptideAtoms), 0.135, 0xe6edf3, { roughness: 0.42 }
          );
          if (bonds) { bonds.meshes.forEach(function (mesh) { group.add(mesh); }); owned.push(bonds.geometry); }
        }
      } else {
        var trace = chainTubes(0.30);
        trace.meshes.forEach(function (mesh) { group.add(mesh); });
        var measured = prepared.atoms.filter(function (atom) { return atom.role !== "mutation"; });
        var illustrative = prepared.atoms.filter(function (atom) { return atom.role === "mutation"; });
        var beads = instancedSpheres(measured, "chain", 0.72, { roughness: 0.34, metalness: 0.1 });
        beads.meshes.forEach(function (mesh) { group.add(mesh); });
        owned.push(beads.geometry);
        var links = instancedBonds(prepared.atoms, prepared.bondPairs, 0.16, 0xc4d0da, { roughness: 0.5 });
        if (links) { links.meshes.forEach(function (mesh) { group.add(mesh); }); owned.push(links.geometry); }
        if (illustrative.length) {
          /* Idealized geometry is drawn translucent and emissive so a viewer can never
             mistake it for a measured atom position. */
          var ideal = instancedSpheres(illustrative, "chain", 0.95, {
            roughness: 0.16,
            metalness: 0,
            transparent: true,
            opacity: 0.62,
            emissive: new THREE.Color(0xf85149),
            emissiveIntensity: 0.55
          });
          ideal.meshes.forEach(function (mesh) { group.add(mesh); });
          owned.push(ideal.geometry);
        }
      }
      return { group: group, owned: owned };
    }

    function buildAtoms() {
      var group = new THREE.Group();
      var owned = [];
      var spheres = instancedSpheres(prepared.atoms, "element", 0.3, { roughness: 0.34, metalness: 0.12 });
      spheres.meshes.forEach(function (mesh) { group.add(mesh); });
      owned.push(spheres.geometry);
      var pairs = prepared.bondPairs.length > prepared.atoms.length * 0.4 ?
        prepared.bondPairs : distanceBonds(prepared.atoms);
      var bonds = instancedBonds(prepared.atoms, pairs, 0.1, 0xaeb9c4, { roughness: 0.55 });
      if (bonds) { bonds.meshes.forEach(function (mesh) { group.add(mesh); }); owned.push(bonds.geometry); }
      return { group: group, owned: owned, bondCount: pairs.length };
    }

    function representation(mode) {
      if (representations[mode]) { return representations[mode]; }
      var built = mode === "atoms" ? buildAtoms() : buildRibbon();
      representations[mode] = built;
      built.group.visible = false;
      content.add(built.group);
      return built;
    }

    function setMode(mode) {
      if (currentMode === mode) { return; }
      Object.keys(representations).forEach(function (name) {
        representations[name].group.visible = false;
      });
      var built = representation(mode);
      built.group.visible = true;
      currentMode = mode;
      var definition = modeDefinitions.filter(function (item) { return item.id === mode; })[0];
      overlayMode.textContent = definition ? definition.label : mode;
      fig.setStatus(
        (definition ? definition.note : mode) + " · " + prepared.atoms.length +
          " displayed atom positions · quality " + tier.name
      );
      requestRender();
    }

    /* ---------------- camera + loop ---------------- */
    function applyCamera() {
      var phi = Math.max(0.08, Math.min(Math.PI - 0.08, view.phi));
      view.phi = phi;
      var sinPhi = Math.sin(phi);
      camera.position.set(
        view.distance * sinPhi * Math.sin(view.theta),
        view.distance * Math.cos(phi),
        view.distance * sinPhi * Math.cos(view.theta)
      );
      camera.lookAt(0, 0, 0);
    }

    var frameId = 0;
    var lastFrame = 0;
    var lastInteraction = 0;
    var visible = true;
    var mostlyVisible = true;
    var destroyed = false;
    var needsRender = true;
    var measuredSlowFrame = false;

    function now() {
      return global.performance && global.performance.now ?
        global.performance.now() : Date.now();
    }
    lastInteraction = now();

    var renderedWidth = 0;
    var renderedHeight = 0;

    function sizeRenderer() {
      var width = Math.max(240, Math.round(stage.clientWidth || 720));
      var height = Math.max(200, Math.round(stage.clientHeight || 420));
      if (renderedWidth === width && renderedHeight === height) { return; }
      renderedWidth = width;
      renderedHeight = height;
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(1, height);
      camera.updateProjectionMatrix();
    }

    function drawFrame() {
      if (destroyed || !visible) { return; }
      sizeRenderer();
      applyCamera();
      var started = now();
      renderer.render(scene, camera);
      needsRender = false;
      if (!measuredSlowFrame) {
        measuredSlowFrame = true;
        if (now() - started > 34 && renderer.getPixelRatio() > 1) {
          /* Adaptive quality: one measured downgrade for weaker GPUs. */
          renderer.setPixelRatio(1);
          tier.name = tier.name + " (reduced for this device)";
          needsRender = true;
        }
      }
    }

    function cancelLoop() {
      if (frameId) { global.cancelAnimationFrame(frameId); frameId = 0; }
      lastFrame = 0;
    }

    function ensureLoop() {
      if (!frameId && !destroyed && visible) {
        frameId = global.requestAnimationFrame(tick);
      }
    }

    function requestRender() {
      needsRender = true;
      if (reduced) { drawFrame(); } else { ensureLoop(); }
    }

    function tick(timestamp) {
      frameId = 0;
      if (destroyed || !visible) { return; }
      var elapsed = lastFrame ? Math.min(48, timestamp - lastFrame) : 16;
      lastFrame = timestamp;
      var animating = false;

      if (resetTween && !reduced) {
        if (resetTween.started === null) { resetTween.started = timestamp; }
        var progress = Math.min(1, (timestamp - resetTween.started) / RESET_DURATION_MS);
        var eased = 1 - Math.pow(1 - progress, 3);
        view.theta = resetTween.from.theta + (home.theta - resetTween.from.theta) * eased;
        view.phi = resetTween.from.phi + (home.phi - resetTween.from.phi) * eased;
        view.distance = resetTween.from.distance +
          (home.distance - resetTween.from.distance) * eased;
        animating = true;
        if (progress === 1) {
          resetTween = null;
          fig.setStatus("View reset to the default framing.");
        }
      } else if (!dragging && (Math.abs(velocity.theta) > 0.00002 || Math.abs(velocity.phi) > 0.00002)) {
        view.theta += velocity.theta * elapsed;
        view.phi += velocity.phi * elapsed;
        var decay = Math.pow(DAMPING, elapsed / 16);
        velocity.theta *= decay;
        velocity.phi *= decay;
        animating = true;
      } else if (!dragging && !reduced && mostlyVisible &&
        timestamp - lastInteraction > IDLE_DELAY_MS) {
        /* Idle rotation only for the scene the reader is actually looking at, so several
           mounted viewports never compete for the same GPU. */
        view.theta += IDLE_SPIN_RADIANS_PER_MS * elapsed;
        animating = true;
      }

      if (animating || needsRender) { drawFrame(); }
      if (animating || needsRender || (!reduced && mostlyVisible)) { ensureLoop(); }
    }

    /* ---------------- interaction ---------------- */
    var listeners = [];
    var dragging = false;
    var pointers = new Map();
    var pinchDistance = 0;
    var lastPointer = { x: 0, y: 0, time: 0 };

    function listen(target, type, handler, options2) {
      target.addEventListener(type, handler, options2);
      listeners.push(function () { target.removeEventListener(type, handler, options2); });
    }

    function interacted() {
      lastInteraction = now();
      resetTween = null;
    }

    function pointerDown(event) {
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      interacted();
      if (pointers.size === 1) {
        dragging = true;
        velocity = { theta: 0, phi: 0 };
        lastPointer = { x: event.clientX, y: event.clientY, time: now() };
        if (stage.setPointerCapture) {
          try { stage.setPointerCapture(event.pointerId); } catch (error) { /* ignore */ }
        }
      } else if (pointers.size === 2) {
        dragging = false;
        var values = Array.from(pointers.values());
        pinchDistance = Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y);
      }
      ensureLoop();
    }

    function pointerMove(event) {
      if (!pointers.has(event.pointerId)) { return; }
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (pointers.size >= 2) {
        var values = Array.from(pointers.values());
        var distance = Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y);
        if (pinchDistance > 0 && distance > 0) {
          view.distance = Math.max(
            bounds.radius * 0.55, Math.min(bounds.radius * 9, view.distance * pinchDistance / distance)
          );
        }
        pinchDistance = distance;
        interacted();
        requestRender();
        return;
      }
      if (!dragging) { return; }
      var currentTime = now();
      var span = Math.max(8, currentTime - lastPointer.time);
      var deltaX = event.clientX - lastPointer.x;
      var deltaY = event.clientY - lastPointer.y;
      view.theta -= deltaX * 0.0085;
      view.phi -= deltaY * 0.0085;
      velocity = { theta: -deltaX * 0.0085 / span, phi: -deltaY * 0.0085 / span };
      lastPointer = { x: event.clientX, y: event.clientY, time: currentTime };
      lastInteraction = currentTime;
      requestRender();
    }

    function pointerUp(event) {
      pointers.delete(event.pointerId);
      if (pointers.size < 2) { pinchDistance = 0; }
      if (pointers.size === 0) {
        dragging = false;
        lastInteraction = now();
        if (reduced) { velocity = { theta: 0, phi: 0 }; }
        ensureLoop();
      }
    }

    function wheel(event) {
      event.preventDefault();
      interacted();
      velocity = { theta: 0, phi: 0 };
      view.distance = Math.max(
        bounds.radius * 0.55,
        Math.min(bounds.radius * 9, view.distance * Math.exp(event.deltaY * 0.0012))
      );
      requestRender();
    }

    function keyDown(event) {
      var handled = true;
      if (event.key === "ArrowLeft") { view.theta -= 0.13; }
      else if (event.key === "ArrowRight") { view.theta += 0.13; }
      else if (event.key === "ArrowUp") { view.phi -= 0.11; }
      else if (event.key === "ArrowDown") { view.phi += 0.11; }
      else if (event.key === "+" || event.key === "=") { view.distance /= 1.13; }
      else if (event.key === "-" || event.key === "_") { view.distance *= 1.13; }
      else if (event.key === "Home") { reset(); return; }
      else { handled = false; }
      if (!handled) { return; }
      event.preventDefault();
      interacted();
      velocity = { theta: 0, phi: 0 };
      view.distance = Math.max(bounds.radius * 0.55, Math.min(bounds.radius * 9, view.distance));
      requestRender();
    }

    function reset() {
      interacted();
      velocity = { theta: 0, phi: 0 };
      if (reduced) {
        view.theta = home.theta;
        view.phi = home.phi;
        view.distance = home.distance;
        fig.setStatus("View reset to the default framing.");
        requestRender();
        return;
      }
      resetTween = { started: null, from: { theta: view.theta, phi: view.phi, distance: view.distance } };
      ensureLoop();
    }

    listen(stage, "pointerdown", pointerDown);
    listen(stage, "pointermove", pointerMove);
    listen(stage, "pointerup", pointerUp);
    listen(stage, "pointercancel", pointerUp);
    listen(stage, "pointerleave", pointerUp);
    listen(stage, "wheel", wheel, { passive: false });
    listen(stage, "keydown", keyDown);

    var modeButtons = [];
    if (modeDefinitions.length > 1) {
      var group = UI.node("div", "seg");
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", "Molecular representation");
      modeDefinitions.forEach(function (definition) {
        var control = UI.button("seg-item", definition.label);
        control.setAttribute("aria-pressed", "false");
        control.dataset.mode = definition.id;
        group.appendChild(control);
        modeButtons.push(control);
      });
      listen(group, "click", function (event) {
        var target = event.target.closest ? event.target.closest("button[data-mode]") : null;
        if (!target) { return; }
        setMode(target.dataset.mode);
        modeButtons.forEach(function (item) {
          item.setAttribute("aria-pressed", item === target ? "true" : "false");
        });
      });
      fig.addControl(group);
    }
    var resetButton = UI.button("btn btn-quiet", "Reset view");
    resetButton.setAttribute("aria-label", "Reset the molecular view to its default framing");
    listen(resetButton, "click", reset);
    fig.addControl(resetButton);
    fig.hint("drag or swipe to orbit · wheel or ± to zoom · arrows rotate · Home resets");

    /* Legend explains every color channel actually on screen. */
    (function buildLegend() {
      var roles = Object.keys(prepared.chainRoles).sort();
      roles.forEach(function (chain) {
        var role = prepared.chainRoles[chain];
        var color = ROLE_COLORS[role];
        fig.addLegend(
          "#" + (color === undefined ? 0x7d8b98 : color).toString(16).padStart(6, "0"),
          "chain " + chain + " — " + role
        );
      });
      if (isReal) {
        fig.addLegend("#b9c2c9", "peptide atoms colored by element: C grey, N blue, O red, S yellow");
      } else {
        fig.addLegend("#4cc4d1", "P2 and PΩ anchor positions (measured template)");
        fig.addLegend("#f85149", "idealized mutation side-chain endpoint — translucent because it is illustrative", "swatch-illustrative");
      }
    })();

    /* Exact provenance, always available regardless of graphics support. */
    (function buildData() {
      var list = UI.node("dl", "kv");
      function pair(term, value) {
        list.appendChild(UI.node("dt", "", term));
        list.appendChild(UI.node("dd", "", value));
      }
      pair("Truth label", label);
      if (isReal) {
        pair("PDB entry", String(data.pdb_id));
        pair("Experimental method", String(data.method));
        pair("Resolution", String(data.resolution_angstrom) + " Å");
        pair("Citation", String(data.citation));
        pair("Displayed chains", (data.display_chains || []).join(", "));
        pair("Selected atom sites in the packaged entry", String(data.source_selected_atom_sites));
        pair("Atom positions drawn here", String(prepared.atoms.length));
        pair("Report coordinate subset", String(data.report_pdb_subset || ""));
      } else {
        pair("Candidate sequence", String(data.sequence));
        pair("Mutation index (0-based)", String(data.mutation_position));
        pair("Backbone template", "PDB " + String(data.backbone_template.pdb_id) +
          " chain " + String(data.backbone_template.chain) + " " + String(data.backbone_template.atom));
        pair("Template mapping", String(data.backbone_template.mapping));
        pair("Illustrative geometry", String(data.geometry));
      }
      pair(
        "Bond rendering",
        "Explicit packaged connectivity where present; otherwise same-chain, same-or-adjacent-residue " +
          "pairs within " + COVALENT_CUTOFF_ANGSTROM + " Å of the packaged coordinates. Bonds are a " +
          "drawing choice; no coordinate is moved."
      );
      pair(
        "Not represented",
        "No molecular dynamics, docking, affinity simulation, energy minimization, electron density, " +
          "or experimentally measured motion is shown or implied."
      );
      fig.dataBody.appendChild(list);
    })();

    var resizeObserver = null;
    if (global.ResizeObserver) {
      resizeObserver = new global.ResizeObserver(function () { requestRender(); });
      resizeObserver.observe(stage);
    } else {
      listen(global, "resize", function () { requestRender(); });
    }

    var intersectionObserver = null;
    if (global.IntersectionObserver) {
      intersectionObserver = new global.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.target !== stage) { return; }
          visible = entry.isIntersecting && entry.intersectionRatio > 0;
          mostlyVisible = entry.isIntersecting && entry.intersectionRatio >= 0.55;
          if (visible) { lastInteraction = now(); requestRender(); } else { cancelLoop(); }
        });
      }, { threshold: [0, 0.25, 0.55, 0.85, 1] });
      intersectionObserver.observe(stage);
    }

    var unsubscribeMotion = motion.subscribe(function (isReduced) {
      reduced = isReduced;
      velocity = { theta: 0, phi: 0 };
      if (reduced) {
        if (resetTween) {
          view.theta = home.theta;
          view.phi = home.phi;
          view.distance = home.distance;
          resetTween = null;
        }
        cancelLoop();
        drawFrame();
      } else {
        lastInteraction = now();
        ensureLoop();
      }
    });

    setMode(modeDefinitions[0].id);
    if (modeButtons.length) { modeButtons[0].setAttribute("aria-pressed", "true"); }
    drawFrame();
    if (!reduced) { ensureLoop(); }

    function destroy() {
      if (destroyed) { return; }
      destroyed = true;
      cancelLoop();
      listeners.splice(0).forEach(function (remove) { remove(); });
      if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null; }
      if (intersectionObserver) { intersectionObserver.disconnect(); intersectionObserver = null; }
      unsubscribeMotion();
      motion.destroy();
      Object.keys(representations).forEach(function (name) {
        var built = representations[name];
        content.remove(built.group);
        disposeObject(built.group);
        (built.owned || []).forEach(function (geometry) {
          if (geometry && geometry.dispose) { geometry.dispose(); }
        });
        (built.geometries || []).forEach(function (geometry) {
          if (geometry && geometry.dispose) { geometry.dispose(); }
        });
      });
      representations = {};
      scene.remove(content);
      scene.remove(hemisphere);
      scene.remove(keyLight);
      scene.remove(fillLight);
      scene.remove(rimLight);
      scene.remove(ambient);
      hemisphere.dispose();
      keyLight.dispose();
      fillLight.dispose();
      rimLight.dispose();
      ambient.dispose();
      scene.clear();
      renderer.dispose();
      if (renderer.forceContextLoss) {
        try { renderer.forceContextLoss(); } catch (error) { /* ignore */ }
      }
      pointers.clear();
      fig.root.remove();
    }

    return {
      destroy: destroy,
      reset: reset,
      resize: requestRender,
      setMode: setMode,
      engine: "webgl",
      quality: tier.name
    };
  }

  /*
   * Public entry point. WebGL is the intended renderer; when it is unavailable the
   * Canvas 2D projection engine takes over and says so, and that engine in turn always
   * ships a text-and-SVG fallback. No path silently degrades without a label.
   */
  function mountBest(container, data, options) {
    var settings = options || {};
    if (webglSupported()) {
      try {
        return mount(container, data, settings);
      } catch (error) {
        container.replaceChildren();
      }
    }
    var controller = global.KEYHOLE.scene.mount(container, data);
    var notice = global.KEYHOLE.ui.node(
      "p",
      "fig-status",
      "WebGL is unavailable in this browser, so this scene uses the Canvas 2D coordinate " +
        "renderer. The coordinates, chain selection, and truth label are identical."
    );
    container.appendChild(notice);
    return {
      destroy: function () { controller.destroy(); notice.remove(); },
      reset: controller.reset,
      resize: controller.resize,
      setMode: function () { return undefined; },
      engine: "canvas2d",
      quality: "fallback"
    };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.molecule = Object.freeze({
    mount: mountBest,
    mountWebgl: mount,
    supported: webglSupported,
    ROLE_COLORS: ROLE_COLORS,
    ELEMENT_COLORS: ELEMENT_COLORS
  });
})(window);
