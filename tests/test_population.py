"""Tests for seeded HLA Monte Carlo coverage and allele evidence matrices."""

from __future__ import annotations

from keyhole.bind import BindingPrediction
from keyhole.data import load_hla_frequencies
from keyhole.funnel import FunnelResult
from keyhole.peptides import PeptidePair
from keyhole.population import (
    ASSUMPTION,
    coverage_from_matrix,
    peptide_allele_matrix,
    simulate_haplotypes,
)
from keyhole.schema import Verdict


def test_seeded_haplotype_draws_are_value_deterministic() -> None:
    first = simulate_haplotypes(draws=250, seed=1729)
    second = simulate_haplotypes(draws=250, seed=1729)
    assert set(first) == {"AFR", "AMR", "EAS", "EUR"}
    assert all((first[pop] == second[pop]).all() for pop in first)
    assert all(values.shape == (250, 4) for values in first.values())
    assert "linkage equilibrium" in ASSUMPTION


def test_coverage_extremes_and_unavailable_population_are_honest() -> None:
    observed_alleles = {record.allele for record in load_hla_frequencies()}
    matrix = {
        "none": {},
        "all": {allele: True for allele in observed_alleles},
    }
    coverage = coverage_from_matrix(matrix, draws=1_000)
    assert set(coverage["none"]) == {"AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"}
    assert "SAS" not in coverage["none"]
    assert all(value == 0 for value in coverage["none"].values())
    assert all(value == 100 for value in coverage["all"].values())


def test_single_allele_monte_carlo_tracks_observed_frequency() -> None:
    records = [
        record
        for record in load_hla_frequencies()
        if record.superpopulation == "EAS" and record.allele == "A*02:01"
    ]
    assert len(records) == 1
    expected = 100 * (1 - (1 - records[0].frequency) ** 2)
    coverage = coverage_from_matrix({"candidate": {"A*02:01": True}}, draws=50_000)
    assert abs(coverage["candidate"]["EAS"] - expected) < 1.0
    assert coverage == coverage_from_matrix({"candidate": {"A*02:01": True}}, draws=50_000)


def test_matrix_recomputes_visibility_for_each_allele() -> None:
    pair = PeptidePair("GILGFVFTL", "GILGFVFTV", 8, 10, "missense")
    strong = BindingPrediction("A*02:01", pair.seq, 20.0, 0.2)
    weak = BindingPrediction("B*07:02", pair.seq, 20_000.0, 35.0)
    wt_strong = BindingPrediction("A*02:01", pair.wt_seq, 100.0, 2.0)
    wt_weak = BindingPrediction("B*07:02", pair.wt_seq, 15_000.0, 30.0)
    result = FunnelResult(
        pair=pair,
        binding={"A*02:01": strong, "B*07:02": weak},
        wt_binding={"A*02:01": wt_strong, "B*07:02": wt_weak},
        cleavage=0.8,
        tap=0.8,
        agretopicity=5.0,
        foreignness=0.3,
        best_allele="A*02:01",
        verdict=Verdict.VISIBLE_CLEAR,
        reason_codes=("STRONG_BINDING",),
        plain_language="test evidence",
    )
    matrix = peptide_allele_matrix([result])
    assert matrix[pair.seq]["A*02:01"]["visible"] is True
    assert matrix[pair.seq]["B*07:02"]["visible"] is False
    assert matrix[pair.seq]["A*02:01"]["ic50"] == 20.0
    assert matrix[pair.seq]["A*02:01"]["method"] == (
        "measured ML + heuristic approximation"
    )
