/* KEYHOLE mutation visibility funnel renderer; consumes serialized values only. */
(function (global) {
  "use strict";
  function node(tag, className, text) { var element = document.createElement(tag); if (className) { element.className = className; } if (text !== undefined) { element.textContent = text; } return element; }
  function fixed(value, digits) { return Number(value).toFixed(digits); }
  function sequenceNode(peptide) {
    var wrapper = node("div", "sequence");
    peptide.seq.split("").forEach(function (residue, index) { var span = node("span", index === peptide.position ? "mutation-residue" : "", residue); if (index === peptide.position) { span.title = "mutated residue"; } wrapper.appendChild(span); });
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
      return '<g><rect x="' + x + '" y="20" width="164" height="105" rx="12" fill="#102638" stroke="#35556d"/><text x="' + (x + 12) + '" y="47" fill="#eaf2f7" font-size="16" font-weight="700">' + stage[0] + '</text><text x="' + (x + 12) + '" y="74" fill="#f3bf4d" font-size="13">' + stage[1] + '</text><text x="' + (x + 12) + '" y="103" fill="#8fcbd0" font-size="10">' + stage[2] + '</text></g>' + arrow;
    }).join("");
    return '<svg class="flow-svg" viewBox="0 0 920 145" role="img" aria-label="Five serialized visibility stages"><title>Visibility funnel for ' + peptide.seq + '</title><desc>Cleavage, TAP, HLA binding, foreignness, and final verdict. Values are precomputed in Python.</desc>' + body + "</svg>";
  }
  function render(container, results, schematics) {
    var candidates = [];
    results.mutations.forEach(function (mutation, mutationIndex) { mutation.peptides.forEach(function (peptide, peptideIndex) { candidates.push({ mutation: mutation, peptide: peptide, key: mutationIndex + ":" + peptideIndex }); }); });
    if (!candidates.length) { container.textContent = "No screenable peptide candidates."; return { destroy: function () {} }; }
    var select = node("select", "candidate-select"); select.setAttribute("aria-label", "Choose mutation-derived peptide");
    candidates.forEach(function (item, index) { var option = node("option", "", item.mutation.gene + " " + item.mutation.protein_effect + " · " + item.peptide.seq); option.value = String(index); select.appendChild(option); });
    container.appendChild(select); var host = node("div", "candidate-detail"); container.appendChild(host); var sceneController = null;
    function update() {
      if (sceneController) { sceneController.destroy(); sceneController = null; }
      host.replaceChildren(); var item = candidates[Number(select.value) || 0]; var peptide = item.peptide;
      host.appendChild(node("h3", "", item.mutation.gene + " " + item.mutation.protein_effect)); host.appendChild(sequenceNode(peptide));
      host.appendChild(node("p", "", "Wild type: " + (peptide.wt_seq || "not available") + " · mutation index " + peptide.position));
      host.appendChild(node("span", "badge " + peptide.verdict.toLowerCase().replaceAll("_", "-"), peptide.verdict.replaceAll("_", " ")));
      host.appendChild(node("p", "", peptide.plain_language)); var svg = node("div", ""); svg.innerHTML = flowSvg(peptide); host.appendChild(svg);
      var scores = node("div", "score-grid");
      Object.keys(peptide.scores.binding).forEach(function (allele) { var value = peptide.scores.binding[allele]; scores.appendChild(node("div", "", allele + " · " + fixed(value.ic50, 1) + " nM · rank " + fixed(value.rank, 2) + "% · measured ML")); });
      scores.appendChild(node("div", "", "Agretopicity: " + fixed(peptide.agretopicity, 3) + " · heuristic approximation")); scores.appendChild(node("div", "", "Reasons: " + peptide.reason_codes.join(", "))); host.appendChild(scores);
      var sceneHost = node("div", "candidate-scene-host"); host.appendChild(sceneHost); sceneController = global.KEYHOLE.scene.mount(sceneHost, schematics[item.key]);
    }
    select.addEventListener("change", update);
    try { update(); } catch (error) { select.removeEventListener("change", update); if (sceneController) { sceneController.destroy(); sceneController = null; } container.replaceChildren(); throw error; }
    return { destroy: function () { select.removeEventListener("change", update); if (sceneController) { sceneController.destroy(); sceneController = null; } container.replaceChildren(); } };
  }
  global.KEYHOLE = global.KEYHOLE || {}; global.KEYHOLE.funnel = Object.freeze({ render: render });
})(window);
