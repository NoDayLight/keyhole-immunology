/* KEYHOLE population atlas renderer; never recomputes coverage. */
(function (global) {
  "use strict";

  var ATLAS_TRUTH = "Schematic — data real, geometry illustrative";
  var POPULATIONS = ["AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"];
  var ILLUSTRATIVE_MARKERS = {
    AFR: { longitude: 20, latitude: 2, color: "#e7a94c" },
    AMR: { longitude: -76, latitude: 12, color: "#d8756f" },
    EAS: { longitude: 112, latitude: 35, color: "#65b9cf" },
    EUR: { longitude: 15, latitude: 52, color: "#8f8bd8" }
  };

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) { element.className = className; }
    if (text !== undefined) { element.textContent = text; }
    return element;
  }

  function tableWithHeadings(headings, className) {
    var table = node("table", className || "");
    var head = node("tr", "");
    headings.forEach(function (text) { head.appendChild(node("th", "", text)); });
    var thead = node("thead", "");
    thead.appendChild(head);
    table.appendChild(thead);
    var body = node("tbody", "");
    table.appendChild(body);
    return { table: table, body: body };
  }

  function projected(longitude, latitude, rotation, radius, centerX, centerY) {
    return global.KEYHOLEProjection.orthographic(
      longitude, latitude, rotation, radius, centerX, centerY
    );
  }

  function render(container, results) {
    var population = results.population;
    var keys = Object.keys(population.per_candidate_coverage);
    if (!keys.length) {
      container.textContent = "No population coverage candidates.";
      return { destroy: function () { container.replaceChildren(); } };
    }

    var destroyed = false;
    var dragging = false;
    var pointer = { x: 0, y: 0 };
    var initialRotation = { longitude: -10, latitude: 15 };
    var rotation = { longitude: initialRotation.longitude, latitude: initialRotation.latitude };
    var currentKey = keys[0];
    var currentCoverage = population.per_candidate_coverage[currentKey];
    var resizeObserver = null;

    var selector = node("select", "");
    selector.setAttribute("aria-label", "Choose peptide for population coverage");
    keys.forEach(function (key) {
      var option = node("option", "", key);
      option.value = key;
      selector.appendChild(option);
    });
    container.appendChild(selector);

    var host = node("section", "population-atlas");
    var truth = node("strong", "scene-truth schematic", ATLAS_TRUTH);
    host.appendChild(truth);
    host.appendChild(node(
      "p",
      "scene-detail",
      "Coverage values and cohort labels are real serialized results; marker locations, globe geometry, and graticule are illustrative."
    ));
    var controls = node("div", "scene-controls");
    var reset = node("button", "", "Reset globe");
    reset.type = "button";
    reset.setAttribute("aria-label", "Reset population globe rotation");
    controls.appendChild(reset);
    controls.appendChild(node("span", "", "Drag or use arrow keys to rotate · Home resets"));
    host.appendChild(controls);

    var canvas = node("canvas", "population-globe-canvas");
    canvas.tabIndex = 0;
    canvas.setAttribute("role", "img");
    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.height = "410px";
    canvas.style.margin = ".7rem 0";
    canvas.style.borderRadius = ".75rem";
    canvas.style.touchAction = "none";
    host.appendChild(canvas);

    var canvasStatus = node("p", "scene-status", "Interactive coverage globe ready.");
    canvasStatus.setAttribute("aria-live", "polite");
    host.appendChild(canvasStatus);

    host.appendChild(node("h3", "", "Exact serialized population coverage"));
    var coverageWrap = node("div", "table-wrap");
    var coverageTable = tableWithHeadings(["Population", "Coverage percent"], "coverage-table");
    coverageWrap.appendChild(coverageTable.table);
    host.appendChild(coverageWrap);

    host.appendChild(node("h3", "", "Peptide × modeled allele evidence"));
    var matrixWrap = node("div", "table-wrap");
    var matrixTable = tableWithHeadings(
      ["Allele", "IC50 nM", "Rank %", "Verdict", "Visible", "Method"],
      "allele-matrix"
    );
    matrixWrap.appendChild(matrixTable.table);
    host.appendChild(matrixWrap);
    var caveat = node("p", "caveat");
    host.appendChild(caveat);
    container.appendChild(host);

    var context = null;
    try {
      context = canvas.getContext("2d", { alpha: false });
      if (!context) { throw new Error("Canvas unavailable"); }
    } catch (error) {
      canvas.hidden = true;
      canvasStatus.textContent = "Canvas unavailable; exact numeric coverage remains below.";
    }

    function dimensions() {
      var width = Math.max(1, Math.round(host.clientWidth || 900));
      return {
        width: width,
        height: Math.max(280, Math.min(410, Math.round(width * 0.62)))
      };
    }

    function sizeCanvas(size) {
      var ratio = Math.min(2, global.devicePixelRatio || 1);
      var pixelWidth = Math.round(size.width * ratio);
      var pixelHeight = Math.round(size.height * ratio);
      if (canvas.width !== pixelWidth) { canvas.width = pixelWidth; }
      if (canvas.height !== pixelHeight) { canvas.height = pixelHeight; }
      if (canvas.style.height !== size.height + "px") { canvas.style.height = size.height + "px"; }
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function strokeProjected(points, radius, centerX, centerY) {
      var drawing = false;
      context.beginPath();
      points.forEach(function (coordinates) {
        var point = projected(
          coordinates[0], coordinates[1], rotation, radius, centerX, centerY
        );
        if (!point.visible) {
          drawing = false;
        } else if (!drawing) {
          context.moveTo(point.x, point.y);
          drawing = true;
        } else {
          context.lineTo(point.x, point.y);
        }
      });
      context.stroke();
    }

    function drawGraticule(radius, centerX, centerY) {
      context.strokeStyle = "rgba(174,205,221,.24)";
      context.lineWidth = 1;
      for (var latitude = -60; latitude <= 60; latitude += 30) {
        var parallel = [];
        for (var longitude = -180; longitude <= 180; longitude += 3) {
          parallel.push([longitude, latitude]);
        }
        strokeProjected(parallel, radius, centerX, centerY);
      }
      for (var meridian = -150; meridian <= 180; meridian += 30) {
        var line = [];
        for (var lineLatitude = -90; lineLatitude <= 90; lineLatitude += 3) {
          line.push([meridian, lineLatitude]);
        }
        strokeProjected(line, radius, centerX, centerY);
      }
    }

    function drawMarkers(radius, centerX, centerY) {
      Object.keys(ILLUSTRATIVE_MARKERS).forEach(function (name) {
        var marker = ILLUSTRATIVE_MARKERS[name];
        var point = projected(
          marker.longitude, marker.latitude, rotation, radius, centerX, centerY
        );
        if (!point.visible) { return; }
        var value = Number(currentCoverage[name]);
        var markerRadius = 7 + value * 0.12;
        context.globalAlpha = 0.52 + value * 0.0048;
        context.fillStyle = marker.color;
        context.beginPath();
        context.arc(point.x, point.y, markerRadius, 0, Math.PI * 2);
        context.fill();
        context.globalAlpha = 1;
        context.strokeStyle = "rgba(255,255,255,.82)";
        context.lineWidth = 1.2;
        context.stroke();
        context.textAlign = "center";
        context.fillStyle = "#f4f8fb";
        context.font = "700 12px system-ui, sans-serif";
        context.fillText(name + " " + value.toFixed(2) + "%", point.x, point.y - markerRadius - 7);
      });
      context.textAlign = "start";
    }

    function drawGlobe() {
      if (!context || destroyed) { return; }
      var size = dimensions();
      sizeCanvas(size);
      var radius = Math.min(158, size.width * 0.34, (size.height - 90) * 0.45);
      var centerX = size.width / 2;
      var centerY = (size.height - 58) / 2;
      var background = context.createLinearGradient(0, 0, size.width, size.height);
      background.addColorStop(0, "#07131e");
      background.addColorStop(1, "#10283a");
      context.fillStyle = background;
      context.fillRect(0, 0, size.width, size.height);

      var sphere = context.createRadialGradient(
        centerX - radius * 0.35, centerY - radius * 0.4, radius * 0.08,
        centerX, centerY, radius
      );
      sphere.addColorStop(0, "#214c64");
      sphere.addColorStop(0.72, "#102f44");
      sphere.addColorStop(1, "#07131e");
      context.fillStyle = sphere;
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.fill();
      context.save();
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.clip();
      drawGraticule(radius, centerX, centerY);
      drawMarkers(radius, centerX, centerY);
      context.restore();
      context.strokeStyle = "#6ca9c0";
      context.lineWidth = 2;
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.stroke();

      context.fillStyle = "#eaf2f7";
      context.font = "700 14px system-ui, sans-serif";
      context.textAlign = "center";
      context.fillText("Selected candidate: " + currentKey, centerX, size.height - 34);
      context.fillStyle = "#f3bf4d";
      context.fillText(
        "ALL_OBSERVED cohort-weighted coverage: " +
          Number(currentCoverage.ALL_OBSERVED).toFixed(2) + "% (not worldwide)",
        centerX,
        size.height - 12
      );
      context.textAlign = "start";
    }

    function updateEvidence() {
      currentKey = selector.value || keys[0];
      currentCoverage = population.per_candidate_coverage[currentKey];
      canvas.setAttribute(
        "aria-label",
        "Schematic orthographic globe for " + currentKey +
          "; exact population coverage is available in the following table"
      );
      coverageTable.body.replaceChildren();
      POPULATIONS.forEach(function (name) {
        var row = node("tr", "");
        row.appendChild(node("td", "", name));
        row.appendChild(node("td", "", Number(currentCoverage[name]).toFixed(4)));
        coverageTable.body.appendChild(row);
      });

      matrixTable.body.replaceChildren();
      var cells = population.peptide_allele_matrix[currentKey];
      Object.keys(cells).sort().forEach(function (allele) {
        var cell = cells[allele];
        var row = node("tr", "");
        row.appendChild(node("td", "", allele));
        row.appendChild(node("td", "", Number(cell.ic50).toFixed(1)));
        row.appendChild(node("td", "", Number(cell.rank).toFixed(2)));
        row.appendChild(node("td", "", cell.verdict));
        row.appendChild(node(
          "td", "matrix-cell " + (cell.visible ? "yes" : "no"), cell.visible ? "yes" : "no"
        ));
        row.appendChild(node("td", "", cell.method));
        matrixTable.body.appendChild(row);
      });
      caveat.textContent = population.meta.assumption + " Seed " + population.meta.seed + "; " +
        population.meta.draws + " draws. ALL_OBSERVED is cohort-weighted, not worldwide coverage. " +
        "SAS is absent; unmodeled HLA alleles are unknown, not invisible.";
      drawGlobe();
    }

    function resetGlobe() {
      rotation.longitude = initialRotation.longitude;
      rotation.latitude = initialRotation.latitude;
      canvasStatus.textContent = "Population globe rotation reset.";
      drawGlobe();
    }

    function pointerDown(event) {
      dragging = true;
      pointer = { x: event.clientX, y: event.clientY };
      if (canvas.setPointerCapture) { canvas.setPointerCapture(event.pointerId); }
    }

    function pointerMove(event) {
      if (!dragging) { return; }
      rotation.longitude -= (event.clientX - pointer.x) * 0.45;
      rotation.longitude = ((rotation.longitude + 180) % 360 + 360) % 360 - 180;
      rotation.latitude = global.KEYHOLEProjection.clamp(
        rotation.latitude + (event.clientY - pointer.y) * 0.35, -80, 80
      );
      pointer = { x: event.clientX, y: event.clientY };
      drawGlobe();
    }

    function pointerUp() { dragging = false; }

    function keyDown(event) {
      var handled = true;
      if (event.key === "ArrowLeft") { rotation.longitude += 8; }
      else if (event.key === "ArrowRight") { rotation.longitude -= 8; }
      else if (event.key === "ArrowUp") { rotation.latitude -= 6; }
      else if (event.key === "ArrowDown") { rotation.latitude += 6; }
      else if (event.key === "Home") {
        event.preventDefault();
        resetGlobe();
        return;
      }
      else { handled = false; }
      if (handled) {
        event.preventDefault();
        rotation.latitude = global.KEYHOLEProjection.clamp(rotation.latitude, -80, 80);
        drawGlobe();
      }
    }

    function teardown() {
      if (destroyed) { return; }
      destroyed = true;
      selector.removeEventListener("change", updateEvidence);
      reset.removeEventListener("click", resetGlobe);
      canvas.removeEventListener("pointerdown", pointerDown);
      canvas.removeEventListener("pointermove", pointerMove);
      canvas.removeEventListener("pointerup", pointerUp);
      canvas.removeEventListener("pointercancel", pointerUp);
      canvas.removeEventListener("keydown", keyDown);
      if (resizeObserver) { resizeObserver.disconnect(); }
      container.replaceChildren();
    }

    try {
      selector.addEventListener("change", updateEvidence);
      reset.addEventListener("click", resetGlobe);
      canvas.addEventListener("pointerdown", pointerDown);
      canvas.addEventListener("pointermove", pointerMove);
      canvas.addEventListener("pointerup", pointerUp);
      canvas.addEventListener("pointercancel", pointerUp);
      canvas.addEventListener("keydown", keyDown);
      if (global.ResizeObserver) {
        resizeObserver = new global.ResizeObserver(function () { drawGlobe(); });
        resizeObserver.observe(host);
      }
      updateEvidence();
    } catch (error) {
      teardown();
      throw error;
    }

    return { destroy: teardown };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.atlas = Object.freeze({ render: render });
})(window);
