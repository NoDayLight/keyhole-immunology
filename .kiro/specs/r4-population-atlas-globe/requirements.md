# R4 Requirements — Population atlas globe

## User story

As a report reader, I need an explorable population-coverage overview that uses the real embedded cohort results while making clear that geographic placement is illustrative and preserving exact numeric evidence.

## EARS acceptance criteria

1. `projection.js` SHALL add an orthographic latitude/longitude projection API without changing the existing molecular `project()` perspective behavior.
2. THE ATLAS SHALL draw a Canvas 2D orthographic globe with sphere boundary and graticule.
3. THE GLOBE SHALL visualize the selected candidate’s real serialized AFR, AMR, EAS, and EUR coverage and SHALL show `ALL_OBSERVED` only as the cohort-weighted summary, not worldwide coverage.
4. THE GLOBE SHALL carry exactly `Schematic — data real, geometry illustrative` and disclose that marker geography is illustrative while coverage values are real serialized results.
5. WHEN the user drags, THE GLOBE SHALL rotate in longitude and bounded latitude; keyboard arrows and a reset control SHALL provide equivalent operation.
6. WHEN canvas is unavailable, THE NUMERIC coverage table SHALL remain complete and usable. The numeric table SHALL also remain visible with canvas.
7. THE EXISTING peptide selector, 26-allele evidence matrix, population assumptions, seed/draw count, and no-SAS/no-worldwide caveats SHALL remain.
8. Destroy and initialization failure SHALL remove all selector, pointer, keyboard, reset, and resize resources.
9. Offline/security tests SHALL remain unchanged and fixed-epoch SKCM `results.json` SHALL remain byte-identical.
