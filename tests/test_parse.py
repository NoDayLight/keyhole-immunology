"""Tests for deterministic MAF, VCF, and famous-mutation parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from keyhole.parse import VariantParseError, load_variants, parse_famous, parse_maf, parse_vcf

DATA = Path(__file__).parents[1] / "data"


def test_famous_variants_use_verified_canonical_context() -> None:
    kras = parse_famous("KRAS G12D")
    braf = parse_famous("braf:p.V600E")
    tp53 = parse_famous("TP53-R175H")
    assert (kras.change, kras.protein_sequence[11]) == ("chr12:g.25398284C>T", "G")
    assert (braf.change, braf.protein_sequence[599]) == ("chr7:g.140453136A>T", "V")
    assert (tp53.change, tp53.protein_sequence[174]) == ("chr17:g.7578406C>T", "R")
    with pytest.raises(VariantParseError, match="must be"):
        parse_famous("EGFR L858R")


def test_tcga_maf_parses_supported_rows_and_enriches_anchor() -> None:
    variants = parse_maf(DATA / "examples" / "tcga_skcm.maf")
    braf = next(
        item for item in variants if item.gene == "BRAF" and item.protein_effect == "p.V600E"
    )
    tp53 = next(
        item for item in variants if item.gene == "TP53" and item.protein_effect == "p.R175H"
    )
    assert braf.sample_id == "TCGA-BF-A1PU-01"
    assert tp53.sample_id == "TCGA-D3-A5GR-06"
    assert braf.protein_sequence is not None and tp53.protein_sequence is not None
    assert all(item.source in {"missense", "frameshift"} for item in variants)


def test_annotated_vcf_parsing_is_stable(tmp_path: Path) -> None:
    vcf = tmp_path / "tumor.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "12\t25398284\t.\tC\tT\t.\tPASS\tGENE=KRAS;HGVSP=p.G12D;SAMPLE=TUMOR-1\n",
        encoding="utf-8",
    )
    first = parse_vcf(vcf)
    second = load_variants(vcf)
    assert first == second
    assert first[0].gene == "KRAS"
    assert first[0].sample_id == "TUMOR-1"
    assert first[0].protein_sequence is not None


def test_maf_reports_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.maf"
    path.write_text("Hugo_Symbol\tChromosome\nBRAF\t7\n", encoding="utf-8")
    with pytest.raises(VariantParseError, match="MAF missing columns"):
        parse_maf(path)
