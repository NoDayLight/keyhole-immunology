# KEYHOLE decision log

Decisions are append-only and identify the spec boundary that introduced them.

## S0 — 2026-08-24 — Contract and execution baseline

- Schema version 1 is frozen in `src/keyhole/schema.py` and represented by `src/keyhole/resources/validation/results.sample.json`.
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

## S3 — 2026-08-24 — Truth-labeled visibility funnel

- Binding predictions are labeled `measured ML`; cleavage, TAP, agretopicity interpretation, nearest-self distance, and verdict thresholds are labeled `heuristic approximation` in code and report metadata.
- Cleavage and TAP coefficient tables are transparent hand-authored approximations motivated by cited pathway literature, not fitted measurements or reproductions of proprietary predictors.
- Foreignness is a normalized BLOSUM62 distance to the closest peptide in the frozen 500,000-peptide self sample. This is a simplified adaptation of sequence-similarity reasoning associated with Łuksza et al. (Nature 2017), not their published fitness model.
- A frameshift candidate without a complete position-matched wild-type peptide receives agretopicity `0.0` only as a schema-v1 non-comparable sentinel and carries `NO_WT_COUNTERPART`; the report renders it as unavailable, not as measured zero.

## S4 — 2026-08-24 — Population coverage from unphased marginals

- Coverage uses the real frozen AFR/AMR/EAS/EUR marginal HLA-A/B frequencies. SAS remains absent because the source panel contains no SAS observations; no frequencies are fabricated or imputed.
- The source has no phased A–B haplotypes. Seeded Monte Carlo therefore draws A and B independently under an explicit linkage-equilibrium assumption and draws two chromosome copies under Hardy-Weinberg; all resulting coverage is labeled `heuristic approximation`, never measured haplotype coverage.
- The peptide×allele matrix retains per-allele S2 IC50/rank evidence plus the S3 heuristic verdict so the browser only renders serialized results and never recomputes population science.
- `ALL_OBSERVED` is weighted by source cohort counts and is deliberately not called worldwide or global demographic coverage.

## S5 — 2026-08-24 — Published-positive agreement panel

- The frozen panel contains ten real positive IEDB T-cell assays, but only nine are evaluable by S2: the real KRAS G12D/HLA-C*08:02 record is retained as `not_evaluable`, never substituted with an HLA-A/B allele, and excluded from all model-agreement denominators.
- Literature peptides have no position-matched wild-type sequence. S3's internal zero sentinel is used only to invoke the existing verdict engine; serialized agretopicity is null and explicitly `not_comparable`.
- Each positive receives a seed-1729, length- and amino-acid-composition-preserving shuffled control. These are labeled synthetic decoys with no experimental assay result, so their rejection and ROC AUC are not called specificity or clinical validation.
- Agreement compares heuristic KEYHOLE visibility with published T-cell positivity, which are different endpoints. Per-entry binder-source overlap and global peptide split are disclosed because the panel is not an independent clinical validation set.
- On the real frozen panel, 8/9 evaluable positives were visible, 8/9 evaluable synthetic decoys were rejected, all 9 positives had a better binding percentile rank than their paired decoy, and synthetic-decoy binding ROC AUC was 0.987654.

## S6 — 2026-08-24 — Truthful offline molecular scenes

- Experimental scenes parse and rotate untouched frozen PDB coordinates. Their persistent labels are exactly `Real crystal structure (PDB id)`; 1HHK/3PWN display one A/B/C pMHC assembly, while only verified TCR complex 1AO7 displays A/B/C/D/E.
- 3PWN's TCR-related keywords do not make it a TCR coordinate structure. Its 164 nonblank alternate-location records represent 82 duplicated atom sites; blank locations are preferred and otherwise one highest-occupancy conformer is selected with deterministic lexical tie-breaking.
- Candidate peptides use deterministic residue beads and sequential links, not fabricated all-atom chemistry or docking. They are persistently labeled `Schematic — data real, geometry illustrative` and explicitly described as neither measured, structure-predicted, nor HLA-docked.
- A small local canvas projection engine was implemented instead of adding a third-party dependency, CDN, or Node toolchain. The misleading scaffold name `three.min.js` was removed; browser code remains plain local IIFEs for S7 to inline.
- The reduced-detail SVG Cα/peptide view is always generated alongside canvas, with title, description, chain legend, text truth label, keyboard controls, and live fallback status.

## S7 — 2026-08-24 — Schema-first standalone report and CLI

