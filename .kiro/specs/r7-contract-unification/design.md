# R7 contract-unification design

## Shared contracts
A dependency-light `keyhole.contracts` module owns schema version `"1.1"`, seed `1729`, the 26 supported alleles, canonical residues, generic HLA normalization, canonical sequence/peptide normalization, and the `(rank, IC50, allele)` binding order key. Existing modules re-export public names where compatibility requires it.

## Single validated result contract
`schema.validate_results` absorbs the renderer traversal and validates finite scores, candidate metadata and winner, complete audit arithmetic, aligned candidate/population keys, all 26 matrix cells, literature metadata/entries, and exposure strata. Report rendering either invokes this validator publicly or accepts the pipeline-validated object through its private trusted path. No second renderer validator remains.

## Funnel delegation
The pipeline validates every `predict_many` result against requested allele, peptide order, and cardinality, stores predictions in a lookup adapter implementing scalar `predict`, and injects precomputed foreignness into `run_funnel`. The same pair order, user/all-allele passes, and serialization remain intact.

## Literature strata
Each published positive controls its pair's bucket: overlapping train peptide, overlapping held-out validation/test peptide, or peptide absent from binder data. Each bucket serializes positive/decoy denominators, visibility/rejection counts, paired rank wins, split composition, and nullable within-bucket AUC. Aggregate statistics remain unchanged.

## Report ownership and gates
`assemble_report_scenes` in report code owns the report-only envelope; structure code remains responsible for geometry primitives. The schema fixture becomes a complete empty v1.1 contract fixture. Acceptance compares R7 output to the R6 golden after removing only schema-version and new literature fields, verifies frozen artifact hashes, then runs full tests, Ruff, JavaScript syntax, and diff checks.
