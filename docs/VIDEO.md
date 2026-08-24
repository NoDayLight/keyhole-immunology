# KEYHOLE demo video storyboard

Target 2:50. Record at 1440p or higher. Terminal text at least 20 px. Never crop a truth label,
a method label, a caveat, a citation, or an audit count.

Build the artifact before recording so nothing is generated on camera except the run you narrate:

```sh
SOURCE_DATE_EPOCH=1787529600 .venv/bin/keyhole screen \
  --maf data/examples/tcga_skcm.maf --hla 'A*02:01,B*07:02' --report docs/index.html
```

## Shot list

| Time | Picture | Voiceover |
|---|---|---|
| 0:00–0:12 | Cold open on the report's first fold. Rotate the 1HHK scene once with the mouse. | "This is a real crystal structure. The blue tubes are a human HLA molecule. The gold chain is a protein fragment sitting in its groove, which is how your immune system checks a cell from the inside." |
| 0:12–0:30 | Cut to terminal. `.venv/bin/keyhole validate`. Hold on the reproduced metrics line. | "Cancer alters those fragments. KEYHOLE reads a real tumour mutation file and asks which altered fragments a given set of HLA molecules could actually display. Twenty-six allele-specific models ship inside the package. Validation reproduces held-out Spearman and censor-aware ROC AUC from frozen data, with no network and no retraining." |
| 0:30–0:50 | Run the `screen` command on `data/examples/tcga_skcm.maf`. Highlight 100 rows, 89 supported, 2 screenable, 87 missing context, 38 candidates. Then the audit ladder in the report. | "One hundred real TCGA rows in. Eighty-seven are dropped because KEYHOLE has no frozen canonical protein context for them. It counts what it discarded instead of inventing a sequence, and the same four numbers appear in the report." |
| 0:50–1:00 | Report first fold. Point at the 0 / 0 / 38 verdict strip, then the two truth-boundary callouts. | "Binding is measured-data machine learning. Processing, foreignness, verdicts, and population coverage are labelled heuristic approximations. The HLA alleles are a command-line input, not a patient genotype." |
| 1:00–1:35 | Section 01. Press *Replay candidate flow* and let it run. Then hover one particle. Then click three candidates in the list. | "Thirty-eight candidates, one particle each, four inspection gates. Eight stop at the proteasome, five at the TAP channel, sixteen at the HLA groove, nine reach the final check. Those counts are tallies of reason codes that Python already wrote. The browser never re-applies a threshold. It can explain a rejection; it cannot decide one." |
| 1:35–1:55 | The gate ladder and the radar for one selected candidate. Point at the red axis, then a grey value. | "Every gate prints its exact serialized value and the method that produced it. The red axis is the gate whose reason code stopped this candidate. Grey means the pipeline never reached that gate, so the number exists but no decision was made. The radar is a profile, not a score, and its axis domains are in the table underneath." |
| 1:55–2:15 | Section 02. Drag the globe. Then the bar chart, then the exact coverage table. | "Coverage uses real AFR, AMR, EAS and EUR frequencies under stated linkage-equilibrium and Hardy-Weinberg assumptions. The geography is decoration. The aggregate is cohort-weighted and never drawn as a place, South Asian data is reported absent rather than zero, and hatched fill means heuristic throughout." |
| 2:15–2:35 | Section 03. Switch to the 1AO7 tab, rotate, then switch to *All displayed atoms*. Then back to a candidate scene. | "Five thousand four hundred and seventy-six measured atoms, five chains, including both T-cell receptor chains. Nothing is moved to make the picture look better. Candidate scenes are labelled real backbone with illustrative side-chain geometry, and the illustrative atom is drawn translucent so you can't mistake it for a measured one." |
| 2:35–2:50 | Section 04 strata table. Then open DevTools Network, reload the `file:` URL, show it empty. End on *What KEYHOLE refuses to claim*. | "Published T-cell positivity and KEYHOLE visibility are different endpoints, stratified by whether the peptide was in the training data, with every denominator shown. Shuffled controls are synthetic, never assayed negatives. One file, no server, zero requests. It explains visibility. It does not diagnose, recommend treatment, or prove immunogenicity." |

## Optional 15-second Kiro coda

Show `.kiro/specs/` with eighteen spec folders, open `r8-presentation-grade-report/requirements.md`,
then `.kiro/steering/invariants.md`.

"Eighteen spec boundaries, each with requirements, design and tasks, plus four steering files
that Kiro applied to every turn. Invariant two is why every 3D scene in this report carries a
truth label."

## Recording checklist

- Use the fixed-epoch build so on-screen values match the committed `docs/index.html`.
- Show the `file:` URL at least once, and keep the network panel visible during one reload.
- Demonstrate drag, wheel zoom, arrow keys, and `Home` on one molecular scene.
- Toggle the OS reduced-motion setting once and show the static evidence path.
- Say "measured-data machine learning" and "heuristic approximation" in full. Never shorten
  either to "measured" or "prediction".
- Never call synthetic decoys negatives, coverage worldwide, or illustrative geometry structure.
- Close on the non-clinical limitation.
