/* KEYHOLE accessible offline molecular scene. */
(function (global) {
  "use strict";

  var REAL_PREFIX = "Real crystal structure (PDB ";
  var SCHEMATIC = "Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative";
  var IDLE_DELAY_MS = 3000;
  var AUTO_ROTATE_RADIANS_PER_MS = 0.00008;
  var INERTIA_DECAY_PER_FRAME = 0.92;
  var RESET_DURATION_MS = 460;
  var VISUAL_RADII = { H: 0.31, C: 0.76, N: 0.71, O: 0.66, S: 1.05, P: 1.07, HG: 1.32 };
  var ROLE_COLORS = {
    "HLA heavy chain": "#287d8e",
    "β2-microglobulin": "#4d67b0",
    "peptide": "#e3a72f",
    "TCR α chain": "#cb6659",
    "TCR β chain": "#9b5aa5",
    "candidate peptide schematic": "#e3a72f"
  };
  var ELEMENT_COLORS = {
    C: "#718096", N: "#3157a4", O: "#b43c4b", S: "#c58b16", P: "#8a4fa3", HG: "#6f7780"
  };
  var gradientCache = new Map();

  function escapeXml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[character];
    });
  }

  function truthLabel(data) {
    if (data.truth) { return data.truth; }
    if (data.kind === "pdb") { return REAL_PREFIX + String(data.pdb_id || "unknown") + ")"; }
    return SCHEMATIC;
  }

  function resolveBondPairs(atoms, bonds) {
    var indexBySerial = new Map();
    atoms.forEach(function (atom, index) { indexBySerial.set(atom.serial, index); });
    return bonds.reduce(function (pairs, bond) {
      var fromIndex = indexBySerial.get(bond.from);
      var toIndex = indexBySerial.get(bond.to);
      if (fromIndex !== undefined && toIndex !== undefined && fromIndex !== toIndex) {
        pairs.push({ fromIndex: fromIndex, toIndex: toIndex });
      }
      return pairs;
    }, []);
  }

  function preparedScene(atoms, bonds, chainRoles, stats, source) {
    return {
      atoms: atoms,
      bonds: bonds,
      bondPairs: resolveBondPairs(atoms, bonds),
      chainRoles: chainRoles,
      stats: stats,
      source: source
    };
  }

  function prepare(data) {
    if (!data || (data.kind !== "pdb" && data.kind !== "schematic")) {
      throw new Error("scene payload must be pdb or schematic");
    }
    if (data.kind === "schematic") {
      var schematicAtoms = data.atoms.map(function (atom) {
        return Object.assign({}, atom, { serial: atom.id, record: "ATOM", occupancy: 1 });
      });
      var schematicBonds = data.bonds.map(function (bond) {
        return { from: bond[0], to: bond[1] };
      });
      return preparedScene(
        schematicAtoms,
        schematicBonds,
        data.chain_roles || { C: "candidate peptide schematic" },
        { selectedAtomSites: schematicAtoms.length },
        null
      );
    }
    var parsed = global.KEYHOLE.pdb.parse(data.pdb_text);
    var displayChains = new Set(data.display_chains || Object.keys(parsed.chains));
    var atoms = parsed.atoms.filter(function (atom) {
      return displayChains.has(atom.chain) && atom.record === "ATOM" && !atom.water &&
        atom.element !== "H" && atom.occupancy > 0;
    });
    var serials = new Set(atoms.map(function (atom) { return atom.serial; }));
    var bonds = parsed.bonds.filter(function (bond) {
      return serials.has(bond.from) && serials.has(bond.to);
    });
    return preparedScene(atoms, bonds, data.chain_roles || {}, parsed.stats, parsed);
  }

  function atomColor(atom, chainRoles) {
    if (atom.role === "mutation") { return "#d02f44"; }
    if (atom.role === "anchor") { return "#55cbd3"; }
    var role = chainRoles[atom.chain] || "";
    if (ROLE_COLORS[role]) { return ROLE_COLORS[role]; }
    return ELEMENT_COLORS[atom.element] || "#68717d";
  }

  function visualRadius(atom) {
    var elementRadius = VISUAL_RADII[atom.element] || VISUAL_RADII.C;
    var roleScale = atom.role ? 1.85 : 1;
    return 2.25 * elementRadius / VISUAL_RADII.C * roleScale;
  }

  function sphereSprite(color) {
    if (gradientCache.has(color)) { return gradientCache.get(color); }
    var sprite = document.createElement("canvas");
    sprite.width = 64;
    sprite.height = 64;
    var context = sprite.getContext("2d");
    if (!context) { return null; }
    var gradient = context.createRadialGradient(21, 18, 2, 32, 32, 30);
    gradient.addColorStop(0, "rgba(255,255,255,0.95)");
    gradient.addColorStop(0.2, color);
    gradient.addColorStop(0.72, color);
    gradient.addColorStop(1, "rgba(0,0,0,0.72)");
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(32, 32, 30, 0, Math.PI * 2);
    context.fill();
    gradientCache.set(color, sprite);
    return sprite;
  }

  function depthCues(points) {
    var minimum = Infinity;
    var maximum = -Infinity;
    points.forEach(function (point) {
      minimum = Math.min(minimum, point.z);
      maximum = Math.max(maximum, point.z);
    });
    var span = Math.max(0.000001, maximum - minimum);
    return points.map(function (point) {
      var painterZ = 1 - (point.z - minimum) / span;
      return {
        alpha: 0.5 + painterZ * 0.5,
        radius: 0.82 + painterZ * 0.28,
        painterZ: painterZ
      };
    });
  }

  function drawBackdrop(context, width, height) {
    var radius = Math.max(width, height) * 0.72;
    var backdrop = context.createRadialGradient(
      width * 0.5, height * 0.45, 8,
      width * 0.5, height * 0.45, radius
    );
    backdrop.addColorStop(0, "#173047");
    backdrop.addColorStop(0.48, "#0c1d2c");
    backdrop.addColorStop(1, "#050d15");
    context.fillStyle = backdrop;
    context.fillRect(0, 0, width, height);
  }

  function drawCanvas(context, prepared, view, width, height) {
    var points = global.KEYHOLEProjection.project(prepared.atoms, view, width, height);
    var cues = depthCues(points);
    context.clearRect(0, 0, width, height);
    drawBackdrop(context, width, height);
    context.lineCap = "round";
    prepared.bondPairs.forEach(function (pair) {
      var from = points[pair.fromIndex];
      var to = points[pair.toIndex];
      var cue = (cues[pair.fromIndex].painterZ + cues[pair.toIndex].painterZ) / 2;
      context.strokeStyle = "rgba(202,217,230," + (0.18 + cue * 0.34).toFixed(3) + ")";
      context.lineWidth = Math.max(0.55, (0.75 + cue * 0.8) * (from.scale + to.scale) / 2);
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
    });

    var painterPoints = points.map(function (point, index) {
      return { point: point, cue: cues[index] };
    }).sort(function (left, right) { return right.point.z - left.point.z; });

    painterPoints.forEach(function (entry) {
      var point = entry.point;
      var cue = entry.cue;
      var radius = Math.max(1.15, visualRadius(point.atom) * point.scale * cue.radius);
      var color = atomColor(point.atom, prepared.chainRoles);
      var sprite = sphereSprite(color);
      context.globalAlpha = cue.alpha;
      if (sprite) {
        context.drawImage(sprite, point.x - radius, point.y - radius, radius * 2, radius * 2);
      } else {
        context.fillStyle = color;
        context.beginPath();
        context.arc(point.x, point.y, radius, 0, Math.PI * 2);
        context.fill();
      }
      context.globalAlpha = 1;
      if (point.atom.role === "mutation") {
        [1.5, 2.05].forEach(function (ringScale, index) {
          context.strokeStyle = index === 0 ? "rgba(255,242,168,0.92)" : "rgba(208,47,68,0.48)";
          context.lineWidth = index === 0 ? 1.7 : 1.15;
          context.beginPath();
          context.arc(point.x, point.y, radius * ringScale, 0, Math.PI * 2);
          context.stroke();
        });
      }
    });
  }

  function fallbackAtoms(prepared) {
    var reduced = prepared.atoms.filter(function (atom) {
      var role = prepared.chainRoles[atom.chain] || "";
      return atom.name === "CA" || atom.role || role === "peptide" ||
        role === "candidate peptide schematic";
    });
    return reduced.length ? reduced : prepared.atoms.slice(0, 500);
  }

  function renderSvg(prepared, view, width, height, label) {
    var atoms = fallbackAtoms(prepared);
    var points = global.KEYHOLEProjection.project(atoms, view, width, height);
    var traces = new Map();
    points.forEach(function (point) {
      var role = prepared.chainRoles[point.atom.chain] || point.atom.chain;
      if (!traces.has(role)) { traces.set(role, []); }
      traces.get(role).push(point);
    });
    var body = [];
    traces.forEach(function (tracePoints, role) {
      tracePoints.sort(function (left, right) { return left.atom.serial - right.atom.serial; });
      if (tracePoints.length > 1) {
        body.push('<polyline fill="none" stroke="' +
          escapeXml(ROLE_COLORS[role] || "#81909f") + '" stroke-width="2.4" points="' +
          tracePoints.map(function (point) {
            return point.x.toFixed(1) + "," + point.y.toFixed(1);
          }).join(" ") + '"/>');
      }
      tracePoints.forEach(function (point) {
        var radius = point.atom.role ? 5 : 2.4;
        body.push('<circle cx="' + point.x.toFixed(1) + '" cy="' + point.y.toFixed(1) +
          '" r="' + radius + '" fill="' +
          escapeXml(atomColor(point.atom, prepared.chainRoles)) + '"/>');
      });
    });
    return '<svg class="keyhole-scene-svg" viewBox="0 0 ' + width + " " + height +
      '" role="img" aria-label="Reduced-detail SVG fallback">' +
      "<title>" + escapeXml(label) + "</title>" +
      "<desc>Reduced-detail SVG fallback showing C-alpha traces and peptide atoms by chain role.</desc>" +
      '<rect width="100%" height="100%" fill="#08131e"/>' + body.join("") + "</svg>";
  }

  function legend(data, prepared) {
    var items = [];
    Object.keys(prepared.chainRoles).forEach(function (chain) {
      var role = prepared.chainRoles[chain];
      items.push("Chain " + chain + ": " + role);
    });
    if (data.kind === "pdb" && prepared.source) {
      var sourceSites = Number(data.source_selected_atom_sites || prepared.source.stats.selectedAtomSites);
      items.push(sourceSites +
        " selected atom sites; rendered view omits water, zero-occupancy atoms, and non-display chains");
    }
    return items;
  }

  function mount(container, data) {
    if (!container || typeof container.appendChild !== "function") {
      throw new Error("scene mount requires a DOM container");
    }
    var prepared = prepare(data);
    var label = truthLabel(data);
    var initial = global.KEYHOLEProjection.initialView(prepared.atoms);
    var view = Object.assign({}, initial, { center: Object.assign({}, initial.center) });
    var listeners = [];
    var destroyed = false;
    var dragging = false;
    var pointer = { x: 0, y: 0, time: 0 };
    var velocity = { yaw: 0, pitch: 0 };
    var resetTween = null;
    var frameId = 0;
    var lastFrame = 0;
    var lastInteraction = 0;
    var canvasDirty = true;
    var svgDirty = true;
    var svgSizeKey = "";
    var visible = true;

    var motionQuery = global.matchMedia ?
      global.matchMedia("(prefers-reduced-motion: reduce)") : null;
    var reducedMotion = Boolean(motionQuery && motionQuery.matches);

    function now() {
      return global.performance && global.performance.now ? global.performance.now() : Date.now();
    }
    lastInteraction = now();

    var wrapper = document.createElement("section");
    wrapper.className = "keyhole-scene";
    wrapper.tabIndex = 0;
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("aria-label", label + ". Interactive molecular coordinate view.");

    var badge = document.createElement("strong");
    badge.className = data.kind === "pdb" ? "scene-truth real" : "scene-truth schematic";
    badge.textContent = label;
    wrapper.appendChild(badge);

    var detail = document.createElement("p");
    detail.className = "scene-detail";
    detail.textContent = data.kind === "pdb" ?
      [data.method, data.resolution_angstrom ? data.resolution_angstrom + " Å" : "", data.citation]
        .filter(Boolean).join(" · ") :
      String(data.geometry || "Illustrative residue layout; not a measured or predicted pose.");
    wrapper.appendChild(detail);

    var canvas = document.createElement("canvas");
    canvas.className = "keyhole-scene-canvas";
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.touchAction = "none";
    wrapper.appendChild(canvas);

    var controls = document.createElement("div");
    controls.className = "scene-controls";
    controls.setAttribute("aria-label", "Molecular scene controls");
    var reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = "Reset 3D view";
    reset.setAttribute("aria-label", "Reset molecular scene rotation and zoom");
    controls.appendChild(reset);
    var help = document.createElement("span");
    help.textContent = "Drag to rotate · wheel or +/− to zoom · arrows rotate · Home resets";
    controls.appendChild(help);
    wrapper.appendChild(controls);

    var fallback = document.createElement("details");
    fallback.className = "scene-fallback";
    var summary = document.createElement("summary");
    summary.textContent = "Reduced-detail SVG fallback";
    fallback.appendChild(summary);
    var svgHost = document.createElement("div");
    fallback.appendChild(svgHost);
    wrapper.appendChild(fallback);

    var list = document.createElement("ul");
    list.className = "scene-chain-legend";
    legend(data, prepared).forEach(function (text) {
      var item = document.createElement("li");
      item.textContent = text;
      list.appendChild(item);
    });
    wrapper.appendChild(list);

    var status = document.createElement("p");
    status.className = "scene-status";
    status.setAttribute("aria-live", "polite");
    status.textContent = "Interactive coordinate view ready.";
    wrapper.appendChild(status);
    container.appendChild(wrapper);

    var context = null;
    function dimensions() {
      var width = Math.max(320, Math.round(wrapper.clientWidth || 720));
      var height = Math.max(280, Math.min(560, Math.round(width * 0.62)));
      return { width: width, height: height };
    }

    function sizeCanvas(size) {
      var ratio = Math.min(2, global.devicePixelRatio || 1);
      var pixelWidth = Math.round(size.width * ratio);
      var pixelHeight = Math.round(size.height * ratio);
      if (canvas.width !== pixelWidth) { canvas.width = pixelWidth; }
      if (canvas.height !== pixelHeight) { canvas.height = pixelHeight; }
      if (canvas.style.width !== size.width + "px") { canvas.style.width = size.width + "px"; }
      if (canvas.style.height !== size.height + "px") { canvas.style.height = size.height + "px"; }
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function drawFrame() {
      if (destroyed || !context || !visible) { return; }
      var size = dimensions();
      sizeCanvas(size);
      drawCanvas(context, prepared, view, size.width, size.height);
      canvasDirty = false;
    }

    function refreshSvg(force) {
      if (destroyed || !fallback.open) { return; }
      var size = dimensions();
      var sizeKey = size.width + "x" + size.height;
      if (!force && !svgDirty && svgSizeKey === sizeKey) { return; }
      /* The fallback markup is fully escaped at construction, and it is adopted through
         an XML parse rather than assigned as HTML, so no string can ever become live
         markup or an event handler in this document. */
      svgHost.replaceChildren();
      var markup = renderSvg(prepared, view, size.width, size.height, label);
      var parsed = new global.DOMParser().parseFromString(markup, "image/svg+xml");
      var root = parsed.documentElement;
      if (root && root.nodeName !== "parsererror") {
        svgHost.appendChild(document.importNode(root, true));
      }
      svgSizeKey = sizeKey;
      svgDirty = false;
    }

    function cancelLoop() {
      if (frameId) {
        global.cancelAnimationFrame(frameId);
        frameId = 0;
      }
      lastFrame = 0;
    }

    function ensureLoop() {
      if (!frameId && !destroyed && context && visible && !reducedMotion) {
        frameId = global.requestAnimationFrame(tick);
      }
    }

    function requestCanvas() {
      canvasDirty = true;
      svgDirty = true;
      if (reducedMotion) { drawFrame(); }
      else { ensureLoop(); }
    }

    function finishAnimatedView() {
      if (fallback.open && svgDirty) { refreshSvg(false); }
    }

    function tick(timestamp) {
      frameId = 0;
      if (destroyed || reducedMotion || !visible || !context) { return; }
      var elapsed = lastFrame ? Math.min(40, timestamp - lastFrame) : 16;
      lastFrame = timestamp;
      var animated = false;

      if (resetTween) {
        if (resetTween.started === null) { resetTween.started = timestamp; }
        var progress = Math.min(1, (timestamp - resetTween.started) / RESET_DURATION_MS);
        var eased = 1 - Math.pow(1 - progress, 3);
        view.yaw = resetTween.from.yaw + (initial.yaw - resetTween.from.yaw) * eased;
        view.pitch = resetTween.from.pitch + (initial.pitch - resetTween.from.pitch) * eased;
        view.zoom = resetTween.from.zoom + (initial.zoom - resetTween.from.zoom) * eased;
        animated = true;
        canvasDirty = true;
        svgDirty = true;
        if (progress === 1) {
          resetTween = null;
          status.textContent = "Molecular scene reset.";
          finishAnimatedView();
        }
      } else if (!dragging && (Math.abs(velocity.yaw) > 0.00001 || Math.abs(velocity.pitch) > 0.00001)) {
        view.yaw += velocity.yaw * elapsed;
        view.pitch = global.KEYHOLEProjection.clamp(
          view.pitch + velocity.pitch * elapsed, -Math.PI / 2, Math.PI / 2
        );
        var decay = Math.pow(INERTIA_DECAY_PER_FRAME, elapsed / 16);
        velocity.yaw *= decay;
        velocity.pitch *= decay;
        if (Math.abs(velocity.yaw) <= 0.00001 && Math.abs(velocity.pitch) <= 0.00001) {
          velocity = { yaw: 0, pitch: 0 };
          finishAnimatedView();
        }
        animated = true;
        canvasDirty = true;
        svgDirty = true;
      } else if (!dragging && timestamp - lastInteraction > IDLE_DELAY_MS) {
        view.yaw += AUTO_ROTATE_RADIANS_PER_MS * elapsed;
        animated = true;
        canvasDirty = true;
        svgDirty = true;
      }

      if (canvasDirty || animated) { drawFrame(); }
      ensureLoop();
    }

    function listen(target, type, handler, options) {
      target.addEventListener(type, handler, options);
      listeners.push(function () { target.removeEventListener(type, handler, options); });
    }

    function interact() {
      lastInteraction = now();
      resetTween = null;
    }

    function restore() {
      interact();
      velocity = { yaw: 0, pitch: 0 };
      if (reducedMotion || !context) {
        view.yaw = initial.yaw;
        view.pitch = initial.pitch;
        view.zoom = initial.zoom;
        status.textContent = "Molecular scene reset.";
        requestCanvas();
        refreshSvg(false);
        return;
      }
      resetTween = {
        started: null,
        pausedAt: null,
        from: { yaw: view.yaw, pitch: view.pitch, zoom: view.zoom }
      };
      status.textContent = "Resetting molecular scene.";
      requestCanvas();
    }

    try {
      context = canvas.getContext("2d", { alpha: false });
      if (!context) { throw new Error("Canvas unavailable"); }
    } catch (error) {
      canvas.hidden = true;
      fallback.open = true;
      status.textContent = "Canvas unavailable; showing the reduced-detail SVG view.";
    }

    listen(canvas, "pointerdown", function (event) {
      interact();
      dragging = true;
      velocity = { yaw: 0, pitch: 0 };
      pointer = { x: event.clientX, y: event.clientY, time: now() };
      if (canvas.setPointerCapture) { canvas.setPointerCapture(event.pointerId); }
      ensureLoop();
    });
    listen(canvas, "pointermove", function (event) {
      if (!dragging) { return; }
      var currentTime = now();
      var elapsed = Math.max(8, currentTime - pointer.time);
      var deltaX = event.clientX - pointer.x;
      var deltaY = event.clientY - pointer.y;
      view.yaw += deltaX * 0.008;
      view.pitch = global.KEYHOLEProjection.clamp(
        view.pitch + deltaY * 0.008, -Math.PI / 2, Math.PI / 2
      );
      velocity = {
        yaw: deltaX * 0.008 / elapsed,
        pitch: deltaY * 0.008 / elapsed
      };
      pointer = { x: event.clientX, y: event.clientY, time: currentTime };
      lastInteraction = currentTime;
      requestCanvas();
    });
    function endDrag() {
      if (!dragging) { return; }
      dragging = false;
      lastInteraction = now();
      if (reducedMotion) { velocity = { yaw: 0, pitch: 0 }; }
      refreshSvg(false);
      ensureLoop();
    }
    listen(canvas, "pointerup", endDrag);
    listen(canvas, "pointercancel", function () {
      velocity = { yaw: 0, pitch: 0 };
      endDrag();
    });
    listen(canvas, "wheel", function (event) {
      event.preventDefault();
      interact();
      velocity = { yaw: 0, pitch: 0 };
      view.zoom = global.KEYHOLEProjection.clamp(
        view.zoom * Math.exp(-event.deltaY * 0.001), 0.35, 4.5
      );
      requestCanvas();
      refreshSvg(false);
    }, { passive: false });
    listen(wrapper, "keydown", function (event) {
      var handled = true;
      if (event.key === "ArrowLeft") { view.yaw -= 0.12; }
      else if (event.key === "ArrowRight") { view.yaw += 0.12; }
      else if (event.key === "ArrowUp") { view.pitch -= 0.12; }
      else if (event.key === "ArrowDown") { view.pitch += 0.12; }
      else if (event.key === "+" || event.key === "=") { view.zoom *= 1.12; }
      else if (event.key === "-" || event.key === "_") { view.zoom /= 1.12; }
      else if (event.key === "Home") { restore(); return; }
      else { handled = false; }
      if (handled) {
        event.preventDefault();
        interact();
        velocity = { yaw: 0, pitch: 0 };
        view.zoom = global.KEYHOLEProjection.clamp(view.zoom, 0.35, 4.5);
        view.pitch = global.KEYHOLEProjection.clamp(view.pitch, -Math.PI / 2, Math.PI / 2);
        requestCanvas();
        refreshSvg(false);
      }
    });
    listen(reset, "click", restore);
    listen(fallback, "toggle", function () {
      if (fallback.open) { refreshSvg(true); }
    });

    var resizeObserver = null;
    if (global.ResizeObserver) {
      resizeObserver = new global.ResizeObserver(function () {
        requestCanvas();
        refreshSvg(false);
      });
      resizeObserver.observe(wrapper);
    } else {
      listen(global, "resize", function () {
        requestCanvas();
        refreshSvg(false);
      });
    }

    var intersectionObserver = null;
    if (global.IntersectionObserver) {
      intersectionObserver = new global.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.target !== wrapper) { return; }
          visible = entry.isIntersecting && entry.intersectionRatio > 0;
          if (visible) {
            if (resetTween && resetTween.started !== null && resetTween.pausedAt !== null) {
              resetTween.started += now() - resetTween.pausedAt;
              resetTween.pausedAt = null;
            }
            canvasDirty = true;
            drawFrame();
            ensureLoop();
          } else {
            if (resetTween && resetTween.started !== null && resetTween.pausedAt === null) {
              resetTween.pausedAt = now();
            }
            cancelLoop();
          }
        });
      });
      intersectionObserver.observe(wrapper);
    }

    function motionChanged(event) {
      reducedMotion = event.matches;
      velocity = { yaw: 0, pitch: 0 };
      if (reducedMotion) {
        if (resetTween) {
          view.yaw = initial.yaw;
          view.pitch = initial.pitch;
          view.zoom = initial.zoom;
          status.textContent = "Molecular scene reset.";
          canvasDirty = true;
          svgDirty = true;
        }
        resetTween = null;
        cancelLoop();
        drawFrame();
        refreshSvg(false);
      } else {
        resetTween = null;
        lastInteraction = now();
        ensureLoop();
      }
    }
    if (motionQuery) {
      if (motionQuery.addEventListener) { motionQuery.addEventListener("change", motionChanged); }
      else if (motionQuery.addListener) { motionQuery.addListener(motionChanged); }
    }

    drawFrame();
    refreshSvg(true);
    ensureLoop();

    return {
      reset: restore,
      resize: function () {
        requestCanvas();
        refreshSvg(false);
      },
      renderSvg: function () {
        var size = dimensions();
        return renderSvg(prepared, view, size.width, size.height, label);
      },
      destroy: function () {
        if (destroyed) { return; }
        destroyed = true;
        cancelLoop();
        listeners.splice(0).forEach(function (remove) { remove(); });
        if (resizeObserver) { resizeObserver.disconnect(); }
        if (intersectionObserver) { intersectionObserver.disconnect(); }
        if (motionQuery) {
          if (motionQuery.removeEventListener) {
            motionQuery.removeEventListener("change", motionChanged);
          } else if (motionQuery.removeListener) {
            motionQuery.removeListener(motionChanged);
          }
        }
        wrapper.remove();
      }
    };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.scene = Object.freeze({
    mount: mount,
    prepare: prepare,
    renderSvg: renderSvg,
    truthLabel: truthLabel
  });
})(window);
