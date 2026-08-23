# R0 Design — Minimal reviewed closure

## Guidance and automation

Three default steering files summarize the audience and truth boundaries, the pinned Python/offline browser stack, and the one-way package architecture. The existing `check-python-source` hook remains a PostToolUse command hook, but matches the current mutation tool names and uses `python -c` so the event JSON remains available on stdin. It recognizes changes below both `src/` and `tests/` and runs the established Ruff and fail-fast pytest commands.

## Hygiene scope

The cleanup deletes only APIs confirmed to have zero callers: `AlleleBindingMLP`, `split_assignment`, `predict_binding`, `run_funnel_many`, `load_self_peptides`, `data.sha256`, and `load_residue_templates`. `run_funnel` and compatibility properties on `BindingPrediction` remain. The unused CCD residue-template JSON and unreferenced top-level RCSB metadata are removed; setuptools explicitly packages only `famous_proteins.json` from the residue directory. Frozen `SOURCES.md` hash records stay historical and unchanged, with supersession documented in `DECISIONS.md`.

Top-level empty acquisition scaffolds are removed from the working tree. `.kiroignore` covers `data/**`, build outputs, the virtual environment, Python/tool caches, and generated `docs/index.html`; Git’s existing ignore rules remain independent.