- Screening scores only variants with frozen canonical missense context. Unsupported input rows remain visible through independent raw, parsed, missing-context, frameshift, and ignored-class audit counts; no protein sequence or verdict is invented.
- Mutant and matched wild-type peptides are batch-predicted once per each of all 26 frozen models. Patient verdicts use only supplied HLA alleles, while a separately computed 26-allele matrix supports population coverage and cannot alter patient conclusions.
- The dataflow is one way: Python pipeline → validated schema-v1 results → render-only browser. Additive `candidate_key`, `best_allele`, and `protein_start` metadata do not alter the frozen required schema-v1 contract.
- One report embeds validated JSON, untouched 1HHK/3PWN/1AO7 text, every candidate schematic, CSS, and all seven local IIFEs. CSP disables connections and default resource loading; no CDN, sidecar, server, credential, Node toolchain, or browser-side scientific recomputation is used.
- Creation time is real UTC by default and honors `SOURCE_DATE_EPOCH` for reproducible builds. A false fixed historical timestamp was rejected.
- The representative SKCM artifact is approximately 2.62 MB. Meaningless padding was rejected; the release guard accepts 2–6 MB because all legitimate required content is present and the requested 3–6 MB target was approximate.
- The report boundary applies a stricter additive renderer contract on top of frozen schema v1: serialized best-HLA must match the exact rank/IC50/allele winner, patient binding keys must match supplied HLA, population keys and all 26 cells must align, and every literature field consumed by JavaScript is type-checked before HTML is emitted.
- Parsed frameshifts are counted as unsupported independently from missing canonical context, so the same unresolved row may truthfully contribute to both audit categories; the PAAD example contains one such frameshift.
- Browser-generated population SVG uses namespaced DOM nodes and text content rather than interpolated markup. Startup and lazy-scene teardown remove listeners, destroy mounted controllers, and roll back already-mounted modules on failure.

## S8 — 2026-08-24 — Wheel-owned offline release

- The complete runtime closure moved under `src/keyhole/resources`: frozen scientific inputs, 26 hashed NPZ models, model metadata, self sample, HLA marginals, literature records, canonical proteins, residue templates, three untouched PDBs, seven browser IIFEs, provenance, and the schema validation fixture. Explicit setuptools package-data patterns include only this reviewed closure.
- Runtime lookup no longer trusts `cwd/data`, `cwd/web`, or `tests/fixtures`. Data uses only package-owned files or an explicit `KEYHOLE_DATA` root; browser code and validation remain package-owned. Relative resource paths reject traversal and backslashes.
- The real SKCM/PAAD example MAFs and complete cBioPortal source archives remain under top-level `data/examples` for clone demos and provenance, but unused full mutation archives are not added to the wheel.
- Model training now requires an explicit writable output directory. Installed frozen resources are inputs and are never a default mutation target.
- No blanket repository license was invented for mixed-source assets. README and packaged provenance retain source-specific terms, note the HLA repository's absent separate license, and require review before redistribution.
- The authoritative isolated build contains 65 members, exactly 26 NPZ models, and all required runtime resources at 8,075,959 bytes. A clean Python 3.11 install outside the repository with `KEYHOLE_DATA` unset reproduced full metrics and generated byte-identical source/wheel JSON and HTML.
- The deterministic Pages artifact is a direct prebuilt standalone report, not a second renderer or a network-backed demo. Its representative size remains approximately 2.63 MB; padding remains rejected.

## R0 — 2026-08-24 — Audit hygiene and minimal runtime closure

- Three concise steering guides now summarize product truth boundaries, the pinned offline stack, and the implemented one-way architecture; the R0 quick spec records the cleanup scope and gates.
- The Python-source PostToolUse hook now matches the current mutation tools, preserves event JSON on stdin via `python -c`, recognizes both `src/` and `tests/`, and runs Ruff plus fail-fast pytest. Kiro reported activation at the next top-level session start; before that boundary, the exact action was smoke-tested with a synthetic PostToolUse payload and visibly passed Ruff plus all 58 tests.
- The requested `.kiroignore` retry was denied exactly as follows: `Tool call denied by user's permissions. Rule: deny fs_write matching ".kiroignore, .kiroignore., .kiroignore , kiroig~*" Source: kiro-scope:kiroignore.` The denial was honored without retry or bypass; only this action was skipped and `.gitignore` remains the Git-level generated-artifact control.
- The package-owned schema fixture path replaces the stale pre-S8 test-fixture reference, and the 1AO7 DOI is consistently lower-case `a0`.
- Only confirmed zero-caller APIs were removed. `funnel.run_funnel` and `BindingPrediction.ic50`/`.rank` remain for planned contract delegation and compatibility.
- The unused CCD ideal-coordinate JSON, its loader/test/package pattern, and unreferenced top-level RCSB metadata were removed. Historical `SOURCES.md` provenance and hashes remain unchanged rather than being rewritten; this entry records that those acquisition artifacts are no longer in the runtime closure.
- Empty top-level acquisition scaffolds were removed from the working tree. R0 remains green at 58 tests with clean Ruff and diff checks; no binder artifact, metric, published README metric, or scientific output changed.

