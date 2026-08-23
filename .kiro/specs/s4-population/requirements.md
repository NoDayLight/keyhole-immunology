# S4 Requirements — Population HLA coverage

## User story

As a user, I need to see how often people in each available superpopulation carry at least one HLA keyhole predicted to display a candidate, while preserving the limits of the source frequency data.

## EARS acceptance criteria

1. THE SYSTEM SHALL use only frozen observed HLA-A/B frequency rows and SHALL preserve absent SAS as absent.
2. WHEN phased A-B haplotypes are unavailable, THE SYSTEM SHALL sample two A-B haplotypes under a visibly labeled linkage-equilibrium heuristic and SHALL NOT invent linkage frequencies.
3. WHEN seed 1729 and draw count are unchanged, repeated simulation SHALL produce value-identical genotypes and percentages.
4. THE SYSTEM SHALL evaluate each candidate against each supplied allele and store IC50, rank, visibility, verdict, reason codes, and method label in the peptide×allele matrix.
5. Per-candidate coverage SHALL be the percentage of simulated diploid people with at least one visible allele in AFR, AMR, EAS, and EUR.
6. `ALL_OBSERVED` SHALL be weighted by observed source cohort sizes and SHALL NOT be described as a global demographic estimate.
7. A candidate visible to no alleles SHALL have 0% coverage; one visible to all observed alleles SHALL have 100% coverage.
