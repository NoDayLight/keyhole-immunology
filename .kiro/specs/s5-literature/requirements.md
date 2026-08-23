# S5 Requirements — Published agreement panel

## User story

As a user, I need to compare KEYHOLE's visibility model with real published positive tumor-epitope assays while seeing endpoint, allele-support, source-overlap, and negative-control limitations.

## EARS acceptance criteria

1. THE SYSTEM SHALL preserve all ten frozen positive IEDB T-cell peptide/HLA records and their assay URLs, PMIDs, titles, disease context, and source molecule without inference.
2. WHEN a restriction is in the 26-allele binder, THE SYSTEM SHALL score only that published restriction through cleavage, TAP, binding, foreignness, and verdict stages.
3. WHEN HLA-C*08:02 is encountered, THE SYSTEM SHALL retain it as `not_evaluable`, SHALL NOT substitute an HLA-A/B allele, and SHALL exclude it from agreement denominators.
4. WHEN no position-matched wild type exists, agretopicity SHALL serialize as null and not comparable rather than measured zero.
5. THE SYSTEM SHALL create one deterministic seed-1729 length- and composition-preserving shuffled control per positive and SHALL label it synthetic and not experimentally assayed negative.
6. Agreement statistics SHALL expose exact totals and denominators for published-positive visibility, synthetic-control rejection, paired binding-rank wins, and synthetic-control binding ROC AUC.
7. THE SYSTEM SHALL disclose per-peptide S2 binding-source overlap and deterministic binder split; it SHALL NOT call this panel independent clinical validation.
8. Repeated evaluation with identical inputs SHALL be value-identical and schema-v1 compatible.
