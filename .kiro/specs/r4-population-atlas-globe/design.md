# R4 Design — Orthographic coverage atlas

## Projection API

`KEYHOLEProjection.orthographic(longitude, latitude, rotation, radius, centerX, centerY)` converts degrees to a rotated unit sphere and returns canvas x/y, front-hemisphere visibility, and depth. Rotation contains central longitude and latitude in degrees. The existing atom `project()` implementation and exports remain untouched; `orthographic` is additive.

## Globe rendering

`atlas.js` owns four explicitly illustrative marker locations for AFR, AMR, EAS, and EUR. Marker radius/opacity and labels use only `population.per_candidate_coverage[selectedKey]`; no value or population is inferred. `ALL_OBSERVED` appears beneath the globe as the cohort-weighted aggregate rather than a geographic point. Longitude and latitude graticules are sampled, projected through the shared API, and broken at the hidden hemisphere.

The persistent truth badge is exactly `Schematic — data real, geometry illustrative`. Adjacent text states that coverage is serialized real output and geography/graticule geometry is illustrative. Pointer drag changes central longitude/latitude; arrows rotate and Home/reset restore the deterministic initial view. Canvas dimensions are device-pixel guarded.

## Evidence and fallback

The exact numeric population table is always rendered after the canvas and is therefore the fallback if `getContext` fails. The existing sorted 26-allele evidence table and assumptions paragraph remain. Initialization and normal destroy share teardown for selector, pointer, key, reset, and ResizeObserver resources.

Static tests assert the additive API, unchanged perspective signature/body markers, orthographic/graticule usage, real coverage access, exact truth text, controls, always-visible table, caveats, no markup injection, and teardown. Full tests, Ruff, JS syntax, diff checks, and fixed-epoch JSON comparison close R4.
