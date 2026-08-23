/* KEYHOLE accessible offline molecular scene. */
(function (global) {
  "use strict";

  var REAL_PREFIX = "Real crystal structure (PDB ";
  var SCHEMATIC = "Schematic — data real, geometry illustrative";
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

  function prepare(data) {
    if (!data || (data.kind !== "pdb" && data.kind !== "schematic")) {
      throw new Error("scene payload must be pdb or schematic");
    }
    if (data.kind === "schematic") {
      var schematicAtoms = data.atoms.map(function (atom) {
        return Object.assign({}, atom, { serial: atom.id, record: "ATOM", occupancy: 1 });
      });
      return {
        atoms: schematicAtoms,
        bonds: data.bonds.map(function (bond) { return { from: bond[0], to: bond[1] }; }),
        chainRoles: data.chain_roles || { C: "candidate peptide schematic" },
        stats: { selectedAtomSites: schematicAtoms.length },
        source: null
      };
    }
    var parsed = global.KEYHOLE.pdb.parse(data.pdb_text);
    var displayChains = new Set(data.display_chains || Object.keys(parsed.chains));
    var atoms = parsed.atoms.filter(function (atom) {
      return displayChains.has(atom.chain) && atom.record === "ATOM" && !atom.water &&
        atom.element !== "H" && atom.occupancy > 0;
    });
    var serials = new Set(atoms.map(function (atom) { return atom.serial; }));
    return {
      atoms: atoms,
      bonds: parsed.bonds.filter(function (bond) {
        return serials.has(bond.from) && serials.has(bond.to);
      }),
      chainRoles: data.chain_roles || {},
      stats: parsed.stats,
      source: parsed
    };
  }

  function atomColor(atom, chainRoles) {
    if (atom.role === "mutation") { return "#d02f44"; }
    var role = chainRoles[atom.chain] || "";
    if (ROLE_COLORS[role]) { return ROLE_COLORS[role]; }
    return ELEMENT_COLORS[atom.element] || "#68717d";
  }

  function projectedMap(prepared, view, width, height) {
    var points = global.KEYHOLEProjection.project(prepared.atoms, view, width, height);
    var bySerial = new Map();
    points.forEach(function (point) { bySerial.set(point.atom.serial, point); });
    return { points: points, bySerial: bySerial };
  }

  function drawCanvas(context, prepared, view, width, height) {
    var projection = projectedMap(prepared, view, width, height);
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#08131e";
    context.fillRect(0, 0, width, height);
    context.lineCap = "round";
    prepared.bonds.forEach(function (bond) {
      var from = projection.bySerial.get(bond.from);
      var to = projection.bySerial.get(bond.to);
      if (!from || !to) { return; }
      context.strokeStyle = "rgba(202, 217, 230, 0.42)";
      context.lineWidth = Math.max(0.65, 1.15 * (from.scale + to.scale) / 2);
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
    });
    projection.points.sort(function (left, right) { return left.z - right.z; });
    projection.points.forEach(function (point) {
      var radius = Math.max(1.2, (point.atom.role ? 5.2 : 2.15) * point.scale);
      context.fillStyle = atomColor(point.atom, prepared.chainRoles);
      context.beginPath();
      context.arc(point.x, point.y, radius, 0, Math.PI * 2);
      context.fill();
      if (point.atom.role === "mutation") {
        context.strokeStyle = "#fff2a8";
        context.lineWidth = 2;
        context.stroke();
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
    var reduced = Object.assign({}, prepared, { atoms: fallbackAtoms(prepared) });
    var projection = projectedMap(reduced, view, width, height);
    var traces = new Map();
    projection.points.forEach(function (point) {
      var role = prepared.chainRoles[point.atom.chain] || point.atom.chain;
      if (!traces.has(role)) { traces.set(role, []); }
      traces.get(role).push(point);
    });
    var body = [];
    traces.forEach(function (points, role) {
      points.sort(function (left, right) { return left.atom.serial - right.atom.serial; });
      if (points.length > 1) {
        body.push('<polyline fill="none" stroke="' +
          escapeXml(ROLE_COLORS[role] || "#81909f") + '" stroke-width="2.4" points="' +
          points.map(function (point) { return point.x.toFixed(1) + "," + point.y.toFixed(1); }).join(" ") + '"/>');
      }
      points.forEach(function (point) {
        var radius = point.atom.role ? 5 : 2.4;
        body.push('<circle cx="' + point.x.toFixed(1) + '" cy="' + point.y.toFixed(1) +
          '" r="' + radius + '" fill="' + escapeXml(atomColor(point.atom, prepared.chainRoles)) + '"/>');
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
      items.push(prepared.source.stats.selectedAtomSites + " selected atom sites; rendered view omits water, zero-occupancy atoms, and non-display chains");
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
    var pointer = { x: 0, y: 0 };

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
      [data.method, data.resolution_angstrom ? data.resolution_angstrom + " Å" : "", data.citation].filter(Boolean).join(" · ") :
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
    function render() {
      if (destroyed) { return; }
      var size = dimensions();
      svgHost.innerHTML = renderSvg(prepared, view, size.width, size.height, label);
      if (!context) { return; }
      var ratio = Math.min(2, global.devicePixelRatio || 1);
      canvas.width = Math.round(size.width * ratio);
      canvas.height = Math.round(size.height * ratio);
      canvas.style.width = size.width + "px";
      canvas.style.height = size.height + "px";
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      drawCanvas(context, prepared, view, size.width, size.height);
    }
    function listen(target, type, handler, options) {
      target.addEventListener(type, handler, options);
      listeners.push(function () { target.removeEventListener(type, handler, options); });
    }
    function restore() {
      view.yaw = initial.yaw;
      view.pitch = initial.pitch;
      view.zoom = initial.zoom;
      status.textContent = "Molecular scene reset.";
      render();
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
      dragging = true;
      pointer = { x: event.clientX, y: event.clientY };
      if (canvas.setPointerCapture) { canvas.setPointerCapture(event.pointerId); }
    });
    listen(canvas, "pointermove", function (event) {
      if (!dragging) { return; }
      view.yaw += (event.clientX - pointer.x) * 0.008;
      view.pitch = global.KEYHOLEProjection.clamp(
        view.pitch + (event.clientY - pointer.y) * 0.008,
        -Math.PI / 2,
        Math.PI / 2
      );
      pointer = { x: event.clientX, y: event.clientY };
      render();
    });
    listen(canvas, "pointerup", function () { dragging = false; });
    listen(canvas, "pointercancel", function () { dragging = false; });
    listen(canvas, "wheel", function (event) {
      event.preventDefault();
      view.zoom = global.KEYHOLEProjection.clamp(
        view.zoom * Math.exp(-event.deltaY * 0.001), 0.35, 4.5
      );
      render();
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
        view.zoom = global.KEYHOLEProjection.clamp(view.zoom, 0.35, 4.5);
        view.pitch = global.KEYHOLEProjection.clamp(view.pitch, -Math.PI / 2, Math.PI / 2);
        render();
      }
    });
    listen(reset, "click", restore);

    var observer = null;
    if (global.ResizeObserver) {
      observer = new global.ResizeObserver(render);
      observer.observe(wrapper);
    } else {
      listen(global, "resize", render);
    }
    render();

    return {
      reset: restore,
      resize: render,
      renderSvg: function () {
        var size = dimensions();
        return renderSvg(prepared, view, size.width, size.height, label);
      },
      destroy: function () {
        if (destroyed) { return; }
        destroyed = true;
        listeners.splice(0).forEach(function (remove) { remove(); });
        if (observer) { observer.disconnect(); }
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
