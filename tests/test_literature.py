"""Tests for the truthful published-positive agreement panel."""

from __future__ import annotations

import copy
import json
from collections import Counter

import numpy as np
import pytest

from keyhole.assets import packaged_file
from keyhole.bind import AA_ORDER, BindingPrediction
from keyhole.data import load_literature_records
from keyhole.literature import (
    NEGATIVE_KIND,
    UNSUPPORTED_REASON,
    evaluate_literature_panel,
    generate_matched_negative,
)
from keyhole.schema import SchemaError, validate_results


class RecordingBinder:
    """Simple deterministic binder that records every requested restriction."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def predict(self, peptide: str, allele: str) -> BindingPrediction:
        self.calls.append((peptide, allele))
        rank = 1.0 if peptide in {record.peptide for record in load_literature_records()} else 12.0
        return BindingPrediction(allele, peptide, 100.0 if rank == 1.0 else 6_000.0, rank)


def _document_with_literature() -> dict:
    document = json.loads(
        packaged_file("validation/results.sample.json").read_text(encoding="utf-8")
    )
    self_index = np.full((1, 9), AA_ORDER.index("W"), dtype=np.uint8)
    document["literature"] = evaluate_literature_panel(
        binder=RecordingBinder(), self_index=self_index
    )
    return document


def test_matched_negative_is_seeded_distinct_and_composition_preserving() -> None:
    positive = "AAGIGILTV"
    first = generate_matched_negative(positive, "A*02:01")
    second = generate_matched_negative(positive, "A*02:01")
    assert first == second
    assert first != positive
    assert len(first) == len(positive)
    assert Counter(first) == Counter(positive)
    with pytest.raises(ValueError, match="non-canonical"):
        generate_matched_negative("AAAAAAAAX", "A*02:01")


def test_panel_preserves_publication_facts_and_excludes_unsupported_hla_c() -> None:
    binder = RecordingBinder()
    self_index = np.full((1, 9), AA_ORDER.index("W"), dtype=np.uint8)
    result = evaluate_literature_panel(binder=binder, self_index=self_index)
    entries = result["entries"]
    stats = result["agreement_stats"]

    assert len(entries) == 10
    assert stats["published_positive_total"] == 10
    assert stats["published_positive_evaluable"] == 9
    assert stats["published_positive_not_evaluable"] == 1
    assert stats["not_evaluable_by_reason"] == {UNSUPPORTED_REASON: 1}
    assert stats["positive_agreement_rate"] == stats["positive_visible_count"] / 9
    assert stats["matched_decoy_evaluable"] == 9
    strata = stats["by_binding_exposure"]
    assert strata["train"] == {
        "published_positive_total": 5,
        "published_positive_evaluable": 5,
        "positive_visible_count": 5,
        "matched_decoy_evaluable": 5,
        "matched_decoy_rejected_count": 5,
        "paired_binding_rank_wins": 5,
        "positive_split_counts": {"train": 5, "validation": 0, "test": 0},
        "synthetic_decoy_binding_roc_auc": 1.0,
    }
    assert strata["held_out"]["published_positive_total"] == 2
    assert strata["held_out"]["positive_split_counts"] == {
        "train": 0,
        "validation": 0,
        "test": 2,
    }
    assert strata["not_in_binding_dataset"]["published_positive_total"] == 3
    assert strata["not_in_binding_dataset"]["published_positive_evaluable"] == 2
    assert len(binder.calls) == 18
    assert all(allele in {"A*01:01", "A*02:01"} for _peptide, allele in binder.calls)

    unsupported = next(entry for entry in entries if entry["peptide"] == "GADGVGKSAL")
    assert unsupported["allele"] == "C*08:02"
    assert unsupported["evaluation_status"] == "not_evaluable"
    assert unsupported["prediction"]["binding"] is None
    assert unsupported["prediction"]["verdict"] is None
    assert unsupported["prediction"]["reason_codes"] == [UNSUPPORTED_REASON]
    assert unsupported["external_facts"]["pmid"] == "27959684"
    assert unsupported["matched_negative"]["evaluation_status"] == "not_evaluable"


def test_panel_is_deterministic_and_never_claims_wild_type_or_assayed_decoys() -> None:
    self_index = np.full((1, 9), AA_ORDER.index("W"), dtype=np.uint8)
    first = evaluate_literature_panel(binder=RecordingBinder(), self_index=self_index)
    second = evaluate_literature_panel(binder=RecordingBinder(), self_index=self_index)
    assert first == second
    for entry in first["entries"]:
        assert entry["prediction"]["agretopicity"]["value"] is None
        assert entry["prediction"]["wild_type"]["status"] == "not_available"
        assert entry["matched_negative"]["kind"] == NEGATIVE_KIND
        assert entry["matched_negative"]["experimental_assay_result"] is None
        assert Counter(entry["peptide"]) == Counter(entry["matched_negative"]["peptide"])
    limitations = " ".join(first["meta"]["limitations"])
    assert "not experimentally measured negatives" in limitations
    assert "not an independent clinical validation" in limitations


def test_schema_reconciles_literature_entries_with_every_summary() -> None:
    document = _document_with_literature()
    validate_results(document)

    impossible_count = copy.deepcopy(document)
    impossible_count["literature"]["agreement_stats"]["positive_visible_count"] = 999
    with pytest.raises(SchemaError, match="positive_visible_count"):
        validate_results(impossible_count)

    wrong_auc = copy.deepcopy(document)
    wrong_auc["literature"]["agreement_stats"]["synthetic_decoy_binding_roc_auc"] = 0.0
    with pytest.raises(SchemaError, match="roc_auc"):
        validate_results(wrong_auc)

    flipped_overlap = copy.deepcopy(document)
    entry = flipped_overlap["literature"]["entries"][0]
    entry["binding_dataset_overlap"] = not entry["binding_dataset_overlap"]
    with pytest.raises(SchemaError, match="by_binding_exposure"):
        validate_results(flipped_overlap)

    swapped_strata = copy.deepcopy(document)
    strata = swapped_strata["literature"]["agreement_stats"]["by_binding_exposure"]
    strata["train"], strata["held_out"] = strata["held_out"], strata["train"]
    with pytest.raises(SchemaError, match="by_binding_exposure"):
        validate_results(swapped_strata)

    mismatched_decoy = copy.deepcopy(document)
    mismatched_decoy["literature"]["entries"][0]["matched_negative"][
        "evaluation_status"
    ] = "not_evaluable"
    with pytest.raises(SchemaError, match="evaluability must agree"):
        validate_results(mismatched_decoy)


def test_schema_types_literature_renderer_fields() -> None:
    document = _document_with_literature()
    mutations = (
        ("disease_context", 42),
        ("source_molecule", ["not", "text"]),
    )
    for name, value in mutations:
        mistyped = copy.deepcopy(document)
        mistyped["literature"]["entries"][0]["external_facts"][name] = value
        with pytest.raises(SchemaError, match=name):
            validate_results(mistyped)

    mistyped_method = copy.deepcopy(document)
    mistyped_method["literature"]["meta"]["methods"]["binding"] = 42
    with pytest.raises(SchemaError, match="methods.binding"):
        validate_results(mistyped_method)
