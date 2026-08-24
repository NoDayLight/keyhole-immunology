"""Tests for deterministic, injection-safe, standalone HTML reports."""

from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import pytest

from keyhole.assets import packaged_file
from keyhole.bind import ALLELES, BindingPrediction
from keyhole.data import pdb_path
from keyhole.parse import parse_famous
from keyhole.pipeline import screen_variants
from keyhole.report import SCRIPT_ORDER, render_report, web_root, write_report
from keyhole.schema import validate_results
from keyhole.vendor import VENDOR_DIGESTS, vendored_runtime

WEB = web_root()
LITERATURE_STUB = json.loads(
    packaged_file("validation/results.sample.json").read_text(encoding="utf-8")
)["literature"]
JSON_SCRIPT = re.compile(
    r'<script type="application/json" id="(?P<id>[^"]+)">(?P<body>.*?)</script>',
    re.DOTALL,
)


class StableBinder:
    """Fast deterministic model double for a complete report-contract document."""

    def predict_many(
        self, peptides: list[str] | tuple[str, ...], allele: str
    ) -> tuple[BindingPrediction, ...]:
        offset = ALLELES.index(allele)
        return tuple(
            BindingPrediction(allele, peptide, 80.0 + offset, 1.0 + offset / 10.0)
            for peptide in peptides
        )


@lru_cache(maxsize=1)
def _report_document() -> dict[str, object]:
    return screen_variants(
        [parse_famous("BRAF V600E")],
        "A*02:01,B*07:02",
        input_name="S7 deterministic report fixture",
        input_path="famous:BRAF V600E",
        binder=StableBinder(),
        foreignness_fn=lambda _peptide: 0.75,
        literature_branch=LITERATURE_STUB,
        population_draws=64,
        created_utc="2026-08-24T00:00:00Z",
    ).results


def _fixture() -> dict[str, object]:
    return copy.deepcopy(_report_document())


def _payloads(html: str) -> dict[str, object]:
    return {match["id"]: json.loads(match["body"]) for match in JSON_SCRIPT.finditer(html)}


def test_report_embeds_valid_results_all_scenes_and_scripts_in_order() -> None:
    html = render_report(_fixture())
    payloads = _payloads(html)
    assert validate_results(payloads["keyhole-results"]) == payloads["keyhole-results"]

    scenes = payloads["keyhole-scenes"]
    assert set(scenes["structures"]) == {"1HHK", "3PWN", "1AO7"}
    for pdb_id, structure in scenes["structures"].items():
        assert structure["truth"] == f"Real crystal structure (PDB {pdb_id})"
        assert "ATOM" in structure["pdb_text"]
    assert scenes["schematics"]
    assert all(
        scene["truth"]
        == "Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative"
        for scene in scenes["schematics"].values()
    )
    assert all(
        any(atom["role"] == "anchor" for atom in scene["atoms"])
        and any(atom["role"] == "mutation" for atom in scene["atoms"])
        for scene in scenes["schematics"].values()
    )

    positions = [html.index(f"/* inline:{name} */") for name in SCRIPT_ORDER]
    assert positions == sorted(positions)
    assert html.count("(function (global)") >= len(SCRIPT_ORDER)


