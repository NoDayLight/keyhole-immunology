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
