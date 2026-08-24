# PROJECT KEYHOLE

Every cell displays fragments of its own proteins like ID cards for immune inspection; cancer corrupts some of those cards. KEYHOLE reads supported variants from a real tumor file and produces a single, inspectable report showing which mutation-derived peptide cards may be visible through the supplied HLA keyholes.

KEYHOLE is a deterministic, offline-after-install comprehension tool—not a clinical predictor. Its report combines measured-data binding ML with explicitly labeled heuristic approximations, real frozen population marginals, published-positive assay context, and truth-labeled molecular scenes.

## Quickstart (three commands)

Requires **CPython 3.11**. From this repository:

```sh
python3.11 -m venv .venv && .venv/bin/pip install .
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla 'A*02:01,B*07:02' --report out.html
.venv/bin/keyhole open out.html
```

The second command produces one self-contained HTML file (about 2.3 MB): no server, sidecar, CDN, credentials, or runtime network request. A prebuilt deterministic SKCM report is also the [Pages-ready demo](docs/index.html).

## Commands

```sh
keyhole validate --quick              # package, schema, 26 models, populations, literature, PDBs
keyhole validate                      # also reproduces held-out Spearman and censor-aware ROC AUC
keyhole explain 'BRAF V600E' --hla 'A*02:01' --report braf.html
keyhole screen --vcf tumor.vcf --hla 'A*02:01,B*07:02' --report out.html --results results.json
keyhole open                           # opens ./out.html as a local file URI
```

`validate` reproduces pooled held-out Spearman **0.7376983698471881** and ROC AUC at 500 nM **0.9313744947688023** from 9,133 held-out rows (9,132 ROC-evaluable; one censor-bound row is indeterminate).

### Input contract

MAF input requires `Hugo_Symbol`, `Chromosome`, `Start_Position`, `Reference_Allele`, `Tumor_Seq_Allele2`, `Variant_Classification`, and `HGVSp_Short`; `Tumor_Sample_Barcode` is optional. Annotated VCF requires `GENE` or `SYMBOL` plus `HGVSP`/`HGVSP_SHORT`, or a standard `ANN` field. The frozen canonical sequence set resolves BRAF V600E, KRAS G12D, and TP53 R175H. Other parsed rows remain in the audit but receive no invented sequence or verdict.

Supported models: `A*01:01`, `A*02:01`, `A*03:01`, `A*11:01`, `A*23:01`, `A*24:02`, `A*29:02`, `A*30:01`, `A*30:02`, `A*31:01`, `A*33:01`, `A*68:01`, `B*07:02`, `B*08:01`, `B*15:01`, `B*18:01`, `B*27:05`, `B*35:01`, `B*40:01`, `B*44:02`, `B*44:03`, `B*46:01`, `B*51:01`, `B*53:01`, `B*57:01`, and `B*58:01`. HLA-C*08:02 remains truthfully unsupported.

## What the report means

- **Binding — measured-data ML:** 26 independent deterministic PyTorch MLPs trained on 95,441 frozen quantitative IEDB HLA-A/B measurements. Patient verdicts use only supplied HLA alleles; all 26 are evaluated separately for population evidence.
- **Processing, foreignness, agretopicity interpretation, and verdict — heuristic approximation:** transparent fixed calculations, not measured antigen processing or T-cell response.
- **Population coverage — heuristic approximation:** seed-1729 Monte Carlo over observed AFR/AMR/EAS/EUR HLA-A/B marginals, assuming A–B linkage equilibrium and Hardy-Weinberg because phased haplotypes are unavailable. `ALL_OBSERVED` is cohort-weighted, not worldwide coverage. SAS is absent rather than fabricated.
- **Literature panel:** 10 real published-positive IEDB T-cell records; 9 are evaluable by the A/B model panel. Composition-preserving shuffled controls are synthetic decoys, never assayed negatives. Agreement is stratified honestly into exact peptide–allele overlaps used for training, overlapping held-out validation/test assignments, and positives absent from the binder dataset; hash assignment alone is not called training exposure.
- **Molecular scenes:** `Real crystal structure (PDB id)` means untouched experimental PDB coordinates. `Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative` means the candidate sequence is mapped onto the measured 1HHK chain-C Cα template; 10-mer interpolation and the mutation side-chain marker are illustrative—not measured candidate coordinates, folded predictions, or HLA docking.

## Reading the report

The report is one continuous argument, numbered once in the left rail:

