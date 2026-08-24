/* KEYHOLE published-positive literature theater. */
(function (global) {
  "use strict";
  function node(tag, className, text) { var element = document.createElement(tag); if (className) { element.className = className; } if (text !== undefined) { element.textContent = text; } return element; }
  function auc(value) { return value === null ? "n/a" : Number(value).toFixed(6); }
  function stat(container, value, label) { var card = node("div", "stat"); card.appendChild(node("strong", "", value)); card.appendChild(document.createTextNode(label)); container.appendChild(card); }
  function render(container, literature) {
    var stats = literature.agreement_stats; var summary = node("div", "audit");
    stat(summary, stats.published_positive_evaluable + "/" + stats.published_positive_total, "published positives evaluable");
    stat(summary, stats.positive_visible_count + "/" + stats.published_positive_evaluable, "evaluable positives visible");
    stat(summary, stats.matched_decoy_rejected_count + "/" + stats.matched_decoy_evaluable, "synthetic decoys rejected");
    stat(summary, auc(stats.synthetic_decoy_binding_roc_auc), "synthetic-decoy binding ROC AUC");
    container.appendChild(summary);
    container.appendChild(node("h3", "", "Agreement by binder-data exposure"));
    var strata = node("div", "audit");
    [["train", "overlapping train positives"], ["held_out", "overlapping held-out positives"], ["not_in_binding_dataset", "positives absent from binder data"]].forEach(function (item) {
      var values = stats.by_binding_exposure[item[0]];
      stat(strata, values.positive_visible_count + "/" + values.published_positive_evaluable, item[1] + " visible (" + values.published_positive_total + " total; AUC " + auc(values.synthetic_decoy_binding_roc_auc) + ")");
    });
    container.appendChild(strata);
    container.appendChild(node("p", "caveat", "Training exposure requires both exact peptide–allele source overlap and train assignment. Held-out combines validation/test assignments; source-unseen positives are separate."));
    var grid = node("div", "grid");
    literature.entries.forEach(function (entry) {
      var card = node("article", "card literature-card"); card.appendChild(node("h3", "", entry.peptide + " · " + entry.allele)); card.appendChild(node("span", "badge", entry.evaluation_status.replaceAll("_", " ")));
      card.appendChild(node("p", "", "Published assay: " + entry.external_facts.assay_result + " · PMID " + entry.external_facts.pmid)); card.appendChild(node("p", "", entry.external_facts.reference_title));
      card.appendChild(node("p", "", "Disease: " + (entry.external_facts.disease_context || "not recorded") + " · source: " + (entry.external_facts.source_molecule || "not recorded")));
      if (entry.prediction.verdict) { card.appendChild(node("p", "", "KEYHOLE: " + entry.prediction.verdict + " · " + entry.prediction.plain_language)); } else { card.appendChild(node("p", "caveat", entry.prediction.plain_language)); }
      card.appendChild(node("p", "caveat", "Binder source overlap: " + entry.binding_dataset_overlap + " · peptide split: " + entry.binder_split)); var decoy = entry.matched_negative;
      card.appendChild(node("p", "caveat", "Synthetic composition-preserving decoy " + decoy.peptide + ": " + (decoy.prediction.verdict || "not evaluable") + ". Experimental negative assay: none.")); grid.appendChild(card);
    });
    container.appendChild(grid); container.appendChild(node("h3", "", "Limitations")); var limits = node("ul", "limitations"); literature.meta.limitations.forEach(function (text) { limits.appendChild(node("li", "", text)); }); container.appendChild(limits);
    return { destroy: function () { container.replaceChildren(); } };
  }
  global.KEYHOLE = global.KEYHOLE || {}; global.KEYHOLE.theater = Object.freeze({ render: render });
})(window);
