"""Tests for frozen dataset integrity and typed loading."""

from __future__ import annotations

from itertools import islice

import pytest

from keyhole.data import (
    CANONICAL_AMINO_ACIDS,
    iter_binding_records,
    iter_self_peptides,
    load_famous_proteins,
    load_hla_frequencies,
    load_literature_records,
    load_residue_templates,
    pdb_path,
)


def test_binding_snapshot_has_measured_common_hla_data() -> None:
    records = list(iter_binding_records(limit=25))
    assert len(records) == 25
    order = lambda item: (item.allele, len(item.peptide), item.peptide)  # noqa: E731
    assert records == sorted(records, key=order)
    assert all(len(item.peptide) in {9, 10} for item in records)
    assert all(item.ic50_nm > 0 and item.inequality in {"<", "=", ">"} for item in records)
    assert sum(1 for _ in iter_binding_records()) == 95_441


def test_self_snapshot_is_exactly_500000_unique_canonical_nine_mers() -> None:
    peptides = list(iter_self_peptides())
    assert len(peptides) == len(set(peptides)) == 500_000
    assert peptides == sorted(peptides)
    assert all(len(peptide) == 9 and set(peptide) <= CANONICAL_AMINO_ACIDS for peptide in peptides)
    assert list(islice(iter_self_peptides(limit=3), 3)) == peptides[:3]


def test_population_and_literature_snapshots_are_real_and_explicitly_narrowed() -> None:
    frequencies = load_hla_frequencies()
    assert len(frequencies) == 230
    assert {item.superpopulation for item in frequencies} == {"AFR", "AMR", "EAS", "EUR"}
    assert "SAS" not in {item.superpopulation for item in frequencies}
    assert all(0 < item.frequency <= 1 for item in frequencies)

    literature = load_literature_records()
    assert len(literature) == 10
    assert all(
        item.assay_result.startswith("Positive") and item.pmid.isdigit() for item in literature
    )
    assert any(item.peptide == "GADGVGKSAL" and item.allele == "C*08:02" for item in literature)


def test_frozen_structural_assets_are_verified_not_generated() -> None:
    templates = load_residue_templates()
    proteins = load_famous_proteins()
    assert set(templates) == CANONICAL_AMINO_ACIDS
    assert sum(len(item["atoms"]) for item in templates.values()) == 387
    assert proteins["BRAF"]["sequence"][599] == "V"
    assert proteins["KRAS"]["sequence"][11] == "G"
    assert proteins["TP53"]["sequence"][174] == "R"
    assert "EXPDTA    X-RAY DIFFRACTION" in pdb_path("1AO7").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="verified frozen set"):
        pdb_path("FAKE")
