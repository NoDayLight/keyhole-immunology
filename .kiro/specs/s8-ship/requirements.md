# S8 Requirements — Ship and fresh-install proof

## User story

As a judge or reviewer, I need to install KEYHOLE from its wheel, run it outside the repository without network-dependent runtime assets, inspect a prebuilt Pages demo, and understand exactly what every scientific claim does and does not mean.

## EARS acceptance criteria

1. THE WHEEL SHALL contain the complete runtime closure: provenance, raw validation data, 26 hashed NPZ models, metrics/model card, self sample, HLA marginals, literature panel, canonical proteins, residue templates, three PDBs, seven browser modules, and schema fixture.
2. WHEN `KEYHOLE_DATA` is unset, THE SYSTEM SHALL resolve reviewed package-owned resources independent of current directory and SHALL reject path traversal.
3. WHEN `KEYHOLE_DATA` is set, THE SYSTEM SHALL use only that explicit complete data root; browser code SHALL remain package-owned.
4. Training SHALL require an explicit writable output directory and SHALL NOT write into installed frozen resources.
5. A clean Python 3.11 wheel installation from an unrelated directory SHALL pass quick and full validation, reproduce held-out metrics, screen the real SKCM MAF, and generate valid standalone JSON/HTML.
6. Repeated fixed-epoch runs SHALL produce byte-identical result and report files between source and clean-wheel installations.
7. THE SHIPPED HTML SHALL remain 2–6 MB, contain all three truth-labeled PDB scenes and seven scripts, validate embedded schema, and contain no external/network-capable code path.
8. THE REPOSITORY SHALL provide a no-more-than-three-command quickstart, input contract, supported HLA list, methods/truth boundaries, citations/terms, deterministic mode, and a prominent “what this does NOT do” section.
9. THE REPOSITORY SHALL include a deterministic Pages-ready single-file demo and a truthful video storyboard.
10. Every S8 test, Ruff check, diff check, wheel inspection, and judge command SHALL pass before the boundary commit.
