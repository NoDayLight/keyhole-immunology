# KEYHOLE invariants

These laws override convenience and apply to every spec boundary.

1. **One-way dataflow.** Scientific pipeline code writes schema-v1 `results.json`; the renderer only reads that artifact. Browser code never recomputes scientific values.
2. **Truthful geometry.** Every 3D scene is visibly labeled either `Real crystal structure (PDB <id>)` or `Schematic — data real, geometry illustrative`. Simulated or idealized geometry is never presented as measured.
3. **Method and source labels.** Every filter is labeled `measured ML` or `heuristic approximation`. Every external fact has a citation carried into the offline report.
4. **Determinism.** Fixed seeds govern training, splits, Monte Carlo, sampling, and animation. Tests assert byte-stable or value-stable results.
5. **Peptide-level validation.** ML train/validation/test splits are by unique peptide. `keyhole validate` reproduces held-out Spearman correlation and ROC AUC on demand.
6. **One offline report.** The report is one self-contained HTML target (approximately 1–2 MB with compact display-only structure payloads), with JavaScript and structures vendored inline. It uses no CDN, network request, credential, or Node toolchain. `report.py` concatenates plain IIFE modules.
7. **No fabrication and no feature narrowing.** If an upstream source is unreachable, freeze a smaller documented real subset, never fake records, and log the decision in `DECISIONS.md`.
8. **Continuous execution.** Do not ask whether to proceed. Surface only genuine contradictions, apply law 7 where possible, and continue to the next spec.
9. **Green boundaries.** Each spec ends with passing tests, clean Ruff output, and a commit. The repository is shippable at every boundary.

The schema-v1 contract freezes at S0. Any incompatible contract change requires a schema version bump and a decision log entry.