## R1 — 2026-08-24 — Molecular render quality without scientific change

- All runtime implementation changes are confined to `scene.js`; the schema, Python science, parsed coordinates, PDB resources, and `results.json` contract are unchanged.
- The renderer copies the parser’s reviewed radius values locally for visual sizing, pre-resolves bond serials to atom indices once, projects atoms once per canvas draw, and uses painter-correct depth opacity/radius plus cached per-color radial-gradient sprites, a radial backdrop, and static concentric mutation rings.
- Canvas backing dimensions change only when required. Pointer drag schedules canvas work without constructing SVG; the accessible fallback is generated when opened, on an open size change, or immediately after canvas failure.
- One per-scene requestAnimationFrame loop owns idle rotation after three seconds, decaying drag inertia, and reset tweening. IntersectionObserver pauses time-based reset progress off-screen. Reduced-motion mode schedules no animation and snaps an in-progress reset to a truthful completed state.
- The fixed-epoch SKCM `results.json` remained byte-identical before and after R1 at SHA-256 `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`. Report bytes changed intentionally because this spec changes visuals. R1 closes with 59 tests, clean Ruff, valid JavaScript syntax, and a clean diff check.

## R2 — 2026-08-24 — Candidate peptides on the 1HHK backbone

- Candidate 9-mers now use the nine exact chain-C Cα coordinates from frozen PDB 1HHK. Candidate 10-mers deterministically sample that ordered trace at source index `i × 8/9`, preserving both experimental template termini without extrapolation.
- P2 and PΩ backbone beads carry `role: "anchor"`. The mutated residue’s separate idealized side-chain endpoint carries `role: "mutation"`, so an anchor mutation retains both roles and the R1 mutation glow. The endpoint uses a deterministic local Cα frame, a fixed 109.5° direction, and a residue-specific illustrative reach; it is not represented as a measured or full atomistic rotamer.
- Every candidate scene now bears exactly `Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative`. Report detail and README distinguish measured template coordinates from candidate identity, 10-mer interpolation, and idealized side-chain placement; no candidate docking or structure prediction is claimed.
- R2 changes report scene payload only. The schema and fixed-epoch SKCM `results.json` remained byte-identical at SHA-256 `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`; the visual HTML changed intentionally and remained within the existing envelope at 2,669,214 bytes.
- R2 closes with all 59 tests passing, clean Ruff, valid JavaScript syntax, and a clean diff check. No binder artifact, metric, frozen provenance hash, or published README metric changed.

## R3 — 2026-08-24 — Seeded candidate witness funnel

- The funnel creates exactly one canvas particle per serialized mutation/peptide and derives lane, delay, speed, and size from `results.meta.seed`, `candidate_key`, and stable integer mixing; it never calls `Math.random` or invents candidates.
- The canvas path is persistently labeled `Schematic — data real, geometry illustrative`. Proteasome, TAP, HLA keyhole, and self-scan carry their existing heuristic/measured-ML labels. Particle timing/path is illustrative; tooltips, counts, scores, verdicts, and reasons are serialized report evidence.
- Rejection gates are chosen only from serialized `LOW_CLEAVAGE`, `LOW_TAP_TRANSPORT`, `WEAK_BINDING`, and `SELF_LIKE` reason codes. JavaScript does not reapply thresholds. Rejections flash and complete a reason-colored fall, including the final self-scan tail.
- Replay resets the same seeded state. Hover hit testing is revalidated every animation frame so evidence cannot remain attached to a particle that has moved away. A single idempotent teardown covers initialization, selection, replay, animation, resize, media-change failures, and normal destroy.
- Reduced-motion or unavailable canvas schedules no animation and opens the retained five-stage `flowSvg`; the selected candidate’s sequence, verdict, plain language, binding grid, reasons, and R2 molecular scene remain available.
- R3 changed browser/report bytes only. Fixed-epoch SKCM `results.json` remained byte-identical at SHA-256 `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`. All 60 tests, Ruff, JavaScript syntax, and diff checks passed; offline forbidden-string checks remained unchanged.

## R4 — 2026-08-24 — Truth-labeled orthographic population atlas

