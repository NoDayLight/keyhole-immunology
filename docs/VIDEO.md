# KEYHOLE demo script — 3 minutes

Strictly chronological. Nothing exists when you start. You type commands, the report gets built,
then you open it. No teaser shot, no pre-made artifacts, no editing required.

**Screen layout:** Ghostty full screen for the first half. When you run the last command a browser
opens on top, and you stay there for the second half.

**Before you hit record:**

```sh
cd ~/Documents/kiro_hackathon_project
rm -f demo.html demo.json
clear
```

Big terminal font, notifications off. Do one silent practice run so you know where the report's
sections are, then delete `demo.html` again and record for real.

**If a command ever takes over the screen and you cannot type:** press `q`. If nothing happens,
press `Ctrl+C` then `q`. Nothing in this script needs that, because every command prints its output
and returns to the prompt on its own.

**To start over at any point:** `rm -f demo.html demo.json && clear`, then begin again from 0:00.
Nothing is left behind and nothing outside this folder changes.

---

# PART 1 — TERMINAL

## 0:00 · What goes in

**Type:**

```sh
wc -l data/examples/tcga_skcm.maf
grep BRAF data/examples/tcga_skcm.maf
tail -n +3 data/examples/tcga_skcm.maf | cut -f8 | sort | uniq -c
```

**Say:**

> This is a real tumour file. A hundred mutation rows from the TCGA melanoma cohort.
> KEYHOLE works out which of these the immune system could actually see.
> Here's the row that matters. BRAF, chromosome 7, a missense SNP, A to T, V600E.
> The most famous mutation in melanoma.
> Eighty-nine missense, nine nonsense, two splice. Hold those numbers.

## 0:30 · It already has everything it needs

**Type:**

```sh
.venv/bin/keyhole validate
```

**Say:**

> Twenty-six trained binding models and all the reference data ship inside the package.
> No download, no API key, no service.
> Validate reloads them and reproduces held-out Spearman and ROC AUC from frozen data.
> Two seconds.

## 0:48 · Build the report

**Type:**

```sh
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report demo.html --results demo.json
```

**Say:**

> One command. Two and a half seconds.
> Read the audit line. Eighty-nine protein-changing, matching the missense count.
> Eleven ignored: the nonsense and splice rows.
> Then eighty-seven dropped, because there's no frozen canonical protein sequence for those genes.
> It counts what it discarded instead of inventing one.
> Two variants survive. Thirty-eight candidates.

## 1:12 · What came out

**Type:**

```sh
ls -lh demo.json demo.html
grep -B 2 -A 27 '"candidate_key": "SQHMTEVVRH"' demo.json
```

That prints the whole candidate, 30 lines, and drops you straight back at the prompt. No pager, no
keys to remember, and the output stays on screen while you talk over it.

**Say:**

> Two files. The JSON is the contract.
> Python computes every value once and validates it. The HTML only draws it.
> One candidate. Wild type ends in arginine, the mutant in histidine.
> That's the last position, an anchor the HLA molecule grips.
> One of my two alleles barely binds it. The other binds at 104 nanomolar.
> Seventeen times better than wild type.

---

# PART 2 — THE REPORT

## 1:36 · Open it

**Type:**

```sh
.venv/bin/keyhole open demo.html
```

A browser opens. Drag the molecule in the top right through one slow rotation.

**Say:**

> That's the report. One file, no server.
> And that is a real crystal structure. Blue is a human HLA molecule.
> The gold chain is a peptide sitting in its groove.

## 1:52 · The funnel

Scroll to section 01. Press **Replay candidate flow** and let it finish.
Then click `IGDFGLATE` in the list. Then click `SQHMTEVVRH`.

**Say:**

> Thirty-eight candidates, one particle each, four gates.
> Eight stop at the proteasome, five at TAP, sixteen at the HLA groove, nine reach the final check.
> Those are tallies of the reason codes we just read in the JSON.
> The browser explains a rejection. It never decides one.
> Here's a failure. TAP is 0.327, that gate is red, everything below it is grey because the pipeline stopped there.
> And here's the candidate from the JSON, with the gate behind every number.

## 2:26 · Coverage

Scroll to section 02. Drag the globe once, then look at the bars.

**Say:**

> Same candidate, different question.
> Thirty-seven percent of the African cohort, fifty-two American, twenty-one East Asian, thirty-eight European.
> Hatched means heuristic.
> The aggregate is never drawn on the globe, because it isn't a place.

## 2:42 · Structures

Scroll to section 03. Click **A T cell reading the card**, rotate it, then click **All displayed atoms**.

**Say:**

> Measured coordinates. A T-cell receptor reading a peptide-HLA complex.
> Five thousand four hundred and seventy-six atoms, five chains.
> Nothing moved to make the picture look better.

## 2:54 · Offline, and the limits

Open DevTools, Network tab, reload the page. Then scroll to **What KEYHOLE refuses to claim**.

**Say:**

> Opened straight from disk. Watch the network panel on reload. Nothing.
> It explains visibility.
> It does not diagnose, recommend treatment, or prove immunogenicity.

## 3:06 · Kiro

Back to the terminal.

**Type:**

```sh
ls .kiro/specs
```

Then open `.kiro/steering/invariants.md`.

**Say:**

> Eighteen spec boundaries, each with requirements, design and tasks. Four steering files.
> Law two is why every 3D scene carries a truth label.
> Law seven is why coverage covers four populations, not five.

---

## Never say

- "Measured" on its own. Say "measured-data machine learning".
- "Negatives" for the shuffled controls. They are synthetic decoys with no assay.
- "Worldwide" for `ALL_OBSERVED`.
- "Structure" or "prediction" for the illustrative candidate geometry.
- Anything implying a patient. The HLA alleles are a command-line argument.

## If you run long

Cut the coverage beat first, then the Kiro beat. Never cut the JSON beat: it is the only thing that
proves the browser is not doing the science.

## If you have 5 minutes

After the JSON beat, add determinism:

```sh
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report r1.html --results r1.json
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report r2.html --results r2.json
shasum -a 256 r1.json r2.json r1.html r2.html
```

> Same input, same seed, fixed timestamp. The JSON is identical and so is the two-megabyte HTML.
> That is a release gate. This hash survived eight rewrites, including a full front-end replacement.
