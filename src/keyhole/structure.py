"""Truth-labeled structural assets and deterministic candidate schematics."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from keyhole.bind import AA_ORDER
from keyhole.data import pdb_path

REAL_TRUTH_PREFIX = "Real crystal structure (PDB "
SCHEMATIC_TRUTH = "Schematic — data real, geometry illustrative"
SCHEMATIC_DETAIL = (
    "Residue-bead layout only; not an experimentally measured, structure-predicted, "
    "or HLA-docked conformation."
)

STRUCTURES: dict[str, dict[str, object]] = {
    "1HHK": {
        "pdb_id": "1HHK",
        "title": "HTLV-1 Tax peptide bound to HLA-A*02:01",
        "method": "X-ray diffraction",
        "resolution_angstrom": 2.5,
        "display_chains": ["A", "B", "C"],
        "chain_roles": {"A": "HLA heavy chain", "B": "β2-microglobulin", "C": "peptide"},
        "peptide": "LLFGYPVYV",
        "citation": "Madden et al. Cell. 1993. DOI 10.1016/0092-8674(93)90490-H",
    },
    "3PWN": {
        "pdb_id": "3PWN",
        "title": "HuD G2L peptide bound to HLA-A2",
        "method": "X-ray diffraction",
        "resolution_angstrom": 1.6,
        "display_chains": ["A", "B", "C"],
        "chain_roles": {"A": "HLA heavy chain", "B": "β2-microglobulin", "C": "peptide"},
        "peptide": "LLYGFVNYI",
        "citation": "Borbulevych et al. J Immunol. 2011. DOI 10.4049/jimmunol.1003150",
    },
    "1AO7": {
        "pdb_id": "1AO7",
        "title": "T-cell receptor bound to Tax peptide–HLA-A*02:01",
        "method": "X-ray diffraction",
        "resolution_angstrom": 2.6,
        "display_chains": ["A", "B", "C", "D", "E"],
        "chain_roles": {
            "A": "HLA heavy chain",
            "B": "β2-microglobulin",
            "C": "peptide",
            "D": "TCR α chain",
            "E": "TCR β chain",
        },
        "peptide": "LLFGYPVYV",
        "citation": "Garboczi et al. Nature. 1996. DOI 10.1038/384134a0",
    },
}


@dataclass(frozen=True, slots=True)
class PDBSummary:
    """Deterministic integrity summary of a legacy fixed-column PDB file."""

    pdb_id: str
    raw_coordinate_records: int
    selected_atom_sites: int
    polymer_atom_sites: int
    hetero_atom_sites: int
    water_atom_sites: int
    polymer_residues: int
    alternate_records: int
    discarded_alternate_records: int
    zero_occupancy_records: int
    chains: tuple[str, ...]
    insertion_codes: tuple[str, ...]
    chain_atom_counts: tuple[tuple[str, int], ...]


def _number(text: str, *, integer: bool = False) -> int | float:
    value = text.strip()
    if not value:
        return 0 if integer else 0.0
    return int(value) if integer else float(value)


def summarize_pdb(path: str | Path) -> PDBSummary:
    """Parse enough fixed-column PDB state to verify real structural assets."""

    source = Path(path)
    raw_atoms: list[dict[str, object]] = []
    model = 0
    first_model = 0
    for line in source.read_text(encoding="utf-8").splitlines():
        record = line[:6].strip()
        if record == "MODEL":
            model = int(line[10:14].strip() or "1")
            if first_model == 0:
                first_model = model
            continue
        if record == "ENDMDL" and model == first_model:
            break
        if record not in {"ATOM", "HETATM"}:
            continue
        if first_model and model != first_model:
            continue
        padded = line.ljust(80)
        x = float(padded[30:38])
        y = float(padded[38:46])
        z = float(padded[46:54])
        if not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError(f"non-finite PDB coordinate in {source}")
        raw_atoms.append(
            {
                "record": record,
                "serial": _number(padded[6:11], integer=True),
                "name": padded[12:16].strip(),
                "alt": padded[16].strip(),
                "residue": padded[17:20].strip(),
                "chain": padded[21].strip() or "_",
                "res_seq": _number(padded[22:26], integer=True),
                "insertion": padded[26].strip(),
                "occupancy": _number(padded[54:60]),
            }
        )

    by_site: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for atom in raw_atoms:
        key = (
            atom["record"],
            atom["chain"],
            atom["res_seq"],
            atom["insertion"],
            atom["residue"],
            atom["name"],
        )
        by_site[key].append(atom)
    selected: list[dict[str, object]] = []
    for alternatives in by_site.values():
        blank = [atom for atom in alternatives if not atom["alt"]]
        choices = blank or alternatives
        selected.append(
            min(
                choices,
                key=lambda atom: (-float(atom["occupancy"]), str(atom["alt"] or " ")),
            )
        )

    chain_counts = Counter(str(atom["chain"]) for atom in selected if atom["record"] == "ATOM")
    polymer_residues = {
        (atom["chain"], atom["res_seq"], atom["insertion"], atom["residue"])
        for atom in selected
        if atom["record"] == "ATOM"
    }
    waters = [atom for atom in selected if atom["residue"] in {"HOH", "WAT"}]
    hetero = [atom for atom in selected if atom["record"] == "HETATM"]
    return PDBSummary(
        pdb_id=source.stem.upper(),
        raw_coordinate_records=len(raw_atoms),
        selected_atom_sites=len(selected),
        polymer_atom_sites=sum(atom["record"] == "ATOM" for atom in selected),
        hetero_atom_sites=len(hetero),
        water_atom_sites=len(waters),
        polymer_residues=len(polymer_residues),
        alternate_records=sum(bool(atom["alt"]) for atom in raw_atoms),
        discarded_alternate_records=len(raw_atoms) - len(selected),
        zero_occupancy_records=sum(float(atom["occupancy"]) == 0 for atom in raw_atoms),
        chains=tuple(sorted(chain_counts)),
        insertion_codes=tuple(
            sorted(
                {
                    f"{atom['chain']}:{atom['res_seq']}{atom['insertion']}"
                    for atom in selected
                    if atom["insertion"]
                }
            )
        ),
        chain_atom_counts=tuple(sorted(chain_counts.items())),
    )


def structure_descriptor(pdb_id: str) -> dict[str, object]:
    """Return additive report metadata for a verified experimental structure."""

    normalized = pdb_id.strip().upper()
    if normalized not in STRUCTURES:
        raise ValueError(f"unknown verified structure: {normalized}")
    descriptor = dict(STRUCTURES[normalized])
    descriptor["chain_roles"] = dict(descriptor["chain_roles"])
    descriptor["display_chains"] = list(descriptor["display_chains"])
    descriptor["truth"] = f"{REAL_TRUTH_PREFIX}{normalized})"
    descriptor["geometry"] = "experimental atomic coordinates"
    return descriptor


def structure_payload(pdb_id: str) -> dict[str, object]:
    """Return a complete inline-ready real structure payload."""

    descriptor = structure_descriptor(pdb_id)
    descriptor["kind"] = "pdb"
    descriptor["pdb_text"] = pdb_path(pdb_id).read_text(encoding="utf-8")
    return descriptor


def schematic_peptide_scene(sequence: str, mutation_position: int) -> dict[str, object]:
    """Build a deterministic residue-bead schematic, never a claimed molecular pose."""

    peptide = sequence.strip().upper()
    if len(peptide) not in {9, 10} or set(peptide) - set(AA_ORDER):
        raise ValueError("candidate schematic requires a canonical 9-mer or 10-mer")
    if mutation_position < 0 or mutation_position >= len(peptide):
        raise ValueError("mutation position must index the candidate peptide")
    center = (len(peptide) - 1) / 2
    atoms: list[dict[str, object]] = []
    for index, residue in enumerate(peptide):
        angle = index * 0.72
        atoms.append(
            {
                "id": index + 1,
                "name": "CA schematic bead",
                "residue": residue,
                "res_seq": index + 1,
                "chain": "C",
                "element": "C",
                "x": round((index - center) * 3.4, 6),
                "y": round(1.25 * math.sin(angle), 6),
                "z": round(1.25 * math.cos(angle), 6),
                "role": "mutation" if index == mutation_position else "peptide",
            }
        )
    return {
        "kind": "schematic",
        "sequence": peptide,
        "mutation_position": mutation_position,
        "truth": SCHEMATIC_TRUTH,
        "geometry": SCHEMATIC_DETAIL,
        "atoms": atoms,
        "bonds": [[index, index + 1] for index in range(1, len(peptide))],
        "chain_roles": {"C": "candidate peptide schematic"},
    }
