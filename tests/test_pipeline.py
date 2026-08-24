"""Tests for deterministic end-to-end screening orchestration."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from keyhole.assets import packaged_file
from keyhole.bind import ALLELES, BindingPrediction
from keyhole.parse import parse_famous
from keyhole.peptides import PeptidePair
from keyhole.pipeline import (
    PipelineError,
    load_screen_input,
    normalize_hla_list,
    screen_variants,
)
from keyhole.schema import validate_results

DATA = Path(__file__).parents[1] / "data"
LITERATURE_STUB = json.loads(
    packaged_file("validation/results.sample.json").read_text(encoding="utf-8")
)["literature"]


class RecordingBinder:
    """Stable test double that records one vectorized call per allele/sequence class."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def predict(self, peptide: str, allele: str) -> BindingPrediction:
        """Return one stable prediction for literature-panel tests."""

        return self.predict_many((peptide,), allele)[0]

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
    foreignness_calls: list[str] = []

    def scalar_foreignness(peptide: str) -> float:
        foreignness_calls.append(peptide)
        return 0.75

    run = screen_variants(
        [parse_famous("BRAF V600E")],
        "A*02:01,B*07:02",
        input_name="fixed",
        input_path="famous:BRAF V600E",
        binder=binder,
        foreignness_fn=scalar_foreignness,
        literature_branch=LITERATURE_STUB,
        population_draws=64,
        created_utc="2026-08-24T00:00:00Z",
    )

    assert validate_results(run.results) is run.results
    assert run.results["alleles"] == ["A*02:01", "B*07:02"]
    calls_per_allele = Counter(allele for allele, _peptides in binder.calls)
    assert calls_per_allele == Counter({allele: 2 for allele in ALLELES})
    assert all(peptides for _allele, peptides in binder.calls)
    assert foreignness_calls == list(binder.calls[0][1])

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


def test_pipeline_reuses_prediction_shared_by_mutant_and_wild_batches(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    import keyhole.pipeline as pipeline_module

    shared = "CCCCCCCCC"
    pairs = (
        PeptidePair("AAAAAAAAA", shared, 0, 0, "missense"),
        PeptidePair(shared, "DDDDDDDDD", 0, 1, "missense"),
    )
    monkeypatch.setattr(pipeline_module, "variant_peptides", lambda _variant: pairs)
    binder = RecordingBinder()

    run = screen_variants(
        [parse_famous("BRAF V600E")],
        "A*02:01",
        input_name="shared",
        input_path="famous:BRAF V600E",
        binder=binder,
        foreignness_fn=lambda _peptide: 0.75,
        literature_branch=LITERATURE_STUB,
        population_draws=8,
        created_utc="2026-08-24T00:00:00Z",
    )

    assert validate_results(run.results) is run.results
    expected_mutants = ("AAAAAAAAA", shared)
    expected_wild = (shared, "DDDDDDDDD")
    assert binder.calls == [
        call
        for allele in ALLELES
        for call in ((allele, expected_mutants), (allele, expected_wild))
    ]

    class ConflictingBinder(RecordingBinder):
        def __init__(self) -> None:
            super().__init__()
            self.returned: set[tuple[str, str]] = set()

        def predict_many(
            self, peptides: list[str] | tuple[str, ...], allele: str
        ) -> tuple[BindingPrediction, ...]:
            predictions = super().predict_many(peptides, allele)
            values: list[BindingPrediction] = []
            for prediction in predictions:
                key = (prediction.peptide, prediction.allele)
                values.append(
                    replace(prediction, ic50_nm=prediction.ic50_nm + 1.0)
                    if key in self.returned
                    else prediction
                )
                self.returned.add(key)
            return tuple(values)

    with pytest.raises(PipelineError, match="conflicting binder predictions"):
        screen_variants(
            [parse_famous("BRAF V600E")],
            "A*02:01",
            input_name="conflicting",
            input_path="famous:BRAF V600E",
            binder=ConflictingBinder(),
            foreignness_fn=lambda _peptide: 0.75,
            literature_branch=LITERATURE_STUB,
            population_draws=8,
        )


def test_pipeline_batches_default_foreignness_once(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import keyhole.pipeline as pipeline_module

    calls: list[tuple[str, ...]] = []

    def batched(peptides: tuple[str, ...]) -> tuple[float, ...]:
        calls.append(tuple(peptides))
        return (0.75,) * len(peptides)

    monkeypatch.setattr(pipeline_module, "foreignness_scores", batched)
    binder = RecordingBinder()
    screen_variants(
        [parse_famous("BRAF V600E")],
        "A*02:01",
        input_name="fixed",
        input_path="famous:BRAF V600E",
        binder=binder,
        literature_branch=LITERATURE_STUB,
        population_draws=8,
        created_utc="2026-08-24T00:00:00Z",
    )
    assert calls == [binder.calls[0][1]]


def test_cli_reuses_pipeline_validation_for_both_outputs(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    import keyhole.pipeline as pipeline_module
    import keyhole.report as report_module
    from keyhole.cli import _write_outputs

    validations: list[object] = []
    original = pipeline_module.validate_results

    def counted(document):  # type: ignore[no-untyped-def]
        validations.append(document)
        return original(document)

    monkeypatch.setattr(pipeline_module, "validate_results", counted)
    monkeypatch.setattr(report_module, "validate_results", counted)
    run = screen_variants(
        [parse_famous("BRAF V600E")],
        "A*02:01",
        input_name="fixed",
        input_path="famous:BRAF V600E",
        binder=RecordingBinder(),
        population_draws=8,
        created_utc="2026-08-24T00:00:00Z",
    )
    report = tmp_path / "report.html"
    results = tmp_path / "results.json"
    assert _write_outputs(run, report, results) == report.resolve()
    assert report.is_file() and results.is_file()
    assert validations == [run.results]


def test_pipeline_rejects_incomplete_prediction_batches() -> None:
    class IncompleteBinder(RecordingBinder):
        def predict_many(
            self, peptides: list[str] | tuple[str, ...], allele: str
        ) -> tuple[BindingPrediction, ...]:
            return super().predict_many(peptides, allele)[:-1]

    with pytest.raises(PipelineError, match="predictions for"):
        screen_variants(
            [parse_famous("BRAF V600E")],
            "A*02:01",
            input_name="broken",
            input_path="famous:BRAF V600E",
            binder=IncompleteBinder(),
            literature_branch=LITERATURE_STUB,
            population_draws=8,
        )


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
