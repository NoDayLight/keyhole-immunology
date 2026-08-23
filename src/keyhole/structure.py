"""Truth-labeled structural assets and deterministic candidate schematics."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from keyhole.bind import AA_ORDER
from keyhole.data import pdb_path

REAL_TRUTH_PREFIX = "Real crystal structure (PDB "
SCHEMATIC_TRUTH = (
    "Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative"
)
SCHEMATIC_DETAIL = (
    "The chain-C Cα backbone comes from measured PDB 1HHK coordinates; candidate residue "
    "identity, 10-mer interpolation, and the idealized mutation side-chain endpoint are "
    "illustrative, not a measured candidate pose, structure prediction, or HLA docking."
)
ONE_HHK_CHAIN_C_CA: tuple[tuple[float, float, float], ...] = (
    (3.009, 11.537, 15.657),
    (2.739, 14.291, 12.992),
    (5.108, 17.244, 12.406),
    (3.634, 20.393, 13.991),
    (4.834, 23.423, 12.017),
    (3.150, 24.808, 8.847),
    (5.225, 24.651, 5.669),
    (3.931, 26.374, 2.503),
    (5.416, 26.033, -1.020),
)
IDEAL_SIDE_CHAIN_REACH = {
    "A": 1.53,
    "C": 2.80,
    "D": 3.70,
    "E": 4.80,
    "F": 5.00,
    "G": 1.20,
    "H": 4.50,
    "I": 3.80,
    "K": 6.30,
    "L": 4.00,
    "M": 5.10,
    "N": 3.60,
    "P": 3.00,
    "Q": 4.70,
    "R": 6.60,
    "S": 2.40,
    "T": 2.80,
    "V": 3.00,
    "W": 6.00,
    "Y": 5.70,
}

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


def _interpolated_backbone(length: int) -> tuple[tuple[float, float, float], ...]:
    """Map a 9/10-mer onto the 1HHK Cα trace without extrapolating its termini."""

    if length == 9:
        return ONE_HHK_CHAIN_C_CA
    points: list[tuple[float, float, float]] = []
    for index in range(length):
        source_position = index * (len(ONE_HHK_CHAIN_C_CA) - 1) / (length - 1)
        lower = math.floor(source_position)
        upper = min(lower + 1, len(ONE_HHK_CHAIN_C_CA) - 1)
        fraction = source_position - lower
        points.append(
            tuple(
                round(
                    ONE_HHK_CHAIN_C_CA[lower][axis] * (1 - fraction)
                    + ONE_HHK_CHAIN_C_CA[upper][axis] * fraction,
                    6,
                )
                for axis in range(3)
            )
        )
    return tuple(points)


def _subtract(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(left[axis] - right[axis] for axis in range(3))


def _cross(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalize(
    vector: tuple[float, float, float],
    fallback: tuple[float, float, float],
) -> tuple[float, float, float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude < 1e-9:
        return fallback
    return tuple(value / magnitude for value in vector)


def _ideal_side_chain_endpoint(
    backbone: tuple[tuple[float, float, float], ...], mutation_position: int, residue: str
) -> tuple[float, float, float]:
    """Place one illustrative endpoint at an ideal tetrahedral angle in a local Cα frame."""

    current = backbone[mutation_position]
    previous = backbone[max(0, mutation_position - 1)]
    following = backbone[min(len(backbone) - 1, mutation_position + 1)]
    tangent = _normalize(_subtract(following, previous), (1.0, 0.0, 0.0))
    incoming = _normalize(_subtract(current, previous), tangent)
    outgoing = _normalize(_subtract(following, current), tangent)
    normal = _normalize(_cross(incoming, outgoing), _cross(tangent, (0.0, 0.0, 1.0)))
    normal = _normalize(normal, _cross(tangent, (0.0, 1.0, 0.0)))
    normal = _normalize(normal, (0.0, 0.0, 1.0))
    tetrahedral = math.radians(109.5)
    direction = _normalize(
        tuple(
            math.cos(tetrahedral) * tangent[axis]
            + math.sin(tetrahedral) * normal[axis]
            for axis in range(3)
        ),
        normal,
    )
    reach = IDEAL_SIDE_CHAIN_REACH[residue]
    return tuple(round(current[axis] + reach * direction[axis], 6) for axis in range(3))


def _side_chain_element(residue: str) -> str:
    if residue in {"D", "E"}:
        return "O"
    if residue in {"H", "K", "N", "Q", "R"}:
        return "N"
    if residue in {"C", "M"}:
        return "S"
    return "C"


def schematic_peptide_scene(sequence: str, mutation_position: int) -> dict[str, object]:
    """Graft a candidate onto the real 1HHK peptide backbone with explicit caveats."""

    peptide = sequence.strip().upper()
    if len(peptide) not in {9, 10} or set(peptide) - set(AA_ORDER):
        raise ValueError("candidate schematic requires a canonical 9-mer or 10-mer")
    if mutation_position < 0 or mutation_position >= len(peptide):
        raise ValueError("mutation position must index the candidate peptide")

    backbone = _interpolated_backbone(len(peptide))
    atoms: list[dict[str, object]] = []
    for index, (residue, coordinates) in enumerate(zip(peptide, backbone, strict=True)):
        atoms.append(
            {
                "id": index + 1,
                "name": "CA from PDB 1HHK chain C",
                "residue": residue,
                "res_seq": index + 1,
                "chain": "C",
                "element": "C",
                "x": coordinates[0],
                "y": coordinates[1],
                "z": coordinates[2],
                "role": "anchor" if index in {1, len(peptide) - 1} else "peptide",
                "mutation_residue": index == mutation_position,
            }
        )

    side_chain = _ideal_side_chain_endpoint(
        backbone, mutation_position, peptide[mutation_position]
    )
    atoms.append(
        {
            "id": len(peptide) + 1,
            "name": "idealized mutation side-chain endpoint",
            "residue": peptide[mutation_position],
            "res_seq": mutation_position + 1,
            "chain": "C",
            "element": _side_chain_element(peptide[mutation_position]),
            "x": side_chain[0],
            "y": side_chain[1],
            "z": side_chain[2],
            "role": "mutation",
            "geometry": "109.5-degree idealized local-backbone direction",
        }
    )
    bonds = [[index, index + 1] for index in range(1, len(peptide))]
    bonds.append([mutation_position + 1, len(peptide) + 1])
    return {
        "kind": "schematic",
        "sequence": peptide,
        "mutation_position": mutation_position,
        "truth": SCHEMATIC_TRUTH,
        "geometry": SCHEMATIC_DETAIL,
        "backbone_template": {
            "pdb_id": "1HHK",
            "chain": "C",
            "atom": "CA",
            "mapping": "direct 9-mer; source-index i*8/9 interpolation for 10-mer",
        },
        "atoms": atoms,
        "bonds": bonds,
        "chain_roles": {"C": "candidate peptide schematic"},
    }
