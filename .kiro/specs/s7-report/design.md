# S7 Design — Offline report and complete CLI

## One-way orchestration

`pipeline.py` owns all scientific orchestration: parse and audit input, generate canonical mutation-overlapping peptides, batch S2 predictions, invoke the S3 funnel for user HLA and the complete 26-allele population panel separately, then attach S4 and S5 evidence. It validates the resulting schema-v1 dictionary before exposing it. Missing protein context remains an audit fact rather than becoming synthetic sequence.

`report.py` accepts only a validated results mapping. It adds display-only structural payloads, JSON-escapes both envelopes, and concatenates checked-in browser IIFEs in the fixed order `projection → pdb → scene → funnel → atlas → theater → main`. Browser modules read serialized values and construct accessible DOM/SVG/canvas views; they do not score binding, processing, foreignness, verdicts, coverage, or literature agreement.

## Offline artifact and safety

The report embeds all three untouched PDB files and candidate residue-bead schematics. A restrictive CSP disables every default resource class and network connections while permitting only the required inline CSS, JavaScript, and data images. There are no external elements, sidecars, credentials, or server assumptions. JSON replaces ampersand, angle brackets, U+2028, and U+2029 before insertion into non-executable `application/json` script elements.

## CLI and determinism

`screen` writes optional canonical JSON and required standalone HTML; `explain` routes a frozen famous mutation through the same pipeline; `validate` checks assets and optionally reproduces held-out metrics; `open` uses a local `file:` URI. Candidate order follows stable parser/peptide order, all stochastic population work uses seed 1729, JSON keys are sorted, and creation time can be fixed through `SOURCE_DATE_EPOCH` for byte reproducibility.
