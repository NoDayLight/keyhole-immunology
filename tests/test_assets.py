"""Tests for safe wheel-owned runtime resources."""

from __future__ import annotations

from pathlib import Path

import pytest

from keyhole.assets import packaged_directory, packaged_file, safe_child
from keyhole.bind import ALLELES
from keyhole.data import asset_path, data_root
from keyhole.report import SCRIPT_ORDER, web_root


def test_packaged_runtime_closure_is_complete() -> None:
    root = data_root()
    assert root == packaged_directory("data")
    assert (root / "SOURCES.md").is_file()
    assert len(list((root / "iedb" / "binder").glob("*.npz"))) == len(ALLELES) == 26
    for relative in (
        "iedb/mhci_binding_9_10mer.tsv.gz",
        "iedb/binder/model_card.json",
        "iedb/binder/metrics.json",
        "self_peptidome/up000005640_human_9mers.txt.gz",
        "hla_freq/1000g_hla_ab_two_field_frequencies.tsv",
        "literature/tumor_epitopes.tsv",
        "residues/famous_proteins.json",
        "pdb/1AO7.pdb",
        "pdb/1HHK.pdb",
        "pdb/3PWN.pdb",
    ):
        assert asset_path(relative).is_file()
    assert all((web_root() / name).is_file() for name in SCRIPT_ORDER)
    assert packaged_file("validation/results.sample.json").is_file()


def test_current_directory_cannot_shadow_reviewed_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "data"
    fake.mkdir()
    (fake / "SOURCES.md").write_text("untrusted", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KEYHOLE_DATA", raising=False)
    assert data_root() == packaged_directory("data")
    assert web_root() == packaged_directory("web")


def test_external_override_must_be_explicit_and_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEYHOLE_DATA", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="KEYHOLE_DATA"):
        data_root()


def test_resource_paths_reject_traversal() -> None:
    with pytest.raises(ValueError, match="unsafe resource path"):
        asset_path("../README.md")
    with pytest.raises(ValueError, match="unsafe resource path"):
        packaged_file("validation\\results.sample.json")
    with pytest.raises(ValueError, match="unsafe resource path"):
        safe_child(packaged_directory("data"), "/etc/passwd")
