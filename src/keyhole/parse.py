"""Deterministic MAF, annotated VCF, and famous-mutation parsing."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, TextIO

from keyhole.data import load_famous_proteins, open_text

ProteinSource = Literal["missense", "frameshift"]
_MISSENSE = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z])$")
_FRAMESHIFT = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z*])fs(?:\*(\d+|\?))?$")


class VariantParseError(ValueError):
    """Raised when a variant input is malformed or lacks required annotations."""


@dataclass(frozen=True, slots=True)
class Variant:
    """A protein-changing tumor variant with optional frozen protein context."""

    gene: str
    change: str
    chromosome: str
    genomic_position: int
    ref: str
    alt: str
    protein_effect: str
    source: ProteinSource
    protein_position: int
    reference_amino_acid: str
    alternate_amino_acid: str
    sample_id: str = ""
    protein_sequence: str | None = None


def _normalize_chromosome(value: str) -> str:
    chromosome = value.strip()
    return chromosome[3:] if chromosome.lower().startswith("chr") else chromosome


def _normalize_effect(effect: str) -> str:
    value = effect.strip()
    if ":" in value:
        value = value.rsplit(":", 1)[-1]
    return value if value.startswith("p.") else f"p.{value}"


def _effect_parts(effect: str) -> tuple[ProteinSource, int, str, str]:
    normalized = _normalize_effect(effect)
    match = _MISSENSE.fullmatch(normalized)
    if match:
        return "missense", int(match.group(2)), match.group(1), match.group(3)
    match = _FRAMESHIFT.fullmatch(normalized)
    if match:
        return "frameshift", int(match.group(2)), match.group(1), match.group(3)
    raise VariantParseError(
        f"unsupported protein effect {effect!r}; expected missense or frameshift"
    )


def _enrich(variant: Variant) -> Variant:
    protein = load_famous_proteins().get(variant.gene)
    if protein is None:
        return variant
    sequence = protein["sequence"]
    if variant.protein_position > len(sequence):
        raise VariantParseError(
            f"{variant.gene} {variant.protein_effect} exceeds frozen canonical sequence"
        )
    observed = sequence[variant.protein_position - 1]
    if observed != variant.reference_amino_acid:
        prefix = f"{variant.gene} {variant.protein_effect} conflicts with canonical"
        raise VariantParseError(
            f"{prefix} {protein['accession']}: position {variant.protein_position} is {observed}"
        )
    return replace(variant, protein_sequence=sequence)


def _build_variant(
    *,
    gene: str,
    chromosome: str,
    position: str | int,
    ref: str,
    alt: str,
    effect: str,
    sample_id: str = "",
) -> Variant:
    gene = gene.strip().upper()
    if not gene:
        raise VariantParseError("missing gene symbol")
    try:
        genomic_position = int(position)
    except (TypeError, ValueError) as error:
        raise VariantParseError(f"invalid genomic position {position!r}") from error
    if genomic_position <= 0:
        raise VariantParseError("genomic position must be positive")
    chromosome = _normalize_chromosome(chromosome)
    if not chromosome or not ref or not alt:
        raise VariantParseError("chromosome, reference allele, and alternate allele are required")
    source, protein_position, reference_aa, alternate_aa = _effect_parts(effect)
    normalized_effect = _normalize_effect(effect)
    variant = Variant(
        gene=gene,
        change=f"chr{chromosome}:g.{genomic_position}{ref}>{alt}",
        chromosome=chromosome,
        genomic_position=genomic_position,
        ref=ref,
        alt=alt,
        protein_effect=normalized_effect,
        source=source,
        protein_position=protein_position,
        reference_amino_acid=reference_aa,
        alternate_amino_acid=alternate_aa,
        sample_id=sample_id,
    )
    return _enrich(variant)


def parse_maf(path: str | Path) -> tuple[Variant, ...]:
    """Parse supported protein-changing rows from a MAF file.

    Non-missense/non-frameshift rows are intentionally ignored because the
    schema's peptide source enum cannot represent them. Malformed rows that
    claim a supported classification fail with a row-specific error.
    """

    source_path = Path(path)
    with open_text(source_path) as handle:
        rows = (line for line in handle if not line.startswith("#"))
        reader = csv.DictReader(rows, delimiter="\t")
        required = {
            "Hugo_Symbol",
            "Chromosome",
            "Start_Position",
            "Reference_Allele",
            "Tumor_Seq_Allele2",
            "Variant_Classification",
            "HGVSp_Short",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise VariantParseError(f"MAF missing columns: {', '.join(missing)}")
        variants: list[Variant] = []
        for row_number, row in enumerate(reader, start=2):
            classification = row["Variant_Classification"]
            if classification == "Missense_Mutation":
                expected: ProteinSource = "missense"
            elif classification.startswith("Frame_Shift"):
                expected = "frameshift"
            else:
                continue
            try:
                variant = _build_variant(
                    gene=row["Hugo_Symbol"],
                    chromosome=row["Chromosome"],
                    position=row["Start_Position"],
                    ref=row["Reference_Allele"],
                    alt=row["Tumor_Seq_Allele2"],
                    effect=row["HGVSp_Short"],
                    sample_id=row.get("Tumor_Sample_Barcode", ""),
                )
            except VariantParseError as error:
                raise VariantParseError(f"{source_path}:{row_number}: {error}") from error
            if variant.source != expected:
                raise VariantParseError(
                    f"{source_path}:{row_number}: classification/effect type mismatch"
                )
            variants.append(variant)
    return tuple(variants)


def _parse_info(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in value.split(";"):
        key, separator, item = field.partition("=")
        if separator:
            result[key.upper()] = item
    return result


def _vcf_annotation(info: dict[str, str]) -> tuple[str, str]:
    gene = info.get("GENE") or info.get("SYMBOL")
    effect = info.get("HGVSP") or info.get("HGVSP_SHORT")
    if gene and effect:
        return gene.split(",", 1)[0], effect.split(",", 1)[0]
    annotation = info.get("ANN", "").split(",", 1)[0].split("|")
    if len(annotation) > 10 and annotation[3] and annotation[10]:
        return annotation[3], annotation[10]
    raise VariantParseError("VCF record requires GENE/SYMBOL and HGVSP, or a standard ANN field")


def _vcf_records(handle: TextIO, source_path: Path) -> Iterator[Variant]:
    for row_number, line in enumerate(handle, start=1):
        if line.startswith("#"):
            continue
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 8:
            raise VariantParseError(f"{source_path}:{row_number}: expected at least 8 VCF columns")
        chromosome, position, _identifier, ref, alt, _quality, _filter, raw_info = fields[:8]
        info = _parse_info(raw_info)
        gene, effect = _vcf_annotation(info)
        for alternate in alt.split(","):
            try:
                yield _build_variant(
                    gene=gene,
                    chromosome=chromosome,
                    position=position,
                    ref=ref,
                    alt=alternate,
                    effect=effect,
                    sample_id=info.get("SAMPLE", ""),
                )
            except VariantParseError as error:
                raise VariantParseError(f"{source_path}:{row_number}: {error}") from error


def parse_vcf(path: str | Path) -> tuple[Variant, ...]:
    """Parse a VCF annotated with GENE/HGVSP or Sequence Ontology ANN."""

    source_path = Path(path)
    with open_text(source_path) as handle:
        return tuple(_vcf_records(handle, source_path))


def parse_famous(value: str) -> Variant:
    """Resolve KRAS G12D, BRAF V600E, or TP53 R175H from frozen real records."""

    compact = re.sub(r"[\s:_-]+", " ", value.strip().upper().replace("P.", " ")).strip()
    match = re.fullmatch(r"(KRAS|BRAF|TP53)\s+(G12D|V600E|R175H)", compact)
    if not match:
        raise VariantParseError("famous mutation must be KRAS G12D, BRAF V600E, or TP53 R175H")
    key = (match.group(1), match.group(2))
    records = {
        ("KRAS", "G12D"): ("12", 25398284, "C", "T"),
        ("BRAF", "V600E"): ("7", 140453136, "A", "T"),
        ("TP53", "R175H"): ("17", 7578406, "C", "T"),
    }
    chromosome, position, ref, alt = records[key]
    return _build_variant(
        gene=key[0],
        chromosome=chromosome,
        position=position,
        ref=ref,
        alt=alt,
        effect=key[1],
    )


def load_variants(path: str | Path) -> tuple[Variant, ...]:
    """Dispatch a `.maf`, `.vcf`, or gzipped equivalent to its parser."""

    source_path = Path(path)
    name = source_path.name.lower()
    if name.endswith((".vcf", ".vcf.gz")):
        return parse_vcf(source_path)
    if name.endswith((".maf", ".maf.gz")):
        return parse_maf(source_path)
    raise VariantParseError(f"unsupported variant file extension: {source_path.name}")
