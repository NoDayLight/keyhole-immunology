"""Static offline and accessibility checks for browser-only scene assets."""

from __future__ import annotations

import re

from keyhole.report import web_root

WEB = web_root()
_BANNER = re.compile(r"\A\s*/\*.*?\*/\s*", re.DOTALL)


def _body(name: str) -> str:
    """Return a module's source with its leading documentation banner removed.

    The banners state which operations KEYHOLE deliberately does *not* perform, so a
    forbidden-token scan has to run against the executable body to mean anything.
    """

    return _BANNER.sub("", (WEB / name).read_text(encoding="utf-8"), count=1)


def test_scene_assets_are_local_iifes_without_network_paths() -> None:
    sources = [
        (WEB / "projection.js").read_text(encoding="utf-8"),
        (WEB / "pdb.js").read_text(encoding="utf-8"),
        (WEB / "scene.js").read_text(encoding="utf-8"),
    ]
    combined = "\n".join(sources)
    assert all("(function" in source for source in sources)
    for forbidden in ("fetch(", "XMLHttpRequest", "import(", "https://", "http://"):
        assert forbidden not in combined
    assert "global.KEYHOLE.pdb" in combined
    assert "global.KEYHOLE.scene" in combined


def test_scene_source_contains_truth_accessibility_and_fallback_contract() -> None:
    source = (WEB / "scene.js").read_text(encoding="utf-8")
    assert "Real crystal structure (PDB " in source
    assert (
        "Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative" in source
    )
    assert "aria-live" in source
    assert "aria-label" in source
    assert "<title>" in source and "<desc>" in source
    assert "Reduced-detail SVG fallback" in source
    assert "Home" in source
    assert "pointerdown" in source and "wheel" in source
    assert "destroy" in source


def test_scene_render_quality_hot_paths_and_motion_contract() -> None:
    source = (WEB / "scene.js").read_text(encoding="utf-8")
    assert "VISUAL_RADII = { H: 0.31, C: 0.76" in source
    assert "gradientCache = new Map()" in source
    assert "createRadialGradient" in source
    assert "[1.5, 2.05]" in source
    assert 'if (atom.role === "anchor") { return "#55cbd3"; }' in source
    assert "bondPairs: resolveBondPairs(atoms, bonds)" in source
    assert "prepared.bondPairs.forEach" in source
    assert "if (canvas.width !== pixelWidth)" in source
    assert "if (canvas.height !== pixelHeight)" in source

    pointer_move = source.split('listen(canvas, "pointermove"', maxsplit=1)[1].split(
        "function endDrag", maxsplit=1
    )[0]
    assert "renderSvg(" not in pointer_move
    assert "innerHTML" not in pointer_move
    assert "requestCanvas()" in pointer_move
    assert "fallback.open" in source and 'listen(fallback, "toggle"' in source

    assert "global.requestAnimationFrame(tick)" in source
    assert "global.cancelAnimationFrame(frameId)" in source
    assert "IDLE_DELAY_MS = 3000" in source
    assert "resetTween" in source and "INERTIA_DECAY_PER_FRAME" in source
    assert "global.IntersectionObserver" in source
    assert "resetTween.pausedAt = now()" in source
    assert "resetTween.started += now() - resetTween.pausedAt" in source
    assert 'global.matchMedia("(prefers-reduced-motion: reduce)")' in source
    assert "if (reducedMotion || !context)" in source
    assert "if (resetTween)" in source and 'status.textContent = "Molecular scene reset."' in source
    assert "if (reducedMotion)" in source and "cancelLoop()" in source
    assert "var painterZ = 1 - (point.z - minimum) / span" in source


