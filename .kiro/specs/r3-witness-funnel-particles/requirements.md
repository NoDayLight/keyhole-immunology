# R3 Requirements — Witness funnel particles

## User story

As a report reader, I need to see every real candidate move through the visibility story while retaining the exact serialized evidence and an accessible non-animated fallback.

## EARS acceptance criteria

1. THE FUNNEL SHALL create exactly one particle for every serialized mutation/peptide candidate and SHALL derive deterministic visual variation from `results.meta.seed` and `candidate_key` without `Math.random`.
2. THE CANVAS SHALL show the ordered illustrative path Proteasome gate → TAP channel → HLA keyhole → self-scan, with persistent measured-ML/heuristic labels.
3. WHEN a serialized rejection reason identifies a failed stage, THE PARTICLE SHALL flash and fall at that stage using a stable reason color; browser code SHALL NOT recompute scientific thresholds or verdicts.
4. WHEN the user activates Replay, THE SAME seeded animation SHALL restart from the same initial particle state.
5. WHEN the pointer hovers a particle, THE UI SHALL show its serialized gene/change, peptide, cleavage, TAP, best-allele binding, foreignness, verdict, and reasons using text-safe DOM APIs.
6. THE NEW CANVAS SHALL carry `Schematic — data real, geometry illustrative` and explain that candidate count/outcomes/scores are real serialized data while paths/timing are illustrative.
7. THE EXISTING selected-candidate sequence, verdict, plain-language evidence, binding grid, reason list, and molecular scene SHALL remain.
8. WHEN reduced motion is requested or canvas is unavailable, no animation SHALL run and the existing static `flowSvg` with stage truth labels SHALL be opened as the fallback.
9. Destroy SHALL cancel animation, remove every new listener/media subscription, destroy the mounted molecular scene, and clear the container.
10. Offline forbidden-string tests SHALL pass unchanged and fixed-epoch SKCM `results.json` SHALL remain byte-identical.
