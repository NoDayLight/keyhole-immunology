# KEYHOLE product

KEYHOLE is a deterministic, offline-after-install cancer-immunology comprehension tool. It turns supported tumor variants plus supplied HLA-A/B alleles into one inspectable HTML report explaining which mutation-derived peptide “cards” may be visible to immune inspection.

## Audience and promise

The primary audience is a reviewer, researcher, educator, or hackathon judge who needs a runnable artifact and an honest explanation of evidence. The report combines measured-data binding ML with clearly labeled heuristic processing, foreignness, population, and verdict calculations. It is not a clinical predictor and must not diagnose, recommend treatment, prove presentation or immunogenicity, or substitute for HLA typing or experimental validation.

## Product rules

- Preserve one-way dataflow: Python emits validated results; browser code renders them without recomputing science.
- Label experimental coordinates as real and all idealized/simulated geometry as illustrative.
- Carry method labels and citations into the offline report.
- Prefer documented real subsets or explicit absence over fabricated records or narrowed claims.
- Keep fixed-seed outputs reproducible and the representative report self-contained, network-free, and directly openable.
- Keep every spec boundary tested, lint-clean, documented in `DECISIONS.md`, and shippable.
