/* KEYHOLE WebGL coverage globe on the vendored cobe renderer.
 *
 * Scientific contract: marker sizes come only from serialized per-candidate coverage for
 * the four observed cohorts. Landmasses are never tinted by coverage, no marker is ever
 * placed for ALL_OBSERVED, and no marker is placed where the frozen panel has no
 * observations. The geography is decoration around serialized numbers, and the numbers
 * themselves are always available as exact text beside it.
 */
(function (global) {
  "use strict";

  /* Editorial centroids. These are presentation anchors, not measured locations. */
  var COHORT_ANCHORS = [
    { cohort: "AFR", location: [2.0, 21.0], color: [0.94, 0.71, 0.34] },
    { cohort: "AMR", location: [4.6, -74.1], color: [0.87, 0.47, 0.44] },
    { cohort: "EAS", location: [35.0, 112.0], color: [0.40, 0.76, 0.85] },
    { cohort: "EUR", location: [51.5, 12.0], color: [0.64, 0.58, 0.87] }
  ];
  /*
   * The base size is a *location* anchor, not a value. A cohort exists whether or not
   * this candidate has any coverage in it, so a 0% cohort still shows a legible dot and
   * the reader can tell the difference between "zero here" and "nothing rendered".
   * Coverage is encoded only in the growth above that floor.
   */
  var BASE_MARKER_SIZE = 0.038;
  var MAX_MARKER_SIZE = 0.095;
  var SPIN_RADIANS_PER_FRAME = 0.0026;

  var probe = null;

  function supported() {
    if (probe !== null) { return probe; }
    probe = false;
    if (!global.COBE || !global.Phenomenon) { return probe; }
    try {
      var canvas = document.createElement("canvas");
      var context = canvas.getContext("webgl2") ||
        canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (context) {
        probe = true;
        var lose = context.getExtension("WEBGL_lose_context");
        if (lose) { lose.loseContext(); }
      }
    } catch (error) {
      probe = false;
    }
    return probe;
  }

  /*
   * Marker radius is a bounded display scale over the serialized percentage. It is a
   * size channel only; the exact value is always printed in the adjacent bar chart and
   * table, so nobody has to read a number off a sphere.
   */
  function markerSize(percent) {
    var value = Number(percent);
    if (!Number.isFinite(value) || value <= 0) { return BASE_MARKER_SIZE; }
    return BASE_MARKER_SIZE + Math.min(1, value / 60) * (MAX_MARKER_SIZE - BASE_MARKER_SIZE);
  }

  function markersFor(coverage) {
    return COHORT_ANCHORS.map(function (anchor) {
      return {
        location: anchor.location,
        size: markerSize(coverage[anchor.cohort]),
        color: anchor.color
      };
    });
  }

  function mount(host, options) {
    var UI = global.KEYHOLE.ui;
    var settings = options || {};
    if (!supported()) { throw new Error("WebGL globe is unavailable"); }

    var motion = UI.motionWatcher();
    var reduced = motion.reduced;
    var canvas = UI.node("canvas", "globe-canvas");
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.touchAction = "none";
    host.appendChild(canvas);

    var destroyed = false;
    var globe = null;
    var phi = settings.phi === undefined ? 4.1 : settings.phi;
    var theta = 0.28;
    var dragStart = null;
    var pointerPhi = 0;
    var width = 0;
    var height = 0;
    var coverage = settings.coverage || {};
    var markers = markersFor(coverage);
    var listeners = [];

    function listen(target, type, handler, extra) {
      target.addEventListener(type, handler, extra);
      listeners.push(function () { target.removeEventListener(type, handler, extra); });
    }

    /*
     * cobe maps its sphere over a square viewport, so the canvas is kept square and the
     * drawing buffer is sized in device pixels while CSS keeps the layout size.
     */
    function measure() {
      var box = host.getBoundingClientRect();
      var available = Math.round(box.width || 520) - 16;
      var side = Math.max(240, Math.min(520, available));
      width = side;
      height = side;
    }

    function create() {
      measure();
      var ratio = Math.min(2, global.devicePixelRatio || 1);
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      globe = global.COBE(canvas, {
        devicePixelRatio: ratio,
        width: width * ratio,
        height: height * ratio,
        phi: phi,
        theta: theta,
        dark: 1,
        diffuse: 1.25,
        mapSamples: 15000,
        mapBrightness: 5.2,
        mapBaseBrightness: 0.03,
        baseColor: [0.16, 0.2, 0.24],
        markerColor: [0.98, 0.78, 0.36],
        glowColor: [0.19, 0.28, 0.34],
        opacity: 0.95,
        markers: markers,
        onRender: function (state) {
          if (destroyed) { return; }
          if (!reduced && dragStart === null) { phi += SPIN_RADIANS_PER_FRAME; }
          var ratio = Math.min(2, global.devicePixelRatio || 1);
          state.phi = phi;
          state.theta = theta;
          state.width = width * ratio;
          state.height = height * ratio;
          state.markers = markers;
        }
      });
    }

    function rebuild() {
      if (globe) {
        try { globe.destroy(); } catch (error) { /* ignore */ }
        globe = null;
      }
      if (!destroyed) { create(); }
    }

    listen(canvas, "pointerdown", function (event) {
      dragStart = event.clientX;
      pointerPhi = phi;
      canvas.classList.add("is-grabbing");
      if (canvas.setPointerCapture) {
        try { canvas.setPointerCapture(event.pointerId); } catch (error) { /* ignore */ }
      }
    });
    listen(canvas, "pointermove", function (event) {
      if (dragStart === null) { return; }
      phi = pointerPhi + (event.clientX - dragStart) * 0.006;
    });
    function release() {
      dragStart = null;
      canvas.classList.remove("is-grabbing");
    }
    listen(canvas, "pointerup", release);
    listen(canvas, "pointercancel", release);
    listen(canvas, "pointerleave", release);

    /*
     * cobe drives its own continuous animation frame. Left alone it would keep a WebGL
     * context busy while scrolled out of view and even under reduced motion, so rendering
     * is gated on visibility and settled to a static frame when motion is not wanted.
     */
    var running = true;
    var settleTimer = 0;
    var onScreen = true;

    function setRunning(next) {
      if (!globe || destroyed || running === next) { return; }
      running = next;
      if (typeof globe.toggle === "function") { globe.toggle(next); }
    }

    function clearSettle() {
      if (settleTimer) { global.clearTimeout(settleTimer); settleTimer = 0; }
    }

    function scheduleSettle() {
      clearSettle();
      if (!reduced || !onScreen) { return; }
      /* Long enough for the embedded data-URI map texture to load and draw once. */
      settleTimer = global.setTimeout(function () {
        settleTimer = 0;
        setRunning(false);
      }, 1400);
    }

    function wake() {
      if (!onScreen) { return; }
      setRunning(true);
      scheduleSettle();
    }

    var resizeObserver = null;
    if (global.ResizeObserver) {
      var lastWidth = 0;
      resizeObserver = new global.ResizeObserver(function () {
        var box = host.getBoundingClientRect();
        var next = Math.round(box.width || 0);
        if (Math.abs(next - lastWidth) < 8) { return; }
        lastWidth = next;
        rebuild();
        wake();
      });
      resizeObserver.observe(host);
    }

    var intersectionObserver = null;
    if (global.IntersectionObserver) {
      intersectionObserver = new global.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.target !== host) { return; }
          onScreen = entry.isIntersecting && entry.intersectionRatio > 0;
          if (onScreen) { wake(); } else { clearSettle(); setRunning(false); }
        });
      });
      intersectionObserver.observe(host);
    }

    var unsubscribeMotion = motion.subscribe(function (isReduced) {
      reduced = isReduced;
      wake();
    });

    listen(canvas, "pointerdown", wake);
    listen(canvas, "wheel", wake, { passive: true });

    create();
    scheduleSettle();

    return {
      canvas: canvas,
      setCoverage: function (next) {
        coverage = next || {};
        markers = markersFor(coverage);
        wake();
      },
      reset: function () {
        phi = settings.phi === undefined ? 4.1 : settings.phi;
        theta = 0.28;
        wake();
      },
      rotate: function (delta) { phi += delta; wake(); },
      destroy: function () {
        if (destroyed) { return; }
        destroyed = true;
        clearSettle();
        listeners.splice(0).forEach(function (remove) { remove(); });
        if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null; }
        if (intersectionObserver) { intersectionObserver.disconnect(); intersectionObserver = null; }
        unsubscribeMotion();
        motion.destroy();
        if (globe) {
          try { globe.destroy(); } catch (error) { /* ignore */ }
          globe = null;
        }
        canvas.remove();
      }
    };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.globe = Object.freeze({
    COHORT_ANCHORS: COHORT_ANCHORS,
    markerSize: markerSize,
    mount: mount,
    supported: supported
  });
})(window);
