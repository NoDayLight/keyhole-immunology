# KEYHOLE demo script — 3 minutes

432 words of narration. Every command verified on macOS. Nothing is pasted; you type it all.

**Before recording:** `cd` into the repo, then `rm -f demo.html demo.json` and `clear`.
Big terminal font, notifications off. Do one silent rehearsal so you know where the sections are.

---

## 0:00 · Cold open

Open on the finished report. Drag the molecule through one slow rotation.

> That's a real crystal structure.
> Blue is a human HLA molecule.
> The gold chain is a protein fragment in its groove.
> This is how your immune system checks a cell from the inside.

---

## 0:10 · The input

```sh
wc -l data/examples/tcga_skcm.maf
grep BRAF data/examples/tcga_skcm.maf
tail -n +3 data/examples/tcga_skcm.maf | cut -f8 | sort | uniq -c
```

> Input is a real tumour file. A hundred rows from the TCGA melanoma cohort.
> Here's the row that matters. BRAF, chromosome 7, a missense SNP, A to T, V600E.
> The most famous mutation in melanoma.
> Eighty-nine missense, nine nonsense, two splice. Hold those numbers.

---

## 0:35 · It already has everything

```sh
.venv/bin/keyhole validate
```

> No download, no API key, no service.
> Twenty-six trained binding models and all the reference data ship inside the package.
> Validate reloads them and reproduces held-out Spearman and ROC AUC from frozen data.
> Two seconds, no network.

---

## 0:52 · Generate

```sh
.venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report demo.html --results demo.json
```

> One command. Two and a half seconds.
> Now read the audit line.
> Eighty-nine protein-changing, matching the missense count. Eleven ignored: the nonsense and splice rows.
> Then eighty-seven dropped, because there's no frozen canonical protein sequence for those genes.
> It counts what it discarded instead of inventing one.
> Two variants survive. Thirty-eight candidates.

---

## 1:15 · The JSON is the real output

```sh
ls -lh demo.json demo.html
less demo.json
```

In `less`: type `/SQHMTEVVRH`, Enter, then `k` `k`. Whole candidate on one screen. `q` to quit.

> Two files. The JSON is the contract.
> Python computes every value once and validates it. The HTML only draws it.
> One candidate. Wild type ends in arginine, the mutant in histidine.
> That's the last position, which is an anchor the HLA molecule grips.
> One of my two alleles barely binds it. The other binds at 104 nanomolar.
> Seventeen times better than wild type. The mutation created the fit.

---

## 1:40 · Open it

```sh
.venv/bin/keyhole open demo.html
```

Section 01. Press **Replay candidate flow**. Then click `IGDFGLATE`, then `SQHMTEVVRH`.

> Thirty-eight candidates, one particle each, four gates.
> Eight stop at the proteasome, five at TAP, sixteen at the HLA groove, nine reach the final check.
> Those are tallies of the reason codes we just read. The browser explains a rejection. It never decides one.
> Here's a failure. TAP is 0.327, that gate is red, everything below is grey because the pipeline stopped there.
> And here's the candidate from the JSON, with the gate behind every number and its method label.

---

## 2:20 · Coverage

Section 02. Drag the globe once, then the bars.

> Same candidate, different question.
> Thirty-seven percent of the African cohort, fifty-two American, twenty-one East Asian, thirty-eight European.
> Hatched means heuristic.
> The aggregate is never drawn on the globe, because it isn't a place.

---

## 2:35 · Structures

Section 03. Click **A T cell reading the card**, rotate, then **All displayed atoms**.

> Measured coordinates. A T-cell receptor reading a peptide-HLA complex.
> Five thousand four hundred and seventy-six atoms, five chains.
> Nothing moved to make the picture look better.

---

## 2:48 · Offline, and the limits

Open DevTools → Network. Reload. Land on **What KEYHOLE refuses to claim**.

> One file, opened from disk. Watch the network panel on reload. Nothing.
> It explains visibility.
> It does not diagnose, recommend treatment, or prove immunogenicity.

---

## 2:58 · Kiro

```sh
ls .kiro/specs
```

Open `.kiro/steering/invariants.md`.

> Eighteen spec boundaries, each with requirements, design and tasks.
> Four steering files.
> Law two is why every 3D scene carries a truth label.
> Law seven is why coverage covers four populations, not five.

---

## Never say

- "Measured" alone. Say "measured-data machine learning".
- "Negatives" for the shuffled controls. They're synthetic decoys, no assay.
- "Worldwide" for `ALL_OBSERVED`.
- "Structure" or "prediction" for the illustrative candidate geometry.
- Anything implying a patient. The HLA alleles are a command-line argument.

## If you have 5 minutes instead

Add after the JSON beat:

```sh
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report r1.html --results r1.json
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen --maf data/examples/tcga_skcm.maf --hla "A*29:02,A*30:02" --report r2.html --results r2.json
shasum -a 256 r1.json r2.json r1.html r2.html
```

> Same input, same seed, fixed timestamp. The JSON is identical, and so is the two-megabyte HTML.
> That's a release gate. This hash survived eight rewrites, including a full front-end replacement.

Also worth adding: `du -sh src/keyhole/resources/data` (11 MB of packaged science), and the OS
reduced-motion toggle to show the static evidence path.