def test_funnel_particles_are_seeded_serialized_and_fallback_safe() -> None:
    source = (WEB / "funnel.js").read_text(encoding="utf-8")
    assert "buildParticles(candidates, results.meta.seed)" in source
    assert "item.peptide.candidate_key" in source
    assert "Math.random" not in source
    assert "candidates.push" in source and "mutation.peptides.forEach" in source
    for stage in ("Proteasome gate", "TAP channel", "HLA keyhole", "Self-scan"):
        assert stage in source

    # The four animated stages carry exactly three heuristic labels and one measured-ML
    # label, and the per-candidate gate ladder repeats the same discipline.
    stages_literal = source.split("var STAGES = [", maxsplit=1)[1].split("];", maxsplit=1)[0]
    assert stages_literal.count('method: "heuristic approximation"') == 3
    assert stages_literal.count('method: "measured ML"') == 1
    gate_evidence = source.split("function gateEvidence(peptide)", maxsplit=1)[1].split(
        "\n  /* Static serialized stage evidence", maxsplit=1
    )[0]
    assert gate_evidence.count('method: "heuristic approximation"') == 4
    assert gate_evidence.count('method: "measured ML"') == 1
    assert 'method: "measured ML"' in source
    for reason in ("LOW_CLEAVAGE", "LOW_TAP_TRANSPORT", "WEAK_BINDING", "SELF_LIKE"):
        assert reason in source
    assert 'FUNNEL_TRUTH = "Schematic — data real, geometry illustrative"' in source
    assert "Replay candidate flow" in source
    assert "global.requestAnimationFrame(animationFrame)" in source
    assert "global.cancelAnimationFrame(frameId)" in source
    assert "tooltip.textContent = tooltipText(nearest.item)" in source
    assert "if (hoverPoint) { updateTooltip(); }" in source
    assert "local - rejectedAt" in source
    assert "STAGES[particle.rejection.stage].progress + 0.18" in source
    assert "item.mutation.gene" in source and "item.mutation.change" in source
    assert "peptide.scores.cleavage" in source and "peptide.scores.tap" in source
    assert "peptide.foreignness" in source and "peptide.reason_codes" in source
    assert "flowSvg(peptide)" in source
    assert "reduced-motion/no-canvas fallback" in source
    assert 'global.matchMedia("(prefers-reduced-motion: reduce)")' in source
    assert "fallbackMode = reducedMotion || !canvasAvailable" in source
    assert 'removeEventListener("pointermove", pointerMove)' in source
    assert 'removeEventListener("click", replayClicked)' in source
    assert "function teardown()" in source and "function fail(error)" in source
    assert "return { destroy: teardown }" in source
    assert "try { update(); }" in source


def test_population_globe_uses_additive_orthographic_projection_and_real_values() -> None:
    projection = (WEB / "projection.js").read_text(encoding="utf-8")
    atlas = (WEB / "atlas.js").read_text(encoding="utf-8")
    assert (
        "function orthographic(longitude, latitude, rotation, radius, centerX, centerY)"
        in projection
    )
    assert "orthographic: orthographic" in projection
    assert "function project(atoms, view, width, height)" in projection
    assert "var perspective = 1 / Math.max" in projection
    assert "project: project" in projection

    assert 'ATLAS_TRUTH = "Schematic — data real, geometry illustrative"' in atlas
    assert "global.KEYHOLEProjection.orthographic" in atlas
    assert "drawGraticule" in atlas and "strokeProjected" in atlas
    assert 'population.per_candidate_coverage[currentKey]' in atlas
    assert 'population.peptide_allele_matrix[currentKey]' in atlas
    for cohort in ("AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"):
        assert cohort in atlas
    assert "ILLUSTRATIVE_MARKERS" in atlas
    assert 'Number(currentCoverage.ALL_OBSERVED).toFixed(2)' in atlas
    assert "not worldwide" in atlas and "SAS is absent" in atlas
    assert 'canvas.getContext("2d"' in atlas
    table_position = atlas.index("Exact serialized population coverage")
    context_position = atlas.index('canvas.getContext("2d"')
    assert table_position < context_position
    assert 'canvas.addEventListener("pointermove", pointerMove)' in atlas
    assert 'canvas.addEventListener("keydown", keyDown)' in atlas
    assert "Reset globe" in atlas and 'event.key === "Home"' in atlas
    assert 'event.key === "ArrowRight") { rotation.longitude -= 8; }' in atlas
    assert 'event.key === "ArrowDown") { rotation.latitude += 6; }' in atlas
    assert "Math.max(1, Math.round(host.clientWidth || 900))" in atlas
    assert 'canvas.style.height !== size.height + "px"' in atlas
    assert "if (canvas.width !== pixelWidth)" in atlas
    assert "if (canvas.height !== pixelHeight)" in atlas
    assert 'removeEventListener("pointermove", pointerMove)' in atlas
    assert 'removeEventListener("keydown", keyDown)' in atlas
    assert "return { destroy: teardown }" in atlas
    assert "innerHTML" not in atlas


