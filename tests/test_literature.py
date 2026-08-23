"""Tests for the truthful published-positive agreement panel."""

from __future__ import annotations

from collections import Counter

import numpy as np

from keyhole.bind import AA_ORDER, BindingPrediction
from keyhole.data import load_literature_records
from keyhole.literature import (
    NEGATIVE_KIND,
    UNSUPPORTED_REASON,
    evaluate_literature_panel,
    generate_matched_negative,
)


class RecordingBinder:
    """Simple deterministic binder that records every requested restriction."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def predict(self, peptide: str, allele: str) -> BindingPrediction:
        self.calls.append((peptide, allele))
        rank = 1.0 if peptide in {record.peptide for record in load_literature_records()} else 12.0
        return BindingPrediction(allele, peptide, 100.0 if rank == 1.0 else 6_000.0, rank)


def test_matched_negative_is_seeded_distinct_and_composition_preserving() -> None:
    positive = "AAGIGILTV"
    first = generate_matched_negative(positive, "A*02:01")
    second = generate_matched_negative(positive, "A*02:01")
    assert first == second
    assert first != positive
    assert len(first) == len(positive)
    assert Counter(first) == Counter(positive)


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
