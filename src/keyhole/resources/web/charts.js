/* KEYHOLE scientific chart primitives.
 *
 * The composable component shape follows two published React chart designs — the Bklit UI
 * radar chart (RadarGrid / RadarAxis / RadarLabels / RadarArea over a 0-100 value space)
 * and the EvilCharts Recharts bar chart (Grid / XAxis / YAxis / Legend plus per-series
 * `variant`, `barRadius`, and horizontal layout). Both upstreams are React + Recharts/visx
 * component libraries, which cannot run inside this single-file, build-free, render-only
 * offline report, so their structure and visual grammar are reimplemented here as plain
 * accessible SVG. Attribution and the reasoning are recorded in DECISIONS.md.
 *
 * One adaptation carries scientific meaning rather than decoration: the upstream
 * "hatched" bar variant, which upstream uses for projected or incomplete data, is used
 * here for every value produced by a heuristic approximation. Solid fills are reserved
 * for measured-data model output. Nothing here recomputes a scientific value; every
 * number is passed in already serialized.
 */
(function (global) {
  "use strict";

  var uid = 0;

  function nextId(prefix) {
    uid += 1;
    return "keyhole-" + prefix + "-" + uid;
  }

  function defs(root, UI) {
    var element = UI.svg("defs");
    root.appendChild(element);
    return element;
  }

  function hatchPattern(UI, container, id, color) {
    var pattern = UI.svg("pattern", {
      id: id, width: 5, height: 5, patternUnits: "userSpaceOnUse",
      patternTransform: "rotate(45)"
    });
    pattern.appendChild(UI.svg("rect", { width: 5, height: 5, fill: color, "fill-opacity": 0.18 }));
    pattern.appendChild(UI.svg("line", {
      x1: 0, y1: 0, x2: 0, y2: 5, stroke: color, "stroke-width": 2.1
    }));
    container.appendChild(pattern);
    return "url(#" + id + ")";
  }

  /* ------------------------------------------------------------------ radar */
  /*
   * metrics: [{ key, label, short, value, display, method, state, unit }]
   * series:  [{ label, color, values: { key: 0..1 } }]
   * `state` is taken from serialized reason codes only: "stopped" marks the gate that
   * produced the rejection, "unevaluated" marks gates the pipeline never reached.
   */
  function radar(host, options) {
    var UI = global.KEYHOLE.ui;
    var settings = options || {};
    var metrics = settings.metrics || [];
    var series = settings.series || [];
    var levels = settings.levels || 4;
    if (metrics.length < 3) {
      host.appendChild(UI.node("p", "fig-status", "Radar needs at least three metrics."));
      return { destroy: function () { host.replaceChildren(); } };
    }

    var size = 420;
    var margin = 78;
    var center = size / 2;
    var radius = center - margin;
    var root = UI.svg("svg", {
      class: "chart chart-radar",
      viewBox: "0 0 " + size + " " + size,
      role: "img",
      "aria-label": settings.ariaLabel || "Gate evidence profile"
    });
    var definitions = defs(root, UI);
    root.appendChild(UI.svgText("title", {}, settings.title || "Gate evidence profile"));
    root.appendChild(UI.svgText("desc", {}, settings.description || ""));

    function point(index, value) {
      var angle = -Math.PI / 2 + index * 2 * Math.PI / metrics.length;
      var distance = radius * Math.max(0, Math.min(1, value));
      return { x: center + Math.cos(angle) * distance, y: center + Math.sin(angle) * distance, angle: angle };
    }

    /* RadarGrid: concentric level polygons using the shared hairline token. */
    var grid = UI.svg("g", { class: "radar-grid" });
    for (var level = levels; level >= 1; level -= 1) {
      var fraction = level / levels;
      var points = metrics.map(function (metric, index) {
        var located = point(index, fraction);
        return located.x.toFixed(2) + "," + located.y.toFixed(2);
      }).join(" ");
      grid.appendChild(UI.svg("polygon", {
        points: points,
        class: "radar-ring" + (level === levels ? " radar-ring-outer" : "")
      }));
    }
    root.appendChild(grid);

    /* RadarAxis: spokes from the center to each metric. */
    var axes = UI.svg("g", { class: "radar-axes" });
    metrics.forEach(function (metric, index) {
      var outer = point(index, 1);
      axes.appendChild(UI.svg("line", {
        x1: center, y1: center, x2: outer.x.toFixed(2), y2: outer.y.toFixed(2),
        class: "radar-axis" + (metric.state === "stopped" ? " radar-axis-stopped" : "")
      }));
    });
    root.appendChild(axes);

    /* RadarArea: one polygon per series, plus its data points. */
    series.forEach(function (item, seriesIndex) {
      var group = UI.svg("g", { class: "radar-area" });
      var coordinates = metrics.map(function (metric, index) {
        return point(index, Number(item.values[metric.key]) || 0);
      });
      var fill = item.variant === "hatched" ?
        hatchPattern(UI, definitions, nextId("radar-hatch"), item.color) : item.color;
      group.appendChild(UI.svg("polygon", {
        points: coordinates.map(function (located) {
          return located.x.toFixed(2) + "," + located.y.toFixed(2);
        }).join(" "),
        fill: fill,
        "fill-opacity": item.variant === "hatched" ? 1 : 0.2,
        stroke: item.color,
        "stroke-width": 2,
        "stroke-linejoin": "round"
      }));
      coordinates.forEach(function (located, index) {
        group.appendChild(UI.svg("circle", {
          cx: located.x.toFixed(2), cy: located.y.toFixed(2),
          r: metrics[index].state === "stopped" ? 5.4 : 3.6,
          fill: metrics[index].state === "stopped" ? "#f85149" : item.color,
          stroke: "#0a0d10", "stroke-width": 1.6
        }));
      });
      group.setAttribute("data-series", String(seriesIndex));
      root.appendChild(group);
    });

    /* RadarLabels: metric name, exact serialized value, and its method label. */
    var labels = UI.svg("g", { class: "radar-labels" });
    metrics.forEach(function (metric, index) {
      var located = point(index, 1);
      var outward = 1 + 26 / radius;
      var anchorX = center + (located.x - center) * outward;
      var anchorY = center + (located.y - center) * outward;
      var anchor = "middle";
      if (anchorX < center - 8) { anchor = "end"; }
      if (anchorX > center + 8) { anchor = "start"; }
      var name = UI.svgText("text", {
        x: anchorX.toFixed(2), y: anchorY.toFixed(2),
        "text-anchor": anchor, class: "radar-label"
      }, metric.label);
      labels.appendChild(name);
      labels.appendChild(UI.svgText("text", {
        x: anchorX.toFixed(2), y: (anchorY + 15).toFixed(2),
        "text-anchor": anchor,
        class: "radar-value" + (metric.state === "stopped" ? " is-stopped" : "") +
          (metric.state === "unevaluated" ? " is-unevaluated" : "")
      }, metric.display));
      labels.appendChild(UI.svgText("text", {
        x: anchorX.toFixed(2), y: (anchorY + 28).toFixed(2),
        "text-anchor": anchor, class: "radar-method"
      }, metric.method || ""));
    });
    root.appendChild(labels);
    host.appendChild(root);

    return {
      element: root,
      destroy: function () { root.remove(); }
    };
  }

  /* -------------------------------------------------------------------- bars */
  /*
   * rows: [{ label, value, display, variant, tone, note, group }]
   * Horizontal layout: categories on the Y axis, values on the X axis.
   */
  function bars(host, options) {
    var UI = global.KEYHOLE.ui;
    var settings = options || {};
    var rows = settings.rows || [];
    if (!rows.length) {
      host.appendChild(UI.node("p", "fig-status", "No values to plot."));
      return { destroy: function () { host.replaceChildren(); } };
    }
    var maximum = settings.max;
    if (!Number.isFinite(maximum) || maximum <= 0) {
      maximum = rows.reduce(function (best, item) {
        return Math.max(best, Number(item.value) || 0);
      }, 0);
    }
    var ticks = settings.ticks || 4;
    var niceMax = Math.max(1, Math.ceil(maximum / ticks * 1.08) * ticks);

    var rowHeight = 40;
    var gap = 12;
    var labelWidth = settings.labelWidth || 128;
    var padRight = 76;
    var padTop = 22;
    var padBottom = 34;
    var plotWidth = 560;
    var width = labelWidth + plotWidth + padRight;
    var groups = [];
    rows.forEach(function (item) {
      if (!groups.length || groups[groups.length - 1].name !== (item.group || "")) {
        groups.push({ name: item.group || "", rows: [] });
      }
      groups[groups.length - 1].rows.push(item);
    });
    var height = padTop + padBottom + rows.length * (rowHeight + gap) +
      groups.filter(function (item) { return item.name; }).length * 22;

    var root = UI.svg("svg", {
      class: "chart chart-bars",
      viewBox: "0 0 " + width + " " + height,
      preserveAspectRatio: "xMinYMin meet",
      role: "img",
      "aria-label": settings.ariaLabel || "Bar chart of serialized values"
    });
    var definitions = defs(root, UI);
    root.appendChild(UI.svgText("title", {}, settings.title || "Serialized values"));
    root.appendChild(UI.svgText("desc", {}, settings.description || ""));

    function scale(value) {
      return plotWidth * Math.max(0, Math.min(1, (Number(value) || 0) / niceMax));
    }

    /* Grid + XAxis */
    var gridGroup = UI.svg("g", { class: "bars-grid" });
    for (var tick = 0; tick <= ticks; tick += 1) {
      var value = niceMax * tick / ticks;
      var x = labelWidth + scale(value);
      gridGroup.appendChild(UI.svg("line", {
        x1: x.toFixed(1), y1: padTop - 8, x2: x.toFixed(1), y2: height - padBottom + 4,
        class: "bars-gridline" + (tick === 0 ? " bars-baseline" : "")
      }));
      gridGroup.appendChild(UI.svgText("text", {
        x: x.toFixed(1), y: height - padBottom + 20, "text-anchor": "middle", class: "bars-tick"
      }, UI.fixed(value, value >= 10 ? 0 : 1) + (settings.unit || "")));
    }
    root.appendChild(gridGroup);

    var cursorY = padTop;
    groups.forEach(function (group) {
      if (group.name) {
        root.appendChild(UI.svgText("text", {
          x: 0, y: cursorY + 11, class: "bars-group"
        }, group.name));
        cursorY += 22;
      }
      group.rows.forEach(function (item) {
        var barWidth = scale(item.value);
        var fill = item.variant === "hatched" ?
          hatchPattern(UI, definitions, nextId("bar-hatch"), item.color || "#8b949e") :
          (item.color || "#8b949e");
        var rowGroup = UI.svg("g", { class: "bars-row" + (item.tone ? " " + item.tone : "") });
        /* YAxis category label */
        rowGroup.appendChild(UI.svgText("text", {
          x: labelWidth - 12, y: cursorY + rowHeight / 2 + 1,
          "text-anchor": "end", "dominant-baseline": "middle", class: "bars-category"
        }, item.label));
        /* Track keeps a zero-value row visible instead of invisible. */
        rowGroup.appendChild(UI.svg("rect", {
          x: labelWidth, y: cursorY + 6, width: plotWidth, height: rowHeight - 12,
          rx: settings.barRadius === undefined ? 2 : settings.barRadius, class: "bars-track"
        }));
        rowGroup.appendChild(UI.svg("rect", {
          x: labelWidth, y: cursorY + 6,
          width: Math.max(1.5, barWidth).toFixed(1), height: rowHeight - 12,
          rx: settings.barRadius === undefined ? 2 : settings.barRadius,
          fill: fill, stroke: item.color || "#8b949e", "stroke-width": 1, class: "bars-bar"
        }));
        rowGroup.appendChild(UI.svgText("text", {
          x: (labelWidth + barWidth + 10).toFixed(1), y: cursorY + rowHeight / 2 + 1,
          "dominant-baseline": "middle", class: "bars-value"
        }, item.display));
        root.appendChild(rowGroup);
        cursorY += rowHeight + gap;
      });
    });

    host.appendChild(root);
    return {
      element: root,
      destroy: function () { root.remove(); }
    };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.charts = Object.freeze({ bars: bars, radar: radar });
})(window);
