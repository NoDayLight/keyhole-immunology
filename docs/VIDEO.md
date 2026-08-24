# KEYHOLE demo script

Full pipeline, input file to rendered report. Target 5:00. Narration is about 750 words, which
lands at a normal speaking pace. Every number below came from a real run, so it will match the
screen. Cut points to reach 3:00 are marked `[TRIM]`.

## Before you record

```sh
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf \
  --hla "A*29:02,A*30:02" --report /tmp/demo.html
open /tmp/demo.html    # scroll the whole page once so WebGL shaders compile, then close
rm /tmp/demo.html      # you will regenerate it on camera
```

- Terminal and browser side by side, or two takes cut together. Terminal at 20 px or larger.
- Browser about 1500 px wide so the desktop layout with the left rail shows.
- Clear scrollback. Notifications off. Hide bookmarks.
- `cd` into the repo root before you start, so every path on screen is relative and short.
- Two candidates matter in section 01: `IGDFGLATE` fails, `SQHMTEVVRH` works.

## 0:00 to 0:12 — Cold open

No title card, no introduction.

**Do:** Open on the finished report's first fold. Drag the hero molecule through one slow rotation.

**Say:** "That's a real crystal structure. The blue tubes are a human HLA molecule. The gold chain
is a protein fragment sitting in its groove. This is how your immune system inspects a cell from
the inside. Everything after this is how that picture got made."

## 0:12 to 0:45 — The input is a real tumour file

**Do:** Terminal. Run these three, pausing on each.

```sh
wc -l data/examples/tcga_skcm.maf
sed -n '2p' data/examples/tcga_skcm.maf | tr '\t' '\n' | nl
awk -F'\t' 'NR==2{split($0,h,"\t")} $1=="BRAF"{
  for (i in a) delete a[i]
  printf "%-24s %s\n", h[1],$1;  printf "%-24s %s\n", h[5],$5
  printf "%-24s %s\n", h[6],$6;  printf "%-24s %s\n", h[8],$8
  printf "%-24s %s\n", h[10],$10; printf "%-24s %s\n", h[11],$11
  printf "%-24s %s\n", h[13],$13; exit}' data/examples/tcga_skcm.maf
```

**Say:** "The input is a mutation annotation file. A hundred real rows from the TCGA melanoma
cohort, not a fixture I wrote. Seventeen columns, and KEYHOLE needs seven of them. Here is the row
that matters: BRAF, chromosome 7, position 140453136, a missense SNP, A to T, protein change
V600E. That is the most famous mutation in melanoma, and it came out of a real patient cohort."

**On screen:** `101` lines, the 17 column names, then
`BRAF 7 140453136 Missense_Mutation A T V600E`.

## 0:45 to 1:15 — Everything it needs is already in the package

**Do:**

```sh
ls src/keyhole/resources/data/iedb/binder/*.npz | wc -l
du -sh src/keyhole/resources/data
.venv/bin/keyhole validate
```

**Say:** "No reference download, no API key, no service. Twenty-six trained binding models,
frozen IEDB measurements, a half-million-peptide self sample, real HLA frequencies and three PDB
structures all ship inside the wheel. Eleven megabytes.

Validate proves they are the models I published. It reloads them and reproduces held-out Spearman
and censor-aware ROC AUC from the packaged data. Two seconds, no network, no retraining. If those
digits ever drift, the release is broken."

**On screen:** `26`, `11M`, then
`spearman=0.7376983698471881 roc_auc_500nm=0.9313744947688023`.

## 1:15 to 1:45 — Generate the report

**Do:**

```sh
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf \
  --hla "A*29:02,A*30:02" \
  --report demo.html --results demo.json
```

Then, to make the audit line checkable:

```sh
awk -F'\t' 'NR>2{n[$8]++} END{for(k in n) print n[k], k}' data/examples/tcga_skcm.maf
```

**Say:** "One command. Two and a half seconds.

Read that audit line, because it is the honest part. A hundred rows in. Eighty-nine are
protein-changing. Eleven are ignored, and you can check that: nine nonsense and two splice-region
mutations, which do not produce a clean substituted peptide. Of the eighty-nine, eighty-seven get
dropped because KEYHOLE has no frozen canonical protein sequence for those genes. It counts what
it discarded instead of inventing a sequence to fill the gap. Two variants survive, and they
produce thirty-eight peptide candidates."

**On screen:**
`input_rows=100 supported_changes=89 screenable=2 missing_canonical_context=87 ignored_classes=11`,
`candidates=38`, then `89 Missense_Mutation / 9 Nonsense_Mutation / 2 Splice_Region`.

## 1:45 to 2:20 — What actually came out, and why the JSON comes first

**Do:**

```sh
ls -lh demo.json demo.html
python3 -c "import json;d=json.load(open('demo.json'));print(list(d))"
python3 -c "
import json;d=json.load(open('demo.json'))
p=[x for m in d['mutations'] for x in m['peptides'] if x['seq']=='SQHMTEVVRH'][0]
print(json.dumps(p, indent=2))"
```

**Say:** "Two artifacts. A 362 kilobyte JSON file and a 2.2 megabyte HTML file.

The JSON is the contract. Python computes every scientific value once, validates it against a
schema, and writes it here. The HTML only draws it. Nothing in the browser recomputes a threshold
or a verdict.

Look at one candidate. Wild type ends in arginine, the mutant ends in histidine. That single
change is at the last position, which is an anchor the HLA molecule grips. Of the two alleles I
supplied, A star 29:02 barely binds it at 3,900 nanomolar. A star 30:02 binds it at 104. And
agretopicity is seventeen, meaning the mutant binds seventeen times better than the original
sequence. The mutation is what created the fit. Every one of those numbers is already decided,
here, before any pixel exists."

