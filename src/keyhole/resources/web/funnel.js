/* KEYHOLE mutation visibility funnel renderer; consumes serialized values only. */
(function (global) {
  "use strict";

  var FUNNEL_TRUTH = "Schematic — data real, geometry illustrative";
  var REASON_STAGES = {
    LOW_CLEAVAGE: 0,
    LOW_TAP_TRANSPORT: 1,
    WEAK_BINDING: 2,
    SELF_LIKE: 3
  };
  var REASON_COLORS = {
    LOW_CLEAVAGE: "#ec6b76",
    LOW_TAP_TRANSPORT: "#f09a59",
    WEAK_BINDING: "#a984d7",
    SELF_LIKE: "#6aa8c8"
  };
  var STAGES = [
    { name: "Proteasome gate", method: "heuristic approximation", progress: 0.16 },
    { name: "TAP channel", method: "heuristic approximation", progress: 0.40 },
    { name: "HLA keyhole", method: "measured ML", progress: 0.65 },
    { name: "Self-scan", method: "heuristic approximation", progress: 0.87 }
  ];

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) { element.className = className; }
    if (text !== undefined) { element.textContent = text; }
    return element;
  }

  function fixed(value, digits) { return Number(value).toFixed(digits); }

  function sequenceNode(peptide) {
    var wrapper = node("div", "sequence");
    peptide.seq.split("").forEach(function (residue, index) {
      var span = node("span", index === peptide.position ? "mutation-residue" : "", residue);
      if (index === peptide.position) { span.title = "mutated residue"; }
      wrapper.appendChild(span);
    });
    return wrapper;
  }

  function flowSvg(peptide) {
    var binding = peptide.scores.binding[peptide.best_allele];
    if (!binding) { throw new Error("Missing serialized best-allele binding evidence"); }
    var stages = [
      ["Cleavage", fixed(peptide.scores.cleavage * 100, 1) + "%", "heuristic approximation"],
      ["TAP transport", fixed(peptide.scores.tap * 100, 1) + "%", "heuristic approximation"],
      ["HLA fit", fixed(binding.ic50, 1) + " nM · rank " + fixed(binding.rank, 2) + "%", "measured ML"],
      ["Foreignness", fixed(peptide.foreignness, 3), "heuristic approximation"],
      ["Verdict", peptide.verdict.replaceAll("_", " "), "heuristic approximation"]
    ];
    var body = stages.map(function (stage, index) {
      var x = 10 + index * 181;
      var arrow = index < stages.length - 1 ? '<path d="M' + (x + 164) + ' 72h17" stroke="#6e8ca2" stroke-width="3"/><path d="M' + (x + 176) + ' 66l7 6-7 6" fill="none" stroke="#6e8ca2" stroke-width="3"/>' : "";
      return '<g><rect x="' + x + '" y="20" width="164" height="105" rx="12" fill="#102638" stroke="#35556d"/><text x="' + (x + 12) + '" y="47" fill="#eaf2f7" font-size="16" font-weight="700">' + stage[0] + '</text><text x="' + (x + 12) + '" y="74" fill="#f3bf4d" font-size="13">' + stage[1] + '</text><text x="' + (x + 12) + '" y="103" fill="#8fcbd0" font-size="10">' + stage[2] + "</text></g>" + arrow;
    }).join("");
    return '<svg class="flow-svg" viewBox="0 0 920 145" role="img" aria-label="Five serialized visibility stages"><title>Visibility funnel for ' + peptide.seq + "</title><desc>Cleavage, TAP, HLA binding, foreignness, and final verdict. Values are precomputed in Python.</desc>" + body + "</svg>";
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
    var binding = peptide.scores.binding[peptide.best_allele];
    return item.mutation.gene + " " + item.mutation.change + " · " + peptide.seq +
      " · cleavage " + fixed(peptide.scores.cleavage, 3) +
      " · TAP " + fixed(peptide.scores.tap, 3) +
      " · " + peptide.best_allele + " " + fixed(binding.ic50, 1) +
      " nM / rank " + fixed(binding.rank, 2) + "%" +
      " · foreignness " + fixed(peptide.foreignness, 3) +
      " · " + peptide.verdict.replaceAll("_", " ") +
      " · reasons " + peptide.reason_codes.join(", ");
  }

  function render(container, results, schematics) {
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
    var currentFallback = null;
    var particles = buildParticles(candidates, results.meta.seed);
    var animationEnd = particles.reduce(function (maximum, particle) {
      var tail = particle.rejection ? Math.max(1, STAGES[particle.rejection.stage].progress + 0.18) : 1;
      return Math.max(maximum, particle.delay + particle.duration * tail);
    }, 0);
    var motionQuery = global.matchMedia ?
      global.matchMedia("(prefers-reduced-motion: reduce)") : null;
    var reducedMotion = Boolean(motionQuery && motionQuery.matches);
    var canvasAvailable = true;
    var fallbackMode = reducedMotion;

    var witness = node("section", "funnel-witness");
    witness.style.position = "relative";
    var truth = node("strong", "scene-truth schematic", FUNNEL_TRUTH);
    witness.appendChild(truth);
    witness.appendChild(node(
      "p",
      "scene-detail",
      "One particle represents each real serialized candidate; scores, reasons, and outcomes are real report data, while paths and timing are illustrative."
    ));
    var witnessControls = node("div", "scene-controls");
    var replay = node("button", "", "Replay candidate flow");
    replay.type = "button";
    replay.setAttribute("aria-label", "Replay the deterministic candidate funnel animation");
    witnessControls.appendChild(replay);
    witnessControls.appendChild(node(
      "span", "", candidates.length + " real mutation-derived peptide candidates · seed " + results.meta.seed
    ));
    witness.appendChild(witnessControls);

    var canvas = node("canvas", "funnel-particle-canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute(
      "aria-label",
      "Schematic candidate particles moving through Proteasome, TAP, HLA keyhole, and self-scan stages"
    );
    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.height = "280px";
    canvas.style.borderRadius = ".75rem";
    canvas.style.marginTop = ".7rem";
    witness.appendChild(canvas);

    var tooltip = node("div", "funnel-tooltip");
    tooltip.hidden = true;
    tooltip.setAttribute("role", "status");
    tooltip.style.position = "absolute";
    tooltip.style.zIndex = "4";
    tooltip.style.maxWidth = "min(36rem, 90%)";
    tooltip.style.padding = ".45rem .6rem";
    tooltip.style.border = "1px solid #6e8ca2";
    tooltip.style.borderRadius = ".45rem";
    tooltip.style.background = "#07111bf2";
    tooltip.style.pointerEvents = "none";
    witness.appendChild(tooltip);
    container.appendChild(witness);

    var select = node("select", "candidate-select");
    select.setAttribute("aria-label", "Choose mutation-derived peptide");
    candidates.forEach(function (item, index) {
      var option = node(
        "option", "", item.mutation.gene + " " + item.mutation.protein_effect + " · " + item.peptide.seq
      );
      option.value = String(index);
      select.appendChild(option);
    });
    container.appendChild(select);
    var host = node("div", "candidate-detail");
    container.appendChild(host);

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
        width: Math.max(560, Math.round(witness.clientWidth || 920)),
        height: 280
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
      var background = context.createLinearGradient(0, 0, size.width, size.height);
      background.addColorStop(0, "#081722");
      background.addColorStop(1, "#10283a");
      context.fillStyle = background;
      context.fillRect(0, 0, size.width, size.height);
      context.strokeStyle = "rgba(120,170,195,.38)";
      context.lineWidth = 3;
      context.beginPath();
      context.moveTo(size.width * 0.05, size.height * 0.58);
      context.bezierCurveTo(
        size.width * 0.30, size.height * 0.38,
        size.width * 0.64, size.height * 0.76,
        size.width * 0.95, size.height * 0.58
      );
      context.stroke();
      STAGES.forEach(function (stage, index) {
        var x = size.width * (0.05 + stage.progress * 0.90);
        context.fillStyle = index === 2 ? "rgba(80,191,202,.20)" : "rgba(227,167,47,.14)";
        context.strokeStyle = index === 2 ? "#50bfca" : "#b98a35";
        context.lineWidth = 2;
        context.beginPath();
        context.rect(x - 58, 36, 116, 62);
        context.fill();
        context.stroke();
        context.textAlign = "center";
        context.fillStyle = "#eaf2f7";
        context.font = "700 13px system-ui, sans-serif";
        context.fillText(stage.name, x, 59);
        context.fillStyle = "#8fcbd0";
        context.font = "10px system-ui, sans-serif";
        context.fillText(stage.method, x, 79);
        context.strokeStyle = "rgba(150,190,210,.24)";
        context.beginPath();
        context.moveTo(x, 101);
        context.lineTo(x, size.height - 20);
        context.stroke();
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
        var color = rejectionColor ||
          (particle.item.peptide.verdict === "VISIBLE_CLEAR" ? "#67cf9a" : "#f3bf4d");
        context.globalAlpha = state.alpha;
        context.fillStyle = color;
        context.beginPath();
        context.arc(state.x, state.y, particle.radius, 0, Math.PI * 2);
        context.fill();
        context.strokeStyle = "rgba(255,255,255,.75)";
        context.lineWidth = 1;
        context.stroke();
        if (state.flash > 0) {
          context.globalAlpha = state.flash;
          context.strokeStyle = color;
          context.lineWidth = 2.5;
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
      context.fillStyle = "#aebdca";
      context.font = "11px system-ui, sans-serif";
      context.fillText("Rejections flash and fall in serialized reason colors", 14, size.height - 10);
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
      }
    }

    function update() {
      if (sceneController) {
        sceneController.destroy();
        sceneController = null;
      }
      host.replaceChildren();
      var item = candidates[Number(select.value) || 0];
      var peptide = item.peptide;
      host.appendChild(node("h3", "", item.mutation.gene + " " + item.mutation.protein_effect));
      host.appendChild(sequenceNode(peptide));
      host.appendChild(node(
        "p", "", "Wild type: " + (peptide.wt_seq || "not available") + " · mutation index " + peptide.position
      ));
      host.appendChild(node(
        "span",
        "badge " + peptide.verdict.toLowerCase().replaceAll("_", "-"),
        peptide.verdict.replaceAll("_", " ")
      ));
      host.appendChild(node("p", "", peptide.plain_language));

      var stageFallback = node("details", "funnel-static-fallback");
      stageFallback.appendChild(node(
        "summary", "", "Static serialized stage evidence (reduced-motion/no-canvas fallback)"
      ));
      var flowHost = node("div", "");
      flowHost.innerHTML = flowSvg(peptide);
      stageFallback.appendChild(flowHost);
      host.appendChild(stageFallback);
      currentFallback = stageFallback;
      syncFallbackMode();

      var scores = node("div", "score-grid");
      Object.keys(peptide.scores.binding).forEach(function (allele) {
        var value = peptide.scores.binding[allele];
        scores.appendChild(node(
          "div", "", allele + " · " + fixed(value.ic50, 1) + " nM · rank " +
            fixed(value.rank, 2) + "% · measured ML"
        ));
      });
      scores.appendChild(node(
        "div", "", "Agretopicity: " + fixed(peptide.agretopicity, 3) + " · heuristic approximation"
      ));
      scores.appendChild(node("div", "", "Reasons: " + peptide.reason_codes.join(", ")));
      host.appendChild(scores);
      var sceneHost = node("div", "candidate-scene-host");
      host.appendChild(sceneHost);
      sceneController = global.KEYHOLE.scene.mount(sceneHost, schematics[item.key]);
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
        left: Math.min(bounds.width - 280, Math.max(8, event.clientX - bounds.left + 12)),
        top: Math.max(105, event.clientY - bounds.top - 12)
      };
      updateTooltip();
    }

    function pointerLeave() {
      hoverPoint = null;
      tooltip.hidden = true;
    }

    var resizeObserver = null;
    function teardown() {
      if (destroyed) { return; }
      destroyed = true;
      cancelAnimation();
      select.removeEventListener("change", selectionChanged);
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
      if (resizeObserver) { resizeObserver.disconnect(); }
      if (sceneController) { sceneController.destroy(); sceneController = null; }
      container.replaceChildren();
    }

    function fail(error) {
      teardown();
      var failure = node(
        "div", "fatal", "Funnel rendering failed: " + error.message + ". Serialized evidence remains embedded."
      );
      failure.setAttribute("role", "alert");
      container.appendChild(failure);
    }

    function selectionChanged() {
      try { update(); }
      catch (error) { fail(error); }
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
      select.addEventListener("change", selectionChanged);
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
        resizeObserver.observe(witness);
      }
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
