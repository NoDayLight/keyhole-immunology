"""Contract and frozen-artifact tests for the deterministic S2 binder."""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
import torch

from keyhole.bind import (
    AA_ORDER,
    ALLELES,
    ARTIFACT_DIRECTORY,
    BLOSUM62,
    BindingMLP,
    assign_split,
    encode_peptide,
    load_binder,
    validate_binder,
)
from keyhole.data import data_root, iter_binding_records


def test_exact_architecture_and_fixed_encoding_shape() -> None:
    model = BindingMLP()
    layers = [module for module in model.modules() if isinstance(module, torch.nn.Linear)]
    assert [(layer.in_features, layer.out_features) for layer in layers] == [
        (189, 128),
        (128, 64),
        (64, 1),
    ]
    encoded = encode_peptide("ARNDCQEGH")
    assert encoded.shape == (9, 21)
    assert encoded.dtype == np.float32
    np.testing.assert_array_equal(encoded[:, :20], BLOSUM62[:9])
    np.testing.assert_array_equal(encoded[:, 20], np.zeros(9, dtype=np.float32))
    assert sum(isinstance(module, torch.nn.Flatten) for module in model.modules()) == 1
    assert sum(isinstance(module, torch.nn.ReLU) for module in model.modules()) == 2
    output = model(torch.from_numpy(encoded).unsqueeze(0))
    assert output.shape == (1, 1)


def test_tenmer_mean_pools_only_the_two_center_residue_vectors() -> None:
    peptide = "ARNDCQEGHI"
    encoded = encode_peptide(peptide)
    indices = [AA_ORDER.index(residue) for residue in peptide]
    expected_scores = np.concatenate(
        (
            BLOSUM62[indices[:4]],
            BLOSUM62[indices[4:6]].mean(axis=0, keepdims=True),
            BLOSUM62[indices[6:]],
        )
    )
    assert encoded.shape == (9, 21)
    np.testing.assert_array_equal(encoded[:, :20], expected_scores)
    np.testing.assert_array_equal(encoded[:, 20], np.ones(9, dtype=np.float32))


def test_global_peptide_split_is_deterministic_and_has_no_cross_allele_leakage() -> None:
    assignments: dict[str, str] = {}
    peptide_alleles: dict[str, set[str]] = {}
    split_peptides = {name: set() for name in ("train", "validation", "test")}
    for record in iter_binding_records():
        split = assign_split(record.peptide)
        assert split == assign_split(record.peptide)
        assert assignments.setdefault(record.peptide, split) == split
        peptide_alleles.setdefault(record.peptide, set()).add(record.allele)
        split_peptides[split].add(record.peptide)
    assert any(len(alleles) > 1 for alleles in peptide_alleles.values())
    assert split_peptides["train"].isdisjoint(split_peptides["validation"])
    assert split_peptides["train"].isdisjoint(split_peptides["test"])
    assert split_peptides["validation"].isdisjoint(split_peptides["test"])
    assert all(split_peptides.values())


def test_frozen_artifacts_cover_all_26_alleles_and_are_safe_arrays() -> None:
    artifact_dir = data_root() / ARTIFACT_DIRECTORY
    model_files = sorted(artifact_dir.glob("*.npz"))
    assert len(ALLELES) == 26
    assert len(model_files) == 26
    binder = load_binder()
    assert set(binder.models) == set(ALLELES)
    assert set(binder.calibrations) == set(ALLELES)
    for path in model_files:
        with np.load(path, allow_pickle=False) as archive:
            assert archive.files
            assert all(archive[name].dtype != object for name in archive.files)
    card = json.loads((artifact_dir / "model_card.json").read_text(encoding="utf-8"))
    assert card["alleles"] == list(ALLELES)
    assert "10.1073/pnas.89.22.10915" in card["blosum62"]["citation"]
    assert "10.1093/nar/gky1006" in card["dataset"]["citation"]
    assert "censor-bound" in card["censoring"]["approximation"]


def test_inference_is_byte_and_value_deterministic() -> None:
    first = load_binder().predict("GILGFVFTL", "HLA-A*02:01")
    second = load_binder().predict("GILGFVFTL", "A*02:01")
    assert first == second
    assert struct.pack("!dd", first.ic50_nm, first.percentile_rank) == struct.pack(
        "!dd", second.ic50_nm, second.percentile_rank
    )
    assert math.isfinite(first.ic50_nm) and first.ic50_nm > 0
    assert math.isfinite(first.percentile_rank) and 0 <= first.percentile_rank <= 100


def test_heldout_metrics_are_finite_and_reproduce_stored_values() -> None:
    artifact_dir = data_root() / ARTIFACT_DIRECTORY
    stored = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
    validation = validate_binder()
    assert validation["stored_metrics_reproduced"] is True
    assert validation["metrics"] == {
        key: value
        for key, value in stored.items()
        if key not in {"evaluation", "training_wall_seconds"}
    }
    assert sum(validation["split_unique_peptides"].values()) == 26_010
    assert stored["aggregate"]["roc_evaluable_rows"] == 9_132
    assert stored["aggregate"]["roc_indeterminate_rows"] == 1
    assert stored["per_allele"]["B*46:01"]["roc_indeterminate_rows"] == 1
    assert sum(
        metrics["roc_indeterminate_rows"] for metrics in stored["per_allele"].values()
    ) == 1
    for metrics in [stored["aggregate"], *stored["per_allele"].values()]:
        for name, value in metrics.items():
            if name != "test_rows":
                assert math.isfinite(value)
    assert 0 <= stored["aggregate"]["pooled_roc_auc_500nm"] <= 1
    assert -1 <= stored["aggregate"]["pooled_spearman"] <= 1


def test_artifact_directory_is_within_frozen_iedb_tree() -> None:
    artifact_dir = (data_root() / ARTIFACT_DIRECTORY).resolve()
    assert artifact_dir.parent == (data_root() / "iedb").resolve()
    assert all(path.is_file() for path in Path(artifact_dir).iterdir())