def test_report_pdb_payload_is_display_only_fixed_column_subset() -> None:
    scenes = _payloads(render_report(_fixture()))["keyhole-scenes"]["structures"]
    expected_source_sites = {"1HHK": 6_322, "3PWN": 7_133, "1AO7": 5_711}
    for pdb_id, structure in scenes.items():
        original = pdb_path(pdb_id).read_text(encoding="utf-8")
        compact = structure["pdb_text"]
        lines = compact.splitlines()
        atom_lines = [line for line in lines if line.startswith("ATOM")]
        retained_serials = {int(line[6:11]) for line in atom_lines}
        assert atom_lines
        assert all(line.startswith(("ATOM", "CONECT")) for line in lines)
        assert all(line[21].strip() in structure["display_chains"] for line in atom_lines)
        assert all(float(line[54:60]) > 0 for line in atom_lines)
        assert all(line[17:20].strip() not in {"HOH", "WAT"} for line in atom_lines)
        assert all(line[76:78].strip().upper() != "H" for line in atom_lines)
        for line in atom_lines:
            for coordinate in (line[30:38], line[38:46], line[46:54]):
                assert re.fullmatch(r"\s*-?\d+\.\d{3}", coordinate)
        for line in (value for value in lines if value.startswith("CONECT")):
            serials = [
                int(line[offset : offset + 5])
                for offset in range(6, len(line), 5)
                if line[offset : offset + 5].strip()
            ]
            assert serials and set(serials) <= retained_serials
        assert structure["source_pdb_bytes"] == len(original.encode("utf-8"))
        assert structure["embedded_pdb_bytes"] == len(compact.encode("utf-8"))
        assert structure["embedded_pdb_bytes"] < structure["source_pdb_bytes"]
        assert structure["source_selected_atom_sites"] == expected_source_sites[pdb_id]
        assert "coordinates serialized at 3 decimals" in structure["report_pdb_subset"]
    assert "ANISOU" in pdb_path("3PWN").read_text(encoding="utf-8")
    assert "ANISOU" not in scenes["3PWN"]["pdb_text"]


NETWORK_APIS = (
    "fetch(",
    "XMLHttpRequest",
    "import(",
    "WebSocket(",
    "EventSource(",
    "navigator.sendBeacon",
    "document.cookie",
    "credentials:",
)
#: The only absolute URI KEYHOLE browser code may contain. It is an XML namespace
#: identifier consumed by ``document.createElementNS``, never a fetched resource.
ALLOWED_NAMESPACE_URI = "http://www.w3.org/2000/svg"


def test_keyhole_browser_code_uses_no_network_api_or_remote_url() -> None:
    """KEYHOLE-authored browser code must contain no network API and no remote URL."""

    for name in SCRIPT_ORDER:
        source = (WEB / name).read_text(encoding="utf-8")
        for forbidden in NETWORK_APIS:
            assert forbidden not in source, f"{name} references {forbidden}"
        remaining = source.replace(ALLOWED_NAMESPACE_URI, "")
        for scheme in ("https://", "http://", "//cdn", "unpkg", "jsdelivr", "googleapis"):
            assert scheme not in remaining, f"{name} references {scheme}"


def test_report_is_network_free_single_file_with_defensive_csp() -> None:
    html = render_report(_fixture())
    for directive in (
        "default-src 'none'",
        "connect-src 'none'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'none'",
        "img-src data:",
        "font-src data:",
    ):
        assert directive in html
    assert re.search(r"<script[^>]+\bsrc\s*=", html, re.IGNORECASE) is None
    assert re.search(r"<link[^>]+\bhref\s*=", html, re.IGNORECASE) is None
    assert "<iframe" not in html and "<object" not in html and "<embed" not in html
    assert "eval(" not in html

    # Every inlined vendor runtime is byte-exact, so no network path can be smuggled in
    # through a dependency, and the dormant loader code inside a general-purpose engine
    # is unreachable regardless because connect-src and default-src are 'none'.
    runtime = vendored_runtime()
    assert runtime.three_module in html
    assert runtime.classic_prelude in html
    for relative, digest in VENDOR_DIGESTS.items():
        assert sha256(packaged_file(relative).read_bytes()).hexdigest() == digest

    # The KEYHOLE-authored portion of the document keeps the original strict guarantee.
    keyhole_only = html.replace(runtime.three_module, "").replace(runtime.classic_prelude, "")
    for forbidden in NETWORK_APIS:
        assert forbidden not in keyhole_only
    assert 1_900_000 <= len(html.encode("utf-8")) <= 2_600_000


def test_report_bytes_are_deterministic_and_json_script_is_escaped(tmp_path: Path) -> None:
    document = copy.deepcopy(_fixture())
    hostile = "</script>&\u2028\u2029"
    document["meta"]["sources"].append(hostile)

    first = render_report(document)
    second = render_report(document)
    assert first == second
    assert hostile not in first
    assert r"\u003c/script\u003e\u0026\u2028\u2029" in first
    assert _payloads(first)["keyhole-results"]["meta"]["sources"][-1] == hostile

    destination = write_report(document, tmp_path / "nested" / "report.html")
    assert destination.read_bytes() == first.encode("utf-8")


