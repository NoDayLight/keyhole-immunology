# KEYHOLE demo script

Target 2:50. Narration is roughly 440 words, which lands at a normal speaking pace. Every number
below comes from the exact command in "Before you record", so it will match what is on screen.

## Before you record

```sh
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf \
  --hla "A*29:02,A*30:02" --report /tmp/demo.html
```

This scenario gives 2 clear, 7 faint, 29 invisible, which is a real story. The committed
`docs/index.html` uses `A*02:01,B*07:02` and returns 38 invisible, which is truthful but flat.

- Open `/tmp/demo.html` once and scroll the whole page before recording, so WebGL shaders compile
  and the funnel has already run. Then reload for the take.
- 1440p or higher. Browser at ~1500 px wide so the desktop layout with the left rail shows.
- Terminal at 20 px or larger. Clear scrollback.
- Notifications off. Hide bookmarks. Neutral wallpaper.
- Two candidates to have ready in section 01: `IGDFGLATE` (fails) and `SQHMTEVVRH` (works).

## Shot list

### 0:00 to 0:14 — Cold open, no title card

**Do:** Start on the report's first fold. Drag the hero molecule through one slow rotation.

**Say:** "That's a real crystal structure. The blue tubes are a human HLA molecule. The gold chain
is a protein fragment sitting in its groove. This is how your immune system inspects a cell from
the inside."

### 0:14 to 0:34 — Terminal, validate

**Do:** Cut to terminal. Run `.venv/bin/keyhole validate`. Hold on the metrics line.

**Say:** "Cancer mutations corrupt some of those fragments. KEYHOLE reads a real tumour file and
works out which corrupted fragments a given set of HLA molecules could actually display.
Twenty-six binding models ship inside the package. Validation reproduces held-out Spearman and
censor-aware ROC AUC from frozen data. No network, no retraining."

**On screen:** `spearman=0.7376983698471881`, `roc_auc_500nm=0.9313744947688023`.

### 0:34 to 0:56 — Terminal, screen, then the audit ladder

**Do:** Run the screen command. Let the summary line land. Cut to the report's audit ladder and
track down the four numbers.

**Say:** "One hundred real TCGA melanoma rows. Eighty-seven get dropped, because KEYHOLE has no
frozen canonical protein sequence for those genes. It counts what it threw away instead of
inventing a sequence to fill the gap. Two variants survive and produce thirty-eight peptide
candidates. The report repeats the same four numbers."

**On screen:** `input_rows=100 supported_changes=89 screenable=2 missing_canonical_context=87`,
then 100 / 89 / 2 / 38 in the ladder.

### 0:56 to 1:40 — The funnel, and two candidates

**Do:** Section 01. Press *Replay candidate flow*, let it finish. Then click `IGDFGLATE`, pause on
the gate ladder. Then click `SQHMTEVVRH` and pause again.

**Say:** "Thirty-eight candidates. One particle each. Four gates. Eight stop at the proteasome,
five at the TAP channel, sixteen at the HLA groove, nine reach the final check. Those are tallies
of reason codes Python already wrote. The browser never re-applies a threshold, so it can explain
a rejection but it cannot decide one.

Here is one that fails. TAP transport is 0.327, and that gate is red. Everything below it is grey,
because the pipeline stopped and never evaluated those gates. The number exists. The decision does
not.

And here is one that works. From TP53 R175H. Rank 0.94 percent, 104 nanomolar, foreignness 0.238.
And it binds seventeen times better than the wild-type sequence, which is the interesting part.
The mutation is what created the fit."

**On screen:** attrition `38 in / 8 stopped`, `30 / 5`, `25 / 16`, `9 / 0`. Then `IGDFGLATE` with a
red TAP row at 0.327 and grey values beneath. Then `SQHMTEVVRH`, `VISIBLE CLEAR`, `A*30:02 0.94%
rank · 104.4 nM`, `17.04x`, reason codes `STRONG_BINDING, FOREIGN_LIKE, MUTANT_BINDS_BETTER`.

### 1:40 to 2:05 — Population coverage

**Do:** Section 02, already showing `SQHMTEVVRH`. Drag the globe once. Move to the bar chart.

**Say:** "Same candidate, different question. Who else could display it? Thirty-seven percent of
the African cohort, fifty-two of the American, twenty-one East Asian, thirty-eight European. Real
observed frequencies. Hatched fill means heuristic. The aggregate is a cohort weighting and it is
never drawn on the globe, because it is not a place. South Asian data is reported absent, not
zero."

**On screen:** AFR 37.47, AMR 52.40, EAS 20.67, EUR 38.28, ALL_OBSERVED 35.64, and the SAS note
under the coverage table.

### 2:05 to 2:25 — Measured structures

**Do:** Section 03. Click *A T cell reading the card*, rotate once, then *All displayed atoms*.
Finish on a candidate scene from section 01.

**Say:** "Back to measured coordinates. This is 1AO7, a T-cell receptor reading a peptide-HLA
complex. Five thousand four hundred and seventy-six atoms, five chains, both receptor chains
distinguished. Nothing is moved to make the picture look better. Candidate geometry gets a
separate label and is drawn translucent, so it cannot pass for a measurement."

**On screen:** the five-chain legend, `5476 displayed atom positions`, then the illustrative truth
label on the candidate scene.

### 2:25 to 2:50 — Reality check, offline proof, close

**Do:** Section 04 strata table. Then open DevTools Network and reload the `file:` URL. Land on
*What KEYHOLE refuses to claim*.

**Say:** "Last question. Does any of this agree with reality? Nine published T-cell positives,
eight called visible. Stratified by whether the peptide was in the training data, with every
denominator shown. The shuffled controls are synthetic. They are not assayed negatives, and the
report says so.

One file. No server. Watch the network panel. Nothing.

It explains visibility. It does not diagnose, recommend treatment, or prove immunogenicity."

**On screen:** `8 / 9`, the three exposure strata, an empty network panel next to a `file://` URL,
then the refusal list.

## Optional 15-second Kiro coda

**Do:** `.kiro/specs/` with 18 folders, open `r8-presentation-grade-report/requirements.md`, then
`.kiro/steering/invariants.md`.

**Say:** "Eighteen spec boundaries. Each has requirements, design and tasks, and closes with a
decision entry. Four steering files applied on every turn. Law two is why every 3D scene in this
report carries a truth label. Law seven is why coverage covers four populations instead of five."

## Do not say

- "Measured" on its own when you mean "measured-data machine learning".
- "Negatives" for the shuffled controls. They are synthetic decoys with no assay.
- "Worldwide" or "global" for `ALL_OBSERVED`.
- "Structure" or "prediction" for the illustrative candidate geometry.
- Any phrasing that implies a patient. The HLA alleles are a command-line input.

## Do show

- A `file://` URL at least once, with the network panel visible during a reload.
- Drag, wheel zoom, an arrow key, and `Home` on one molecular scene.
- The OS reduced-motion toggle once, so the static evidence path is on camera.
- At least one truth label held long enough to read.