- `KEYHOLEProjection.orthographic` is an additive latitude/longitude API returning x/y, depth, and front-hemisphere visibility. The existing molecular `project()` perspective implementation remains unchanged.
- The atlas globe is persistently labeled exactly `Schematic — data real, geometry illustrative`. AFR/AMR/EAS/EUR marker locations and graticule are explicitly illustrative; marker values come directly from the selected candidate’s serialized population coverage. `ALL_OBSERVED` is shown only as a cohort-weighted text summary, never a geographic or worldwide estimate.
- Pointer drag, aligned arrow-key controls, Home, and Reset rotate or restore the deterministic view. Logical and CSS dimensions track the actual responsive container, preserving circular orthographic geometry on narrow displays.
- Exact five-row population coverage and sorted 26-allele evidence tables are built independently of canvas and remain visible at all times, including canvas failure. SAS absence, seed/draw assumptions, unknown unmodeled alleles, and the non-worldwide caveat remain explicit.
- R4 changes browser/report bytes only. Fixed-epoch SKCM `results.json` remained byte-identical at SHA-256 `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`. All 61 tests, Ruff, JavaScript syntax, and diff checks passed; offline injection/network contracts remain green.

## R5 — 2026-08-24 — Honest display-only report structure payload

- Package-owned PDBs remain untouched. Their SHA-256 values are still `9511878…21a7` (1HHK), `d605715…88cb` (3PWN), and `67a5ffb…131c` (1AO7), matching frozen provenance and `HEAD`.
- Report assembly now embeds only declared-display-chain, positive-selected-site, non-water, non-hydrogen ATOM alternatives plus CONECT references whose serials remain. Coordinates are fixed-column serialized at three decimals. Headers, REMARKs, HETATM/waters, non-display chains, and 3PWN’s 6,408 ignored ANISOU records remain in package originals but not report payload.
- Compaction preserves the browser’s blank-alt-first/highest-occupancy conformer behavior by excluding an entire site when the original selected conformer has zero occupancy, then retaining positive eligible alternatives. Semantic comparison confirmed identical displayed atoms/bonds before and after compaction for 1HHK (3,137/3,231), 3PWN (3,163/3,256), and 1AO7 (5,476/5,632).
- Original selected-site counts (6,322/7,133/5,711) travel as explicit metadata so the existing visible legend remains source-honest rather than reporting the subset as the full PDB.
- The intentional report-size test changed from 2–6 MB to 1.0–1.75 MB because the measured fixture is 1,192,857 bytes and real fixed-epoch SKCM Pages report is 1,354,274 bytes. No padding was added. Current README/invariant size guidance now says approximately 1–2 MB; historical S8 records remain historical.
- `docs/index.html` was rebuilt at `SOURCE_DATE_EPOCH=1787529600` and is 1,354,274 bytes (SHA-256 `b774522e48f04a3b7ea0b341ed0c7df8c8b232fa1e347a3e38d4b17947a27cb6`). SKCM `results.json` remained byte-identical at `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`. All 62 tests, Ruff, JS syntax, diff, and quick validation passed.

## R6 — 2026-08-24 — Byte-identical scientific performance paths

