/* KEYHOLE report orchestration; the browser is render-only and never recomputes science. */
(function (global) {
  "use strict";

  var UI = null;

  /*
   * Deliberately literal structure titles. 3PWN is a peptide-HLA complex, not a TCR
   * complex, and is never labelled as one: only 1AO7 contains TCR chains.
   */
  var STRUCTURE_TABS = [
    {
      id: "1HHK",
      label: "Peptide in the keyhole",
      detail: "HLA-A*02:01 heavy chain, β2-microglobulin, and a bound 9-mer peptide."
    },
    {
      id: "3PWN",
      label: "A second measured keyhole",
      detail: "An independent HLA-A2 complex with a different bound peptide, at 1.6 Å."
    },
    {
      id: "1AO7",
      label: "A T cell reading the card",
      detail: "The same Tax peptide-HLA-A*02:01 complex engaged by TCR α and β chains."
    }
  ];

  function parseJson(id) {
    var element = document.getElementById(id);
    if (!element) { throw new Error("Missing embedded payload " + id); }
    return JSON.parse(element.textContent);
  }

  /* ------------------------------------------------------------------ hero */
  function mountHero(structures) {
    var host = document.getElementById("hero-app");
    if (!host || !structures["1HHK"]) { return null; }
    return global.KEYHOLE.molecule.mount(host, structures["1HHK"], {
      compact: true,
      title: "One real peptide sitting in one real HLA groove",
      description: "PDB 1HHK · X-ray diffraction · 2.5 Å · Madden et al. Cell 1993. " +
        "The gold ball-and-stick chain is the displayed peptide; the tubes trace measured " +
        "Cα positions of the HLA heavy chain and β2-microglobulin."
    });
  }

  /* ------------------------------------------------------------ structures */
  function mountStructures(container, structures) {
    var available = STRUCTURE_TABS.filter(function (entry) {
      return Boolean(structures[entry.id]);
    });
    if (!available.length) {
      container.appendChild(UI.node("p", "fig-status", "No packaged molecular structures."));
      return { destroy: function () { container.replaceChildren(); } };
    }

    var tabs = UI.node("div", "seg");
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", "Packaged experimental structures");
    var panel = UI.node("div", "");
    panel.id = "structure-panel";
    panel.setAttribute("role", "tabpanel");
    container.appendChild(tabs);
    container.appendChild(panel);

    var controller = null;
    var tornDown = false;
    var buttons = available.map(function (entry, index) {
      var tab = UI.button("seg-item", entry.label);
      tab.id = "structure-tab-" + entry.id;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", "structure-panel");
      tab.setAttribute("aria-selected", index === 0 ? "true" : "false");
      tab.setAttribute("aria-pressed", index === 0 ? "true" : "false");
      tab.tabIndex = index === 0 ? 0 : -1;
      tabs.appendChild(tab);
      return tab;
    });

    function show(index) {
      if (tornDown) { return; }
      var entry = available[index];
      buttons.forEach(function (tab, position) {
        var selected = position === index;
        tab.setAttribute("aria-selected", selected ? "true" : "false");
        tab.setAttribute("aria-pressed", selected ? "true" : "false");
        tab.tabIndex = selected ? 0 : -1;
      });
      if (controller) { controller.destroy(); controller = null; }
      panel.replaceChildren();
      controller = global.KEYHOLE.molecule.mount(panel, structures[entry.id], {
        label: "Figure " + (index + 1) + "a",
        title: String(structures[entry.id].title),
        description: [
          entry.detail,
          "PDB " + entry.id,
          String(structures[entry.id].method),
          structures[entry.id].resolution_angstrom + " Å",
          String(structures[entry.id].citation)
        ].join(" · ")
      });
    }

    function clicked(event) {
      var tab = event.target.closest ? event.target.closest("button[role='tab']") : null;
      if (!tab || !tabs.contains(tab)) { return; }
      show(buttons.indexOf(tab));
    }

    function keyed(event) {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" &&
        event.key !== "Home" && event.key !== "End") { return; }
      var current = buttons.findIndex(function (tab) {
        return tab.getAttribute("aria-selected") === "true";
      });
      var next = current;
      if (event.key === "ArrowRight") { next = (current + 1) % buttons.length; }
      else if (event.key === "ArrowLeft") { next = (current + buttons.length - 1) % buttons.length; }
      else if (event.key === "Home") { next = 0; }
      else { next = buttons.length - 1; }
      event.preventDefault();
      show(next);
      buttons[next].focus();
    }

    tabs.addEventListener("click", clicked);
    tabs.addEventListener("keydown", keyed);
    show(0);

    return {
      destroy: function () {
        if (tornDown) { return; }
        tornDown = true;
        tabs.removeEventListener("click", clicked);
        tabs.removeEventListener("keydown", keyed);
        if (controller) { controller.destroy(); controller = null; }
        container.replaceChildren();
      }
    };
  }

  /* --------------------------------------------------------------- methods */
  function renderMethods(container, results, literature) {
    var methodNames = Object.keys(results.meta.methods).sort();
    var measured = methodNames.filter(function (name) {
      return results.meta.methods[name] === "measured ML";
    });
    var heuristic = methodNames.filter(function (name) {
      return results.meta.methods[name] === "heuristic approximation";
    });

    var split = UI.node("div", "split");
    var left = UI.node("div", "");
    var right = UI.node("div", "");
    split.appendChild(left);
    split.appendChild(right);

    left.appendChild(UI.node("h3", "", "Measured-data machine learning"));
    var measuredList = UI.node("ul", "limitations");
    measured.forEach(function (name) {
      measuredList.appendChild(UI.node(
        "li", "", name.replaceAll("_", " ") + " — " + results.meta.methods[name]
      ));
    });
    if (!measured.length) { measuredList.appendChild(UI.node("li", "", "none")); }
    left.appendChild(measuredList);

    left.appendChild(UI.node("h3", "", "Transparent heuristic approximation"));
    var heuristicList = UI.node("ul", "limitations");
    heuristic.forEach(function (name) {
      heuristicList.appendChild(UI.node("li", "", name.replaceAll("_", " ")));
    });
    left.appendChild(heuristicList);

    var others = methodNames.filter(function (name) {
      return measured.indexOf(name) === -1 && heuristic.indexOf(name) === -1;
    });
    if (others.length) {
      left.appendChild(UI.node("h3", "", "Additional declared assumptions"));
      var otherList = UI.node("ul", "limitations");
      others.forEach(function (name) {
        otherList.appendChild(UI.node("li", "", name.replaceAll("_", " ") + ": " + results.meta.methods[name]));
      });
      left.appendChild(otherList);
    }

    right.appendChild(UI.node("h3", "", "What KEYHOLE refuses to claim"));
    var refusals = UI.node("ul", "limitations");
    [
      "It does not diagnose cancer or recommend any treatment.",
      "It does not prove peptide presentation, immunogenicity, or checkpoint response.",
      "It does not replace clinical HLA typing, and it does not model HLA-C.",
      "It does not estimate worldwide demographic coverage.",
      "It does not dock peptides, predict structures, or simulate molecular motion.",
      "It does not treat illustrative geometry as measured molecular structure."
    ].forEach(function (text) { refusals.appendChild(UI.node("li", "", text)); });
    right.appendChild(refusals);
    container.appendChild(split);

    var sources = UI.node("details", "");
    sources.appendChild(UI.node("summary", "", "Frozen sources and citations"));
    var sourceList = UI.node("ul", "limitations");
    results.meta.sources.forEach(function (source) {
      sourceList.appendChild(UI.node("li", "", source));
    });
    Object.keys(literature.meta.citations).sort().forEach(function (name) {
      sourceList.appendChild(UI.node("li", "", name + ": " + literature.meta.citations[name]));
    });
    sources.appendChild(sourceList);
    container.appendChild(sources);

    var runtimeNote = UI.node("details", "");
    runtimeNote.appendChild(UI.node("summary", "", "Offline browser runtime and third-party components"));
    var runtimeList = UI.node("ul", "limitations");
    [
      "three.js 0.169.0 (MIT) renders the molecular scenes. The pinned distribution is " +
        "inlined byte-exact into this file; there is no CDN, runtime import, or remote texture.",
      "cobe 0.6.4 and phenomenon 1.6.0 (both MIT) render the coverage globe, including its " +
        "embedded data-URI dot map.",
      "IBM Plex Serif 400 (SIL OFL 1.1) is embedded as a base64 WOFF2 subset; no external " +
        "font request is made.",
      "The radar and bar figures reimplement the composable structure of the Bklit UI radar " +
        "chart and the EvilCharts Recharts bar chart as plain SVG, because those upstreams are " +
        "React component libraries that cannot run in a build-free single file.",
      "This document makes no network request of any kind. Its Content-Security-Policy sets " +
        "default-src 'none' and connect-src 'none'."
    ].forEach(function (text) { runtimeList.appendChild(UI.node("li", "", text)); });
    runtimeNote.appendChild(runtimeList);
    container.appendChild(runtimeNote);

    container.appendChild(UI.node(
      "p",
      "boundary",
      "This comprehension report does not predict treatment response, prove immunogenicity, " +
        "replace HLA typing, or provide medical advice. Results require experimental and " +
        "clinical validation."
    ));
    return { destroy: function () { container.replaceChildren(); } };
  }

  /* ------------------------------------------------------------------ rail */
  function activeRail() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".rail-nav a"));
    if (!links.length || !global.IntersectionObserver) { return { destroy: function () {} }; }
    var targets = links.map(function (link) {
      return document.querySelector(link.getAttribute("href"));
    });
    var ratios = new Map();
    function mark() {
      var best = -1;
      var bestRatio = 0;
      targets.forEach(function (target, index) {
        var ratio = ratios.get(target) || 0;
        if (ratio > bestRatio) { bestRatio = ratio; best = index; }
      });
      links.forEach(function (link, index) {
        if (index === best) { link.setAttribute("aria-current", "true"); }
        else { link.removeAttribute("aria-current"); }
      });
    }
    var observer = new global.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { ratios.set(entry.target, entry.intersectionRatio); });
      mark();
    }, { threshold: [0, 0.08, 0.25, 0.5, 0.75, 1] });
    targets.forEach(function (target) { if (target) { observer.observe(target); } });
    return { destroy: function () { observer.disconnect(); ratios.clear(); } };
  }

  /* ----------------------------------------------------------------- start */
  function start() {
    var controllers = [];
    var appIds = ["funnel-app", "atlas-app", "structures-app", "literature-app", "methods-app"];
    try {
      UI = global.KEYHOLE.ui;
      var results = parseJson("keyhole-results");
      var scenes = parseJson("keyhole-scenes");
      var selection = UI.selectionStore();

      controllers.push(mountHero(scenes.structures));
      controllers.push(global.KEYHOLE.funnel.render(
        document.getElementById("funnel-app"), results, scenes.schematics, selection
      ));
      controllers.push(global.KEYHOLE.atlas.render(
        document.getElementById("atlas-app"), results, selection
      ));
      controllers.push(mountStructures(
        document.getElementById("structures-app"), scenes.structures
      ));
      controllers.push(global.KEYHOLE.theater.render(
        document.getElementById("literature-app"), results.literature
      ));
      controllers.push(renderMethods(
        document.getElementById("methods-app"), results, results.literature
      ));
      controllers.push(activeRail());
      /* Registered last so it also covers every disclosure the sections just created. */
      controllers.push(UI.enhanceDisclosures(document));

      var destroyed = false;
      global.KEYHOLE.report = Object.freeze({
        results: results,
        scenes: scenes,
        selection: selection,
        webgl: {
          molecule: global.KEYHOLE.molecule.supported(),
          globe: global.KEYHOLE.globe.supported()
        },
        destroy: function () {
          if (destroyed) { return; }
          destroyed = true;
          controllers.slice().reverse().forEach(function (controller) {
            if (controller && controller.destroy) { controller.destroy(); }
          });
          selection.destroy();
        }
      });
    } catch (error) {
      controllers.slice().reverse().forEach(function (controller) {
        if (controller && controller.destroy) { controller.destroy(); }
      });
      appIds.forEach(function (id) {
        var container = document.getElementById(id);
        if (container) { container.replaceChildren(); }
      });
      var host = document.getElementById("report") || document.body;
      var failure = document.createElement("div");
      failure.className = "fatal";
      failure.textContent = "Figure rendering failed: " + error.message +
        ". Every serialized result, coordinate set, and citation remains embedded in this file, " +
        "and the exact-value tables below each figure are generated from that same data.";
      failure.setAttribute("role", "alert");
      host.prepend(failure);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})(window);
