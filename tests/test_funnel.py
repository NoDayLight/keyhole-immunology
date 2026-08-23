"""Tests for truthful labels, deterministic heuristics, and verdict language."""

from __future__ import annotations

import numpy as np

from keyhole.bind import AA_ORDER
from keyhole.data import iter_self_peptides
from keyhole.funnel import (
    CITATIONS,
    METHOD_LABELS,
    cleavage_score,
    foreignness_score,
    tap_score,
    verdict_engine,
)
from keyhole.schema import Verdict


def test_every_stage_is_truth_labeled_and_cited() -> None:
    assert METHOD_LABELS["binding"] == "measured ML"
    assert set(METHOD_LABELS.values()) == {"measured ML", "heuristic approximation"}
    assert {"cleavage", "processing", "tap", "foreignness", "blosum62"} <= CITATIONS.keys()
    assert "10.1038/nature24473" in CITATIONS["foreignness"]


def test_processing_heuristics_are_bounded_and_deterministic() -> None:
    peptide = "GILGFVFTL"
    assert cleavage_score(peptide) == cleavage_score(peptide)
    assert tap_score(peptide) == tap_score(peptide)
    assert 0 <= cleavage_score(peptide) <= 1
    assert 0 <= tap_score(peptide) <= 1
    assert cleavage_score("AAAAAAAAF") > cleavage_score("AAAAAAAAP")


def test_nearest_self_blosum_distance_is_zero_for_exact_sampled_self() -> None:
    self_peptide = next(iter_self_peptides())
    row = np.asarray([[AA_ORDER.index(residue) for residue in self_peptide]], dtype=np.uint8)
    assert foreignness_score(self_peptide, self_index=row) == 0.0
    changed = "W" + self_peptide[1:]
    assert 0 <= foreignness_score(changed, self_index=row) <= 1


def test_verdict_engine_covers_all_verdicts_and_required_language() -> None:
    invisible_processing = verdict_engine(
        cleavage=0.1,
        tap=0.8,
        binding_rank=0.1,
        binding_ic50=20,
        foreignness=0.5,
        agretopicity=4,
    )
    invisible_binding = verdict_engine(
        cleavage=0.8,
        tap=0.8,
        binding_rank=30,
        binding_ic50=20_000,
        foreignness=0.5,
        agretopicity=4,
    )
    invisible_self = verdict_engine(
        cleavage=0.8,
        tap=0.8,
        binding_rank=0.1,
        binding_ic50=20,
        foreignness=0.01,
        agretopicity=4,
    )
    faint = verdict_engine(
        cleavage=0.8,
        tap=0.8,
        binding_rank=4,
        binding_ic50=800,
        foreignness=0.07,
        agretopicity=1.1,
    )
    clear = verdict_engine(
        cleavage=0.8,
        tap=0.8,
        binding_rank=0.1,
        binding_ic50=20,
        foreignness=0.5,
        agretopicity=4,
    )
    assert invisible_processing[0] is Verdict.INVISIBLE
    assert "never gets displayed" in invisible_processing[2]
    assert "doesn't fit your keyhole" in invisible_binding[2]
    assert "looks too much like yourself" in invisible_self[2]
    assert faint[0] is Verdict.VISIBLE_FAINT
    assert clear[0] is Verdict.VISIBLE_CLEAR
    assert {item[0] for item in (invisible_processing, faint, clear)} == set(Verdict)