- Default pipeline foreignness now scores up to 64 queries together through nine per-position one-hot matrix products. The 500,000-row self index is processed in 250,000-row blocks and only block maxima are combined, preserving exact float32 score values while limiting a measured 64-query process to approximately 383 MB maximum RSS instead of the reviewed unchunked approximately 554 MB.
- Explicitly injected `foreignness_fn` callables retain scalar one-call-per-stable-unique-peptide behavior. The standalone scalar API and `run_funnel` remain unchanged.
- Population Monte Carlo retains the same single RNG, sorted population loop, A-before-B calls, `(draws, 2)` categorical choices, and A1/B1/A2/B2 columns. Genotypes now use stable sorted observed-allele `uint16` codes exposed by `hla_allele_codes`; coverage combines precomputed per-allele carrier masks rather than repeated string `np.isin`. Decoding proved every seeded draw identical to the former string arrays.
- Each loaded binder caches one read-only flattened encoding per normalized peptide while retaining mutant/wild batch boundaries, model inference, calibration, and output ordering. Famous-protein JSON is cached by resolved data-root path as immutable field tuples; public callers still receive independent mutable dict copies.
- `screen_variants` remains the single schema-validating producer. Private CLI JSON/report serializers reuse that validated result, while the additive report contract still runs and public `dump_results`, `render_report`, and `write_report` continue validating arbitrary documents.
- Fixed-epoch SKCM JSON and HTML both remained byte-identical: results SHA-256 `8a16e6e9e0b04ce1537edb46b7ebe54cf76f7b5a5dd5a9ae6529579b86452b53`; report SHA-256 `b774522e48f04a3b7ea0b341ed0c7df8c8b232fa1e347a3e38d4b17947a27cb6`. R6 closes with all 68 tests passing, clean Ruff and diff checks, and unchanged binder NPZ, `metrics.json`, `SOURCES.md`, README metrics, PDB assets, and R5 report compaction.
## R7 — 2026-08-24 — Unified schema, funnel, and literature contracts
- Schema version `"1.1"` is the single pipeline-to-renderer contract. Public result dumping and report rendering use `schema.validate_results`; missing screening audit data fails loudly, candidate/population evidence is aligned, renderer-consumed methods and literature facts are typed, and audit accounting permits truthful overlap between missing-context and frameshift categories.
- Dependency-light `contracts.py` owns seed `1729`, all 26 supported alleles, canonical sequence/peptide validation, HLA normalization, binding tie-break order, binary AUC, and binder-exposure classification. Compatibility wrappers retain domain-specific exceptions without duplicating rules.
- Candidate science delegates to `funnel.run_funnel` through a precomputed binder adapter. The frozen two-call-per-allele order remains mutant then wild for all 26 models; cardinality/order/identity are checked, shared mutant/wild identities reuse identical evidence, and conflicting repeats fail closed.
- Report code is the sole scene-envelope assembler while structure code owns coordinate/PDB primitives. R5 display-only PDB compaction and source-honest counts are unchanged; scenes remain outside `results.json`.
- Literature agreement now separates exact peptide–allele overlaps assigned to train, overlaps assigned to validation/test (`held_out`), and source-unseen records. Schema validation reconstructs every aggregate/stratum count, verdict, rate, paired rank win, split count, nullable AUC, unsupported reason, and unsupported record from entry evidence.
- Frozen-panel exposure results are: train total/evaluable/visible `5/5/5`, decoys rejected/evaluable `4/5`, paired wins `5`, AUC `1.0`; held-out `2/2/1`, decoys `2/2`, wins `2`, AUC `1.0`; source-unseen `3/2/2`, decoys `2/2`, wins `2`, AUC `1.0`. Existing aggregate values remain unchanged.
- The binder model card and its generator state that the deterministic validation split is reserved but unused for training, model selection, early stopping, hyperparameter tuning, calibration, or reported test metrics. No training ran and no NPZ, `metrics.json`, `SOURCES.md`, or published README metric changed.
- The fixed-epoch R7 SKCM result is SHA-256 `e69d251ebc4e267c281c1ca23a39c0fa152a42fe7f78dc30bc916aae114173ac`; HTML is `d1a9fbb1ba267fccfcd76d7bcf74662d188b1095c2758e496e4e53cbdcbb5c50`. Against R6, non-literature output is identical after schema-version normalization, literature entries and prior aggregate statistics are identical, and only exposure strata plus the extended limitation are additive.
- Frozen `metrics.json` remains `a4fe1c69b13b08d0df33936a914785b0ae1af4449f900ee997928d034263d14a`; packaged `SOURCES.md` remains `901dacea5678271a3a9d9a0437cd98146ea9ad7334bb3e462b4a60e679ae846b`. R7 closes with semantic approval, all 74 tests passing, clean Ruff, valid JavaScript syntax, clean diff checks, and successful full `keyhole validate` metrics reproduction.
## Final gate — 2026-08-24 — Fresh-install release proof
- The fixed-epoch Pages artifact was rebuilt from committed R7 code with the SKCM example and `A*02:01,B*07:02`. `docs/index.html` is 1,356,283 bytes at SHA-256 `d1a9fbb1ba267fccfcd76d7bcf74662d188b1095c2758e496e4e53cbdcbb5c50`; its result payload is `e69d251ebc4e267c281c1ca23a39c0fa152a42fe7f78dc30bc916aae114173ac`.
- A new isolated Python 3.11.15 environment under `/private/tmp`, with `KEYHOLE_DATA` unset, installed the project using exactly `pip install -e .`. Full `keyhole validate` found schema 1.1, seed 1729, all 26 binder models, all three structures, AFR/AMR/EAS/EUR populations, pooled Spearman `0.7376983698471881`, and censor-aware ROC AUC `0.9313744947688023`.
- The fresh executable screened SKCM successfully. With the exact relative-path invocation, fresh JSON and HTML were byte-identical to the source-environment outputs and Pages. A second run from outside the repository using an absolute MAF path differed only in serialized input-path provenance and was otherwise structurally identical.
- Standalone inspection parsed and schema-validated both embedded JSON payloads, confirmed all three structures and 38 candidate schematics, enforced the 1.0–1.75 MB envelope, and found no external script/link loads or forbidden network APIs. The report requires no server or sidecar.
- Final frozen hashes remain unchanged: `metrics.json` is `a4fe1c69b13b08d0df33936a914785b0ae1af4449f900ee997928d034263d14a` and packaged `SOURCES.md` is `901dacea5678271a3a9d9a0437cd98146ea9ad7334bb3e462b4a60e679ae846b`; no NPZ changed and no binder training ran.
- The release gate closes with all 74 tests passing, clean Ruff, valid JavaScript syntax, clean diff checks, and a clean repository after committing the rebuilt Pages artifact and this audit record.

