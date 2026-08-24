# KEYHOLE demo script

Full pipeline on camera: input file, generation, the JSON contract, then the report. Target 5:00.

## There is nothing to prepare

Everything is typed live. Before you hit record, do only this:

```sh
cd /path/to/keyhole-immunology
rm -f demo.html demo.json r1.json r2.json
clear
```

Then make the terminal font large (20 px or more) and turn off notifications. That is the whole
setup. Do one silent rehearsal so you know where things are in the report, then record for real.

Every command below is short enough to type on camera without a typo. Nothing is piped through a
one-liner you would never write by hand.

---

## 0:00 to 0:12 — Cold open

**Show:** the finished report from your rehearsal, first fold. Drag the molecule through one slow
rotation. Then close it.

**Say:** "That's a real crystal structure. The blue tubes are a human HLA molecule. The gold chain
is a protein fragment sitting in its groove. This is how your immune system inspects a cell from
the inside. Everything after this is how that picture got made, from a real tumour file."

---

## 0:12 to 0:45 — The input

**Type:**

```sh
wc -l data/examples/tcga_skcm.maf
grep BRAF data/examples/tcga_skcm.maf
```

**Say:** "The input is a mutation annotation file. A hundred real rows from the TCGA melanoma
cohort, not a fixture I wrote. Here is the row that matters. BRAF. Chromosome 7, position
140453136. A missense SNP, A to T. Protein change V600E. That is the most famous mutation in
melanoma."

**Type:**

```sh
tail -n +3 data/examples/tcga_skcm.maf | cut -f8 | sort | uniq -c
```

**Say:** "Eighty-nine missense, nine nonsense, two splice-region. Remember those numbers for
thirty seconds."

---

## 0:45 to 1:15 — Everything it needs is already installed

**Type:**

```sh
ls src/keyhole/resources/data/iedb/binder/*.npz | wc -l
du -sh src/keyhole/resources/data
.venv/bin/keyhole validate
```

**Say:** "No reference download, no API key, no service. Twenty-six trained binding models, frozen
IEDB measurements, a half-million-peptide self sample, real HLA frequencies and three PDB
structures all ship inside the package. Eleven megabytes.

Validate proves they are the models I published. It reloads all of them and reproduces held-out
Spearman and censor-aware ROC AUC from the packaged data. Two seconds. No network, no retraining.
If those digits ever drift, the release is broken."

---

## 1:15 to 1:50 — Generate

**Type:**

```sh
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report demo.html --results demo.json
```

**Say:** "One command. Two and a half seconds.

Now read that audit line, because it is the honest part. A hundred rows in. Eighty-nine
protein-changing, which matches the missense count we just saw. Eleven ignored, which is the nine
nonsense plus the two splice-region rows. Then of the eighty-nine, eighty-seven get dropped,
because KEYHOLE has no frozen canonical protein sequence for those genes. It counts what it
discarded instead of inventing a sequence to fill the gap. Two variants survive, and they produce
thirty-eight peptide candidates."

---

## 1:50 to 2:30 — The JSON is the real output

**Type:**

```sh
ls -lh demo.json demo.html
less demo.json
```

Inside `less`, type `/SQHMTEVVRH` and press Enter, then press `k` twice so the two lines above come
into view. The whole candidate fits on one screen. Press `q` to quit when you are done.

(If you prefer, open `demo.json` in Kiro and use Cmd+F for the same string. It reads better with
syntax highlighting.)

**Say:** "Two files. A 362 kilobyte JSON and a 2.2 megabyte HTML.

The JSON is the contract. Python computes every scientific value once, validates it against a
schema, and writes it here. The HTML only draws it. Nothing in the browser recomputes a threshold
or a verdict.

Here is one candidate. Wild type ends in arginine. The mutant ends in histidine. That single change
is at the last position, which is an anchor the HLA molecule grips. Of the two alleles I supplied,
A star 29:02 barely binds it, 3,900 nanomolar. A star 30:02 binds it at 104. And agretopicity is
seventeen, meaning the mutant binds seventeen times better than the original sequence. The mutation
is what created the fit.

Every number is already decided, right here, before a single pixel exists."

**On screen:** `agretopicity: 17.04`, `best_allele: A*30:02`, `reason_codes: STRONG_BINDING,
FOREIGN_LIKE, MUTANT_BINDS_BETTER`, both alleles under `scores.binding`, `seq: SQHMTEVVRH`,
`verdict: VISIBLE_CLEAR`, `wt_seq: SQHMTEVVRR`.

---

## 2:30 to 2:50 — Determinism

**Type:**