def test_webgl_molecule_renderer_draws_only_serialized_coordinates() -> None:
    source = (WEB / "molecule3d.js").read_text(encoding="utf-8")

    # The WebGL renderer reuses the reviewed parser, chain selection, and truth label
    # rather than re-deriving any of them.
    assert "global.KEYHOLE.scene.prepare(data)" in source
    assert "global.KEYHOLE.scene.truthLabel(data)" in source
    assert "Math.random" not in source

    # Atom positions are read, never written: no coordinate may be moved, scaled, or
    # idealized to improve a composition.
    for mutation in ("atom.x =", "atom.y =", "atom.z =", "atom.x=", "atom.y=", "atom.z="):
        assert mutation not in source
    assert "matrix.setPosition(atom.x, atom.y, atom.z)" in source

    # Nothing outside the explicit refusal disclosure may mention dynamics, docking,
    # affinity simulation, minimisation, or electron density.
    disclosure = (
        "No molecular dynamics, docking, affinity simulation, energy minimization, "
        "electron density, "
    )
    assert disclosure in source
    scannable = _body("molecule3d.js").replace(disclosure, "")
    for forbidden in (
        "simulat", "docking", "minimiz", "trajector", "density", "dynamics", "affinity"
    ):
        assert forbidden not in scannable, forbidden

    # Real WebGL: instanced geometry, real lights, real tone mapping.
    assert "new THREE.WebGLRenderer(" in source
    assert "new THREE.InstancedMesh(" in source
    assert "new THREE.TubeGeometry(" in source
    assert "new THREE.CatmullRomCurve3(" in source
    assert "THREE.ACESFilmicToneMapping" in source
    assert "THREE.SRGBColorSpace" in source
    assert "HemisphereLight" in source and "DirectionalLight" in source

    # Deterministic instance ordering, so the same payload always draws the same scene.
    assert "ordered = Array.from(groups.keys()).sort(" in source
    assert "pairs.sort(function (left, right)" in source

    # Adaptive quality plus a truthful non-WebGL fallback that names itself.
    assert "function qualityTier(atomCount)" in source
    assert 'renderer.setPixelRatio(1)' in source
    assert "reduced for this device" in source
    assert "function webglSupported()" in source
    assert "WEBGL_lose_context" in source
    assert "WebGL is unavailable in this browser" in source
    assert "global.KEYHOLE.scene.mount(container, data)" in source

    # Pointer, touch, pinch, keyboard, reset, reduced motion.
    assert 'listen(stage, "pointerdown", pointerDown)' in source
    assert "pointers.size === 2" in source and "pinchDistance" in source
    assert 'event.key === "Home"' in source
    assert 'global.matchMedia' not in source  # shared watcher owns the media query
    assert "UI.motionWatcher()" in source
    assert "if (reduced)" in source

    # Bond drawing is disclosed as a representation choice, not measured connectivity.
    assert "COVALENT_CUTOFF_ANGSTROM = 1.9" in source
    assert "Bond rendering" in source
    assert "Bonds are a " in source and "drawing choice; no coordinate is moved" in source


def test_webgl_molecule_renderer_disposes_every_resource() -> None:
    source = (WEB / "molecule3d.js").read_text(encoding="utf-8")
    for teardown in (
        "cancelLoop();",
        "listeners.splice(0).forEach",
        "resizeObserver.disconnect()",
        "intersectionObserver.disconnect()",
        "unsubscribeMotion()",
        "motion.destroy()",
        "disposeObject(built.group)",
        "geometry.dispose()",
        "renderer.dispose()",
        "renderer.forceContextLoss()",
        "pointers.clear()",
        "fig.root.remove()",
    ):
        assert teardown in source, teardown
    assert "if (destroyed) { return; }\n      destroyed = true;" in source


def test_globe_uses_only_four_observed_cohorts_and_never_maps_the_aggregate() -> None:
    globe = (WEB / "globe.js").read_text(encoding="utf-8")
    atlas = (WEB / "atlas.js").read_text(encoding="utf-8")

    assert 'COHORTS = ["AFR", "AMR", "EAS", "EUR"]' in atlas
    for cohort in ("AFR", "AMR", "EAS", "EUR"):
        assert f'cohort: "{cohort}"' in globe
    # The aggregate is never a marker, and no unobserved population is invented.
    globe_body = _body("globe.js")
    assert "ALL_OBSERVED" not in globe_body
    assert "SAS" not in globe_body
    assert globe_body.count("cohort:") == 4

    assert "Editorial centroids" in globe
    assert "not measured locations" in globe
    assert "function markerSize(percent)" in globe
    assert "BASE_MARKER_SIZE" in globe and "MAX_MARKER_SIZE" in globe
    assert "Math.min(1, value / 60)" in globe

    # Visibility-gated rendering and complete teardown of the third-party context.
    assert "global.IntersectionObserver" in globe
    assert "globe.toggle(next)" in globe
    assert "globe.destroy()" in globe
    assert "intersectionObserver.disconnect()" in globe

    # The atlas never plots the aggregate and always keeps exact text available.
    assert "drawn on the globe because it is a cohort-weighted aggregate, not a place." in atlas
    assert "ALL_OBSERVED is not drawn on the sphere" in atlas
    assert "Cohort-weighted aggregate of the four rows above" in atlas
    assert "Exact serialized population coverage" in atlas
    assert "no SAS observations" in atlas