**On screen:** `362K demo.json`, `2.2M demo.html`, the six top-level keys, then the candidate
block: `SQHMTEVVRH` / `SQHMTEVVRR`, `VISIBLE_CLEAR`, `A*30:02`, `agretopicity: 17.04`,
`STRONG_BINDING, FOREIGN_LIKE, MUTANT_BINDS_BETTER`.

## 2:20 to 2:40 — Determinism `[TRIM]`

**Do:**

```sh
for i in 1 2; do SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen \
  --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" \
  --report r$i.html --results r$i.json; done
shasum -a 256 r1.json r2.json r1.html r2.html
```

**Say:** "Same input, same seed, fixed timestamp. Both the JSON and the two-megabyte HTML come out
byte for byte identical. That is a release gate, not a nice property. The melanoma hash has been
stable across eight rewrites of this codebase, including a full front-end replacement."

**On screen:** two identical JSON hashes, two identical HTML hashes.

## 2:40 to 3:55 — Open it. The funnel, and two candidates.

**Do:** `.venv/bin/keyhole open demo.html`. Scroll to section 01. Press *Replay candidate flow*
and let it finish. Click `IGDFGLATE`, hold on the gate ladder. Click `SQHMTEVVRH`, hold again.

**Say:** "Thirty-eight candidates. One particle each. Four gates.

Eight stop at the proteasome. Five at the TAP channel. Sixteen at the HLA groove. Nine reach the
final check. Those are tallies of the reason codes we just read in the JSON. The browser can
explain a rejection. It cannot decide one.

Here is one that fails. TAP transport is 0.327, and that gate is red. Everything below it is grey,
because the pipeline stopped and never evaluated those gates. The number exists. The decision does
not. Most tools would just show you a bad score.

And here is the one from the JSON. Rank 0.94 percent, 104 nanomolar, foreignness 0.238, seventeen
times better than wild type. Same numbers, now with the gate that produced each one, and the
method label next to it. Blue is the trained model. Everything else says heuristic
approximation."

**On screen:** attrition `38 in / 8 stopped`, `30 / 5`, `25 / 16`, `9 / 0`. Then `IGDFGLATE` with a
red TAP row and grey values beneath. Then `SQHMTEVVRH`, `VISIBLE CLEAR`, and the radar with one
`measured ML` axis among four heuristics.

## 3:55 to 4:20 — Who else could display it

**Do:** Section 02, already showing the same candidate. Drag the globe once. Move to the bar chart.

**Say:** "Same candidate, different question. Thirty-seven percent of the African cohort,
fifty-two of the American, twenty-one East Asian, thirty-eight European. Real observed
frequencies. Hatched fill means heuristic. The aggregate is a cohort weighting and it is never
drawn on the globe, because it is not a place. South Asian data is reported absent, not zero,
because the frozen panel has none."

**On screen:** AFR 37.47, AMR 52.40, EAS 20.67, EUR 38.28, ALL_OBSERVED 35.64, and the SAS note.

## 4:20 to 4:40 — Measured coordinates

**Do:** Section 03. Click *A T cell reading the card*, rotate once, switch to *All displayed
atoms*. Cut back to a candidate scene.

**Say:** "Back to measured coordinates. 1AO7, a T-cell receptor reading a peptide-HLA complex.
Five thousand four hundred and seventy-six atoms, five chains, both receptor chains distinguished.
Nothing is moved to make the picture look better. Candidate geometry gets a different label and is
drawn translucent, so it cannot pass for a measurement."

## 4:40 to 5:05 — Reality check, offline proof, close

**Do:** Section 04 strata table. Then in terminal:

```sh
grep -coE '<(script|link)[^>]+(src|href)=' demo.html
```

Then open DevTools Network and reload the `file:` URL. Land on *What KEYHOLE refuses to claim*.

**Say:** "Last question. Does any of this agree with reality? Nine published T-cell positives,
eight called visible, stratified by whether the peptide was in the training data, with every
denominator shown. The shuffled controls are synthetic. They are not assayed negatives, and the
report says so.

Zero external references in the file. No server, no CDN. Watch the network panel on reload.
Nothing.

It explains visibility. It does not diagnose, recommend treatment, or prove immunogenicity."

**On screen:** `8 / 9`, the three exposure strata, `0` from the grep, an empty network panel beside
a `file://` URL, then the refusal list.

## 5:05 to 5:25 — Kiro

**Do:** `ls .kiro/specs | wc -l`, then open `.kiro/specs/r8-presentation-grade-report/requirements.md`,
then `.kiro/steering/invariants.md`, then scroll `DECISIONS.md`.

**Say:** "Eighteen spec boundaries, each with requirements, design and tasks, each closing with an
append-only decision entry. Four steering files applied on every turn. Law two is why every 3D
scene in this report carries a truth label. Law seven is why coverage covers four populations
instead of five: the frozen panel has no South Asian data, so freeze a smaller real subset and
never fake records."

## Trimming to 3:00

Cut the determinism beat, the package-contents commands, and the Kiro chapter. Keep the input file,
the audit line, the JSON candidate, both funnel candidates, and the close. The JSON beat is the one
never to cut: it is what proves the browser is not doing the science.

## Do not say

- "Measured" alone when you mean "measured-data machine learning".
- "Negatives" for the shuffled controls. They are synthetic decoys with no assay.
- "Worldwide" or "global" for `ALL_OBSERVED`.
- "Structure" or "prediction" for the illustrative candidate geometry.
- Anything implying a patient. The HLA alleles are a command-line input.

## Do show

- A `file://` URL at least once, with the network panel visible during a reload.
- Drag, wheel zoom, an arrow key, and `Home` on one molecular scene.
- The OS reduced-motion toggle once, so the static evidence path is on camera.
- At least one truth label held long enough to read.
