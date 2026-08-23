# S2 Requirements — Candidate peptides and binding ML

## Requirements analysis

The contract requires both 9- and 10-residue candidates, but the specified network input is fixed at 9×21. Neither requirement is narrowed. Nine-mers occupy nine sequence slots directly. For a 10-mer, the central positions 5 and 6 are mean-pooled into one center slot, representing the class-I peptide bulge while retaining the N/C anchor order. Twenty channels are the BLOSUM62 row against canonical amino acids; channel 21 is a constant length indicator (0 for 9, 1 for 10). This is an explicit representation choice, not a measured structural claim.

The architecture contains no allele input, so one independent model is trained per allele. A single global peptide hash assigns every sequence to train/validation/test before allele grouping; the same peptide can never leak across splits through another allele. Censored IEDB values (`<`/`>`) are trained at their reported numeric boundary under ordinary MSE and identified as an approximation in the model card.

## User story

As a tumor-screening user, I need mutation-centered peptide candidates and reproducible measured-data binding estimates so I can compare mutant and wild-type display potential for each HLA allele.

## EARS acceptance criteria

1. WHEN a verified missense variant is supplied, THE SYSTEM SHALL emit every unique position-matched 9/10-mer pair spanning the changed residue.
2. WHEN a translated frameshift stream is supplied, THE SYSTEM SHALL stop at the first stop codon and emit only 9/10-mers containing novel sequence.
3. WHEN protein context or a translated frameshift stream is absent, THE SYSTEM SHALL fail explicitly rather than invent sequence.
4. THE binder SHALL encode each peptide as exactly 9×21 BLOSUM62/length features and SHALL use the exact 189→128→64→1 MLP.
5. THE binder SHALL train one model for each frozen HLA allele using MSE on log10(IC50 nM).
6. THE split SHALL be keyed only by unique peptide and seed 1729, with no peptide shared across train/validation/test.
7. WHEN the same artifact and candidates are evaluated repeatedly, THE SYSTEM SHALL return value-identical positive IC50 and percentile ranks.
8. `validate_binder` SHALL reproduce stored held-out Spearman correlation and ROC AUC from frozen test rows on demand.
9. Full deterministic training on CPU SHALL complete in less than ten minutes on the development machine.