def test_charts_are_local_svg_with_declared_upstream_design_attribution() -> None:
    source = (WEB / "charts.js").read_text(encoding="utf-8")
    assert "innerHTML" not in source
    assert "createElementNS" not in source  # goes through the shared UI.svg helper
    assert "UI.svg(" in source and "UI.svgText(" in source

    # Attribution and the reason the upstream React components were reimplemented.
    assert "Bklit UI" in source and "EvilCharts" in source
    assert "React" in source and "cannot run inside this single-file" in source
    assert "DECISIONS.md" in source

    # The upstream decorative "hatched" variant is repurposed as an evidence channel.
    assert "hatched" in source
    assert "heuristic approximation" in source
    assert "Solid fills are reserved" in source

    # Composable parts mirroring the upstream component APIs.
    for part in ("RadarGrid", "RadarAxis", "RadarArea", "RadarLabels"):
        assert part in source
    for part in ("Grid + XAxis", "YAxis category label"):
        assert part in source
    assert "role: \"img\"" in source
    assert 'UI.svgText("title"' in source and 'UI.svgText("desc"' in source
    assert "levels" in source and "barRadius" in source

    # A chart may not compute science.
    assert "Nothing here recomputes a scientific value" in source
    assert "Math.random" not in source


def test_funnel_gate_ladder_reads_reason_codes_without_any_comparison() -> None:
    """Gate states must come from serialized reason codes, never a re-applied threshold."""

    source = (WEB / "funnel.js").read_text(encoding="utf-8")
    gate_evidence = source.split("function gateEvidence(peptide)", maxsplit=1)[1].split(
        "\n  /* Static serialized stage evidence", maxsplit=1
    )[0]
    # No relational operator of any kind appears in the gate ladder.
    for operator in ("<", ">", "<=", ">=", "===", "!=="):
        assert operator not in gate_evidence, operator
    # Every state is decided by a serialized reason code.
    for code in (
        "LOW_CLEAVAGE",
        "LOW_TAP_TRANSPORT",
        "WEAK_BINDING",
        "STRONG_BINDING",
        "BORDERLINE_BINDING",
        "SELF_LIKE",
        "FOREIGN_LIKE",
        "PARTLY_SELF_LIKE",
        "MUTANT_BINDS_BETTER",
        "LIMITED_DIFFERENTIAL_BINDING",
        "NO_WT_COUNTERPART",
    ):
        assert f'has(peptide, "{code}")' in gate_evidence, code
    assert 'function has(peptide, code) { return peptide.reason_codes.indexOf(code) !== -1; }' \
        in source

    # Attrition is a count of serialized reason codes, and says so.
    assert "function gateAttrition(candidates)" in source
    assert "Attrition is a count of serialized rejection reason codes" in source
    assert "never re-applies a threshold" in source

    # One witness particle per serialized candidate, still seeded and deterministic.
    assert "particles = buildParticles(candidates, results.meta.seed)" in source
    assert "candidates.push" in source

    # The radar axes are labelled as display normalisations, not a composite score.
    assert "not a composite score" in source
    assert "0 to 20% percentile rank, inverted and clipped" in source
    assert "0 to 3\\u00d7 wild-type/mutant IC50 ratio, clipped" in source


def test_figure_anatomy_forces_a_persistent_truth_label() -> None:
    source = (WEB / "figure.js").read_text(encoding="utf-8")
    assert "function figure(options)" in source
    assert 'node("p", "fig-truth")' in source
    assert "fig-truth-mark" in source and "fig-truth-text" in source
    assert '"measured"' in source and '"illustrative"' in source
    assert 'status.setAttribute("aria-live", "polite")' in source
    assert "setTruth" in source and "setStatus" in source and "addLegend" in source
    # A shared reduced-motion watcher and selection store, both fully unsubscribable.
    assert 'global.matchMedia("(prefers-reduced-motion: reduce)")' in source
    assert "function motionWatcher()" in source and "function selectionStore()" in source
    assert "listeners.splice(index, 1)" in source or "listeners.splice(position, 1)" in source
    assert "destroy: function () { listeners.length = 0; }" in source


def test_stylesheet_declares_one_accent_three_type_roles_and_motion_rules() -> None:
    css = (WEB / "style.css").read_text(encoding="utf-8")
    # Three type roles, declared once each.
    assert css.count("--serif:") == 1
    assert css.count("--sans:") == 1
    assert css.count("--mono:") == 1
    assert "'IBM Plex Serif'" in css
    # Exactly one interactive accent, plus the three verdict states and nothing else.
    assert css.count("--accent:") == 1
    for token in ("--clear:", "--faint:", "--invisible:"):
        assert css.count(token) == 1
    # No remote resource may enter through CSS.
    for forbidden in ("http://", "https://", "@import", "url(//"):
        assert forbidden not in css
    # Accessibility and output modes.
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media print" in css
    assert ":focus-visible" in css
    assert ".skip" in css
    assert ".screen-reader" in css
    # The Canvas 2D fallback chrome is styled, so a fallback never looks unlabeled.
    for selector in (".scene-truth", ".scene-detail", ".keyhole-scene-canvas", ".scene-status"):
        assert selector in css
