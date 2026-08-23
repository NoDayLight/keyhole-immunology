"""Tests for deterministic, injection-safe, standalone HTML reports."""

from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path

import pytest

from keyhole.bind import ALLELES, BindingPrediction
from keyhole.parse import parse_famous
from keyhole.pipeline import screen_variants
from keyhole.report import SCRIPT_ORDER, render_report, web_root, write_report
from keyhole.schema import validate_results

WEB = web_root()
LITERATURE_STUB = {
    "agreement_stats": {
        "matched_decoy_evaluable": 0,
        "matched_decoy_rejected_count": 0,
        "positive_visible_count": 0,
        "published_positive_evaluable": 0,
        "published_positive_total": 0,
        "synthetic_decoy_binding_roc_auc": 0.0,
    },
    "entries": [],
    "meta": {"citations": {}, "limitations": []},
}
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
        scene["truth"] == "Schematic — data real, geometry illustrative"
        for scene in scenes["schematics"].values()
    )

    positions = [html.index(f"/* inline:{name} */") for name in SCRIPT_ORDER]
    assert positions == sorted(positions)
    assert html.count("(function (global)") >= len(SCRIPT_ORDER)


def test_report_is_network_free_single_file_with_defensive_csp() -> None:
    html = render_report(_fixture())
    assert "connect-src 'none'" in html
    assert re.search(r"<script[^>]+\bsrc\s*=", html, re.IGNORECASE) is None
    assert re.search(r"<link[^>]+\bhref\s*=", html, re.IGNORECASE) is None
    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "import(",
        "WebSocket(",
        "EventSource(",
        "navigator.sendBeacon",
        "document.cookie",
        "credentials:",
    ):
        assert forbidden not in html
    assert 2_000_000 <= len(html.encode("utf-8")) <= 6_000_000


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


def test_browser_sources_avoid_atlas_markup_injection_and_clean_up_listeners() -> None:
    atlas = (WEB / "atlas.js").read_text(encoding="utf-8")
    main = (WEB / "main.js").read_text(encoding="utf-8")
    funnel = (WEB / "funnel.js").read_text(encoding="utf-8")
    assert "innerHTML" not in atlas
    assert "createElementNS" in atlas and "textContent" in atlas
    assert 'removeEventListener("toggle"' in main
    assert "if (tornDown)" in main
    assert "record.controller.destroy()" in main
    assert "controllers.slice().reverse()" in main
    assert '"funnel-app", "atlas-app", "theater-app", "structure-app", "methods-app"' in main
    assert 'removeEventListener("change"' in atlas
    assert 'removeEventListener("change"' in funnel
