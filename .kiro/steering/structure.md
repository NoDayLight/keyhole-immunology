# KEYHOLE structure

## One-way architecture

1. `parse.py` reads supported MAF/VCF records; `peptides.py` creates canonical candidate pairs.
2. `bind.py` loads 26 frozen allele-specific models. `funnel.py`, `population.py`, and `literature.py` compute labeled evidence.
3. `pipeline.py` orchestrates deterministic science and emits schema-conforming results.
4. `schema.py` owns the serialized contract and validation.
5. `report.py` embeds validated results, browser modules, and scene payloads into one offline HTML file; browser code only renders.
6. `cli.py` exposes `screen`, `explain`, `validate`, and `open`.

## Repository map

- `src/keyhole/`: Python application and scientific logic.
- `src/keyhole/resources/data/`: reviewed wheel-owned models, sources, examples needed at runtime, and provenance.
- `src/keyhole/resources/web/`: plain IIFE rendering modules.
- `src/keyhole/resources/validation/`: package-owned schema fixture.
- `data/examples/`: clone-demo MAFs and retained source archives; not a runtime lookup root.
- `tests/`: deterministic unit, contract, report, and release checks.
- `.kiro/specs/`: requirements/design/tasks per boundary; `.kiro/steering/` contains governing guidance.
- `docs/index.html`: generated Pages-ready representative report.

New science belongs in Python before serialization. New browser behavior must consume existing or explicitly versioned payload fields and carry truthful visual labels.
