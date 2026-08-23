"""Static offline and accessibility checks for browser-only scene assets."""

from __future__ import annotations

from keyhole.report import web_root

WEB = web_root()


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
    assert source.count('method: "heuristic approximation"') == 3
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
