# KEYHOLE decision log

Decisions are append-only and identify the spec boundary that introduced them.

## S0 — 2026-08-24 — Contract and execution baseline

- Schema version 1 is frozen in `src/keyhole/schema.py` and represented by `tests/fixtures/results.sample.json`.
- Scientific computation is Python-only. Browser modules are render-only IIFEs and consume `window.KEYHOLE`.
- Runtime dependencies are exactly NumPy and PyTorch. Packaging and development tools are pinned separately.
- All stochastic components use the project seed `1729`; deterministic validation is a release gate.
- No source was narrowed at S0.
- The IDE's `kiroignore` scope explicitly denied creation of the requested `.kiroignore`. The denial was honored and not bypassed; equivalent generated/local artifacts are excluded from Git by `.gitignore`. This is an environment access-control constraint, not feature narrowing.