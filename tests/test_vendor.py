"""Contracts for the byte-exact, offline, locally packaged browser runtime."""

from __future__ import annotations

import re
from hashlib import sha256

import pytest

from keyhole.assets import packaged_file
from keyhole.vendor import (
    COBE_VERSION,
    PHENOMENON_VERSION,
    PLEX_VERSION,
    THREE_EXPORTS,
    THREE_VERSION,
    VENDOR_DIGESTS,
    cobe_classic_script,
    three_global_bridge,
    vendored_runtime,
)

THREE_SOURCE = "vendor/three/three.module.min.js"
COBE_SOURCE = "vendor/cobe/index.esm.js"


def test_every_vendored_artifact_matches_its_recorded_digest() -> None:
    assert VENDOR_DIGESTS, "no vendored artifacts are recorded"
    for relative, expected in VENDOR_DIGESTS.items():
        payload = packaged_file(relative).read_bytes()
        assert sha256(payload).hexdigest() == expected, relative
        assert payload, relative


def test_provenance_records_every_artifact_version_and_license() -> None:
    provenance = packaged_file("vendor/PROVENANCE.md").read_text(encoding="utf-8")
    for relative, digest in VENDOR_DIGESTS.items():
        assert relative.split("vendor/", maxsplit=1)[1] in provenance
        assert digest in provenance
    for version in (THREE_VERSION, COBE_VERSION, PHENOMENON_VERSION, PLEX_VERSION):
        assert version in provenance
    assert "MIT" in provenance and "SIL Open Font License" in provenance
    # Each dependency keeps its unmodified upstream license text beside it.
    for relative in (
        "vendor/three/LICENSE",
        "vendor/cobe/LICENSE",
        "vendor/phenomenon/LICENSE",
        "vendor/fonts/LICENSE.txt",
    ):
        assert len(packaged_file(relative).read_text(encoding="utf-8")) > 500


def test_three_distribution_is_self_contained_and_unmodified() -> None:
    source = packaged_file(THREE_SOURCE).read_text(encoding="utf-8")
    assert f'const t="{THREE_VERSION.split(".")[1]}"' in source
    assert "SPDX-License-Identifier: MIT" in source
    # A single trailing export clause and no module resolution of any kind, which is what
    # makes verbatim inlining into one <script type="module"> possible.
    assert len(re.findall(r"\bexport\s*\{", source)) == 1
    assert re.search(r"^import[^;]*;", source, re.MULTILINE) is None
    assert "import.meta" not in source
    assert re.search(r"\bimport\s*\(", source) is None
    assert 'from"./' not in source and "from './" not in source


def test_three_bridge_exposes_exactly_the_declared_symbols() -> None:
    source = packaged_file(THREE_SOURCE).read_text(encoding="utf-8")
    bridge = three_global_bridge(source)
    assert bridge.count("globalThis.THREE=Object.freeze({") == 1
    for name in THREE_EXPORTS:
        assert f"{name}:" in bridge
    assert bridge.count(":") == len(THREE_EXPORTS) + 0
    assert "WebGLRenderer:" in bridge and "InstancedMesh:" in bridge


def test_three_bridge_fails_loudly_when_an_export_disappears() -> None:
    with pytest.raises(ValueError, match="missing required exports"):
        three_global_bridge("export{a as Scene};")
    with pytest.raises(ValueError, match="no trailing export clause"):
        three_global_bridge("const x = 1;")


def test_cobe_adaptation_is_anchored_and_fails_loudly() -> None:
    source = packaged_file(COBE_SOURCE).read_text(encoding="utf-8")
    assert source.startswith('import v from"phenomenon";')
    assert source.rstrip().endswith("export{p as default};")
    # cobe carries its own dot-map texture as a data URI, so the globe needs no network.
    assert "data:image/png;base64," in source

    adapted = cobe_classic_script(source)
    # Neither module statement survives as executable code.
    assert 'import v from"phenomenon";' not in adapted
    assert "export{p as default}" not in adapted
    assert re.search(r"(^|[;}])\s*(import|export)[\s{]", adapted) is None
    assert "var v=window.Phenomenon;" in adapted
    assert "window.COBE=p;" in adapted
    assert '"use strict"' in adapted
    # The untouched body survives the two anchored replacements.
    stripped = source.strip()
    body = stripped[len('import v from"phenomenon";') : -len("export{p as default};")]
    assert body in adapted

    with pytest.raises(ValueError, match="phenomenon import"):
        cobe_classic_script("var x=1;export{p as default};")
    with pytest.raises(ValueError, match="default export"):
        cobe_classic_script('import v from"phenomenon";var x=1;')


def test_phenomenon_is_a_global_umd_build_needing_no_adaptation() -> None:
    source = packaged_file("vendor/phenomenon/phenomenon.umd.js").read_text(encoding="utf-8")
    assert "t.Phenomenon=e()" in source
    assert re.search(r"^import[^;]*;", source, re.MULTILINE) is None
    assert "export{" not in source


def test_fonts_are_embedded_as_local_data_uris_only() -> None:
    css = vendored_runtime().font_face_css
    assert css.count("@font-face") == 2
    assert css.count("data:font/woff2;base64,") == 2
    assert "'IBM Plex Serif'" in css
    assert "font-weight:400" in css
    assert "font-style:normal" in css and "font-style:italic" in css
    # No local() source, so rendering never depends on an installed system font, and no
    # url() ever points outside this document.
    assert "local(" not in css
    assert "http" not in css
    assert "unicode-range:" in css


def test_runtime_banner_attributes_every_component() -> None:
    banner = vendored_runtime().banner
    for text in ("three.js", "cobe", "phenomenon", "IBM Plex Serif"):
        assert text in banner
    assert "MIT" in banner and "SIL OFL 1.1" in banner
    assert "No network request" in banner or "no network request" in banner
    assert banner.startswith("\n<!--") and banner.rstrip().endswith("-->")


def test_runtime_is_resolved_once_and_is_deterministic() -> None:
    first = vendored_runtime()
    second = vendored_runtime()
    assert first is second
    assert first.three_module.endswith("});\n")
    assert "globalThis.THREE=Object.freeze({" in first.three_module
