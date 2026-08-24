/* KEYHOLE shared figure anatomy, formatting, and selection store; render-only. */
(function (global) {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) { element.className = className; }
    if (text !== undefined) { element.textContent = text; }
    return element;
  }

  function svg(tag, attributes) {
    var element = document.createElementNS(SVG_NS, tag);
    if (attributes) {
      Object.keys(attributes).forEach(function (name) {
        element.setAttribute(name, String(attributes[name]));
      });
    }
    return element;
  }

  function svgText(tag, attributes, text) {
    var element = svg(tag, attributes);
    if (text !== undefined) { element.textContent = String(text); }
    return element;
  }

  function button(className, label) {
    var element = node("button", className, label);
    element.type = "button";
    return element;
  }

  function fixed(value, digits) {
    var number = Number(value);
    return Number.isFinite(number) ? number.toFixed(digits) : "n/a";
  }

  function verdictClass(verdict) {
    return String(verdict).toLowerCase().replaceAll("_", "-");
  }

  function verdictLabel(verdict) {
    return String(verdict).replaceAll("_", " ").toLowerCase();
  }

  /* One shared reduced-motion watcher so every module agrees and nothing leaks. */
  function motionWatcher() {
    var query = global.matchMedia ?
      global.matchMedia("(prefers-reduced-motion: reduce)") : null;
    var listeners = [];
    function changed(event) {
      listeners.slice().forEach(function (listener) { listener(Boolean(event.matches)); });
    }
    if (query) {
      if (query.addEventListener) { query.addEventListener("change", changed); }
      else if (query.addListener) { query.addListener(changed); }
    }
    return {
      get reduced() { return Boolean(query && query.matches); },
      subscribe: function (listener) {
        listeners.push(listener);
        return function () {
          var index = listeners.indexOf(listener);
          if (index !== -1) { listeners.splice(index, 1); }
        };
      },
      destroy: function () {
        listeners.length = 0;
        if (!query) { return; }
        if (query.removeEventListener) { query.removeEventListener("change", changed); }
        else if (query.removeListener) { query.removeListener(changed); }
      }
    };
  }

  /* Minimal selection store so one candidate choice drives the whole narrative. */
  function selectionStore() {
    var state = { index: 0, candidateKey: "" };
    var listeners = [];
    return {
      get: function () { return { index: state.index, candidateKey: state.candidateKey }; },
      set: function (index, candidateKey, origin) {
        if (state.index === index && state.candidateKey === candidateKey) { return; }
        state = { index: index, candidateKey: candidateKey };
        listeners.slice().forEach(function (listener) {
          listener({ index: index, candidateKey: candidateKey, origin: origin || "" });
        });
      },
      subscribe: function (listener) {
        listeners.push(listener);
        return function () {
          var position = listeners.indexOf(listener);
          if (position !== -1) { listeners.splice(position, 1); }
        };
      },
      destroy: function () { listeners.length = 0; }
    };
  }

  /*
   * Canonical figure anatomy. Every scientific visualization in the report is built
   * from exactly this structure so truth labels can never drift out of view:
   *   caption number + title -> persistent truth label -> viewport -> controls
   *   -> legend -> live status -> exact-data disclosure.
   */
  function figure(options) {
    var settings = options || {};
    var root = node("figure", "fig" + (settings.className ? " " + settings.className : ""));
    var head = node("div", "fig-head");
    var heading = node("figcaption", "fig-caption");
    if (settings.label) {
      heading.appendChild(node("span", "fig-label", settings.label));
    }
    heading.appendChild(node("span", "fig-title", settings.title || ""));
    head.appendChild(heading);
    var headExtra = node("div", "fig-head-extra");
    head.appendChild(headExtra);
    root.appendChild(head);

    var truth = node("p", "fig-truth");
    truth.appendChild(node("span", "fig-truth-mark", settings.truthKind === "real" ? "measured" : "illustrative"));
    var truthText = node("span", "fig-truth-text", settings.truth || "");
    truth.appendChild(truthText);
    root.appendChild(truth);

    if (settings.description) {
      root.appendChild(node("p", "fig-note", settings.description));
    }

    var viewport = node("div", "fig-viewport");
    root.appendChild(viewport);

    var controls = node("div", "fig-controls");
    root.appendChild(controls);

    var legend = node("ul", "fig-legend");
    root.appendChild(legend);

    var status = node("p", "fig-status");
    status.setAttribute("aria-live", "polite");
    root.appendChild(status);

    var data = node("details", "fig-data");
    var dataSummary = node("summary", "", settings.dataSummary || "Exact serialized values");
    data.appendChild(dataSummary);
    var dataBody = node("div", "fig-data-body");
    data.appendChild(dataBody);
    root.appendChild(data);

    return {
      root: root,
      headExtra: headExtra,
      viewport: viewport,
      controls: controls,
      legend: legend,
      status: status,
      data: data,
      dataBody: dataBody,
      setTruth: function (text, kind) {
        truthText.textContent = text;
        truth.firstChild.textContent = kind === "real" ? "measured" : "illustrative";
      },
      setStatus: function (text) { status.textContent = text; },
      addLegend: function (swatch, text, variant) {
        var item = node("li", "fig-legend-item");
        var mark = node("span", "fig-swatch" + (variant ? " " + variant : ""));
        if (swatch) { mark.style.setProperty("--swatch", swatch); }
        item.appendChild(mark);
        item.appendChild(node("span", "", text));
        legend.appendChild(item);
        return item;
      },
      addControl: function (element) { controls.appendChild(element); return element; },
      hint: function (text) {
        var element = node("span", "fig-hint", text);
        controls.appendChild(element);
        return element;
      }
    };
  }

  function table(headings, className) {
    var wrap = node("div", "table-wrap");
    var element = node("table", className || "");
    var thead = node("thead", "");
    var headRow = node("tr", "");
    headings.forEach(function (heading) {
      var cell = node("th", "");
      if (typeof heading === "string") {
        cell.textContent = heading;
      } else {
        cell.textContent = heading.label;
        if (heading.numeric) { cell.className = "numeric"; }
      }
      headRow.appendChild(cell);
    });
    thead.appendChild(headRow);
    element.appendChild(thead);
    var body = node("tbody", "");
    element.appendChild(body);
    wrap.appendChild(element);
    return { wrap: wrap, table: element, body: body };
  }

  function row(body, cells) {
    var element = node("tr", "");
    cells.forEach(function (cell) {
      var td = node("td", "");
      if (cell && typeof cell === "object" && !(cell instanceof Node)) {
        td.textContent = cell.text === undefined ? "" : String(cell.text);
        if (cell.className) { td.className = cell.className; }
      } else if (cell instanceof Node) {
        td.appendChild(cell);
      } else {
        td.textContent = cell === undefined || cell === null ? "" : String(cell);
      }
      element.appendChild(td);
    });
    body.appendChild(element);
    return element;
  }

  function metric(value, label, sublabel, tone) {
    var element = node("div", "metric" + (tone ? " " + tone : ""));
    element.appendChild(node("strong", "metric-value", value));
    element.appendChild(node("span", "metric-label", label));
    if (sublabel) { element.appendChild(node("span", "metric-sub", sublabel)); }
    return element;
  }

  function sequence(seq, position, className) {
    var wrapper = node("span", "seq" + (className ? " " + className : ""));
    String(seq).split("").forEach(function (residue, index) {
      var span = node("span", index === position ? "seq-mut" : "seq-res", residue);
      if (index === position) { span.title = "mutated residue"; }
      wrapper.appendChild(span);
    });
    return wrapper;
  }

  /*
   * Native <details> elements snap open, which breaks the reading rhythm of a long report.
   * This adds a height transition and an SVG plus-to-minus morph without changing how any
   * disclosure behaves:
   *
   *   - `open` is still the single source of truth, and the `toggle` event still fires, so
   *     scene.js keeps rebuilding its SVG fallback and funnel.js keeps forcing panels open.
   *   - Programmatic `.open = true/false` assignments are deliberately left un-animated.
   *     They are state synchronisation, not a reader gesture.
   *   - One delegated click listener and one observer cover every disclosure, including the
   *     ones funnel.js and the structure tabs recreate, so nothing has to opt in.
   *   - Under reduced motion, or if anything throws, the native behaviour runs untouched.
   */
  var DISCLOSURE_OPEN_MS = 340;
  var DISCLOSURE_CLOSE_MS = 260;
  var DISCLOSURE_EASING = "cubic-bezier(0.32, 0.72, 0, 1)";

  function disclosureIcon() {
    var icon = svg("svg", {
      class: "disc", viewBox: "0 0 14 14", "aria-hidden": "true", focusable: "false"
    });
    icon.appendChild(svg("line", { class: "disc-bar disc-h", x1: 2.6, y1: 7, x2: 11.4, y2: 7 }));
    icon.appendChild(svg("line", { class: "disc-bar disc-v", x1: 7, y1: 2.6, x2: 7, y2: 11.4 }));
    return icon;
  }

  function enhanceDisclosures(root) {
    var scope = root || document;
    var animations = new WeakMap();
    var observer = null;

    function prefersReducedMotion() {
      return Boolean(
        global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    }

    function addIcon(summary) {
      if (summary.dataset.discIcon === "1") { return; }
      summary.dataset.discIcon = "1";
      summary.insertBefore(disclosureIcon(), summary.firstChild);
    }

    function addIcons(container) {
      if (container.nodeType !== 1) { return; }
      if (container.matches && container.matches("details > summary")) { addIcon(container); }
      var found = container.querySelectorAll ?
        container.querySelectorAll("details > summary") : [];
      Array.prototype.forEach.call(found, addIcon);
    }

    /* Always restore the element to natural height, so late-growing content never clips. */
    function release(details) {
      animations.delete(details);
      details.style.removeProperty("height");
      details.style.removeProperty("overflow");
      details.style.removeProperty("will-change");
    }

    function run(details, from, to, duration, done) {
      var existing = animations.get(details);
      if (existing) { existing.cancel(); }
      details.style.overflow = "hidden";
      details.style.willChange = "height";
      var animation;
      try {
        animation = details.animate(
          [{ height: from + "px" }, { height: to + "px" }],
          { duration: duration, easing: DISCLOSURE_EASING }
        );
      } catch (error) {
        release(details);
        if (done) { done(); }
        return;
      }
      animations.set(details, animation);
      animation.onfinish = function () {
        if (animations.get(details) !== animation) { return; }
        release(details);
        if (done) { done(); }
      };
      animation.oncancel = function () {
        if (animations.get(details) === animation) { release(details); }
      };
    }

    function clicked(event) {
      if (event.defaultPrevented || event.button !== 0) { return; }
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) { return; }
      var summary = event.target.closest ? event.target.closest("summary") : null;
      if (!summary) { return; }
      var details = summary.parentElement;
      if (!details || details.tagName !== "DETAILS" || !scope.contains(details)) { return; }
      if (prefersReducedMotion() || typeof details.animate !== "function") { return; }

      var start = details.offsetHeight;
      if (details.open) {
        event.preventDefault();
        var collapsed = summary.offsetHeight;
        run(details, start, collapsed, DISCLOSURE_CLOSE_MS, function () {
          details.open = false;
        });
      } else {
        /* Let the browser open it first so the real content height can be measured. */
        details.open = true;
        var full = details.offsetHeight;
        run(details, start, full, DISCLOSURE_OPEN_MS);
        event.preventDefault();
      }
    }

    try {
      addIcons(scope === document ? document.body : scope);
      scope.addEventListener("click", clicked, true);
      if (global.MutationObserver) {
        observer = new global.MutationObserver(function (records) {
          records.forEach(function (record) {
            Array.prototype.forEach.call(record.addedNodes, addIcons);
          });
        });
        observer.observe(scope === document ? document.body : scope, {
          childList: true, subtree: true
        });
      }
    } catch (error) {
      if (observer) { observer.disconnect(); observer = null; }
    }

    return {
      destroy: function () {
        scope.removeEventListener("click", clicked, true);
        if (observer) { observer.disconnect(); observer = null; }
      }
    };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.ui = Object.freeze({
    SVG_NS: SVG_NS,
    button: button,
    enhanceDisclosures: enhanceDisclosures,
    figure: figure,
    fixed: fixed,
    metric: metric,
    motionWatcher: motionWatcher,
    node: node,
    row: row,
    selectionStore: selectionStore,
    sequence: sequence,
    svg: svg,
    svgText: svgText,
    table: table,
    verdictClass: verdictClass,
    verdictLabel: verdictLabel
  });
})(window);
