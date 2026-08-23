/* KEYHOLE local 3D projection engine; no third-party runtime or network access. */
(function (global) {
  "use strict";

  function finite(value, fallback) {
    return Number.isFinite(value) ? value : fallback;
  }

  function bounds(atoms) {
    if (!atoms.length) {
      return { center: { x: 0, y: 0, z: 0 }, radius: 1 };
    }
    var min = { x: Infinity, y: Infinity, z: Infinity };
    var max = { x: -Infinity, y: -Infinity, z: -Infinity };
    atoms.forEach(function (atom) {
      min.x = Math.min(min.x, atom.x); max.x = Math.max(max.x, atom.x);
      min.y = Math.min(min.y, atom.y); max.y = Math.max(max.y, atom.y);
      min.z = Math.min(min.z, atom.z); max.z = Math.max(max.z, atom.z);
    });
    var center = {
      x: (min.x + max.x) / 2,
      y: (min.y + max.y) / 2,
      z: (min.z + max.z) / 2
    };
    var radius = 1;
    atoms.forEach(function (atom) {
      var dx = atom.x - center.x;
      var dy = atom.y - center.y;
      var dz = atom.z - center.z;
      radius = Math.max(radius, Math.sqrt(dx * dx + dy * dy + dz * dz));
    });
    return { center: center, radius: radius };
  }

  function initialView(atoms) {
    var box = bounds(atoms);
    return {
      center: box.center,
      radius: box.radius,
      yaw: -0.45,
      pitch: 0.28,
      zoom: 1
    };
  }

  function rotate(atom, view) {
    var x = atom.x - view.center.x;
    var y = atom.y - view.center.y;
    var z = atom.z - view.center.z;
    var cy = Math.cos(view.yaw);
    var sy = Math.sin(view.yaw);
    var cp = Math.cos(view.pitch);
    var sp = Math.sin(view.pitch);
    var x1 = cy * x + sy * z;
    var z1 = -sy * x + cy * z;
    return { x: x1, y: cp * y - sp * z1, z: sp * y + cp * z1 };
  }

  function project(atoms, view, width, height) {
    var size = Math.max(1, Math.min(width, height));
    var scale = size * 0.43 * finite(view.zoom, 1) / Math.max(1, view.radius);
    return atoms.map(function (atom) {
      var point = rotate(atom, view);
      var perspective = 1 / Math.max(0.35, 1 + point.z / (view.radius * 4));
      return {
        atom: atom,
        x: width / 2 + point.x * scale * perspective,
        y: height / 2 - point.y * scale * perspective,
        z: point.z,
        scale: perspective
      };
    });
  }

  function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
  }

  global.KEYHOLEProjection = Object.freeze({
    bounds: bounds,
    clamp: clamp,
    initialView: initialView,
    project: project
  });
})(window);
