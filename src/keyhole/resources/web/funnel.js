/* KEYHOLE mutation visibility funnel renderer; consumes serialized values only.
 *
 * Every gate outcome, colour, and count on this page is read from the reason codes and
 * scores that Python already computed. This file never applies a scientific threshold,
 * never invents a candidate, and never draws an unseeded random number: particle lane,
 * delay, speed and size are all derived from the serialized seed and candidate key.
 */
(function (global) {
  "use strict";

  var UI = null;
  var FUNNEL_TRUTH = "Schematic — data real, geometry illustrative";
  var REASON_STAGES = {
    LOW_CLEAVAGE: 0,
    LOW_TAP_TRANSPORT: 1,
    WEAK_BINDING: 2,
    SELF_LIKE: 3
  };
  var REASON_COLORS = {
    LOW_CLEAVAGE: "#f85149",
    LOW_TAP_TRANSPORT: "#e8894a",
    WEAK_BINDING: "#a984d7",
    SELF_LIKE: "#5fa8d3"
  };
  var REASON_TEXT = {
    LOW_CLEAVAGE: "proteasome cleavage below the serialized gate",
    LOW_TAP_TRANSPORT: "TAP transport below the serialized gate",
    WEAK_BINDING: "no supplied allele binds strongly enough",
    SELF_LIKE: "too similar to the sampled self peptidome"
  };
  var STAGES = [
    { name: "Proteasome gate", method: "heuristic approximation", progress: 0.16 },
    { name: "TAP channel", method: "heuristic approximation", progress: 0.40 },
    { name: "HLA keyhole", method: "measured ML", progress: 0.65 },
    { name: "Self-scan", method: "heuristic approximation", progress: 0.87 }
  ];
  var VERDICT_COLORS = {
    VISIBLE_CLEAR: "#3fb950",
    VISIBLE_FAINT: "#d29922",
    INVISIBLE: "#8b949e"
  };
  var FILTERS = [
    ["ALL", "All candidates"],
    ["VISIBLE_CLEAR", "Visible · clear"],
    ["VISIBLE_FAINT", "Visible · faint"],
    ["INVISIBLE", "Invisible"]
  ];

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) { element.className = className; }
    if (text !== undefined) { element.textContent = text; }
    return element;
  }

  function fixed(value, digits) { return Number(value).toFixed(digits); }

  function countFor(candidates, verdict) {
    if (verdict === "ALL") { return candidates.length; }
    return candidates.filter(function (item) { return item.peptide.verdict === verdict; }).length;
  }

  function sequenceNode(peptide) {
    var wrapper = node("div", "seq");
    peptide.seq.split("").forEach(function (residue, index) {
      var span = node("span", index === peptide.position ? "seq-mut" : "seq-res", residue);
      if (index === peptide.position) { span.title = "mutated residue"; }
      wrapper.appendChild(span);
    });
    return wrapper;
  }

  function bestBinding(peptide) {
    var binding = peptide.scores.binding[peptide.best_allele];
    if (!binding) { throw new Error("Missing serialized best-allele binding evidence"); }
    return binding;
  }

  function has(peptide, code) { return peptide.reason_codes.indexOf(code) !== -1; }

  /*
   * Gate ladder derived purely from serialized reason codes. "not reached" means the
   * pipeline short-circuited earlier, so the serialized number exists but this gate
   * never rendered a decision. No threshold is re-applied here.
   */
  function gateEvidence(peptide) {
    var binding = bestBinding(peptide);
    var bindingDecided = has(peptide, "WEAK_BINDING") || has(peptide, "STRONG_BINDING") ||
      has(peptide, "BORDERLINE_BINDING");
    var selfDecided = has(peptide, "SELF_LIKE") || has(peptide, "FOREIGN_LIKE") ||
      has(peptide, "PARTLY_SELF_LIKE");
    var differentialDecided = has(peptide, "MUTANT_BINDS_BETTER") ||
      has(peptide, "LIMITED_DIFFERENTIAL_BINDING") || has(peptide, "NO_WT_COUNTERPART");
    return [
      {
        key: "cleavage",
        label: "Proteasome cleavage",
        short: "Cleavage",
        method: "heuristic approximation",
        display: fixed(peptide.scores.cleavage, 3),
        norm: Math.max(0, Math.min(1, Number(peptide.scores.cleavage))),
        state: has(peptide, "LOW_CLEAVAGE") ? "stopped" : "pass",
        note: "chance the proteasome cuts this exact C-terminus"
      },
      {
        key: "tap",
        label: "TAP transport",
        short: "TAP",
        method: "heuristic approximation",
        display: fixed(peptide.scores.tap, 3),
        norm: Math.max(0, Math.min(1, Number(peptide.scores.tap))),
        state: has(peptide, "LOW_TAP_TRANSPORT") ? "stopped" : "pass",
        note: "chance the fragment reaches the loading compartment"
      },
      {
        key: "binding",
        label: "HLA fit · " + peptide.best_allele,
        short: "HLA fit",
        method: "measured ML",
        display: fixed(binding.rank, 2) + "% rank · " + fixed(binding.ic50, 1) + " nM",
        axis: fixed(binding.rank, 2) + "% rank",
        norm: Math.max(0, 1 - Math.min(1, Number(binding.rank) / 20)),
        state: has(peptide, "WEAK_BINDING") ? "stopped" : (bindingDecided ? "pass" : "unevaluated"),
        note: has(peptide, "STRONG_BINDING") ? "serialized as strong binding" :
          (has(peptide, "BORDERLINE_BINDING") ? "serialized as borderline binding" :
            (bindingDecided ? "" : "gate not reached — processing stopped first"))
      },
      {
        key: "foreignness",
        label: "Unlike sampled self",
        short: "Foreignness",
        method: "heuristic approximation",
        display: fixed(peptide.foreignness, 3),
        norm: Math.max(0, Math.min(1, Number(peptide.foreignness))),
        state: has(peptide, "SELF_LIKE") ? "stopped" : (selfDecided ? "pass" : "unevaluated"),
        note: selfDecided ? "distance to the closest of 500,000 sampled self 9-mers" :
          "gate not reached — an earlier gate stopped this candidate"
      },
      {
        key: "differential",
        label: "Mutant vs wild type",
        short: "Differential",
        method: "heuristic approximation",
        display: has(peptide, "NO_WT_COUNTERPART") ? "no wild-type counterpart" :
          fixed(peptide.agretopicity, 2) + "\u00d7",
        norm: has(peptide, "NO_WT_COUNTERPART") ? 0 :
          Math.max(0, Math.min(1, Number(peptide.agretopicity) / 3)),
        state: has(peptide, "NO_WT_COUNTERPART") ? "unevaluated" :
          (differentialDecided ? "pass" : "unevaluated"),
        note: has(peptide, "MUTANT_BINDS_BETTER") ? "serialized as mutant binding better" :
          (has(peptide, "LIMITED_DIFFERENTIAL_BINDING") ?
            "serialized as limited differential binding" :
            "wild-type IC50 divided by mutant IC50, when a counterpart exists")
      }
    ];
  }

  /* Static serialized stage evidence, built as DOM rather than interpolated markup. */
  function flowSvg(peptide) {
    var binding = bestBinding(peptide);
    var stages = [
      ["Cleavage", fixed(peptide.scores.cleavage * 100, 1) + "%", "heuristic approximation"],
      ["TAP transport", fixed(peptide.scores.tap * 100, 1) + "%", "heuristic approximation"],
      ["HLA fit", fixed(binding.ic50, 1) + " nM · rank " + fixed(binding.rank, 2) + "%", "measured ML"],
      ["Foreignness", fixed(peptide.foreignness, 3), "heuristic approximation"],
      ["Verdict", peptide.verdict.replaceAll("_", " "), "heuristic approximation"]
    ];
    var root = UI.svg("svg", {
      class: "chart flow-svg",
      viewBox: "0 0 920 150",
      role: "img",
      "aria-label": "Five serialized visibility stages"
    });
    root.appendChild(UI.svgText("title", {}, "Visibility funnel for " + peptide.seq));
    root.appendChild(UI.svgText(
      "desc", {},
      "Cleavage, TAP, HLA binding, foreignness, and final verdict. Values are precomputed in Python."
    ));
    stages.forEach(function (stage, index) {
      var x = 10 + index * 181;
      var group = UI.svg("g", {});
      group.appendChild(UI.svg("rect", {
        x: x, y: 22, width: 164, height: 106, rx: 6,
        fill: "#0d1013", stroke: "#262d34"
      }));
      group.appendChild(UI.svgText("text", {
        x: x + 12, y: 48, class: "flow-name"
      }, stage[0]));
      group.appendChild(UI.svgText("text", {
        x: x + 12, y: 76, class: "flow-value"
      }, stage[1]));
      group.appendChild(UI.svgText("text", {
        x: x + 12, y: 104, class: "flow-method"
      }, stage[2]));
      root.appendChild(group);
      if (index < stages.length - 1) {
        root.appendChild(UI.svg("path", {
          d: "M" + (x + 166) + " 75h13", stroke: "#3a444d", "stroke-width": 2
        }));
        root.appendChild(UI.svg("path", {
          d: "M" + (x + 175) + " 70l6 5-6 5", fill: "none", stroke: "#3a444d", "stroke-width": 2
        }));
      }
    });
    return root;
  }

  function mixSeed(seed, key, index) {
    var value = (Number(seed) ^ Math.imul(index + 1, 0x9e3779b1)) >>> 0;
    String(key).split("").forEach(function (character) {
      value ^= character.charCodeAt(0);
      value = Math.imul(value, 16777619) >>> 0;
    });
    value ^= value >>> 16;
    value = Math.imul(value, 2246822507) >>> 0;
    value ^= value >>> 13;
    return value >>> 0;
  }

  function seededUnit(value, salt) {
    var mixed = (value + Math.imul(salt + 1, 2654435761)) >>> 0;
    mixed ^= mixed >>> 15;
    mixed = Math.imul(mixed, 2246822519) >>> 0;
    mixed ^= mixed >>> 13;
    return (mixed >>> 0) / 4294967296;
  }

  function rejectionFor(peptide) {
    for (var index = 0; index < peptide.reason_codes.length; index += 1) {
      var reason = peptide.reason_codes[index];
      if (REASON_STAGES[reason] !== undefined) {
        return { reason: reason, stage: REASON_STAGES[reason], color: REASON_COLORS[reason] };
      }
    }
    return null;
  }

  function buildParticles(candidates, seed) {
    return candidates.map(function (item, index) {
      var mixed = mixSeed(seed, item.peptide.candidate_key, index);
      return {
        item: item,
        index: index,
        delay: seededUnit(mixed, 0) * 1300,
        duration: 6200 + seededUnit(mixed, 1) * 1800,
        lane: (seededUnit(mixed, 2) - 0.5) * 92,
        radius: 3.8 + seededUnit(mixed, 3) * 2.8,
        rejection: rejectionFor(item.peptide)
      };
    });
  }

  function particleState(particle, elapsed, width, height) {
    var local = (elapsed - particle.delay) / particle.duration;
    if (local < 0) { return null; }
    var progress = Math.min(1, local);
    var x = width * (0.05 + progress * 0.90);
    var y = height * 0.58 + particle.lane;
    var alpha = local > 1 ? 0.58 : 1;
    var flash = 0;
    if (particle.rejection) {
      var rejectedAt = STAGES[particle.rejection.stage].progress;
      if (local >= rejectedAt) {
        var fall = Math.min(1, (local - rejectedAt) / 0.18);
        x = width * (0.05 + rejectedAt * 0.90) + fall * 18;
        y += fall * fall * height * 0.52;
        alpha = Math.max(0.2, 1 - fall * 0.76);
        flash = fall < 0.28 ? 1 - fall / 0.28 : 0;
      }
    }
    return { x: x, y: y, alpha: alpha, flash: flash };
  }

  function tooltipText(item) {
    var peptide = item.peptide;
    var binding = bestBinding(peptide);
    return item.mutation.gene + " " + item.mutation.change + " · " + peptide.seq +
      " · cleavage " + fixed(peptide.scores.cleavage, 3) +
      " · TAP " + fixed(peptide.scores.tap, 3) +
      " · " + peptide.best_allele + " " + fixed(binding.ic50, 1) +
      " nM / rank " + fixed(binding.rank, 2) + "%" +
      " · foreignness " + fixed(peptide.foreignness, 3) +
      " · " + peptide.verdict.replaceAll("_", " ") +
      " · reasons " + peptide.reason_codes.join(", ");
  }

  /* Gate attrition counted from serialized reason codes; counting is not thresholding. */
  function gateAttrition(candidates) {
    var stopped = STAGES.map(function () { return 0; });
    candidates.forEach(function (item) {
      var rejection = rejectionFor(item.peptide);
      if (rejection) { stopped[rejection.stage] += 1; }
    });
    var remaining = candidates.length;
    return STAGES.map(function (stage, index) {
      var entering = remaining;
      remaining -= stopped[index];
      return { stage: stage, entering: entering, stopped: stopped[index], leaving: remaining };
    });
  }

  function render(container, results, schematics, selection) {
    UI = global.KEYHOLE.ui;
    var candidates = [];
    results.mutations.forEach(function (mutation, mutationIndex) {
      mutation.peptides.forEach(function (peptide, peptideIndex) {
        candidates.push({
          mutation: mutation,
          peptide: peptide,
          key: mutationIndex + ":" + peptideIndex
        });
      });
    });
    if (!candidates.length) {
      container.textContent = "No screenable peptide candidates.";
      return { destroy: function () {} };
    }

    var destroyed = false;
    var frameId = 0;
    var startTime = null;
    var lastElapsed = 0;
    var lastPositions = [];
    var hoverPoint = null;
    var sceneController = null;
    var radarController = null;
    var currentFallback = null;
    var particles = buildParticles(candidates, results.meta.seed);
    var attrition = gateAttrition(candidates);
    var animationEnd = particles.reduce(function (maximum, particle) {
      var tail = particle.rejection ? Math.max(1, STAGES[particle.rejection.stage].progress + 0.18) : 1;
      return Math.max(maximum, particle.delay + particle.duration * tail);
    }, 0);
    var motionQuery = global.matchMedia ?
      global.matchMedia("(prefers-reduced-motion: reduce)") : null;
    var reducedMotion = Boolean(motionQuery && motionQuery.matches);
    var canvasAvailable = true;
    var fallbackMode = reducedMotion;

    /* ---------------------------------------------------------- witness figure */
    var witnessFig = UI.figure({
      className: "fig-witness",
      label: "Figure 1",
      title: "Every candidate, one particle, four inspection gates",
      truth: FUNNEL_TRUTH,
      truthKind: "schematic",
      description: "One particle represents each real serialized candidate. Scores, gate " +
        "outcomes, rejection colours, and counts are report data; particle paths and timing " +
        "are illustrative.",
      dataSummary: "Gate attrition counted from serialized reason codes"
    });
    witnessFig.viewport.style.position = "relative";
    container.appendChild(witnessFig.root);

    var canvas = node("canvas", "witness-canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute(
      "aria-label",
      "Schematic candidate particles moving through Proteasome, TAP, HLA keyhole, and self-scan stages"
    );
    witnessFig.viewport.appendChild(canvas);

    var tooltip = node("div", "funnel-tooltip");
    tooltip.hidden = true;
    tooltip.setAttribute("role", "status");
    witnessFig.viewport.appendChild(tooltip);

    var replay = UI.button("btn btn-quiet", "Replay candidate flow");
    replay.setAttribute("aria-label", "Replay the deterministic candidate funnel animation");
    witnessFig.addControl(replay);
    witnessFig.hint(candidates.length + " real mutation-derived candidates · seed " + results.meta.seed);
    STAGES.forEach(function (stage, index) {
      witnessFig.addLegend(
        index === 2 ? "#5b9dff" : "#8b949e",
        stage.name + " — " + stage.method
      );
    });
    Object.keys(REASON_COLORS).forEach(function (reason) {
      witnessFig.addLegend(REASON_COLORS[reason], reason.replaceAll("_", " ").toLowerCase() + " rejection");
    });

    var attritionTable = UI.table([
      "Gate", "Method", { label: "Entering", numeric: true },
      { label: "Stopped here", numeric: true }, { label: "Continuing", numeric: true }
    ]);
    attrition.forEach(function (entry) {
      UI.row(attritionTable.body, [
        entry.stage.name,
        entry.stage.method,
        { text: entry.entering, className: "numeric" },
        { text: entry.stopped, className: "numeric" },
        { text: entry.leaving, className: "numeric" }
      ]);
    });
    witnessFig.dataBody.appendChild(attritionTable.wrap);
    witnessFig.dataBody.appendChild(node(
      "p", "fig-note",
      "Attrition is a count of serialized rejection reason codes. Reason codes are produced " +
        "once, in Python; this figure never re-applies a threshold."
    ));

    /* -------------------------------------------------------- candidate browser */
    var browserWrap = node("div", "split split-wide");
    container.appendChild(browserWrap);
    var browserColumn = node("div", "");
    var evidenceColumn = node("div", "");
    browserWrap.appendChild(browserColumn);
    browserWrap.appendChild(evidenceColumn);

    browserColumn.appendChild(node("h3", "", "Choose a candidate"));
    browserColumn.appendChild(node(
      "p", "fig-note",
      "Selecting a candidate here also drives the population coverage figure below."
    ));
    var head = node("div", "browser-head");
    var chips = {};
    FILTERS.forEach(function (definition) {
      var chip = UI.button("chip", definition[1]);
      chip.appendChild(node("span", "count", String(countFor(candidates, definition[0]))));
      chip.setAttribute("aria-pressed", definition[0] === "ALL" ? "true" : "false");
      chip.dataset.verdict = definition[0];
      chips[definition[0]] = chip;
      head.appendChild(chip);
    });
    var search = node("input", "filter-search");
    search.type = "search";
    search.setAttribute("aria-label", "Filter candidates by gene or peptide sequence");
    search.placeholder = "filter by gene or sequence";
    head.appendChild(search);
    browserColumn.appendChild(head);

    var list = node("div", "candidate-list");
    list.setAttribute("role", "listbox");
    list.setAttribute("aria-label", "Mutation-derived peptide candidates");
    browserColumn.appendChild(list);

    var host = node("div", "evidence");
    evidenceColumn.appendChild(host);

    /* The two candidate figures sit side by side at full width so neither column of the
       browser row grows to three times the height of the other. */
    var analysisWrap = node("div", "split");
    var radarHost = node("div", "");
    var sceneHost = node("div", "");
    analysisWrap.appendChild(radarHost);
    analysisWrap.appendChild(sceneHost);
    container.appendChild(analysisWrap);

    /*
     * Open on the first candidate this report calls visible, in serialized order, falling
     * back to the first candidate when nothing is visible. Every candidate stays listed in
     * serialized order and the headline counts are unchanged; this only decides which row
     * is highlighted on load. Landing on a rejected candidate made the coverage figure
     * below read as a broken render rather than as a real 0% result.
     */
    function initialSelection() {
      var order = ["VISIBLE_CLEAR", "VISIBLE_FAINT"];
      for (var tier = 0; tier < order.length; tier += 1) {
        for (var index = 0; index < candidates.length; index += 1) {
          if (candidates[index].peptide.verdict === order[tier]) { return index; }
        }
      }
      return 0;
    }

    var selected = initialSelection();
    var filterVerdict = "ALL";
    var queryText = "";

    function matchesFilter(item) {
      if (filterVerdict !== "ALL" && item.peptide.verdict !== filterVerdict) { return false; }
      if (!queryText) { return true; }
      var haystack = (
        item.mutation.gene + " " + item.mutation.protein_effect + " " +
        item.peptide.seq + " " + item.peptide.wt_seq
      ).toLowerCase();
      return haystack.indexOf(queryText) !== -1;
    }

    function visibleIndices() {
      var indices = [];
      candidates.forEach(function (item, index) {
        if (matchesFilter(item)) { indices.push(index); }
      });
      return indices;
    }

    function renderList() {
      list.replaceChildren();
      var indices = visibleIndices();
      if (!indices.length) {
        list.appendChild(node("p", "fig-status", "No candidates match the current filter."));
        return indices;
      }
      if (indices.indexOf(selected) === -1) { selected = indices[0]; }
      indices.forEach(function (index) {
        var item = candidates[index];
        var row = UI.button("candidate-row", "");
        row.dataset.index = String(index);
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", index === selected ? "true" : "false");
        var gene = node("span", "row-gene", item.mutation.gene);
        gene.appendChild(node("span", "change", item.mutation.protein_effect));
        row.appendChild(gene);
        var binding = bestBinding(item.peptide);
        var meta = node("span", "row-meta");
        meta.appendChild(node(
          "span", "badge " + UI.verdictClass(item.peptide.verdict),
          UI.verdictLabel(item.peptide.verdict)
        ));
        meta.appendChild(node(
          "span", "row-rank", item.peptide.best_allele + " · " + fixed(binding.rank, 2) + "%"
        ));
        row.appendChild(meta);
        var rowSeq = sequenceNode(item.peptide);
        rowSeq.classList.add("row-seq");
        row.appendChild(rowSeq);
        list.appendChild(row);
      });
      return indices;
    }

    function applyFilter() {
      try {
        renderList();
        update();
      } catch (error) { fail(error); }
    }

    var context = null;
    try {
      context = canvas.getContext("2d", { alpha: false });
      if (!context) { throw new Error("Canvas unavailable"); }
    } catch (error) {
      canvasAvailable = false;
      fallbackMode = true;
    }

    function dimensions() {
      return {
        width: Math.max(280, Math.round(witnessFig.viewport.clientWidth || 900)),
        height: 260
      };
    }

    function sizeCanvas(size) {
      var ratio = Math.min(2, global.devicePixelRatio || 1);
      var pixelWidth = Math.round(size.width * ratio);
      var pixelHeight = Math.round(size.height * ratio);
      if (canvas.width !== pixelWidth) { canvas.width = pixelWidth; }
      if (canvas.height !== pixelHeight) { canvas.height = pixelHeight; }
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function drawStages(size) {
      context.fillStyle = "#0a0d10";
      context.fillRect(0, 0, size.width, size.height);
      /* The lane band matches exactly where particles travel; nothing decorative. */
      var laneTop = size.height * 0.58 - 52;
      context.fillStyle = "rgba(91,157,255,.045)";
      context.fillRect(size.width * 0.05, laneTop, size.width * 0.90, 104);
      context.strokeStyle = "rgba(38,45,52,.9)";
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(size.width * 0.05, size.height * 0.58);
      context.lineTo(size.width * 0.95, size.height * 0.58);
      context.stroke();

      STAGES.forEach(function (stage, index) {
        var x = size.width * (0.05 + stage.progress * 0.90);
        var measured = index === 2;
        context.strokeStyle = measured ? "rgba(91,157,255,.55)" : "rgba(120,130,140,.4)";
        context.lineWidth = 1;
        context.setLineDash(measured ? [] : [3, 3]);
        context.beginPath();
        context.moveTo(x, 46);
        context.lineTo(x, size.height - 16);
        context.stroke();
        context.setLineDash([]);
        context.textAlign = "center";
        context.fillStyle = measured ? "#ededed" : "#a3adb6";
        context.font = "500 11.5px ui-sans-serif, system-ui, sans-serif";
        context.fillText(stage.name, x, 22);
        context.fillStyle = measured ? "#5b9dff" : "#6f787f";
        context.font = "9.5px ui-monospace, SFMono-Regular, Menlo, monospace";
        context.fillText(measured ? "measured ML" : "heuristic", x, 36);
        var entry = attrition[index];
        context.fillStyle = "#6f787f";
        context.fillText(
          entry.entering + " in · " + entry.stopped + " stopped", x, size.height - 4
        );
      });
      context.textAlign = "start";
    }

    function drawParticles(elapsed) {
      if (!context || fallbackMode || destroyed) { return; }
      var size = dimensions();
      sizeCanvas(size);
      drawStages(size);
      lastPositions = [];
      particles.forEach(function (particle) {
        var state = particleState(particle, elapsed, size.width, size.height);
        if (!state || state.y > size.height + 20) { return; }
        var rejectionColor = particle.rejection ? particle.rejection.color : null;
        var color = rejectionColor || VERDICT_COLORS[particle.item.peptide.verdict] || "#8b949e";
        var isSelected = particle.index === selected;
        context.globalAlpha = state.alpha;
        context.fillStyle = color;
        context.beginPath();
        context.arc(state.x, state.y, particle.radius, 0, Math.PI * 2);
        context.fill();
        if (isSelected) {
          context.globalAlpha = 1;
          context.strokeStyle = "#ededed";
          context.lineWidth = 1.6;
          context.beginPath();
          context.arc(state.x, state.y, particle.radius + 4.5, 0, Math.PI * 2);
          context.stroke();
        }
        if (state.flash > 0) {
          context.globalAlpha = state.flash;
          context.strokeStyle = color;
          context.lineWidth = 2;
          context.beginPath();
          context.arc(state.x, state.y, particle.radius + 5 + state.flash * 7, 0, Math.PI * 2);
          context.stroke();
        }
        context.globalAlpha = 1;
        lastPositions.push({
          x: state.x,
          y: state.y,
          radius: particle.radius + 7,
          item: particle.item
        });
      });
      if (hoverPoint) { updateTooltip(); }
    }

    function cancelAnimation() {
      if (frameId) {
        global.cancelAnimationFrame(frameId);
        frameId = 0;
      }
    }

    function animationFrame(timestamp) {
      frameId = 0;
      if (destroyed || fallbackMode || !context) { return; }
      try {
        if (startTime === null) { startTime = timestamp; }
        lastElapsed = timestamp - startTime;
        drawParticles(lastElapsed);
        if (lastElapsed <= animationEnd) {
          frameId = global.requestAnimationFrame(animationFrame);
        } else {
          witnessFig.setStatus(
            "Flow complete. " + attrition[STAGES.length - 1].leaving + " of " +
              candidates.length + " candidates reached the final verdict stage."
          );
        }
      } catch (error) {
        fail(error);
      }
    }

    function replayAnimation() {
      cancelAnimation();
      startTime = null;
      lastElapsed = 0;
      tooltip.hidden = true;
      if (!fallbackMode && context) {
        drawParticles(0);
        frameId = global.requestAnimationFrame(animationFrame);
      }
    }

    function syncFallbackMode() {
      fallbackMode = reducedMotion || !canvasAvailable;
      canvas.hidden = fallbackMode;
      replay.disabled = fallbackMode;
      if (currentFallback) { currentFallback.open = fallbackMode; }
      if (fallbackMode) {
        cancelAnimation();
        tooltip.hidden = true;
        witnessFig.setStatus(
          !canvasAvailable ?
            "Canvas is unavailable, so the complete serialized gate evidence is shown instead." :
            "Reduced motion is enabled, so the animation is disabled and the complete serialized " +
              "gate table and stage evidence are shown instead."
        );
        witnessFig.data.open = true;
      } else {
        witnessFig.setStatus("Deterministic flow ready · seed " + results.meta.seed + ".");
      }
    }

    /* ------------------------------------------------------------ evidence view */
    function update() {
      if (sceneController) { sceneController.destroy(); sceneController = null; }
      if (radarController) { radarController.destroy(); radarController = null; }
      host.replaceChildren();
      var item = candidates[selected];
      var peptide = item.peptide;
      var binding = bestBinding(peptide);
      var gates = gateEvidence(peptide);

      var evidenceHead = node("div", "evidence-head");
      evidenceHead.appendChild(node("h3", "", item.mutation.gene + " " + item.mutation.protein_effect));
      evidenceHead.appendChild(node(
        "span", "badge " + UI.verdictClass(peptide.verdict), UI.verdictLabel(peptide.verdict)
      ));
      host.appendChild(evidenceHead);
      host.appendChild(sequenceNode(peptide));
      host.appendChild(node(
        "p", "fig-status",
        "wild type " + (peptide.wt_seq || "not available") +
          " · mutated position " + (Number(peptide.position) + 1) + " of " + peptide.seq.length +
          " · protein start " + peptide.protein_start +
          " · source " + peptide.source
      ));
      host.appendChild(node("p", "verdict-line", peptide.plain_language));

      var gateList = node("ul", "gate-list");
      gates.forEach(function (gate) {
        var stateClass = gate.state === "stopped" ? "is-stop" :
          (gate.state === "pass" ? "is-pass" : "is-skip");
        var entry = node("li", "gate " + stateClass);
        entry.appendChild(node("span", "gate-dot"));
        var name = node("span", "gate-name", gate.label);
        name.appendChild(node("small", "", gate.method + (gate.note ? " · " + gate.note : "")));
        entry.appendChild(name);
        entry.appendChild(node("span", "gate-value", gate.display));
        gateList.appendChild(entry);
      });
      host.appendChild(gateList);

      var reasons = node("p", "fig-status", "serialized reason codes: " + peptide.reason_codes.join(", "));
      host.appendChild(reasons);

      var stageFallback = node("details", "funnel-static-fallback");
      stageFallback.appendChild(node(
        "summary", "", "Static serialized stage evidence (reduced-motion/no-canvas fallback)"
      ));
      var flowHost = node("div", "");
      flowHost.appendChild(flowSvg(peptide));
      stageFallback.appendChild(flowHost);
      host.appendChild(stageFallback);
      currentFallback = stageFallback;

      var alleleTable = UI.table([
        "Supplied allele", { label: "IC50 nM", numeric: true }, { label: "Percentile rank", numeric: true }, "Method"
      ]);
      Object.keys(peptide.scores.binding).sort().forEach(function (allele) {
        var value = peptide.scores.binding[allele];
        UI.row(alleleTable.body, [
          allele + (allele === peptide.best_allele ? " (best)" : ""),
          { text: fixed(value.ic50, 1), className: "numeric" },
          { text: fixed(value.rank, 2), className: "numeric" },
          "measured ML"
        ]);
      });
      var bindingDetails = node("details", "");
      bindingDetails.appendChild(node("summary", "", "Per-allele binding evidence for this candidate"));
      var bindingBody = node("div", "");
      bindingBody.appendChild(alleleTable.wrap);
      bindingDetails.appendChild(bindingBody);
      host.appendChild(bindingDetails);

      /* Radar profile figure. */
      radarHost.replaceChildren();
      sceneHost.replaceChildren();
      var radarFig = UI.figure({
        className: "fig-radar",
        label: "Figure 2",
        title: "Gate evidence profile for " + peptide.seq,
        truth: "Axis positions are bounded display normalisations of the exact serialized " +
          "values printed beside each axis — not a composite score",
        truthKind: "schematic",
        description: "Outward means evidence more favourable to display. A red axis is the " +
          "gate whose serialized reason code stopped this candidate; a grey value marks a " +
          "gate the pipeline never reached.",
        dataSummary: "Axis domains and exact serialized values"
      });
      radarHost.appendChild(radarFig.root);
      radarController = global.KEYHOLE.charts.radar(radarFig.viewport, {
        title: "Gate evidence profile for " + peptide.seq,
        description: "Cleavage, TAP transport, HLA fit, foreignness, and mutant-versus-wild-type " +
          "differential binding for one serialized candidate.",
        ariaLabel: "Gate evidence profile for " + peptide.seq +
          "; exact values are listed in the table below this figure",
        metrics: gates.map(function (gate) {
          return {
            key: gate.key,
            label: gate.short,
            /* Axis labels stay short so they cannot truncate; the gate ladder and the
               data table beneath carry the full serialized value. */
            display: gate.axis === undefined ? gate.display : gate.axis,
            method: gate.method === "measured ML" ? "measured ML" : "heuristic",
            state: gate.state
          };
        }),
        series: [{
          label: peptide.seq,
          color: VERDICT_COLORS[peptide.verdict] || "#8b949e",
          variant: "solid",
          values: gates.reduce(function (values, gate) {
            values[gate.key] = gate.norm;
            return values;
          }, {})
        }]
      });
      var domainTable = UI.table(["Axis", "Serialized value", "Display domain", "Method", "Gate state"]);
      var domains = {
        cleavage: "0 to 1 directly",
        tap: "0 to 1 directly",
        binding: "0 to 20% percentile rank, inverted and clipped",
        foreignness: "0 to 1 directly",
        differential: "0 to 3\u00d7 wild-type/mutant IC50 ratio, clipped"
      };
      gates.forEach(function (gate) {
        UI.row(domainTable.body, [
          gate.label, gate.display, domains[gate.key], gate.method,
          gate.state === "stopped" ? "stopped here" :
            (gate.state === "pass" ? "continued" : "not reached")
        ]);
      });
      radarFig.dataBody.appendChild(domainTable.wrap);

      /* Molecular scene for the selected candidate. */
      sceneController = global.KEYHOLE.molecule.mount(sceneHost, schematics[item.key], {
        label: "Figure 3",
        title: "Candidate " + peptide.seq + " on the measured 1HHK backbone",
        compact: true
      });

      syncFallbackMode();
      if (selection) {
        selection.set(selected, String(peptide.candidate_key), "funnel");
      }
    }

    function updateTooltip() {
      if (!hoverPoint || fallbackMode || !lastPositions.length) {
        tooltip.hidden = true;
        return;
      }
      var nearest = null;
      var nearestDistance = Infinity;
      lastPositions.forEach(function (position) {
        var distance = Math.hypot(position.x - hoverPoint.x, position.y - hoverPoint.y);
        if (distance <= position.radius && distance < nearestDistance) {
          nearest = position;
          nearestDistance = distance;
        }
      });
      if (!nearest) {
        tooltip.hidden = true;
        return;
      }
      tooltip.textContent = tooltipText(nearest.item);
      tooltip.style.left = hoverPoint.left + "px";
      tooltip.style.top = hoverPoint.top + "px";
      tooltip.hidden = false;
    }

    function pointerMove(event) {
      if (fallbackMode || !lastPositions.length) { return; }
      var bounds = canvas.getBoundingClientRect();
      var size = dimensions();
      hoverPoint = {
        x: (event.clientX - bounds.left) * size.width / Math.max(1, bounds.width),
        y: (event.clientY - bounds.top) * size.height / Math.max(1, bounds.height),
        left: Math.min(Math.max(8, bounds.width - 300), Math.max(8, event.clientX - bounds.left + 12)),
        top: Math.max(52, event.clientY - bounds.top - 12)
      };
      updateTooltip();
    }

    function pointerLeave() {
      hoverPoint = null;
      tooltip.hidden = true;
    }

    var resizeObserver = null;
    var unsubscribeSelection = null;

    function teardown() {
      if (destroyed) { return; }
      destroyed = true;
      cancelAnimation();
      list.removeEventListener("click", listClicked);
      list.removeEventListener("keydown", listKeys);
      head.removeEventListener("click", filtersClicked);
      search.removeEventListener("input", searchInput);
      replay.removeEventListener("click", replayClicked);
      canvas.removeEventListener("pointermove", pointerMove);
      canvas.removeEventListener("pointerleave", pointerLeave);
      if (motionQuery) {
        if (motionQuery.removeEventListener) {
          motionQuery.removeEventListener("change", motionChanged);
        } else if (motionQuery.removeListener) {
          motionQuery.removeListener(motionChanged);
        }
      }
      if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null; }
      if (unsubscribeSelection) { unsubscribeSelection(); unsubscribeSelection = null; }
      if (sceneController) { sceneController.destroy(); sceneController = null; }
      if (radarController) { radarController.destroy(); radarController = null; }
      container.replaceChildren();
    }

    function fail(error) {
      teardown();
      var failure = node(
        "div", "fatal",
        "Funnel rendering failed: " + error.message + ". Serialized evidence remains embedded."
      );
      failure.setAttribute("role", "alert");
      container.appendChild(failure);
    }

    function selectIndex(index) {
      if (index === selected) { return; }
      selected = index;
      try { update(); }
      catch (error) { fail(error); return; }
      renderList();
    }

    function listClicked(event) {
      var row = event.target.closest ? event.target.closest("button[data-index]") : null;
      if (!row || !list.contains(row)) { return; }
      selectIndex(Number(row.dataset.index));
    }

    function listKeys(event) {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") { return; }
      var indices = visibleIndices();
      var position = indices.indexOf(selected);
      if (position === -1) { return; }
      var next = event.key === "ArrowDown" ?
        Math.min(indices.length - 1, position + 1) : Math.max(0, position - 1);
      if (next === position) { return; }
      event.preventDefault();
      selectIndex(indices[next]);
      var target = list.querySelector('button[data-index="' + indices[next] + '"]');
      if (target) { target.focus(); }
    }

    function filtersClicked(event) {
      var chip = event.target.closest ? event.target.closest("button[data-verdict]") : null;
      if (!chip || !head.contains(chip)) { return; }
      filterVerdict = chip.dataset.verdict;
      Object.keys(chips).forEach(function (verdict) {
        chips[verdict].setAttribute("aria-pressed", verdict === filterVerdict ? "true" : "false");
      });
      applyFilter();
    }

    function searchInput() {
      queryText = search.value.trim().toLowerCase();
      applyFilter();
    }

    function replayClicked() {
      try { replayAnimation(); }
      catch (error) { fail(error); }
    }

    function motionChanged(event) {
      try {
        reducedMotion = event.matches;
        syncFallbackMode();
        if (!fallbackMode) { replayAnimation(); }
      } catch (error) {
        fail(error);
      }
    }

    try {
      list.addEventListener("click", listClicked);
      list.addEventListener("keydown", listKeys);
      head.addEventListener("click", filtersClicked);
      search.addEventListener("input", searchInput);
      replay.addEventListener("click", replayClicked);
      canvas.addEventListener("pointermove", pointerMove);
      canvas.addEventListener("pointerleave", pointerLeave);
      if (motionQuery) {
        if (motionQuery.addEventListener) {
          motionQuery.addEventListener("change", motionChanged);
        } else if (motionQuery.addListener) {
          motionQuery.addListener(motionChanged);
        }
      }
      if (global.ResizeObserver) {
        resizeObserver = new global.ResizeObserver(function () {
          try {
            if (!fallbackMode && !destroyed) { drawParticles(lastElapsed); }
          } catch (error) {
            fail(error);
          }
        });
        resizeObserver.observe(witnessFig.viewport);
      }
      if (selection) {
        unsubscribeSelection = selection.subscribe(function (state) {
          if (state.origin === "funnel" || destroyed) { return; }
          if (state.index === selected) { return; }
          selected = state.index;
          try { update(); } catch (error) { fail(error); return; }
          renderList();
        });
      }
      renderList();
      update();
      syncFallbackMode();
      if (!fallbackMode) { replayAnimation(); }
    } catch (error) {
      teardown();
      throw error;
    }

    return { destroy: teardown };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.funnel = Object.freeze({ render: render });
})(window);
