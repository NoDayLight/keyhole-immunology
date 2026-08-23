# KEYHOLE demo video storyboard

Target: 2 minutes 45 seconds. Record at 1440p with terminal text at least 20 px. Do not crop truth labels, caveats, citations, or audit counts.

| Time | Picture | Voiceover |
|---|---|---|
| 0:00–0:15 | Title, then the three-command README quickstart. | “Tumors alter the protein fragments cells display to T cells. KEYHOLE turns a real tumor mutation file and patient HLA types into one inspectable offline report.” |
| 0:15–0:35 | Run `keyhole validate`; hold on reproduced metrics. | “The package ships its frozen data and 26 allele-specific models. Validation reproduces held-out peptide-level Spearman and censor-aware ROC without retraining or network access.” |
| 0:35–0:55 | Run the SKCM `screen` command; highlight 100 input rows, 89 supported changes, 2 screenable variants, 87 missing-context rows, and 38 candidates. | “Unsupported rows are counted, not silently discarded or assigned invented sequences. Only frozen canonical BRAF and TP53 contexts are screenable here.” |
| 0:55–1:25 | Open funnel; switch candidates; point to method labels and patient HLA scores. | “Binding is measured-data machine learning. Cleavage, TAP, foreignness, agretopicity interpretation, and the final visibility language are transparent heuristic approximations. Patient conclusions use only the supplied HLA alleles.” |
| 1:25–1:45 | Open population atlas and allele matrix. | “Population evidence separately evaluates all 26 modeled alleles. Coverage uses real AFR, AMR, EAS, and EUR marginals with explicit linkage-equilibrium and Hardy-Weinberg assumptions. The aggregate is not worldwide coverage.” |
| 1:45–2:15 | Open 1HHK and rotate/zoom; show SVG fallback; open 1AO7; return to candidate schematic. Keep badges visible. | “Experimental scenes use untouched PDB coordinates and say ‘Real crystal structure.’ Candidate beads say ‘Schematic—data real, geometry illustrative’; they are not docking or predicted structures.” |
| 2:15–2:30 | Scroll published panel and limitations. | “The published panel contains real positive T-cell assays. Shuffled controls are explicitly synthetic, not experimental negatives, and HLA-C*08:02 remains unsupported.” |
| 2:30–2:45 | Disconnect network or show DevTools network empty; reload local `file:` report; end on ‘What this does NOT do’. | “The final artifact is a single file with no CDN, server, credentials, or runtime requests. It explains candidate visibility; it does not diagnose, recommend treatment, or prove immunogenicity.” |

## Recording checklist

- Use the deterministic Pages build (`SOURCE_DATE_EPOCH=1787529600`) so timestamps and values match the checked-in demo.
- Show the `file:` URL at least once and keep the network panel visible during one reload.
- Demonstrate pointer rotation, wheel zoom, keyboard arrows, Home reset, and the reduced-detail SVG fallback.
- Read “measured-data ML” and “heuristic approximation” aloud; never shorten either to “measured” or “prediction.”
- Never describe synthetic decoys as negatives, population estimates as global, or schematic beads as molecular structures.
- End with the non-clinical limitation and full provenance link.
