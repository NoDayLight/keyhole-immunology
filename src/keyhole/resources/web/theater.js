/* KEYHOLE published-positive literature panel.
 *
 * Scientific contract: published T-cell positivity is an external experimental fact and
 * KEYHOLE visibility is this tool's heuristic verdict. They are different endpoints and
 * are never merged into a single accuracy claim. Composition-preserving shuffled controls
 * are synthetic decoys with no experimental assay result: their rejection is never called
 * specificity, a negative assay, or clinical validation. Every denominator is printed.
 */
(function (global) {
  "use strict";

  var UI = null;
  var STRATA = [
    ["train", "Overlapping · assigned to train",
      "exact peptide-allele overlap with the binder dataset, in the training split"],
    ["held_out", "Overlapping · held out",
      "exact peptide-allele overlap assigned to the validation or test split"],
    ["not_in_binding_dataset", "Absent from the binder dataset",
      "no exact peptide-allele overlap with any binder training record"]
  ];

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) { element.className = className; }
    if (text !== undefined) { element.textContent = text; }
    return element;
  }

  /* Nullable AUC stays nullable: an undefined AUC is reported, never imputed. */
  function auc(value) {
    return value === null || value === undefined ? "not defined" : Number(value).toFixed(6);
  }

  function definitionRow(parent, term, value) {
    var row = node("dl", "lit-row");
    row.appendChild(node("dt", "", term));
    row.appendChild(node("dd", "", value));
    parent.appendChild(row);
  }

  function agreementState(entry) {
    if (entry.evaluation_status !== "evaluable") { return "is-na"; }
    if (!entry.prediction.verdict) { return "is-na"; }
    return entry.prediction.verdict === "INVISIBLE" ? "is-miss" : "is-agree";
  }

  function render(container, literature) {
    UI = global.KEYHOLE.ui;
    var stats = literature.agreement_stats;

    /* ------------------------------------------------- the two endpoints */
    var endpoints = node("div", "endpoints");
    var published = node("div", "endpoint");
    published.appendChild(node("h3", "", "Published T-cell positivity"));
    published.appendChild(node(
      "p", "",
      "An external, experimentally measured fact from a cited IEDB record: a T-cell assay " +
        "responded to this peptide with this HLA allele. KEYHOLE does not reproduce, rerun, " +
        "or re-interpret the assay."
    ));
    endpoints.appendChild(published);
    var keyhole = node("div", "endpoint");
    keyhole.appendChild(node("h3", "", "KEYHOLE visibility"));
    keyhole.appendChild(node(
      "p", "",
      "This tool's heuristic verdict that a peptide could be processed, transported, and " +
        "displayed by a modeled HLA allele. Display is a precondition for a T-cell response, " +
        "not the response itself."
    ));
    endpoints.appendChild(keyhole);
    var relation = node("div", "endpoint");
    relation.appendChild(node("h3", "", "What agreement can and cannot show"));
    relation.appendChild(node(
      "p", "",
      "A published positive that KEYHOLE calls visible is consistent. A published positive " +
        "that KEYHOLE calls invisible is a real disagreement. Neither direction measures " +
        "immunogenicity, and none of this panel is an independent clinical validation set."
    ));
    endpoints.appendChild(relation);
    container.appendChild(endpoints);

    /* ------------------------------------------------------- headline metrics */
    var summary = node("div", "grid grid-3");
    summary.appendChild(UI.metric(
      stats.published_positive_evaluable + " / " + stats.published_positive_total,
      "published positives evaluable by the 26-allele model panel",
      "records outside the modeled HLA-A/B panel stay in the table and out of every denominator"
    ));
    summary.appendChild(UI.metric(
      stats.positive_visible_count + " / " + stats.published_positive_evaluable,
      "evaluable published positives KEYHOLE calls visible",
      "agreement between two different endpoints",
      "tone-clear"
    ));
    summary.appendChild(UI.metric(
      stats.matched_decoy_rejected_count + " / " + stats.matched_decoy_evaluable,
      "synthetic composition-preserving decoys rejected",
      "seed-1729 shuffled controls with no experimental assay result — not specificity"
    ));
    summary.appendChild(UI.metric(
      auc(stats.synthetic_decoy_binding_roc_auc),
      "binding ROC AUC, published positives against their synthetic decoys",
      "a synthetic-control separation measure, not clinical performance",
      "tone-accent"
    ));
    container.appendChild(summary);

    /* --------------------------------------------------- exposure strata table */
    container.appendChild(node("h3", "", "Agreement stratified by binder-dataset exposure"));
    container.appendChild(node(
      "p", "caveat",
      "Training exposure requires both an exact peptide-allele source overlap and a train " +
        "split assignment. Held-out combines validation and test assignments. Positives with " +
        "no source overlap are reported separately; hash assignment alone is never called " +
        "training exposure."
    ));
    var strataTable = UI.table([
      "Binder-dataset exposure",
      { label: "Positives", numeric: true },
      { label: "Evaluable", numeric: true },
      { label: "Called visible", numeric: true },
      { label: "Decoys rejected", numeric: true },
      { label: "Paired rank wins", numeric: true },
      { label: "Decoy binding ROC AUC", numeric: true }
    ]);
    STRATA.forEach(function (entry) {
      var values = stats.by_binding_exposure[entry[0]];
      UI.row(strataTable.body, [
        entry[1],
        { text: values.published_positive_total, className: "numeric" },
        { text: values.published_positive_evaluable, className: "numeric" },
        { text: values.positive_visible_count, className: "numeric" },
        {
          text: values.matched_decoy_rejected_count + " / " + values.matched_decoy_evaluable,
          className: "numeric"
        },
        { text: values.paired_binding_rank_wins, className: "numeric" },
        { text: auc(values.synthetic_decoy_binding_roc_auc), className: "numeric" }
      ]);
    });
    container.appendChild(strataTable.wrap);
    var strataNotes = node("ul", "limitations");
    STRATA.forEach(function (entry) {
      var values = stats.by_binding_exposure[entry[0]];
      var splits = values.positive_split_counts;
      strataNotes.appendChild(node(
        "li", "",
        entry[1] + " — " + entry[2] + ". Peptide split counts: train " + splits.train +
          ", validation " + splits.validation + ", test " + splits.test + "."
      ));
    });
    container.appendChild(strataNotes);

    /* Records excluded from every denominator, named rather than silently dropped. */
    var excluded = node("details", "");
    excluded.appendChild(node(
      "summary", "",
      "Records excluded from every denominator (" + stats.published_positive_not_evaluable +
        " of " + stats.published_positive_total + ")"
    ));
    var excludedBody = node("div", "");
    var reasons = node("ul", "limitations");
    Object.keys(stats.not_evaluable_by_reason).sort().forEach(function (reason) {
      reasons.appendChild(node(
        "li", "",
        reason.replaceAll("_", " ").toLowerCase() + ": " +
          stats.not_evaluable_by_reason[reason] + " record(s)"
      ));
    });
    stats.unsupported_records.forEach(function (record) {
      reasons.appendChild(node(
        "li", "",
        record.peptide + " with " + record.allele +
          " is retained as a real published record and excluded from all model-agreement " +
          "denominators; no substitute allele was used."
      ));
    });
    excludedBody.appendChild(reasons);
    excluded.appendChild(excludedBody);
    container.appendChild(excluded);

    /* Whole-panel aggregates, printed with their denominators. */
    var aggregates = UI.table(["Aggregate", "Value", "Denominator"]);
    [
      ["Published positives called visible", stats.positive_visible_count,
        stats.published_positive_evaluable + " evaluable positives"],
      ["Published positives called invisible", stats.positive_invisible_count,
        stats.published_positive_evaluable + " evaluable positives"],
      ["Positive agreement rate", stats.positive_agreement_rate,
        stats.published_positive_evaluable + " evaluable positives"],
      ["Synthetic decoys rejected", stats.matched_decoy_rejected_count,
        stats.matched_decoy_evaluable + " evaluable of " + stats.matched_decoy_total + " generated"],
      ["Synthetic decoy rejection rate", stats.matched_decoy_rejection_rate,
        stats.matched_decoy_evaluable + " evaluable decoys"],
      ["Paired binding rank wins", stats.paired_binding_rank_wins,
        stats.matched_decoy_evaluable + " positive/decoy pairs"],
      ["Paired binding rank win rate", stats.paired_binding_rank_win_rate,
        stats.matched_decoy_evaluable + " positive/decoy pairs"],
      ["Synthetic decoy binding ROC AUC", auc(stats.synthetic_decoy_binding_roc_auc),
        "positives versus their own synthetic decoys — not assayed negatives"]
    ].forEach(function (line) {
      UI.row(aggregates.body, [line[0], String(line[1]), line[2]]);
    });
    var aggregateDetails = node("details", "");
    aggregateDetails.appendChild(node("summary", "", "Whole-panel aggregates with denominators"));
    var aggregateBody = node("div", "");
    aggregateBody.appendChild(aggregates.wrap);
    aggregateDetails.appendChild(aggregateBody);
    container.appendChild(aggregateDetails);

    /* ------------------------------------------------------------ per entry */
    container.appendChild(node("h3", "", "Every record in the frozen panel"));
    var grid = node("div", "grid grid-2");
    literature.entries.forEach(function (entry) {
      var card = node("article", "lit-card " + agreementState(entry));
      card.appendChild(node("h3", "", entry.peptide + " · " + entry.allele));
      var badges = node("div", "fig-head-extra");
      badges.appendChild(node(
        "span", "badge badge-neutral", entry.evaluation_status.replaceAll("_", " ")
      ));
      if (entry.prediction.verdict) {
        badges.appendChild(node(
          "span", "badge " + UI.verdictClass(entry.prediction.verdict),
          UI.verdictLabel(entry.prediction.verdict)
        ));
      }
      card.appendChild(badges);
      definitionRow(card, "Published assay",
        entry.external_facts.assay_result + " · PMID " + entry.external_facts.pmid);
      definitionRow(card, "Reference", entry.external_facts.reference_title);
      definitionRow(card, "Disease context",
        entry.external_facts.disease_context || "not recorded");
      definitionRow(card, "Source molecule",
        entry.external_facts.source_molecule || "not recorded");
      definitionRow(card, "KEYHOLE verdict", entry.prediction.verdict ?
        entry.prediction.verdict.replaceAll("_", " ") + " — " + entry.prediction.plain_language :
        entry.prediction.plain_language);
      definitionRow(card, "Binder overlap",
        String(entry.binding_dataset_overlap) + " · peptide split " + entry.binder_split);
      definitionRow(card, "Synthetic decoy",
        entry.matched_negative.peptide + " → " +
          (entry.matched_negative.prediction.verdict ?
            entry.matched_negative.prediction.verdict.replaceAll("_", " ") : "not evaluable") +
          ". Experimental negative assay: none.");
      grid.appendChild(card);
    });
    container.appendChild(grid);

    container.appendChild(node("h3", "", "Limitations carried by this panel"));
    var limits = node("ul", "limitations");
    literature.meta.limitations.forEach(function (text) {
      limits.appendChild(node("li", "", text));
    });
    container.appendChild(limits);

    return { destroy: function () { container.replaceChildren(); } };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.theater = Object.freeze({ render: render });
})(window);
