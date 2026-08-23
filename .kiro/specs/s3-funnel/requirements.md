# S3 Requirements — Visibility funnel

## Requirements analysis

Only peptide–HLA binding is produced by a model trained on measured affinity data, and it is labeled `measured ML`. Proteasomal cleavage, TAP transport, agretopicity interpretation, BLOSUM nearest-self distance, thresholding, and verdicts are simplified computational filters; each is labeled `heuristic approximation`. Their scores are deterministic evidence summaries, not patient measurements or clinical predictions.

Łuksza et al. used sequence similarity in a neoantigen fitness model; KEYHOLE adapts that broad recognition concept into a nearest-human-self distance because the requested comprehension question is self-likeness. It does not claim to reproduce their model. Citation: Łuksza M et al. Nature. 2017;551:517–520. DOI `10.1038/nature24473`.

## User story

As a user, I need each altered protein card to pass through understandable processing, HLA fit, differential fit, and self-likeness gates so the final verdict says why it is clear, faint, or invisible without presenting heuristics as measurements.

## EARS acceptance criteria

1. THE cleavage gate SHALL return a bounded deterministic C-terminal PWM heuristic and carry its method label and citation.
2. THE TAP gate SHALL return a bounded deterministic positional transport heuristic and carry its method label and citation.
3. THE HLA gate SHALL use frozen S2 binding ML and SHALL retain IC50 and percentile rank per requested allele.
4. WHEN wild-type counterpart sequence exists, THE SYSTEM SHALL compute agretopicity as WT IC50 divided by mutant IC50 for the same best allele.
5. WHEN no wild-type counterpart exists, THE SYSTEM SHALL report `NO_WT_COUNTERPART` and SHALL NOT invent a comparison.
6. THE self scan SHALL compute normalized nearest-self BLOSUM62 distance against the frozen 500,000-peptide sample.
7. THE verdict engine SHALL emit exactly `VISIBLE_CLEAR`, `VISIBLE_FAINT`, or `INVISIBLE`, stable reason codes, and plain language.
8. WHEN processing fails, language SHALL include “never gets displayed”; WHEN binding fails, “doesn't fit your keyhole”; WHEN self-like, “looks too much like yourself”.
9. Repeated execution over identical inputs SHALL produce value-identical scores, reasons, and verdicts.
