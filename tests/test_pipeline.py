"""Tests for deterministic end-to-end screening orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from keyhole.bind import ALLELES, BindingPrediction
from keyhole.parse import parse_famous
from keyhole.pipeline import (
    PipelineError,
    load_screen_input,
    normalize_hla_list,
    screen_variants,
)
from keyhole.schema import validate_results

DATA = Path(__file__).parents[1] / "data"
LITERATURE_STUB = {"entries": [], "agreement_stats": {}}


class RecordingBinder:
    """Stable test double that records one vectorized call per allele/sequence class."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def predict_many(
        self, peptides: list[str] | tuple[str, ...], allele: str
    ) -> tuple[BindingPrediction, ...]:
        values = tuple(peptides)
        self.calls.append((allele, values))
        offset = ALLELES.index(allele)
        return tuple(
            BindingPrediction(
                allele=allele,
                peptide=peptide,
                ic50_nm=75.0 + offset,
                percentile_rank=1.0 + offset / 10.0,
            )
            for peptide in values
        )


def test_hla_normalization_is_strict_and_stable() -> None:
    assert normalize_hla_list(" hla-a*02:01, B*07:02 ") == ("A*02:01", "B*07:02")
    with pytest.raises(PipelineError, match="duplicate"):
        normalize_hla_list("A*02:01,HLA-A*02:01")
    with pytest.raises(PipelineError, match="unsupported"):
        normalize_hla_list("C*08:02")
    with pytest.raises(PipelineError, match="at least one"):
        normalize_hla_list(" , ")


def test_real_skcm_input_audit_preserves_unsupported_rows() -> None:
    variants, audit = load_screen_input(DATA / "examples" / "tcga_skcm.maf")
    assert len(variants) == 89
    assert audit.as_dict() == {
        "ignored_class_count": 11,
        "input_row_count": 100,
        "missing_canonical_context_count": 87,
        "screenable_variant_count": 2,
        "supported_change_count": 89,
        "unsupported_frameshift_count": 0,
    }


def test_real_paad_audit_counts_unresolved_frameshifts_independently() -> None:
    variants, audit = load_screen_input(DATA / "examples" / "tcga_paad.maf")
    assert len(variants) == 94
    assert audit.as_dict() == {
        "ignored_class_count": 6,
        "input_row_count": 100,
        "missing_canonical_context_count": 92,
        "screenable_variant_count": 2,
        "supported_change_count": 94,
        "unsupported_frameshift_count": 1,
    }


def test_pipeline_batches_all_models_but_patient_evidence_uses_only_user_hla() -> None:
    binder = RecordingBinder()
    run = screen_variants(
        [parse_famous("BRAF V600E")],
        "A*02:01,B*07:02",
        input_name="fixed",
        input_path="famous:BRAF V600E",
        binder=binder,
        foreignness_fn=lambda _peptide: 0.75,
        literature_branch=LITERATURE_STUB,
        population_draws=64,
        created_utc="2026-08-24T00:00:00Z",
    )

    assert validate_results(run.results) is run.results
    assert run.results["alleles"] == ["A*02:01", "B*07:02"]
    calls_per_allele = Counter(allele for allele, _peptides in binder.calls)
    assert calls_per_allele == Counter({allele: 2 for allele in ALLELES})
    assert all(peptides for _allele, peptides in binder.calls)

    mutations = run.results["mutations"]
    assert isinstance(mutations, list)
    peptides = mutations[0]["peptides"]
    assert peptides
    assert all(
        set(peptide["scores"]["binding"]) == {"A*02:01", "B*07:02"}
        for peptide in peptides
    )
    matrix = run.results["population"]["peptide_allele_matrix"]
    assert all(set(cells) == set(ALLELES) for cells in matrix.values())

    repeated = screen_variants(
        [parse_famous("BRAF V600E")],
        ["A*02:01", "B*07:02"],
        input_name="fixed",
        input_path="famous:BRAF V600E",
        binder=RecordingBinder(),
        foreignness_fn=lambda _peptide: 0.75,
        literature_branch=LITERATURE_STUB,
        population_draws=64,
        created_utc="2026-08-24T00:00:00Z",
    )
    assert repeated.results == run.results


def test_pipeline_refuses_to_invent_missing_canonical_context() -> None:
    unresolved = replace(parse_famous("KRAS G12D"), protein_sequence=None)
    with pytest.raises(PipelineError, match="no variants have frozen canonical missense context"):
        screen_variants(
            [unresolved],
            "A*02:01",
            input_name="unresolved",
            input_path="test.maf",
            binder=RecordingBinder(),
            literature_branch=LITERATURE_STUB,
            population_draws=8,
        )