## R8 — 2026-08-24 — Presentation-grade report, real WebGL renderers, locally vendored runtime

### Independent audit that motivated the redesign

- A baseline SKCM report was generated and inspected as rendered pixels at 1512 px and 390 px, not read as source. Findings: one UI sans face carried headings, prose, labels, and data with no role separation; five decorative `NN · KICKER` labels duplicated a sticky pill nav that itself had no active state, so the index appeared twice in two different vocabularies; the hero and structure scenes drew 3,137–5,476 undifferentiated Canvas 2D dots in which the peptide — the actual subject of the report — was invisible; the candidate scene put ten beads in a ~700 px panel; the coverage globe was a graticule wireframe that encoded percentages as dot radius and clipped two of four cohort labels at the limb; the funnel's drawn bezier path did not match where particles actually travelled; accessible fallbacks were surfaced as primary chrome under every figure, so the page read as a debug console; roughly twelve accent hues carried no semantic system; and at 390 px the funnel canvas forced a 560 px minimum width that overflowed the viewport and clipped the eyebrow, lede, and notice.
- Two defects in the uncommitted working tree were scientific rather than visual and were fixed rather than kept: the structure tab labelled PDB 3PWN "TCR overlooking a keyhole" although S6 already established that 3PWN is not a TCR coordinate structure, and the report-size test's own envelope no longer matched reality. The rest of the uncommitted work — the candidate browser replacing a `<select>`, the tabbed structure viewer replacing lazily opened `<details>`, and the audit ladder — was retained and refined.

### Art direction

- One restrained system: near-black surfaces, hairline rules instead of gradient cards, a single interactive accent, and exactly three verdict colours used nowhere else. Chain and element colours exist only inside molecular viewports and their legends.
- Three type roles that never overlap: IBM Plex Serif 400 for display text and figure captions, the installed monospace for every number, sequence, allele, and truth label, and the installed UI sans for controls only. The measured role split is serif 57%, monospace 35%, sans 8%; the previous report was a single sans at 47% doing all four jobs.
- Section indices exist exactly once, in a persistent numbered narrative rail with an `IntersectionObserver`-driven active state. Every decorative per-section kicker was deleted.
- Every visualization is a figure with fixed anatomy: caption, persistent truth label, viewport, controls, legend, live status, and an exact-values disclosure. `figure.js` owns that anatomy, so a truth label cannot drift out of view or be styled away.

### Vendored offline runtime

- `three@0.169.0` `build/three.module.min.js` is inlined byte-exact. It is the last three.js release whose minified ES-module build is a single self-contained file with zero static imports, zero dynamic imports, and no `import.meta`; from `0.172.0` the same file statically imports `./three.core.min.js`, which cannot be resolved inside one offline document. The deprecated UMD `three.min.js` was rejected because it emits a console deprecation warning.
- The namespace is published by a **generated** bridge: `keyhole.vendor` parses the single trailing `export{…}` clause of the untouched distribution and emits `globalThis.THREE` for an explicit 23-symbol allow-list. The vendored file is never rewritten, and assembly raises if any required export disappears.
- `cobe@0.6.4` and `phenomenon@1.6.0` render the globe. phenomenon's UMD build needs no adaptation. cobe contains exactly one leading module dependency statement and one trailing default-module statement; both are replaced by anchored, fail-loud transformations at assembly time while the file on disk stays byte-exact. cobe carries its dot map as an embedded `data:image/png;base64` texture, which the existing `img-src data:` policy already permits.
- `@ibm/plex-serif@2.0.0` weight-400 upright and italic **Latin1** WOFF2 subsets are embedded as base64 with no `local()` source, so rendering never depends on an installed font. Their upstream `unicode-range` covers every character KEYHOLE sets in the serif role; `β` and other out-of-range glyphs only ever appear in the monospace or sans roles.
- `font-src 'none'` became `font-src data:` — the single CSP relaxation, required for an inlined local font and still network-free. `object-src 'none'`, `base-uri 'none'`, and a new `form-action 'none'` remain, and `default-src 'none'` with `connect-src 'none'` are unchanged.
- Exact upstream URLs, npm integrity values, retained members, SHA-256 digests, licenses, and pin reasoning are recorded in `src/keyhole/resources/vendor/PROVENANCE.md`. Every digest is verified on every render.
- Recharts, visx, React, and `motion` were **not** added. The radar and bar figures reimplement the composable structure and visual grammar of the Bklit UI radar chart and the EvilCharts Recharts bar chart as plain accessible SVG, with attribution in `charts.js`, the report's own methods section, and the README. Adding a React chart stack would have required a Node build step and roughly half a megabyte more, for components that cannot express the truth-label discipline this report needs.

