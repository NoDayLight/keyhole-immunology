"""Deterministic, typed access to KEYHOLE's frozen scientific datasets."""

from __future__ import annotations

import csv
import gzip
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from keyhole.assets import packaged_directory, safe_child

CANONICAL_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


@dataclass(frozen=True, slots=True)
class BindingRecord:
    """One experimentally measured IEDB peptide–HLA affinity."""

    allele: str
    peptide: str
    ic50_nm: float
    inequality: str


@dataclass(frozen=True, slots=True)
class FrequencyRecord:
    """One observed HLA allele frequency within a superpopulation and locus."""

    superpopulation: str
    locus: str
    allele: str
    allele_count: int
    resolved_allele_copies: int
    excluded_ambiguous_copies: int
    individuals: int
    frequency: float


@dataclass(frozen=True, slots=True)
class LiteratureRecord:
    """One published positive tumor peptide/HLA T-cell assay from IEDB."""

    peptide: str
    allele: str
    source_molecule: str
    disease_context: str
    iedb_epitope: str
    iedb_assay: str
    assay_result: str
    pmid: str
    reference_title: str


def data_root() -> Path:
    """Locate complete frozen data from an explicit override or the installed wheel."""

    configured = os.environ.get("KEYHOLE_DATA")
    root = Path(configured).expanduser().resolve() if configured else packaged_directory("data")
    if not (root / "SOURCES.md").is_file():
        origin = "KEYHOLE_DATA" if configured else "installed package"
        raise FileNotFoundError(f"{origin} does not contain a complete KEYHOLE data root: {root}")
    return root


def asset_path(relative: str) -> Path:
    """Return an existing, non-traversing path below the frozen data root."""

    path = safe_child(data_root(), relative)
    if not path.is_file():
        raise FileNotFoundError(f"required frozen asset is missing: {path}")
    return path


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8", newline="")
    return path.open(encoding="utf-8", newline="")


def normalize_allele(allele: str) -> str:
    """Normalize an HLA name to the schema's two-field display form."""

    value = allele.strip().upper()
    if value.startswith("HLA-"):
        value = value[4:]
    return value


def iter_binding_records(
    *, alleles: set[str] | frozenset[str] | None = None, limit: int | None = None
) -> Iterator[BindingRecord]:
    """Stream measured IEDB affinities in frozen stable order."""

    selected = {normalize_allele(value) for value in alleles} if alleles else None
    emitted = 0
    with _open_text(asset_path("iedb/mhci_binding_9_10mer.tsv.gz")) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            allele = normalize_allele(row["hla_allele"])
            if selected is not None and allele not in selected:
                continue
            yield BindingRecord(
                allele=allele,
                peptide=row["peptide"],
                ic50_nm=float(row["ic50_nm"]),
                inequality=row["measurement_inequality"],
            )
            emitted += 1
            if limit is not None and emitted >= limit:
                return


def iter_self_peptides(*, limit: int | None = None) -> Iterator[str]:
    """Stream the deterministic 500,000-peptide human self sample."""

    with _open_text(asset_path("self_peptidome/up000005640_human_9mers.txt.gz")) as handle:
        for index, line in enumerate(handle):
            if limit is not None and index >= limit:
                return
            peptide = line.rstrip("\n")
            if peptide:
                yield peptide


def load_hla_frequencies() -> tuple[FrequencyRecord, ...]:
    """Load observed Phase-I HLA-A/B frequencies; absent populations stay absent."""

    records: list[FrequencyRecord] = []
    path = asset_path("hla_freq/1000g_hla_ab_two_field_frequencies.tsv")
    with _open_text(path) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            records.append(
                FrequencyRecord(
                    superpopulation=row["superpopulation"],
                    locus=row["locus"],
                    allele=normalize_allele(row["allele"]),
                    allele_count=int(row["allele_count"]),
                    resolved_allele_copies=int(row["resolved_allele_copies"]),
                    excluded_ambiguous_copies=int(row["excluded_ambiguous_copies"]),
                    individuals=int(row["individuals"]),
                    frequency=float(row["frequency"]),
                )
            )
    return tuple(records)


def load_literature_records() -> tuple[LiteratureRecord, ...]:
    """Load the ten frozen positive tumor epitope/HLA records."""

    records: list[LiteratureRecord] = []
    with _open_text(asset_path("literature/tumor_epitopes.tsv")) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            records.append(
                LiteratureRecord(
                    peptide=row["peptide"],
                    allele=normalize_allele(row["hla_allele"]),
                    source_molecule=row["source_molecule"],
                    disease_context=row["disease_context"],
                    iedb_epitope=row["iedb_epitope"],
                    iedb_assay=row["iedb_assay"],
                    assay_result=row["assay_result"],
                    pmid=row["pmid"],
                    reference_title=row["reference_title"],
                )
            )
    return tuple(records)


def load_famous_proteins() -> dict[str, dict[str, str]]:
    """Load verified canonical sequences keyed by gene symbol."""

    raw = json.loads(asset_path("residues/famous_proteins.json").read_text(encoding="utf-8"))
    return {record["gene"]: record for record in raw}


def pdb_path(pdb_id: str) -> Path:
    """Resolve one of the verified frozen experimental PDB entries."""

    normalized = pdb_id.strip().upper()
    if normalized not in {"1AO7", "1HHK", "3PWN"}:
        raise ValueError(f"PDB {normalized!r} is not in the verified frozen set")
    return asset_path(f"pdb/{normalized}.pdb")
