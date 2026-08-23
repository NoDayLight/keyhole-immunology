# S4 Design — Population HLA coverage

## Frequency panels

S1 frequencies are grouped by superpopulation and HLA-A/B locus. Decimal values are renormalized only to remove ten-decimal serialization drift; source allele counts remain unchanged. The panel must contain exactly AFR, AMR, EAS, and EUR with both loci. SAS absence is an explicit source limitation.

## Monte Carlo

NumPy `default_rng(1729)` draws A1/B1 and A2/B2 for 100,000 synthetic people per available population. Since the published frozen table has no phase, A and B are independent (linkage equilibrium); copies are independently drawn from each locus (Hardy-Weinberg). This is labeled `heuristic approximation`. It estimates genotype coverage from real marginals but is not a measured haplotype panel.

For each candidate, a person is covered when any of four allele copies has a non-`INVISIBLE` per-allele verdict. Population percentages are rounded to four decimals after counting. `ALL_OBSERVED` weights those percentages by source-panel individual counts and is named to prevent global-population interpretation.

## Matrix

The pipeline serializes every peptide×allele cell with S2 IC50/rank plus S3 per-allele verdict, visibility, reason codes, and combined method label. Browser code only renders this matrix.
