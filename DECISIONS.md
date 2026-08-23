# KEYHOLE decision log

Decisions are append-only and identify the spec boundary that introduced them.

## S0 — 2026-08-24 — Contract and execution baseline

- Schema version 1 is frozen in `src/keyhole/schema.py` and represented by `tests/fixtures/results.sample.json`.
- Scientific computation is Python-only. Browser modules are render-only IIFEs and consume `window.KEYHOLE`.
- Runtime dependencies are exactly NumPy and PyTorch. Packaging and development tools are pinned separately.
- All stochastic components use the project seed `1729`; deterministic validation is a release gate.
- No source was narrowed at S0.
- The IDE's `kiroignore` scope explicitly denied creation of the requested `.kiroignore`. The denial was honored and not bypassed; equivalent generated/local artifacts are excluded from Git by `.gitignore`. This is an environment access-control constraint, not feature narrowing.
## S1 — 2026-08-24 — Frozen data sources and narrowing

- The requested IEDB archive URL on `tools-api.iedb.org` returned HTTP 404 even with `curl -k`; the identical documented archive path on the official `tools.iedb.org` host was used and both the failure and upstream archive hash are recorded in `data/SOURCES.md`.
- The MHC-I snapshot is narrowed to measured human 9/10-mers for a fixed panel of 26 common two-field HLA-A/B alleles, retaining original IC50 text and `<`, `=`, or `>` measurement relations; this yields 95,441 rows without stochastic downsampling.
- A defensible published HLA-A/B table spanning AFR/AMR/EAS/EUR/SAS was not available from an official endpoint. The frozen substitute uses 878 exact sample-ID matches between published 1000 Genomes HLA typing and its Phase I panel for AFR/AMR/EAS/EUR only; Phase I `ASN` is labeled `EAS`, SAS is explicitly absent, and allele copies still ambiguous at two fields are excluded rather than resolved or imputed.
- The UniProt self-peptidome snapshot samples exactly 500,000 indices with seed `1729` from the lexicographically ordered universe of distinct canonical 9-mers, so source-record ordering cannot affect the sample.
- Complete detailed cBioPortal mutation profiles are retained for TCGA PanCancer Atlas SKCM and PAAD. Their screenable MAF examples are independent 100-record seed-`1729` samples after stable genomic/sample ordering; only API-provided fields are written.
- RCSB entry `1AKJ` is an HLA-A2/CD8 co-receptor complex, not a TCR-pMHC complex. It is replaced by RCSB-verified `1AO7`, a human TCR-Tax peptide-HLA-A*02:01 complex, alongside `1HHK` and `3PWN`.
- The 100-row TCGA MAF examples deterministically force one real profile row for each offline demonstration anchor (SKCM BRAF V600E and TP53 R175H; PAAD KRAS G12D), sample the remaining distinct background rows with seed `1729` after excluding same-event rows, and stable-sort the result. This deliberate anchor inclusion makes offline examples scientifically processable against frozen canonical UniProt reference sequences while every MAF row is mapped solely from a real TCGA record returned by cBioPortal, without invented values.