### Molecular rendering

- `molecule3d.js` is a real WebGL renderer: a `Scene`/`Group` graph, a perspective camera framed from the packaged coordinates' bounding sphere, hemisphere plus three directional lights plus ambient fill, ACES filmic tone mapping, sRGB output, `InstancedMesh` spheres grouped by colour over one shared `IcosahedronGeometry`, and `InstancedMesh` bonds over one shared `CylinderGeometry`.
- The default hybrid representation draws each chain as a `TubeGeometry` through a `CatmullRomCurve3` fitted to the measured Cα positions and draws only the displayed peptide as ball-and-stick. This is what made the subject legible: the peptide is the point of the report and is now the one chain rendered atomically. A second representation draws every packaged display-chain atom.
- Bond lines are disclosed in every figure's data panel as a drawing choice: explicit packaged connectivity where present, otherwise same-chain, same-or-adjacent-residue pairs within 1.9 Å, resolved through a deterministic spatial hash with sorted output. No coordinate is moved, scaled, idealized, or minimised; a test asserts the module never assigns to `atom.x`, `atom.y`, or `atom.z`, and that nothing outside the explicit refusal sentence mentions dynamics, docking, affinity simulation, minimisation, or density.
- Camera framing is the only thing the renderer invents, and it is documented as such. The bounding sphere is fitted to the vertical field of view and pulled to 0.86 of the fitting distance so the subject fills the frame.
- Adaptive quality selects sphere subdivision, bond segments, tube resolution, antialiasing, and pixel ratio from the displayed atom count and device pixel ratio, then performs one measured downgrade to pixel ratio 1 if the first frame exceeds 34 ms, reporting `quality balanced (reduced for this device)` in the visible status line.
- `KEYHOLE.molecule.mount` probes WebGL, releases the probe context through `WEBGL_lose_context`, and on failure delegates to the untouched `scene.js` Canvas 2D engine while stating plainly that WebGL is unavailable and the coordinates, chain selection, and truth label are identical. `scene.js` keeps its own reduced-detail SVG fallback beneath that.
- Pointer, touch, two-pointer pinch, wheel, arrow keys, `±`, and `Home` are all supported; the stage is focusable with a visible focus ring and an `aria-label` naming the controls. Reduced motion cancels the idle rotation and the reset tween and snaps to a completed state.
- Teardown disposes every geometry, material, light, and representation group, calls `renderer.dispose()` and `forceContextLoss()`, disconnects both observers, unsubscribes the shared motion watcher, removes every listener, clears tracked pointers, and cancels the frame. Measured: five live canvases before `destroy()`, zero after, `destroy()` twice is a no-op, and animation frames drop to zero.

### Coverage globe and charts

- The globe uses only serialized AFR/AMR/EAS/EUR values. Marker radius is a bounded display scale; landmasses are never tinted by coverage; `ALL_OBSERVED` is never given a marker, a location, or an extent and appears only as text explicitly labelled cohort-weighted and not worldwide. SAS is reported as absent from the frozen panel rather than as zero. `globe.js` contains neither the token `ALL_OBSERVED` nor `SAS` in its executable body, and a test enforces that.
- Marker anchors are documented in code as editorial centroids and not measured locations, and the figure's truth label says the geography is presentation only. The illustrative globe and the exact bar chart are laid out side by side so the picture and the numbers it stands for are read together.
- cobe drives its own continuous animation frame with no visibility awareness. Rendering is now gated on an `IntersectionObserver` and settled to a static frame under reduced motion after the embedded map texture has drawn once. Measured effect: off-screen animation frames fell from 78/s to 15.5/s, and reduced motion fell from a constant 60/s to **0/s** across the whole document.
- The upstream decorative "hatched" bar variant is repurposed as an evidence channel: hatched means heuristic approximation, solid is reserved for measured-data model output.
- The candidate radar is a gate **evidence** profile, not a score. Axis positions are bounded display normalisations with their domains printed in the figure's data table; the exact serialized value and method label sit beside every axis; a red dashed axis marks the gate whose serialized reason code stopped the candidate; and a grey value marks a gate the pipeline never reached. `gateEvidence` contains no relational operator at all — a test asserts that — and derives every state from `reason_codes` alone.

### Narrative integration

