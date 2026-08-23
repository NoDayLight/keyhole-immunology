# R3 Design — Deterministic candidate witnesses

## Data model and path

`funnel.js` flattens `results.mutations[].peptides[]` once. Each item retains the real mutation object, peptide object, scene key, and stable `candidate_key`. A small integer mixer combines `results.meta.seed`, candidate-key characters, and particle index to produce lane offset, delay, speed, and hue variation; `Math.random` is forbidden.

The canvas draws four labeled gates: Proteasome and TAP (`heuristic approximation`), HLA keyhole (`measured ML`), and self-scan (`heuristic approximation`). Particle progress is visual timing only. Rejection stage is selected exclusively from serialized reason codes: `LOW_CLEAVAGE`, `LOW_TAP_TRANSPORT`, `WEAK_BINDING`, or `SELF_LIKE`; no score threshold is evaluated in JavaScript. Rejected particles flash briefly, then fall with stable reason colors. Non-rejected serialized outcomes reach the final gate.

## Interaction, fallback, and lifecycle

A Replay button resets the same seeded elapsed-time animation. Pointer hit testing uses the latest drawn particle positions and fills a DOM tooltip through `textContent` with mutation identity and serialized scores. Canvas sizing is device-pixel guarded. The persistent truth badge says `Schematic — data real, geometry illustrative` and a nearby explanation distinguishes real candidate evidence from illustrative motion.

The original `flowSvg(peptide)` remains the selected-candidate fallback and retains its five score/method stages. It is opened automatically when `matchMedia("(prefers-reduced-motion: reduce)")` matches or `getContext` fails; in those modes no animation frame is requested. The existing evidence panel and candidate molecular scene remain. Destroy cancels the frame, removes select/replay/pointer/media listeners, destroys the scene, and empties the container.

Static tests assert one-particle-per-candidate construction, seeded/no-random behavior, serialized reason mapping, gate/method/truth labels, replay, hover evidence, reduced/no-canvas fallback, and teardown. Full tests, Ruff, JS syntax, diff checks, and fixed-epoch JSON comparison close the boundary.
