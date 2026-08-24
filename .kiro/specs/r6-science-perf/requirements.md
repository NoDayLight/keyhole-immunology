# R6 science-performance requirements

## Intent
Improve deterministic scientific runtime and allocation behavior without changing any scientific result, frozen model, source asset, metric, threshold, or public safety boundary.

## Requirements
1. Foreignness scoring shall evaluate multiple peptide queries together using per-position one-hot matrix products while preserving the scalar API, input validation, stable ordering, float values, verdicts, and serialized output exactly.
2. `screen_variants` shall use batched foreignness only for its default production scorer; explicitly injected scalar scorers shall retain their existing one-call-per-unique-peptide contract.
3. Population simulation shall retain seed `1729`, population order, A-before-B draw order, genotype column order A1/B1/A2/B2, categorical probabilities, rounded coverage, and cohort weighting while representing genotypes as compact integer allele codes and reusing precomputed per-allele carrier masks.
4. A loaded frozen binder shall encode each normalized peptide at most once and reuse an immutable cached encoding across alleles without changing inference batch boundaries, predictions, calibration, ordering, or frozen artifacts.
5. Famous canonical protein JSON shall be parsed once per resolved data root into immutable cached records; public callers shall continue receiving independent mutable dict copies.
6. A pipeline run shall undergo schema validation once. Trusted CLI JSON/report serialization may reuse that proof internally, while public `dump_results`, `render_report`, and `write_report` shall continue validating arbitrary caller documents.
7. The fixed-epoch SKCM `results.json` shall remain byte-identical with SHA-256 `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`.
8. Binder NPZ files, `metrics.json`, source hashes, published README metrics, browser science, R5 report compaction, and report truth labels shall not change.