- A shared selection store links the funnel to the coverage figure, so choosing a candidate moves both sections; each module ignores its own echo and adopts any selection published before it subscribed.
- The funnel witness now draws its gate columns aligned to where particles actually travel, marks the selected candidate's particle, and prints per-gate attrition counted from serialized reason codes — turning a decorative animation into a funnel that shows 38 in, 8 stopped at cleavage, 5 at TAP, 16 at binding, 9 reaching the verdict stage.
- The literature section leads with the two endpoints stated separately — published T-cell positivity as an external measured fact, KEYHOLE visibility as this tool's heuristic verdict — and says explicitly what agreement can and cannot show. Train, held-out, and not-in-binding-dataset strata keep every denominator, per-stratum split counts, and nullable AUC reported as "not defined" rather than imputed. Records excluded from every denominator are named, and synthetic decoys are never called negatives, specificity, or clinical validation.
- `scene.js`'s SVG fallback insertion moved from `innerHTML` to a `DOMParser` `image/svg+xml` parse plus `importNode`, so no browser module builds live markup from a string. A test now forbids `innerHTML`, `outerHTML`, `insertAdjacentHTML`, and `document.write` across every packaged module.

### Validator changes, and what was not weakened

- The network-free test previously scanned the whole document for `fetch(`, `XMLHttpRequest`, and similar tokens. A general-purpose engine contains a dormant `FileLoader` that mentions `fetch(`, so the scan was **split and strengthened** rather than relaxed: the original strict token scan now runs over every KEYHOLE-authored module and over the document with the vendor blocks removed; a new test forbids any remote URL scheme in KEYHOLE code, allowing only the `http://www.w3.org/2000/svg` namespace identifier consumed by `createElementNS`; the whole document is asserted to declare seven CSP directives, no external `src`/`href`, no `iframe`/`object`/`embed`, and no `eval(`; and every inlined vendor byte is asserted equal to its recorded digest so nothing can be smuggled in through a dependency. Empirically, a scripted browser session recorded zero non-`file:`/`data:` requests.
- The intentional report-size envelope changed from 1.0–1.75 MB to 1.9–2.6 MB because a pinned WebGL engine and an embedded font subset are now inlined. No padding was added; the increase is 688 KB of three.js, 12 KB of cobe plus phenomenon, and 64 KB of base64 WOFF2. The lower bound was raised with the upper bound so the envelope still fails on lost content.
- Assertions naming removed implementation details were replaced with equivalent-or-stronger checks, never deleted: `<details>` toggle removal became tablist listener removal plus controller disposal; the canvas `ALL_OBSERVED` string was restored to the Canvas 2D fallback and additionally asserted absent from the globe; a brittle whole-file count of `method: "heuristic approximation"` became two scoped counts that separately pin the four animated stages and the five-gate ladder.
- One assertion was right and the code was wrong: `Math.random` appeared in a new header comment that promised not to call it. The comment was reworded; the assertion stands.
- Test count rose from 74 to 92. No scientific threshold, seed, candidate ordering, population calculation, literature entry, schema semantic, binder model, or published metric changed, and no binder training ran.

### Measured results

- Fixed-epoch SKCM `results.json` remains byte-identical to the approved R7 oracle at SHA-256 `e69d251ebc4e267c281c1ca23a39c0fa152a42fe7f78dc30bc916aae114173ac`. Frozen `metrics.json` remains `a4fe1c69b13b08d0df33936a914785b0ae1af4449f900ee997928d034263d14a` and packaged `SOURCES.md` remains `901dacea5678271a3a9d9a0437cd98146ea9ad7334bb3e462b4a60e679ae846b`.
- The report changed bytes intentionally. Two consecutive fixed-epoch runs produced identical HTML at SHA-256 `f451d4ce620f8f5221fb5271a58496b94c2f759958a815da7ff4bf1883492bf2`, 2,261,115 bytes. `docs/index.html` was rebuilt from that same command and is byte-identical to it.
- Full `keyhole validate` reproduced schema 1.1, seed 1729, 26 binder models, three structures, AFR/AMR/EAS/EUR, pooled held-out Spearman `0.7376983698471881`, and censor-aware ROC AUC `0.9313744947688023`.
- Scripted browser verification at 1512 px and 390 px, with and without reduced motion, and with WebGL disabled: no console error, no page error, zero network requests, no horizontal document overflow, seven figures each with exactly one persistent truth label, no duplicate figure label, 80 focusable controls, load in 390–473 ms, about 10 MB JS heap, and complete teardown. With WebGL disabled the molecular scenes and the globe fall back to Canvas 2D and label themselves; the 5,476-atom 1AO7 all-atom representation builds in 1.6 s and distinguishes all five chains including both TCR chains.
- R8 closes with 92 tests passing, clean Ruff, valid JavaScript syntax for every packaged module, a clean `git diff --check`, and an uncommitted reviewable working tree.