def test_report_rejects_missing_misaligned_or_mistyped_renderer_evidence() -> None:
    missing_best = _fixture()
    del missing_best["mutations"][0]["peptides"][0]["best_allele"]
    with pytest.raises(ValueError, match="best_allele"):
        render_report(missing_best)

    wrong_best = _fixture()
    wrong_best["mutations"][0]["peptides"][0]["best_allele"] = "B*07:02"
    with pytest.raises(ValueError, match="does not match serialized binding winner"):
        render_report(wrong_best)

    hostile_key = '<svg onload="alert(1)">'
    misaligned = _fixture()
    coverage = misaligned["population"]["per_candidate_coverage"]
    original = next(iter(coverage))
    coverage[hostile_key] = coverage.pop(original)
    with pytest.raises(ValueError, match="candidate keys must align"):
        render_report(misaligned)

    mistyped = _fixture()
    mistyped["literature"]["entries"].append(
        {
            "allele": "A*02:01",
            "binder_split": "test",
            "binding_dataset_overlap": False,
            "evaluation_status": 42,
            "external_facts": {
                "assay_result": "Positive",
                "pmid": "1",
                "reference_title": "Example",
            },
            "matched_negative": {
                "peptide": "AAAAAAAAA",
                "prediction": {"plain_language": "Example", "verdict": None},
            },
            "peptide": "AAAAAAAAA",
            "prediction": {"plain_language": "Example", "verdict": None},
        }
    )
    with pytest.raises(ValueError, match="evaluation_status"):
        render_report(mistyped)

    missing_audit = _fixture()
    del missing_audit["tumor"]["screening"]
    with pytest.raises(ValueError, match="screening"):
        render_report(missing_audit)


def test_browser_sources_avoid_markup_injection_and_clean_up_listeners() -> None:
    """No browser module may build markup from strings, and every mount must tear down."""

    for name in SCRIPT_ORDER:
        assert "innerHTML" not in (WEB / name).read_text(encoding="utf-8"), name
        assert "outerHTML" not in (WEB / name).read_text(encoding="utf-8"), name
        assert "insertAdjacentHTML" not in (WEB / name).read_text(encoding="utf-8"), name
        assert "document.write" not in (WEB / name).read_text(encoding="utf-8"), name

    atlas = (WEB / "atlas.js").read_text(encoding="utf-8")
    main = (WEB / "main.js").read_text(encoding="utf-8")
    funnel = (WEB / "funnel.js").read_text(encoding="utf-8")
    molecule = (WEB / "molecule3d.js").read_text(encoding="utf-8")
    globe = (WEB / "globe.js").read_text(encoding="utf-8")

    assert 'canvas.getContext("2d"' in atlas and "textContent" in atlas
    assert 'removeEventListener("change"' in atlas
    assert 'removeEventListener("change"' in funnel

    # The structure viewer is now a tablist rather than lazily opened details elements.
    assert 'tabs.removeEventListener("click", clicked)' in main
    assert 'tabs.removeEventListener("keydown", keyed)' in main
    assert "if (controller) { controller.destroy(); controller = null; }" in main
    assert "if (tornDown)" in main
    assert "controllers.slice().reverse()" in main
    assert (
        '["funnel-app", "atlas-app", "structures-app", "literature-app", "methods-app"]'
        in main
    )

    # WebGL owners must release GPU resources, observers, and frames exactly once.
    assert "listeners.splice(0).forEach" in molecule
    assert "renderer.dispose()" in molecule
    assert "renderer.forceContextLoss()" in molecule
    assert "geometry.dispose()" in molecule
    assert "material.dispose()" in molecule or "item.dispose()" in molecule
    assert "intersectionObserver.disconnect()" in molecule
    assert "resizeObserver.disconnect()" in molecule
    assert "global.cancelAnimationFrame(frameId)" in molecule
    assert "if (destroyed) { return; }" in molecule
    assert "globe.destroy()" in globe
    assert "intersectionObserver.disconnect()" in globe
    assert "if (destroyed) { return; }" in globe
