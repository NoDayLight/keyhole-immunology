# S3 Design — Visibility funnel

## One-way gauntlet

`PeptidePair → cleavage heuristic → TAP heuristic → measured-data binding ML → same-allele agretopicity → nearest-self heuristic → verdict`. The renderer receives only serialized results and cannot recompute any gate.

Cleavage uses a transparent three-position C-terminal weighted score, motivated by C-terminal processing signals (Holzhütter et al., J Mol Biol. 1999, PMID `10656797`) and integrated class-I pathway work (Peters et al., J Immunol. 2005, PMID `15868101`). TAP uses transparent terminal weights motivated by Peters et al., J Immunol. 2003;171:1741–1749. Coefficients are hand-authored heuristics, not copied learned parameters or measurements.

## Foreignness

The frozen self-peptidome is stored as a 500,000×9 uint8 index. For each position, BLOSUM62 similarity to every sampled self peptide is summed; the greatest similarity is the nearest self match. Distance is normalized between the query row's theoretical minimum and maximum. A sampled exact 9-mer has distance zero; larger values mean less self-like. Ten-mers use the same documented center-pooling approximation as S2.

## Verdict policy

Processing below 0.35 rejects first. Binding is strong at rank ≤2 and IC50 ≤500 nM, faint at rank ≤10 and IC50 ≤5000 nM, otherwise rejected. Foreignness below 0.04 rejects as self-like. Clear visibility requires strong binding, foreignness ≥0.10, and agretopicity ≥1.5 when comparable. Remaining passing candidates are faint. These thresholds are comprehension heuristics, versioned in code and labeled in every output.
