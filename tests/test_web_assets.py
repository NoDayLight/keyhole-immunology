"""Static offline and accessibility checks for browser-only scene assets."""

from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


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
    assert "Schematic — data real, geometry illustrative" in source
    assert "aria-live" in source
    assert "aria-label" in source
    assert "<title>" in source and "<desc>" in source
    assert "Reduced-detail SVG fallback" in source
    assert "Home" in source
    assert "pointerdown" in source and "wheel" in source
    assert "destroy" in source
