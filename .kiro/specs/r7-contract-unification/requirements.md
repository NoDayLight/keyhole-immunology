# R7 contract-unification requirements

## Intent
Remove duplicated implementations and make schema v1.1 the single strict pipeline-to-renderer contract. The binder is never retrained; frozen predictions, metrics, source hashes, candidate science, population values, and report structure compaction remain unchanged.

## Requirements
1. Results shall use semantic schema version string `"1.1"`. One validator shall enforce every field and cross-branch invariant consumed by the offline renderer, including a complete input audit; missing or inconsistent audit data shall fail before rendering.
2. The pipeline shall preserve R6 mutant/wild batch boundaries and batched foreignness, then delegate candidate processing, best-binding selection, agretopicity, verdicts, and `FunnelResult` assembly to `funnel.run_funnel` through a validated precomputed-prediction adapter.
3. Text opening, generic HLA normalization, canonical peptide validation, binding winner ordering, supported allele constants, and project seed/version constants shall each have one shared implementation.
4. Report code shall solely assemble the derived scene envelope while structure code retains coordinate/geometry primitives. R5 display-only PDB compaction shall not regress.
5. Literature agreement shall retain aggregate values and add honest exposure-aware `train`, `held_out`, and `not_in_binding_dataset` strata. Training exposure requires both source overlap and train assignment; empty AUC values are null.
6. Browser literature rendering shall show stratum denominators and distinguish source-unseen records; it shall not recompute scientific classifications.
7. The model card generator and frozen model card shall state that the deterministic validation split was reserved but unused for training, model selection, early stopping, hyperparameter tuning, calibration, or reported test metrics.
8. No binder NPZ, `metrics.json`, `SOURCES.md`, published README binder metric, threshold, or frozen scientific prediction may change. R7 `results.json` changes are limited to schema version and intentional literature contract fields.
