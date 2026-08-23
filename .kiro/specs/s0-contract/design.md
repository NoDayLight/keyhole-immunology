# S0 Design — Direct execution and frozen contract

## Architecture

The one-way boundary is `pipeline modules → schema-v1 results.json → report renderer`. `schema.py` has no scientific logic and validates plain JSON values without adding a runtime dependency. It rejects invalid paths early and writes sorted, indented UTF-8 JSON for deterministic diffs.

The source tree is a flat Python package whose modules map one-to-one to scientific and output concerns. Browser modules are plain IIFEs, concatenated in a fixed order by `report.py`; they never import or calculate pipeline scores. Frozen source records live under `data/`, with provenance in `data/SOURCES.md`.

## Contract

Top-level keys are `meta`, `tumor`, `alleles`, `mutations`, `population`, and `literature`. A mutation contains `gene`, `change`, `protein_effect`, and candidate `peptides`. Candidate fields and enum values are frozen by `schema.py` and the fixture. Additive metadata is allowed; incompatible changes require version 2 and a decision-log entry.

## Determinism

The global seed is 1729. Canonical JSON output sorts keys and ends with one newline. Future learned and Monte Carlo components must reset every relevant random generator from this seed.
