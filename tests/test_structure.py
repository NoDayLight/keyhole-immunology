"""Tests for verified PDB metadata and truthful candidate schematics."""

from __future__ import annotations

import pytest

from keyhole.data import pdb_path
from keyhole.structure import (
    SCHEMATIC_TRUTH,
    schematic_peptide_scene,
    structure_descriptor,
    summarize_pdb,
)


def test_fixed_column_summaries_match_frozen_coordinate_assets() -> None:
    one_hhk = summarize_pdb(pdb_path("1HHK"))
    three_pwn = summarize_pdb(pdb_path("3PWN"))
    one_ao7 = summarize_pdb(pdb_path("1AO7"))

    assert (one_hhk.raw_coordinate_records, one_hhk.selected_atom_sites) == (6_322, 6_322)
    assert dict(one_hhk.chain_atom_counts) == {
        "A": 2_247,
        "B": 837,
        "C": 77,
        "D": 2_247,
        "E": 837,
        "F": 77,
    }
    assert one_hhk.polymer_residues == 768

    assert (three_pwn.raw_coordinate_records, three_pwn.selected_atom_sites) == (7_215, 7_133)
    assert three_pwn.polymer_atom_sites == 6_326
    assert three_pwn.hetero_atom_sites == 807
    assert three_pwn.water_atom_sites == 777
    assert three_pwn.alternate_records == 164
    assert three_pwn.discarded_alternate_records == 82
    assert three_pwn.polymer_residues == 768

    assert (one_ao7.raw_coordinate_records, one_ao7.selected_atom_sites) == (5_711, 5_711)
    assert one_ao7.polymer_atom_sites == 5_668
    assert one_ao7.hetero_atom_sites == 43
    assert one_ao7.water_atom_sites == 37
    assert one_ao7.polymer_residues == 707
    assert one_ao7.chains == ("A", "B", "C", "D", "E")
    assert "E:116A" in one_ao7.insertion_codes


def test_real_structures_have_exact_truth_labels_and_roles() -> None:
    pmhc = structure_descriptor("1HHK")
    tcr = structure_descriptor("1AO7")
    misleading_keyword_entry = structure_descriptor("3PWN")
    assert pmhc["truth"] == "Real crystal structure (PDB 1HHK)"
    assert tcr["truth"] == "Real crystal structure (PDB 1AO7)"
    assert tcr["chain_roles"]["D"] == "TCR α chain"
    assert tcr["chain_roles"]["E"] == "TCR β chain"
    assert "D" not in misleading_keyword_entry["display_chains"]


def test_candidate_scene_is_deterministic_and_unambiguously_schematic() -> None:
    first = schematic_peptide_scene("GILGFVFTL", 4)
    second = schematic_peptide_scene("GILGFVFTL", 4)
    assert first == second
    assert first["truth"] == SCHEMATIC_TRUTH
    assert "not an experimentally measured" in first["geometry"]
    assert "not" in first["geometry"] and "HLA-docked" in first["geometry"]
    assert len(first["atoms"]) == 9
    assert len(first["bonds"]) == 8
    assert first["atoms"][4]["role"] == "mutation"
    assert all(atom["role"] == "peptide" for atom in first["atoms"][:4])
    with pytest.raises(ValueError, match="canonical"):
        schematic_peptide_scene("INVALIDXX", 2)
    with pytest.raises(ValueError, match="index"):
        schematic_peptide_scene("GILGFVFTL", 9)
