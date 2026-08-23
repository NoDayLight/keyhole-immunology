# R1 Design — Low-level molecular renderer

## Preparation and drawing

`scene.js` copies the parser’s reviewed element-radius table as `VISUAL_RADII` because R1 may not change `pdb.js`. `prepare()` filters atoms as before, builds a serial→index map once, and stores `bondPairs` with direct atom indices. Each draw projects atoms exactly once. Bonds use indexed projected endpoints; atoms use a painter-sorted copy so indices remain stable.

Depth is normalized over projected painter-z. It scales atom radius and opacity and softens distant bonds. A module-level `gradientCache` stores one normalized offscreen radial-gradient sphere sprite per unique color; draw-time scaling applies element radius, perspective, and depth. Mutation atoms receive two static concentric glow rings. A separate radial gradient supplies the subtle dark backdrop.

## Render scheduling and fallback

Mount owns at most one `requestAnimationFrame` ID. Events mutate view state and mark the canvas dirty; the loop performs drawing, decaying drag inertia, a cubic reset tween, and idle auto-rotation after 3,000 ms. `IntersectionObserver` cancels the frame while off-screen. The exact media query `matchMedia("(prefers-reduced-motion: reduce)")` cancels all animation and renders interaction changes synchronously.

Canvas backing-store and CSS dimensions are assigned only when changed. SVG generation is separate from canvas drawing: pointer movement never calls `renderSvg` or writes `innerHTML`. The fallback refreshes when opened and after an observed size change while open; canvas failure opens and renders it immediately. Existing truth badge, details, keyboard controls, public API, and teardown contract remain.

## Regression evidence

Static browser tests assert scheduler/motion APIs, lazy SVG separation from pointermove, pre-resolved bonds, guarded dimensions, cached gradients/radii, and mutation rings. Full pytest/Ruff/diff checks run at the boundary. A fixed-epoch SKCM result generated before R1 is compared byte-for-byte after R1; report bytes are expected to change because this spec intentionally changes visuals.
