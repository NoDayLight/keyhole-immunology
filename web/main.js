/* KEYHOLE report orchestration; browser is render-only. */
(function (global) {
  "use strict";
  function parseJson(id) { var element = document.getElementById(id); if (!element) { throw new Error("Missing embedded payload " + id); } return JSON.parse(element.textContent); }
  function node(tag, className, text) { var element = document.createElement(tag); if (className) { element.className = className; } if (text !== undefined) { element.textContent = text; } return element; }
  function renderMethods(container, results, literature) {
    container.appendChild(node("h3", "", "Truth labels")); var methods = node("ul", ""); Object.keys(results.meta.methods).sort().forEach(function (name) { methods.appendChild(node("li", "", name + ": " + results.meta.methods[name])); }); container.appendChild(methods);
    container.appendChild(node("h3", "", "Frozen sources and citations")); var sources = node("ul", ""); results.meta.sources.forEach(function (source) { sources.appendChild(node("li", "", source)); }); Object.keys(literature.meta.citations).sort().forEach(function (name) { sources.appendChild(node("li", "", name + ": " + literature.meta.citations[name])); }); container.appendChild(sources);
    container.appendChild(node("p", "notice", "This comprehension report does not predict treatment response, prove immunogenicity, replace HLA typing, or provide medical advice."));
    return { destroy: function () { container.replaceChildren(); } };
  }
  function mountStructures(container, structures) {
    var records = []; var tornDown = false;
    ["1HHK", "3PWN", "1AO7"].forEach(function (pdbId) {
      var payload = structures[pdbId]; var card = node("article", "card"); card.appendChild(node("h3", "", payload.title)); var details = node("details", ""); var summary = node("summary", "", payload.truth + " — open interactive coordinates"); details.appendChild(summary); var host = node("div", ""); details.appendChild(host); card.appendChild(details); container.appendChild(card);
      var record = { controller: null, details: details, host: host, handler: null };
      record.handler = function () {
        if (tornDown) { return; }
        if (details.open && !record.controller) { record.controller = global.KEYHOLE.scene.mount(host, payload); }
        if (!details.open && record.controller) { record.controller.destroy(); record.controller = null; host.replaceChildren(); }
      };
      details.addEventListener("toggle", record.handler); records.push(record);
    });
    return { destroy: function () {
      if (tornDown) { return; } tornDown = true;
      records.forEach(function (record) { record.details.removeEventListener("toggle", record.handler); if (record.controller) { record.controller.destroy(); record.controller = null; } });
      container.replaceChildren();
    } };
  }
  function start() {
    var controllers = [];
    try {
      var results = parseJson("keyhole-results"); var scenes = parseJson("keyhole-scenes");
      controllers.push(global.KEYHOLE.funnel.render(document.getElementById("funnel-app"), results, scenes.schematics));
      controllers.push(global.KEYHOLE.atlas.render(document.getElementById("atlas-app"), results));
      controllers.push(global.KEYHOLE.theater.render(document.getElementById("theater-app"), results.literature));
      controllers.push(mountStructures(document.getElementById("structure-app"), scenes.structures));
      controllers.push(renderMethods(document.getElementById("methods-app"), results, results.literature));
      var destroyed = false;
      global.KEYHOLE.report = Object.freeze({ results: results, scenes: scenes, destroy: function () { if (destroyed) { return; } destroyed = true; controllers.forEach(function (controller) { if (controller && controller.destroy) { controller.destroy(); } }); } });
    } catch (error) {
      controllers.slice().reverse().forEach(function (controller) { if (controller && controller.destroy) { controller.destroy(); } });
      ["funnel-app", "atlas-app", "theater-app", "structure-app", "methods-app"].forEach(function (id) { var container = document.getElementById(id); if (container) { container.replaceChildren(); } });
      var main = document.getElementById("report") || document.body; var failure = node("div", "fatal", "Report rendering failed: " + error.message + ". The embedded results remain in this file."); failure.setAttribute("role", "alert"); main.prepend(failure);
    }
  }
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", start); } else { start(); }
})(window);
