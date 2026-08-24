"""Byte-exact vendored browser runtime, inlined without a network or build step.

Every artifact resolved here is an unmodified file from an official pinned upstream
distribution recorded in ``resources/vendor/PROVENANCE.md``. Nothing is fetched at
runtime. The two upstream files that use ES-module syntax are adapted with *anchored*
transformations that fail loudly rather than silently rewriting a dependency.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256

from keyhole.assets import packaged_file

#: Exact upstream releases. Report assembly refuses to run against anything else.
THREE_VERSION = "0.169.0"
COBE_VERSION = "0.6.4"
PHENOMENON_VERSION = "1.6.0"
PLEX_VERSION = "2.0.0"

#: SHA-256 of every vendored file, verified on every report render.
VENDOR_DIGESTS: dict[str, str] = {
    "vendor/three/three.module.min.js": (
        "f7cee3c7533449a1505cc12cb5128b89e3d4fd3d7ea62b05f9f5464a217472ee"
    ),
    "vendor/three/LICENSE": (
        "4c40a1ef62450b857c3b2aaf294936304cd552d965fbcd9d32d4c5bcf4ba4454"
    ),
    "vendor/cobe/index.esm.js": (
        "f4f29c3e95e77b091b4350ec848a9aaf2dfeb262df5c876dab981badb3beed0f"
    ),
    "vendor/cobe/LICENSE": (
        "226e31827d99b53fe36d8476824a7238056db4c8bd8ac5abe7e73f6004fba24e"
    ),
    "vendor/phenomenon/phenomenon.umd.js": (
        "0765263a32157f6737429d7d83117d96ce23e29ee26160ec3304f67168543736"
    ),
    "vendor/phenomenon/LICENSE": (
        "67a210dd59d8eb003aad302c07db2cd9a553d03f8639e4c3815066080f388bb1"
    ),
    "vendor/fonts/IBMPlexSerif-Regular-Latin1.woff2": (
        "324a502545695a3e8dd9e9d9273ec56e3aa2a729689807756b9439e2c7a48071"
    ),
    "vendor/fonts/IBMPlexSerif-Italic-Latin1.woff2": (
        "1bceb36acfb5828f10ef9462de2003b0da6c53781faff4a942d426378d9fd975"
    ),
    "vendor/fonts/LICENSE.txt": (
        "7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da"
    ),
}

#: The only three.js symbols KEYHOLE's renderer uses. The generated global bridge
#: exposes exactly these, so an upstream rename fails the build instead of the browser.
THREE_EXPORTS: tuple[str, ...] = (
    "ACESFilmicToneMapping",
    "AmbientLight",
    "Box3",
    "CatmullRomCurve3",
    "Color",
    "CylinderGeometry",
    "DirectionalLight",
    "Group",
    "HemisphereLight",
    "IcosahedronGeometry",
    "InstancedMesh",
    "MathUtils",
    "Matrix4",
    "Mesh",
    "MeshStandardMaterial",
    "PerspectiveCamera",
    "Quaternion",
    "SRGBColorSpace",
    "Scene",
    "Sphere",
    "TubeGeometry",
    "Vector3",
    "WebGLRenderer",
)

_COBE_IMPORT = 'import v from"phenomenon";'
_COBE_EXPORT = "export{p as default};"
_EXPORT_CLAUSE = re.compile(r"export\{(?P<body>[^{}]*)\};?\s*\Z")


@dataclass(frozen=True, slots=True)
class VendoredRuntime:
    """Inline-ready browser runtime text plus its attribution banner."""

    banner: str
    three_module: str
    classic_prelude: str
    font_face_css: str


def _verified_bytes(relative: str) -> bytes:
    """Read one packaged vendor file and verify its recorded SHA-256."""

    expected = VENDOR_DIGESTS.get(relative)
    if expected is None:
        raise KeyError(f"unrecorded vendor artifact: {relative}")
    payload = packaged_file(relative).read_bytes()
    digest = sha256(payload).hexdigest()
    if digest != expected:
        raise ValueError(
            f"vendored artifact {relative} has digest {digest}, expected {expected}"
        )
    return payload


def _verified_text(relative: str) -> str:
    return _verified_bytes(relative).decode("utf-8")


def _three_export_map(source: str) -> dict[str, str]:
    """Map exported name to minified local binding from the single export clause."""

    matches = _EXPORT_CLAUSE.search(source)
    if matches is None:
        raise ValueError("three.js distribution has no trailing export clause")
    bindings: dict[str, str] = {}
    for entry in matches.group("body").split(","):
        item = entry.strip()
        if not item:
            continue
        local, _, exported = item.partition(" as ")
        exported = exported.strip() or local.strip()
        bindings[exported] = local.strip()
    return bindings


def three_global_bridge(source: str) -> str:
    """Generate the deterministic ``globalThis.THREE`` bridge for an untouched build."""

    bindings = _three_export_map(source)
    missing = [name for name in THREE_EXPORTS if name not in bindings]
    if missing:
        raise ValueError(
            "three.js distribution is missing required exports: " + ", ".join(missing)
        )
    pairs = ",".join(f"{name}:{bindings[name]}" for name in THREE_EXPORTS)
    return (
        "\n/* KEYHOLE-generated global bridge for the untouched three.js ES module. */\n"
        f"globalThis.THREE=Object.freeze({{{pairs}}});\n"
    )


def cobe_classic_script(source: str) -> str:
    """Adapt cobe's ES module into a classic script with anchored replacements."""

    text = source.strip()
    if not text.startswith(_COBE_IMPORT):
        raise ValueError("cobe distribution no longer starts with its phenomenon import")
    if not text.endswith(_COBE_EXPORT):
        raise ValueError("cobe distribution no longer ends with its default export")
    body = text[len(_COBE_IMPORT) : -len(_COBE_EXPORT)]
    return (
        '(function(){"use strict";\n'
        "/* KEYHOLE: the single leading module dependency statement of the untouched cobe"
        " distribution is resolved here to the vendored phenomenon UMD global. */\n"
        "var v=window.Phenomenon;\n"
        f"{body}\n"
        "/* KEYHOLE: the single trailing default-module statement of the untouched cobe"
        " distribution is published here as a window global. */\n"
        "window.COBE=p;})();\n"
    )


