# R1 Requirements — Molecular render quality

## User story

As a report reader, I need molecular scenes that are visually legible and fluid on an offline page without changing scientific results, geometry truth labels, accessibility fallbacks, or network guarantees.

## EARS acceptance criteria

1. THE CANVAS SHALL render a subtle radial backdrop, depth-cued atoms/bonds, cached radial-gradient sphere shading by color, visual element radii derived from the parser radius table, and concentric mutation glow rings.
2. WHEN a scene is prepared, bond serials SHALL be resolved to atom-index pairs once rather than mapped by serial during every draw.
3. WHEN the user drags, THE SYSTEM SHALL update only the canvas through one requestAnimationFrame loop and SHALL NOT rebuild an SVG string.
4. WHEN the fallback details opens or its rendered dimensions change, THE SYSTEM SHALL refresh its reduced-detail accessible SVG; otherwise hidden fallback markup SHALL remain untouched.
5. WHEN canvas CSS or device-pixel dimensions are unchanged, THE SYSTEM SHALL NOT assign canvas width or height again.
6. AFTER three seconds without interaction, an on-screen scene SHALL auto-rotate; drag release SHALL retain decaying inertia and reset SHALL tween smoothly.
7. WHEN the scene is off-screen, animation SHALL pause through IntersectionObserver.
8. WHEN `prefers-reduced-motion: reduce` is set, THE SYSTEM SHALL run no animation, inertia, auto-rotation, or reset tween; direct interaction and the SVG fallback SHALL remain usable.
9. R1 implementation changes SHALL stay inside `scene.js`; additive static tests/spec/decision evidence are allowed. Fixed-epoch SKCM `results.json` SHALL remain byte-identical.