| # | Section | What it answers |
|---|---------|-----------------|
| 00 | Overview | How many candidate cards exist, how many are predicted visible, and the exact command that produced the file |
| 01 | Visibility funnel | Which candidates survive proteasome cleavage, TAP transport, HLA binding, and the self-scan, and exactly why each rejection happened |
| 02 | Population coverage | How much of each observed cohort carries a modeled allele that could display the selected candidate |
| 03 | Molecular keyhole | What the measured peptide–HLA and TCR–peptide–HLA coordinates actually look like |
| 04 | Reality check | How KEYHOLE visibility compares with published T-cell positivity, stratified by binder-dataset exposure |
| 05 | Methods and limits | Every method label, frozen source, and refusal |

Every figure carries the same anatomy: a caption, a **persistent truth label** (`measured` or
`illustrative`) that cannot scroll out of view, a viewport, a legend explaining every colour
channel, a live status line, and a disclosure containing the exact serialized values behind
the picture. Selecting a candidate in section 01 also drives section 02, so one choice moves
the whole narrative.

Typography carries meaning: IBM Plex Serif sets prose and figure captions, the installed
monospace face sets **every number, sequence, allele, and truth label**, and the installed UI
sans is reserved for controls. Solid chart fills mean measured-data model output; hatched
fills mean heuristic approximation.

Interaction: drag or swipe to orbit any molecular scene, wheel or `±` to zoom, arrow keys to
rotate, `Home` to reset. `prefers-reduced-motion` disables every animation and opens the
static evidence instead. Without WebGL, the scenes fall back to the Canvas 2D coordinate
renderer and say so; without any canvas, the exact tables remain the complete evidence.

## Offline browser runtime

The report inlines four byte-exact, locally packaged third-party components. There is no CDN,
runtime import, remote texture, external font, or network request of any kind, and the
document's `Content-Security-Policy` sets `default-src 'none'` and `connect-src 'none'`.

