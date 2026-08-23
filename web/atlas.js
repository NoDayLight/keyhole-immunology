/* KEYHOLE population atlas renderer; never recomputes coverage. */
(function (global) {
  "use strict";
  var SVG_NS = "http://www.w3.org/2000/svg";
  function node(tag, className, text) { var element = document.createElement(tag); if (className) { element.className = className; } if (text !== undefined) { element.textContent = text; } return element; }
  function svgNode(tag, attributes, text) { var element = document.createElementNS(SVG_NS, tag); Object.keys(attributes || {}).forEach(function (name) { element.setAttribute(name, String(attributes[name])); }); if (text !== undefined) { element.textContent = text; } return element; }
  function coverageSvg(key, coverage, populations) {
    var svg = svgNode("svg", { "class": "atlas-svg", "viewBox": "0 0 900 205", "role": "img", "aria-label": "Population coverage bars" });
    svg.appendChild(svgNode("title", {}, "Modeled population coverage for " + key));
    svg.appendChild(svgNode("desc", {}, "Percent carrying at least one modeled visible HLA allele in four observed cohorts and their cohort-weighted aggregate."));
    populations.forEach(function (name, index) {
      var value = Number(coverage[name]); var y = 18 + index * 37;
      svg.appendChild(svgNode("text", { x: 5, y: y + 15, fill: "#dce8ef", "font-size": 12 }, name));
      svg.appendChild(svgNode("rect", { x: 105, y: y, width: 700, height: 22, rx: 5, fill: "#122b3c" }));
      svg.appendChild(svgNode("rect", { x: 105, y: y, width: value * 7, height: 22, rx: 5, fill: "#50bfca" }));
      svg.appendChild(svgNode("text", { x: 815, y: y + 15, fill: "#f3bf4d", "font-size": 12 }, value.toFixed(2) + "%"));
    });
    return svg;
  }
  function render(container, results) {
    var population = results.population; var keys = Object.keys(population.per_candidate_coverage);
    if (!keys.length) { container.textContent = "No population coverage candidates."; return { destroy: function () { container.replaceChildren(); } }; }
    var selector = node("select", ""); selector.setAttribute("aria-label", "Choose peptide for population coverage");
    keys.forEach(function (key) { var option = node("option", "", key); option.value = key; selector.appendChild(option); }); container.appendChild(selector);
    var host = node("div", ""); container.appendChild(host);
    function update() {
      host.replaceChildren(); var key = selector.value || keys[0]; var coverage = population.per_candidate_coverage[key]; var populations = ["AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"];
      host.appendChild(coverageSvg(key, coverage, populations));
      var tableWrap = node("div", "table-wrap"); var table = node("table", ""); var head = node("tr", ""); ["Population", "Coverage percent"].forEach(function (text) { head.appendChild(node("th", "", text)); }); var thead = node("thead", ""); thead.appendChild(head); table.appendChild(thead); var tbody = node("tbody", "");
      populations.forEach(function (name) { var row = node("tr", ""); row.appendChild(node("td", "", name)); row.appendChild(node("td", "", Number(coverage[name]).toFixed(4))); tbody.appendChild(row); }); table.appendChild(tbody); tableWrap.appendChild(table); host.appendChild(tableWrap);
      var cells = population.peptide_allele_matrix[key]; var matrixWrap = node("div", "table-wrap"); var matrix = node("table", "allele-matrix"); var matrixHead = node("tr", "");
      ["Allele", "IC50 nM", "Rank %", "Verdict", "Visible", "Method"].forEach(function (text) { matrixHead.appendChild(node("th", "", text)); }); var matrixThead = node("thead", ""); matrixThead.appendChild(matrixHead); matrix.appendChild(matrixThead); var matrixBody = node("tbody", "");
      Object.keys(cells).sort().forEach(function (allele) { var cell = cells[allele]; var row = node("tr", ""); row.appendChild(node("td", "", allele)); row.appendChild(node("td", "", Number(cell.ic50).toFixed(1))); row.appendChild(node("td", "", Number(cell.rank).toFixed(2))); row.appendChild(node("td", "", cell.verdict)); row.appendChild(node("td", "matrix-cell " + (cell.visible ? "yes" : "no"), cell.visible ? "yes" : "no")); row.appendChild(node("td", "", cell.method)); matrixBody.appendChild(row); });
      matrix.appendChild(matrixBody); matrixWrap.appendChild(matrix); host.appendChild(node("h3", "", "Peptide × modeled allele evidence")); host.appendChild(matrixWrap);
      host.appendChild(node("p", "caveat", population.meta.assumption + " Seed " + population.meta.seed + "; " + population.meta.draws + " draws. ALL_OBSERVED is cohort-weighted, not worldwide coverage. Unmodeled HLA alleles are unknown, not invisible."));
    }
    selector.addEventListener("change", update);
    try { update(); } catch (error) { selector.removeEventListener("change", update); container.replaceChildren(); throw error; }
    return { destroy: function () { selector.removeEventListener("change", update); container.replaceChildren(); } };
  }
  global.KEYHOLE = global.KEYHOLE || {}; global.KEYHOLE.atlas = Object.freeze({ render: render });
})(window);
