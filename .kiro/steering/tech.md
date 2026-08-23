# KEYHOLE technology

## Runtime

- CPython 3.11 only; package uses a `src/` layout and setuptools.
- Runtime dependencies are pinned NumPy 2.2.3 and PyTorch 2.6.0.
- Scientific assets are package-owned under `src/keyhole/resources/data`; `KEYHOLE_DATA` is the only explicit data override.
- Browser rendering is plain local JavaScript IIFEs and CSS assembled into one HTML file by Python. No Node toolchain, CDN, sidecar server, runtime fetch, or credentials.

## Engineering constraints

- Seed all stochastic behavior from `schema.PROJECT_SEED` (`1729`) and preserve stable ordering and serialization.
- Frozen binder NPZs are safe array-only artifacts; never retrain or rewrite their published metrics/hashes during feature work.
- Treat schema validation as the Python/browser contract. A breaking contract change requires a version bump and decision entry.
- Keep experimental PDB assets untouched; report-only compaction must not alter package originals.
- Use `SOURCE_DATE_EPOCH` for byte-reproducible JSON/HTML gates.

## Standard checks

Run `.venv/bin/pytest -q`, `.venv/bin/ruff check src tests`, and `git diff --check` at every spec boundary. Use `.venv/bin/keyhole validate` and a fixed-epoch SKCM screen for scientific/release gates.
