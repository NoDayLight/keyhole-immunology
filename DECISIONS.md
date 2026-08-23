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

## S2 — 2026-08-24 — Deterministic allele-specific binding ML

- Binding uses one independent model for each of all 26 frozen IEDB HLA-A/B alleles. With no allele descriptor input, weights are never shared across alleles.
- Peptides use a fixed 9x21 BLOSUM62 representation. A 10-mer preserves both termini by mean-pooling only residue vectors 5 and 6 into the fifth of nine slots; the extra channel is a constant 9-mer/10-mer indicator.
- Split identity is global and peptide-only: the first eight SHA-256 bytes of `1729:<peptide>` modulo 10,000 define 80%/10%/10% train/validation/test before allele grouping. This prevents a peptide from crossing splits through another allele or duplicate measurement row.
- IEDB `<` and `>` measurements remain identified as censored in source provenance. Their reported numeric bounds are used as observed point targets for ordinary log10-IC50 MSE; this is a deliberate approximation and is not interpreted as exact affinity.
- Frozen model persistence is safe array-only NPZ with deterministic ZIP metadata, never pickle. Each allele artifact includes its fixed self-peptidome calibration distribution; JSON carries hashes, architecture, citations, fitting parameters, runtime, and real held-out metrics.
- Percentile ranks are empirical self-calibration percentiles with lower values indicating stronger binding. Held-out Spearman uses average ranks, and ROC AUC defines measured binders at IC50 <= 500 nM; both implementations use only NumPy/stdlib rather than SciPy.
- The final 24-epoch, learning-rate-0.003 deterministic CPU run took 6.46758654108271 seconds and produced pooled held-out Spearman 0.7376983698471881 and ROC AUC 0.9313822300930815 across 9,133 rows. A second seeded run reproduced all 26 NPZ files byte-for-byte.

### S2 evaluation amendment — censor-aware ROC thresholding

- A censored held-out row contributes to 500 nM ROC AUC only when its reported relation and boundary establish a true threshold side: `<` at or below 500 is positive, `>` at or above 500 is negative, and equality is classified from its reported value. Bounds that straddle the threshold are excluded from ROC only, rather than assigned an unsupported class.
- One of 9,133 held-out rows (`B*46:01`, `<5000 nM`) is therefore ROC-indeterminate. The authoritative 9,132-row ROC values are pooled `0.9313744947688023` and macro `0.9209613910509277`; Spearman is unchanged because its documented censor-bound-as-value approximation still includes all 9,133 rows.