| Component | Version | License | Role |
|-----------|---------|---------|------|
| [three.js](https://github.com/mrdoob/three.js) | 0.169.0 | MIT | WebGL molecular renderer: instanced ball-and-stick, backbone tubes, studio lighting |
| [cobe](https://github.com/shuding/cobe) | 0.6.4 | MIT | WebGL coverage globe, including its embedded data-URI dot map |
| [phenomenon](https://github.com/vaneenige/phenomenon) | 1.6.0 | MIT | cobe's WebGL instancing runtime |
| [IBM Plex Serif](https://github.com/IBM/plex) | 2.0.0 | SIL OFL 1.1 | Weight-400 upright and italic Latin1 WOFF2 subsets, embedded as base64 |

The radar and bar figures reimplement the composable structure and visual grammar of the
[Bklit UI radar chart](https://bklit.com/docs/components/radar-chart) and the
[EvilCharts Recharts bar chart](https://evilcharts.com/docs/recharts/bar-chart/static) as
plain accessible SVG, because both upstreams are React component libraries that cannot run
inside a build-free single file.

Exact upstream URLs, npm integrity values, retained members, SHA-256 digests, license texts,
and the reasoning behind each pin are recorded in
[`src/keyhole/resources/vendor/PROVENANCE.md`](src/keyhole/resources/vendor/PROVENANCE.md).
Every digest is verified on every render, and report assembly fails loudly rather than
silently adapting to a changed dependency.

## What this does NOT do

KEYHOLE does **not** diagnose cancer, recommend treatment, predict checkpoint response, prove peptide presentation or immunogenicity, replace clinical HLA typing, model HLA-C, infer missing protein sequences, estimate worldwide demographic coverage, perform peptide–HLA docking, or claim illustrative geometry is molecular structure. Results require experimental and clinical validation and are not medical advice.

## Determinism and offline operation

All stochastic work uses seed `1729`. Set `SOURCE_DATE_EPOCH` to fix report creation time and obtain byte-identical JSON/HTML across repeated runs:

```sh
SOURCE_DATE_EPOCH=1787529600 keyhole screen --maf data/examples/tcga_skcm.maf --hla 'A*02:01,B*07:02' --report out.html --results results.json
```

Scientific data, 26 safe-array NPZ models, browser modules, the stylesheet, the vendored browser runtime, validation fixture, and three PDBs are wheel-owned resources. The current directory cannot shadow them. `KEYHOLE_DATA=/absolute/complete/data-root` is an explicit advanced override; it must contain the documented `SOURCES.md` and full runtime layout. Browser assets are never overridden. Training requires an explicit writable `output_dir` and never writes into installed resources.

## Sources, terms, and citations

Complete frozen URLs, transformations, counts, hashes, license/terms notes, and citations are in [`src/keyhole/resources/data/SOURCES.md`](src/keyhole/resources/data/SOURCES.md). Core references include:

- Kim et al., BMC Bioinformatics 2014, [DOI 10.1186/1471-2105-15-241](https://doi.org/10.1186/1471-2105-15-241); Vita et al., NAR 2019, [DOI 10.1093/nar/gky1006](https://doi.org/10.1093/nar/gky1006) — IEDB binding/assay data (CC BY 4.0 terms noted in provenance).
- UniProt Consortium, NAR 2025, [DOI 10.1093/nar/gkae1010](https://doi.org/10.1093/nar/gkae1010) — human proteins/self peptides (CC BY 4.0).
- Gourraud et al., PLOS ONE 2014, [DOI 10.1371/journal.pone.0097282](https://doi.org/10.1371/journal.pone.0097282); Brandt et al., G3 2015, [DOI 10.1534/g3.115.016949](https://doi.org/10.1534/g3.115.016949) — HLA observations. The authors’ data repository declares no separate license; KEYHOLE records attribution and does not assert broader rights.
- Berman et al., NAR 2000, [DOI 10.1093/nar/28.1.235](https://doi.org/10.1093/nar/28.1.235) — PDB/wwPDB structures (CC0).
- Henikoff & Henikoff, PNAS 1992, [DOI 10.1073/pnas.89.22.10915](https://doi.org/10.1073/pnas.89.22.10915) — BLOSUM62.

TCGA/cBioPortal examples retain original study and GDC data-use terms. Review the provenance file before redistribution. This repository does not invent a blanket license for third-party assets.

## How this was built with Kiro

KEYHOLE was written in Kiro across 18 spec boundaries, kept in [`.kiro/`](.kiro). Every
boundary has `requirements.md`, `design.md`, and `tasks.md`, and closes with an append-only
entry in [`DECISIONS.md`](DECISIONS.md) recording what changed, what was measured, and what was
refused. Reading `DECISIONS.md` top to bottom is the honest history of the project, including
the parts that went wrong.

Four steering files in [`.kiro/steering/`](.kiro/steering) applied on every turn and did the
real work of keeping the science honest under time pressure. `invariants.md` is the important
one. Its second law says every 3D scene must be visibly labelled either
`Real crystal structure (PDB <id>)` or as illustrative, which is why no molecular figure in the
report can lose its truth label. Its seventh law says that when an upstream source is
unreachable, freeze a smaller documented real subset and never fake records. That law is why
population coverage covers four superpopulations instead of five: the frozen 1000 Genomes HLA
panel has no South Asian observations, so the report says SAS is absent rather than reporting
zero.

Two agent hooks in [`.kiro/hooks/`](.kiro/hooks) enforced the gates without being asked.
`check-python-source.json` runs Ruff and a fail-fast pytest after any Kiro edit that touches
`src/` or `tests/`. `full-suite-report-smoke.json` runs the full suite, quick validation, and an
end-to-end offline report build when an agent execution stops. Several regressions died in the
hook rather than in a commit.

Some specific places where the spec-first loop changed the code rather than just documenting it:

- **S1 froze a smaller real dataset instead of a bigger fake one.** The documented IEDB archive
  URL returned HTTP 404. The failure, the substitute official host, and the upstream hash are
  all recorded in provenance rather than papered over.
- **S6 rejected a dependency, R8 accepted one on conditions.** The first 3D renderer was a local
  Canvas 2D projection engine, chosen to avoid a CDN and a Node toolchain. R8 replaced it with
  real WebGL only after proving that an exact-pinned three.js build could be inlined byte-exact
  with no network request, and the old engine stayed as the truthful fallback.
- **R8 caught two of its own mistakes.** A structure tab labelled PDB 3PWN as a TCR complex,
  which contradicts the S6 decision entry stating that 3PWN contains no TCR chains. A new source
  comment promising never to call `Math.random` tripped the test that forbids `Math.random`. The
  test was right, so the comment changed.

## Development and release gates

```sh
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/keyhole validate
```

The S8 release gate additionally builds and inspects the wheel, installs it into a clean Python 3.11 environment, changes to an unrelated directory with `KEYHOLE_DATA` unset, runs full validation and the SKCM screen, verifies deterministic bytes and network-free HTML, and opens the report as a local file URI. See [`docs/VIDEO.md`](docs/VIDEO.md) for the demo storyboard and [`DECISIONS.md`](DECISIONS.md) for append-only scientific/engineering decisions.