```sh
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report r1.html --results r1.json
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report r2.html --results r2.json
shasum -a 256 r1.json r2.json r1.html r2.html
```

**Say:** "Same input, same seed, fixed timestamp. The JSON is byte for byte identical, and so is the
two-megabyte HTML. That is a release gate, not a nice property. This hash has survived eight
rewrites of the codebase, including a complete replacement of the front end."

**On screen:** four hashes, matching in pairs.

---

## 2:50 to 4:05 — Open it

**Type:**

```sh
.venv/bin/keyhole open demo.html
```

**Do:** scroll to section 01. Press *Replay candidate flow* and let it finish. Click `IGDFGLATE`
and hold on the gate ladder. Then click `SQHMTEVVRH` and hold again.

**Say:** "Thirty-eight candidates. One particle each. Four gates.

Eight stop at the proteasome. Five at the TAP channel. Sixteen at the HLA groove. Nine reach the
final check. Those are tallies of the reason codes we just read in the JSON. The browser can
explain a rejection. It cannot decide one.

Here is one that fails. TAP transport is 0.327 and that gate is red. Everything below it is grey,
because the pipeline stopped and never evaluated those gates. The number exists. The decision does
not. Most tools would just show you a bad score.

And here is the candidate from the JSON. Rank 0.94 percent, 104 nanomolar, foreignness 0.238,
seventeen times better than wild type. The same numbers, now with the gate that produced each one
and the method label beside it. Blue is the trained model. Everything else says heuristic
approximation."

---

## 4:05 to 4:30 — Who else could display it

**Do:** section 02, already showing the same candidate. Drag the globe once, then move to the bars.

**Say:** "Same candidate, different question. Thirty-seven percent of the African cohort, fifty-two
of the American, twenty-one East Asian, thirty-eight European. Real observed frequencies. Hatched
fill means heuristic. The aggregate is a cohort weighting and it is never drawn on the globe,
because it is not a place. South Asian data is reported absent, not zero, because the frozen panel
has none."

---

## 4:30 to 4:50 — Measured coordinates

**Do:** section 03. Click *A T cell reading the card*, rotate once, then *All displayed atoms*.

**Say:** "Back to measured coordinates. 1AO7, a T-cell receptor reading a peptide-HLA complex. Five
thousand four hundred and seventy-six atoms. Five chains, both receptor chains distinguished.
Nothing is moved to make the picture look better. Candidate geometry carries a different label and
is drawn translucent, so it cannot pass for a measurement."

---

## 4:50 to 5:15 — Reality check, offline, close

**Do:** section 04 strata table. Then open DevTools, Network tab, and reload. The URL bar shows
`file://` and the panel stays empty. Land on *What KEYHOLE refuses to claim*.

**Say:** "Last question. Does any of this agree with reality? Nine published T-cell positives,
eight called visible, stratified by whether the peptide was in the training data, with every
denominator shown. The shuffled controls are synthetic. They are not assayed negatives, and the
report says so.

One file, opened from disk. No server, no CDN. Watch the network panel on reload. Nothing.

It explains visibility. It does not diagnose, recommend treatment, or prove immunogenicity."

---

## 5:15 to 5:35 — Kiro

**Type:**

```sh
ls .kiro/specs
```

**Do:** open `.kiro/specs/r8-presentation-grade-report/requirements.md`, then
`.kiro/steering/invariants.md`, then scroll `DECISIONS.md`.

**Say:** "Eighteen spec boundaries, each with requirements, design and tasks, each closing with an
append-only decision entry. Four steering files applied on every turn. Law two is why every 3D
scene carries a truth label. Law seven is why coverage covers four populations instead of five:
the frozen panel has no South Asian data, so freeze a smaller real subset and never fake records."

---

## Cutting to 3:00

Drop the determinism beat, the packaged-assets commands, and the Kiro chapter. Keep the input file,
the audit line, the JSON candidate, both funnel candidates, and the close. Never cut the JSON beat.
It is the only thing that proves the browser is not doing the science.

## Do not say

- "Measured" alone when you mean "measured-data machine learning".
- "Negatives" for the shuffled controls. They are synthetic decoys with no assay.
- "Worldwide" or "global" for `ALL_OBSERVED`.
- "Structure" or "prediction" for the illustrative candidate geometry.
- Anything implying a patient. The HLA alleles are a command-line input.

## Do show

- A `file://` URL with the network panel visible during a reload.
- Drag, wheel zoom, an arrow key, and `Home` on one molecular scene.
- The OS reduced-motion toggle once, so the static evidence path is on camera.
- At least one truth label held long enough to read.
