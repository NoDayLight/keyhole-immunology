/* KEYHOLE population coverage renderer; never recomputes coverage.
 *
 * Scientific contract: only the serialized AFR/AMR/EAS/EUR marginals and the serialized
 * cohort-weighted ALL_OBSERVED aggregate are shown. ALL_OBSERVED is never plotted on the
 * globe and is never described as worldwide. SAS is absent from the frozen panel and is
 * therefore reported as absent rather than as zero. Exact numbers are always present as
 * text, whether or not any graphics context exists.
 */
(function (global) {
  "use strict";

  var UI = null;
  var ATLAS_TRUTH = "Schematic — data real, geometry illustrative";
  var POPULATIONS = ["AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"];
  var COHORTS = ["AFR", "AMR", "EAS", "EUR"];
  var COHORT_COLORS = {
    AFR: "#e8b45c",
    AMR: "#dd7871",
    EAS: "#66c2d9",
    EUR: "#a394de",
    ALL_OBSERVED: "#8b949e"
  };
  var ILLUSTRATIVE_MARKERS = {
    AFR: { longitude: 21, latitude: 2, color: "#e8b45c" },
    AMR: { longitude: -74, latitude: 5, color: "#dd7871" },
    EAS: { longitude: 112, latitude: 35, color: "#66c2d9" },
    EUR: { longitude: 12, latitude: 52, color: "#a394de" }
  };

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) { element.className = className; }
    if (text !== undefined) { element.textContent = text; }
    return element;
  }

  function projected(longitude, latitude, rotation, radius, centerX, centerY) {
    return global.KEYHOLEProjection.orthographic(
      longitude, latitude, rotation, radius, centerX, centerY
    );
  }

  function render(container, results, selection) {
    UI = global.KEYHOLE.ui;
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
    var globeController = null;
    var barsController = null;
    var menuController = null;
    var unsubscribeSelection = null;
    var useWebglGlobe = global.KEYHOLE.globe.supported();

    /* ------------------------------------------------------------- controls */
    var chooser = node("div", "browser-head");
    var chooserLabel = node("span", "fig-hint", "Candidate peptide");
    var selector = node("select", "");
    selector.id = "atlas-candidate";
    selector.setAttribute("aria-label", "Choose peptide for population coverage");
    keys.forEach(function (key) {
      var option = node("option", "", key);
      option.value = key;
      selector.appendChild(option);
    });
    chooser.appendChild(chooserLabel);
    chooser.appendChild(selector);
    container.appendChild(chooser);

    /* The illustrative globe and the exact bar chart sit side by side, so the picture
       and the numbers it stands for are always read together. */
    var coverageRow = node("div", "split");
    container.appendChild(coverageRow);
    var globeColumn = node("div", "");
    var barsColumn = node("div", "");
    coverageRow.appendChild(globeColumn);
    coverageRow.appendChild(barsColumn);

    /* --------------------------------------------------------- globe figure */
    var globeFig = UI.figure({
      className: "fig-globe",
      label: "Figure 4",
      title: "Where a compatible keyhole has been observed",
      truth: ATLAS_TRUTH,
      truthKind: "schematic",
      description: "Coverage values and cohort labels are serialized results. Marker " +
        "positions are editorial centroids for four cohorts, marker size is a bounded " +
        "display scale, and the geography is presentation only. ALL_OBSERVED is never " +
        "drawn on the globe because it is a cohort-weighted aggregate, not a place.",
      dataSummary: "Marker placement, display scale, and cohort assumptions"
    });
    globeColumn.appendChild(globeFig.root);
    var globeStage = node("div", "globe-stage");
    globeStage.tabIndex = 0;
    globeStage.setAttribute("role", "img");
    globeFig.viewport.appendChild(globeStage);
    var globeStatus = globeFig.status;
    COHORTS.forEach(function (cohort) {
      globeFig.addLegend(COHORT_COLORS[cohort], cohort + " — illustrative centroid marker");
    });
    var resetGlobeButton = UI.button("btn btn-quiet", "Reset globe");
    resetGlobeButton.setAttribute("aria-label", "Reset the population globe rotation");
    globeFig.addControl(resetGlobeButton);
    globeFig.hint("drag or use arrow keys to rotate · Home resets");

    /* ----------------------------------------------------------- bar figure */
    var barsFig = UI.figure({
      className: "fig-coverage-bars",
      label: "Figure 5",
      title: "Exact coverage for the selected candidate",
      truth: "Serialized heuristic Monte Carlo coverage; hatched fills mark every " +
        "heuristic-approximation value",
      truthKind: "schematic",
      description: "The horizontal axis maximum is scaled to the largest plotted value, so " +
        "the exact percentage is printed on every bar. The aggregate row is separated " +
        "because it is a cohort weighting of the four rows above it, not a fifth population.",
      dataSummary: "Serialized coverage, assumptions, and absent populations"
    });
    barsColumn.appendChild(barsFig.root);
    barsFig.addLegend("#8b949e", "hatched fill — heuristic approximation", "swatch-illustrative");

    /* --------------------------------------- exact serialized value tables */
    var tables = node("div", "");
    var coverageBlock = node("div", "");
    coverageBlock.appendChild(node("h3", "", "Exact serialized population coverage"));
    var coverageTable = UI.table(
      ["Population", { label: "Coverage percent", numeric: true }, "Method"], "coverage-table"
    );
    coverageBlock.appendChild(coverageTable.wrap);
    var absence = node(
      "p", "fig-note",
      "SAS is absent because the frozen panel contains no SAS observations; it is not " +
        "reported as zero. HLA alleles outside the 26-model panel are unknown, not invisible."
    );
    coverageBlock.appendChild(absence);
    /* The exact numbers sit directly under the chart that plots them, which also stops
       the right column from ending in a block of empty space. */
    barsColumn.appendChild(coverageBlock);
    var assumptionBlock = node("div", "atlas-assumptions");
    assumptionBlock.appendChild(node("h3", "", "How this coverage was computed"));
    tables.appendChild(assumptionBlock);

    var matrixBlock = node("div", "");
    matrixBlock.appendChild(node("h3", "", "Peptide × modeled allele evidence"));
    matrixBlock.appendChild(node(
      "p", "fig-note",
      "All 26 frozen models are evaluated for population coverage. Only the alleles supplied " +
        "on the command line can affect the verdicts above."
    ));
    var matrixTable = UI.table(
      [
        "Allele", { label: "IC50 nM", numeric: true }, { label: "Rank %", numeric: true },
        "Verdict", "Visible", "Method"
      ],
      "allele-matrix"
    );
    matrixTable.wrap.classList.add("scroll-pane");
    matrixBlock.appendChild(matrixTable.wrap);
    var caveat = node("p", "caveat");
    assumptionBlock.appendChild(caveat);
    container.appendChild(tables);
    container.appendChild(matrixBlock);

    /* ------------------------------------------- Canvas 2D globe fallback */
    var canvas = node("canvas", "population-globe-canvas");
    canvas.tabIndex = 0;
    canvas.setAttribute("role", "img");
    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.height = "410px";
    canvas.style.touchAction = "none";

    var context = null;
    if (!useWebglGlobe) {
      globeStage.appendChild(canvas);
      try {
        context = canvas.getContext("2d", { alpha: false });
        if (!context) { throw new Error("Canvas unavailable"); }
      } catch (error) {
        canvas.hidden = true;
        globeStatus.textContent =
          "No graphics context is available, so the exact numeric coverage below is the " +
          "complete evidence for this figure.";
      }
    }

    var host = globeStage;

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
      context.strokeStyle = "rgba(163,173,182,.2)";
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
        var markerRadius = 6 + Math.min(1, value / 60) * 10;
        context.globalAlpha = 0.72;
        context.fillStyle = marker.color;
        context.beginPath();
        context.arc(point.x, point.y, markerRadius, 0, Math.PI * 2);
        context.fill();
        context.globalAlpha = 1;
        context.strokeStyle = "rgba(237,237,237,.75)";
        context.lineWidth = 1.1;
        context.stroke();
        context.textAlign = "center";
        context.fillStyle = "#ededed";
        context.font = "500 11.5px ui-monospace, SFMono-Regular, Menlo, monospace";
        context.fillText(name + " " + value.toFixed(2) + "%", point.x, point.y - markerRadius - 6);
      });
      context.textAlign = "start";
    }

    function drawGlobe() {
      if (!context || destroyed) { return; }
      var size = dimensions();
      sizeCanvas(size);
      var radius = Math.min(158, size.width * 0.34, (size.height - 70) * 0.45);
      var centerX = size.width / 2;
      var centerY = (size.height - 40) / 2;
      context.fillStyle = "#0a0d10";
      context.fillRect(0, 0, size.width, size.height);

      var sphere = context.createRadialGradient(
        centerX - radius * 0.35, centerY - radius * 0.4, radius * 0.08,
        centerX, centerY, radius
      );
      sphere.addColorStop(0, "#1b2a35");
      sphere.addColorStop(0.72, "#101a22");
      sphere.addColorStop(1, "#0a0d10");
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
      context.strokeStyle = "#2a343d";
      context.lineWidth = 1.4;
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.stroke();

      context.textAlign = "center";
      /* The aggregate is reported as text only. It is never given a location, a marker,
         or a geographic extent, because it is a cohort weighting rather than a place. */
      context.fillStyle = "#a3adb6";
      context.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
      context.fillText(
        "ALL_OBSERVED cohort-weighted coverage: " +
          Number(currentCoverage.ALL_OBSERVED).toFixed(2) + "% (not worldwide)",
        centerX, size.height - 26
      );
      context.fillStyle = "#6f787f";
      context.font = "10.5px ui-monospace, SFMono-Regular, Menlo, monospace";
      context.fillText(
        "illustrative graticule · four cohort markers · ALL_OBSERVED is not drawn on the sphere",
        centerX, size.height - 10
      );
      context.textAlign = "start";
    }

    /* ---------------------------------------------------------- evidence sync */
    function renderBars() {
      if (barsController) { barsController.destroy(); barsController = null; }
      var rows = COHORTS.map(function (cohort) {
        return {
          label: cohort,
          value: Number(currentCoverage[cohort]),
          display: Number(currentCoverage[cohort]).toFixed(4) + "%",
          color: COHORT_COLORS[cohort],
          variant: "hatched",
          group: "Observed cohorts · marginal HLA-A/B frequencies"
        };
      });
      rows.push({
        label: "ALL_OBSERVED",
        value: Number(currentCoverage.ALL_OBSERVED),
        display: Number(currentCoverage.ALL_OBSERVED).toFixed(4) + "%",
        color: COHORT_COLORS.ALL_OBSERVED,
        variant: "hatched",
        group: "Cohort-weighted aggregate of the four rows above · not worldwide"
      });
      barsController = global.KEYHOLE.charts.bars(barsFig.viewport, {
        rows: rows,
        unit: "%",
        labelWidth: 118,
        title: "Serialized population coverage for " + currentKey,
        description: "Percent of sampled genotypes in each observed cohort carrying at least " +
          "one modeled HLA-A or HLA-B allele that displays this candidate.",
        ariaLabel: "Coverage percentages for " + currentKey +
          "; the same values appear in the adjacent table"
      });
      var everyValueZero = rows.every(function (item) { return Number(item.value) === 0; });
      barsFig.setStatus(everyValueZero ?
        "Every serialized cohort value for this candidate is exactly 0%: no sampled genotype " +
          "in any observed cohort carries a modeled allele that displays it." :
        "Values are the serialized per-candidate coverage for " + currentKey + ".");
    }

    function updateEvidence() {
      currentKey = selector.value || keys[0];
      currentCoverage = population.per_candidate_coverage[currentKey];
      globeStage.setAttribute(
        "aria-label",
        "Illustrative globe for candidate " + currentKey +
          "; exact population coverage is listed in the tables below this figure"
      );
      canvas.setAttribute(
        "aria-label",
        "Schematic orthographic globe for " + currentKey +
          "; exact population coverage is available in the following table"
      );
      coverageTable.body.replaceChildren();
      POPULATIONS.forEach(function (name) {
        var row = UI.row(coverageTable.body, [
          name,
          { text: Number(currentCoverage[name]).toFixed(4), className: "numeric" },
          "heuristic approximation"
        ]);
        if (name === "ALL_OBSERVED") { row.classList.add("is-selected"); }
      });

      matrixTable.body.replaceChildren();
      var cells = population.peptide_allele_matrix[currentKey];
      Object.keys(cells).sort().forEach(function (allele) {
        var cell = cells[allele];
        var row = UI.row(matrixTable.body, [
          allele,
          { text: Number(cell.ic50).toFixed(1), className: "numeric" },
          { text: Number(cell.rank).toFixed(2), className: "numeric" },
          cell.verdict,
          { text: cell.visible ? "yes" : "no", className: cell.visible ? "yes" : "no" },
          cell.method
        ]);
        if (cell.visible) { row.classList.add("is-selected"); }
      });
      /* Keep the enhanced menu trigger truthful however the value was set, including the
         programmatic adoption of a selection published before this module subscribed. */
      if (menuController) { menuController.sync(); }
      caveat.textContent = population.meta.assumption + " Seed " + population.meta.seed + "; " +
        population.meta.draws + " draws. ALL_OBSERVED is cohort-weighted, not worldwide coverage. " +
        "SAS is absent; unmodeled HLA alleles are unknown, not invisible.";
      renderBars();
      if (globeController) { globeController.setCoverage(currentCoverage); }
      drawGlobe();
      /* An all-zero candidate is a real result, not a failed render. Say so on the globe
         as well as on the bar chart, so an empty-looking figure is never ambiguous. */
      var allZero = POPULATIONS.every(function (name) {
        return Number(currentCoverage[name]) === 0;
      });
      if (allZero) {
        globeStatus.textContent =
          "Every serialized cohort value for this candidate is exactly 0%, so the markers show " +
          "cohort locations at their base size and none of them grows. No sampled genotype in " +
          "any observed cohort carries a modeled allele that displays this candidate.";
      } else if (globeController) {
        globeStatus.textContent =
          "Marker size is a bounded display scale over the serialized cohort coverage printed " +
          "below. The smallest dot is a location anchor, not a value.";
      }
      if (selection) {
        var index = keys.indexOf(currentKey);
        if (index !== -1) { selection.set(selection.get().index, currentKey, "atlas"); }
      }
    }

    function resetGlobe() {
      rotation.longitude = initialRotation.longitude;
      rotation.latitude = initialRotation.latitude;
      if (globeController) { globeController.reset(); }
      globeStatus.textContent = "Globe rotation reset.";
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
        if (globeController) {
          globeController.rotate(event.key === "ArrowLeft" ? -0.14 : (event.key === "ArrowRight" ? 0.14 : 0));
        }
        drawGlobe();
      }
    }

    function teardown() {
      if (destroyed) { return; }
      destroyed = true;
      selector.removeEventListener("change", updateEvidence);
      resetGlobeButton.removeEventListener("click", resetGlobe);
      canvas.removeEventListener("pointerdown", pointerDown);
      canvas.removeEventListener("pointermove", pointerMove);
      canvas.removeEventListener("pointerup", pointerUp);
      canvas.removeEventListener("pointercancel", pointerUp);
      canvas.removeEventListener("keydown", keyDown);
      globeStage.removeEventListener("keydown", keyDown);
      if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null; }
      if (unsubscribeSelection) { unsubscribeSelection(); unsubscribeSelection = null; }
      if (globeController) { globeController.destroy(); globeController = null; }
      if (barsController) { barsController.destroy(); barsController = null; }
      if (menuController) { menuController.destroy(); menuController = null; }
      container.replaceChildren();
    }

    try {
      selector.addEventListener("change", updateEvidence);
      menuController = UI.selectMenu(selector);
      resetGlobeButton.addEventListener("click", resetGlobe);
      canvas.addEventListener("pointerdown", pointerDown);
      canvas.addEventListener("pointermove", pointerMove);
      canvas.addEventListener("pointerup", pointerUp);
      canvas.addEventListener("pointercancel", pointerUp);
      canvas.addEventListener("keydown", keyDown);
      globeStage.addEventListener("keydown", keyDown);
      if (global.ResizeObserver) {
        resizeObserver = new global.ResizeObserver(function () { drawGlobe(); });
        resizeObserver.observe(globeStage);
      }
      if (useWebglGlobe) {
        try {
          globeController = global.KEYHOLE.globe.mount(globeStage, {
            coverage: population.per_candidate_coverage[currentKey]
          });
          globeStatus.textContent =
            "WebGL globe ready. Marker size is a bounded display scale over the serialized " +
            "cohort coverage printed below.";
        } catch (error) {
          globeController = null;
          useWebglGlobe = false;
        }
      }
      if (!useWebglGlobe && !context) {
        globeStage.appendChild(canvas);
        try {
          context = canvas.getContext("2d", { alpha: false });
          if (context) {
            globeStatus.textContent =
              "WebGL is unavailable, so this figure uses the Canvas 2D orthographic globe. " +
              "The serialized values are identical.";
          }
        } catch (error) {
          context = null;
        }
      }
      if (selection) {
        unsubscribeSelection = selection.subscribe(function (state) {
          if (destroyed || state.origin === "atlas") { return; }
          if (!state.candidateKey || keys.indexOf(state.candidateKey) === -1) { return; }
          if (selector.value === state.candidateKey) { return; }
          selector.value = state.candidateKey;
          /* Dispatching change keeps the enhanced menu label and updateEvidence in step
             from one place. The handler tags its own selection origin, so no loop. */
          selector.dispatchEvent(new Event("change", { bubbles: true }));
        });
        /* Adopt any selection published before this module subscribed. */
        var initial = selection.get().candidateKey;
        if (initial && keys.indexOf(initial) !== -1) { selector.value = initial; }
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