def _font_data_uri(relative: str) -> str:
    encoded = base64.b64encode(_verified_bytes(relative)).decode("ascii")
    return f"data:font/woff2;base64,{encoded}"


def _font_face_css() -> str:
    faces = (
        ("normal", "vendor/fonts/IBMPlexSerif-Regular-Latin1.woff2"),
        ("italic", "vendor/fonts/IBMPlexSerif-Italic-Latin1.woff2"),
    )
    unicode_range = (
        "U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,"
        "U+2013-2014,U+2018-201A,U+201C-201E,U+2020-2022,U+2026,U+2030,"
        "U+2039-203A,U+2044,U+20AC,U+2122,U+2212,U+FB01-FB02"
    )
    return "".join(
        "@font-face{font-family:'IBM Plex Serif';font-style:"
        f"{style};font-weight:400;font-display:block;"
        f"src:url({_font_data_uri(relative)}) format('woff2');"
        f"unicode-range:{unicode_range}}}"
        for style, relative in faces
    )


def _banner() -> str:
    return (
        "\n<!--\n"
        "  KEYHOLE inlines these byte-exact vendored browser runtimes. No network request,\n"
        "  CDN, runtime import, remote texture, or external font is used at any point.\n"
        f"  three.js {THREE_VERSION} - MIT - (c) 2010-2024 three.js authors -"
        " https://github.com/mrdoob/three.js\n"
        f"  cobe {COBE_VERSION} - MIT - (c) 2021 Shu Ding -"
        " https://github.com/shuding/cobe\n"
        f"  phenomenon {PHENOMENON_VERSION} - MIT - (c) Colin van Eenige -"
        " https://github.com/vaneenige/phenomenon\n"
        f"  IBM Plex Serif {PLEX_VERSION} - SIL OFL 1.1 - (c) 2017 IBM Corp. -"
        " https://github.com/IBM/plex\n"
        "  Full license texts and upstream digests:"
        " src/keyhole/resources/vendor/PROVENANCE.md\n"
        "-->\n"
    )


@lru_cache(maxsize=1)
def vendored_runtime() -> VendoredRuntime:
    """Resolve, verify, and adapt the complete inline browser runtime exactly once."""

    for relative in VENDOR_DIGESTS:
        _verified_bytes(relative)
    three_source = _verified_text("vendor/three/three.module.min.js")
    cobe_source = _verified_text("vendor/cobe/index.esm.js")
    phenomenon_source = _verified_text("vendor/phenomenon/phenomenon.umd.js")
    return VendoredRuntime(
        banner=_banner(),
        three_module=three_source + three_global_bridge(three_source),
        classic_prelude=(
            f"/* vendor:phenomenon@{PHENOMENON_VERSION} (MIT), byte-exact UMD */\n"
            f"{phenomenon_source}\n"
            f"/* vendor:cobe@{COBE_VERSION} (MIT), byte-exact body, anchored module"
            " statements adapted */\n"
            f"{cobe_classic_script(cobe_source)}"
        ),
        font_face_css=_font_face_css(),
    )
