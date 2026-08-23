"""Deterministic end-to-end screening orchestration for schema-v1 results."""

from __future__ import annotations

import gzip
import math
import os
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from keyhole.bind import ALLELES, BindingPrediction, load_binder
from keyhole.funnel import (
    CITATIONS,
    METHOD_LABELS,
    FunnelResult,
    cleavage_score,
    differential_agretopicity,
    foreignness_score,
    tap_score,
    verdict_engine,
)
from keyhole.literature import evaluate_literature_panel
from keyhole.parse import Variant, load_variants
from keyhole.peptides import PeptidePair, variant_peptides
from keyhole.population import ASSUMPTION, DEFAULT_DRAWS, population_summary
from keyhole.schema import PROJECT_SEED, SCHEMA_VERSION, validate_results


class PipelineError(ValueError):
    """Raised when an input cannot yield a truthful screen."""


class BatchBinder(Protocol):
    """Prediction interface required by the batch orchestrator."""

    def predict_many(
        self, peptides: Sequence[str], allele: str
    ) -> tuple[BindingPrediction, ...]:
        """Predict stable peptide order for one allele."""


@dataclass(frozen=True, slots=True)
class InputAudit:
    """Counts separating input rows, representable changes, and screenable variants."""

    input_row_count: int
    supported_change_count: int
    screenable_variant_count: int
    missing_canonical_context_count: int
    unsupported_frameshift_count: int
    ignored_class_count: int

    def as_dict(self) -> dict[str, int]:
        """Return JSON-ready audit counts."""

        return {
            "ignored_class_count": self.ignored_class_count,
            "input_row_count": self.input_row_count,
            "missing_canonical_context_count": self.missing_canonical_context_count,
            "screenable_variant_count": self.screenable_variant_count,
            "supported_change_count": self.supported_change_count,
            "unsupported_frameshift_count": self.unsupported_frameshift_count,
        }


@dataclass(frozen=True, slots=True)
class ScreeningRun:
    """Validated document plus ordered user-facing evidence for CLI presentation."""

    results: dict[str, object]
    audit: InputAudit
    funnel_results: tuple[FunnelResult, ...]


def normalize_hla_list(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize a CSV/sequence of unique supported two-field HLA names."""

    raw = value.split(",") if isinstance(value, str) else value
    normalized: list[str] = []
    for item in raw:
        allele = item.strip().upper()
        if allele.startswith("HLA-"):
            allele = allele[4:]
        if not allele:
            continue
        if allele not in ALLELES:
            raise PipelineError(f"unsupported HLA allele: {item!r}")
        if allele in normalized:
            raise PipelineError(f"duplicate HLA allele: {allele}")
        normalized.append(allele)
    if not normalized:
        raise PipelineError("at least one supported HLA allele is required")
    return tuple(normalized)


def _open_input(path: Path):  # type: ignore[no-untyped-def]
    if path.suffix == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8", newline="")
    return path.open(encoding="utf-8", newline="")


def _input_row_count(path: Path) -> int:
    with _open_input(path) as handle:
        if path.name.lower().endswith((".maf", ".maf.gz")):
            lines = [line for line in handle if not line.startswith("#")]
            return max(0, len(lines) - 1)
        return sum(1 for line in handle if line.strip() and not line.startswith("#"))


def _screenable(variants: Sequence[Variant]) -> tuple[Variant, ...]:
    return tuple(
        variant
        for variant in variants
        if variant.protein_sequence is not None and variant.source == "missense"
    )


def audit_variants(variants: Sequence[Variant], *, input_row_count: int) -> InputAudit:
    """Classify parsed changes without inventing missing sequence or frameshift context."""

    screenable = _screenable(variants)
    missing = sum(variant.protein_sequence is None for variant in variants)
    frameshifts = sum(variant.source == "frameshift" for variant in variants)
    return InputAudit(
        input_row_count=input_row_count,
        supported_change_count=len(variants),
        screenable_variant_count=len(screenable),
        missing_canonical_context_count=missing,
        unsupported_frameshift_count=frameshifts,
        ignored_class_count=max(0, input_row_count - len(variants)),
    )


def load_screen_input(path: str | Path) -> tuple[tuple[Variant, ...], InputAudit]:
    """Parse a MAF/VCF and retain an independent raw-row audit."""

    source = Path(path)
    if not source.is_file():
        raise PipelineError(f"variant input does not exist: {source}")
    variants = load_variants(source)
    return variants, audit_variants(variants, input_row_count=_input_row_count(source))


def _created_utc(value: str | None) -> str:
    if value is not None:
        return value
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    moment = datetime.fromtimestamp(int(epoch), tz=UTC) if epoch else datetime.now(UTC)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _funnel_result(
    pair: PeptidePair,
    alleles: Sequence[str],
    predictions: Mapping[tuple[str, str], BindingPrediction],
    evidence: Mapping[str, tuple[float, float, float]],
) -> FunnelResult:
    binding = {allele: predictions[(pair.seq, allele)] for allele in alleles}
    wt_binding = (
        {allele: predictions[(pair.wt_seq, allele)] for allele in alleles}
        if pair.wt_seq
        else {}
    )
    best = min(binding.values(), key=lambda item: (item.percentile_rank, item.ic50_nm, item.allele))
    wild_type = wt_binding.get(best.allele)
    agretopicity = differential_agretopicity(best, wild_type)
    cleavage, tap, foreignness = evidence[pair.seq]
    verdict, reasons, language = verdict_engine(
        cleavage=cleavage,
        tap=tap,
        binding_rank=best.percentile_rank,
        binding_ic50=best.ic50_nm,
        foreignness=foreignness,
        agretopicity=agretopicity,
        has_wt=wild_type is not None,
    )
    return FunnelResult(
        pair=pair,
        binding=binding,
        wt_binding=wt_binding,
        cleavage=cleavage,
        tap=tap,
        agretopicity=agretopicity,
        foreignness=foreignness,
        best_allele=best.allele,
        verdict=verdict,
        reason_codes=reasons,
        plain_language=language,
    )


def _serialize_peptide(result: FunnelResult, candidate_key: str) -> dict[str, object]:
    values = {
        "agretopicity": result.agretopicity,
        "best_allele": result.best_allele,
        "candidate_key": candidate_key,
        "foreignness": result.foreignness,
        "plain_language": result.plain_language,
        "position": result.pair.position,
        "protein_start": result.pair.protein_start,
        "reason_codes": list(result.reason_codes),
        "scores": {
            "binding": {
                allele: {"ic50": prediction.ic50_nm, "rank": prediction.percentile_rank}
                for allele, prediction in result.binding.items()
            },
            "cleavage": result.cleavage,
            "tap": result.tap,
        },
        "seq": result.pair.seq,
        "source": result.pair.source,
        "verdict": result.verdict.value,
        "wt_seq": result.pair.wt_seq,
    }
    for number in (
        values["agretopicity"],
        values["foreignness"],
        values["scores"]["cleavage"],  # type: ignore[index]
        values["scores"]["tap"],  # type: ignore[index]
    ):
        if not math.isfinite(float(number)):
            raise PipelineError("pipeline produced a non-finite score")
    return values


def screen_variants(
    variants: Sequence[Variant],
    alleles: str | Sequence[str],
    *,
    input_name: str,
    input_path: str,
    audit: InputAudit | None = None,
    binder: BatchBinder | None = None,
    foreignness_fn: Callable[[str], float] = foreignness_score,
    literature_branch: Mapping[str, object] | None = None,
    population_draws: int = DEFAULT_DRAWS,
    created_utc: str | None = None,
) -> ScreeningRun:
    """Screen resolvable variants while preserving every unsupported-input count."""

    user_alleles = normalize_hla_list(alleles)
    source_variants = tuple(variants)
    screenable = _screenable(source_variants)
    effective_audit = audit or audit_variants(
        source_variants, input_row_count=len(source_variants)
    )
    if not screenable:
        raise PipelineError(
            "no variants have frozen canonical missense context; no scientific result generated"
        )

    grouped_pairs = tuple(tuple(variant_peptides(variant)) for variant in screenable)
    all_pairs = tuple(pair for group in grouped_pairs for pair in group)
    mutant_sequences = _stable_unique([pair.seq for pair in all_pairs])
    wild_sequences = _stable_unique([pair.wt_seq for pair in all_pairs if pair.wt_seq])
    model = load_binder() if binder is None else binder
    predictions: dict[tuple[str, str], BindingPrediction] = {}
    for allele in ALLELES:
        for prediction in model.predict_many(mutant_sequences, allele):
            predictions[(prediction.peptide, prediction.allele)] = prediction
        for prediction in model.predict_many(wild_sequences, allele):
            predictions[(prediction.peptide, prediction.allele)] = prediction

    evidence = {
        peptide: (cleavage_score(peptide), tap_score(peptide), foreignness_fn(peptide))
        for peptide in mutant_sequences
    }
    user_results = tuple(
        _funnel_result(pair, user_alleles, predictions, evidence) for pair in all_pairs
    )
    population_results = tuple(
        _funnel_result(pair, ALLELES, predictions, evidence) for pair in all_pairs
    )
    population = population_summary(population_results, draws=population_draws)
    literature = (
        dict(literature_branch)
        if literature_branch is not None
        else evaluate_literature_panel(binder=model)
    )

    occurrences: Counter[str] = Counter()
    result_offset = 0
    mutations: list[dict[str, object]] = []
    for variant, pairs in zip(screenable, grouped_pairs, strict=True):
        serialized: list[dict[str, object]] = []
        for result in user_results[result_offset : result_offset + len(pairs)]:
            occurrences[result.pair.seq] += 1
            count = occurrences[result.pair.seq]
            key = result.pair.seq if count == 1 else f"{result.pair.seq}#{count}"
            serialized.append(_serialize_peptide(result, key))
        result_offset += len(pairs)
        mutations.append(
            {
                "change": variant.change,
                "gene": variant.gene,
                "peptides": serialized,
                "protein_effect": variant.protein_effect,
            }
        )

    results: dict[str, object] = {
        "alleles": list(user_alleles),
        "literature": literature,
        "meta": {
            "created_utc": _created_utc(created_utc),
            "methods": {
                **METHOD_LABELS,
                "population": "heuristic approximation",
                "population_assumption": ASSUMPTION,
            },
            "schema_version": SCHEMA_VERSION,
            "seed": PROJECT_SEED,
            "sources": [
                "IEDB measured MHC-I binding snapshot and positive T-cell assay panel",
                "UniProt human reference proteome and canonical BRAF/KRAS/TP53 sequences",
                "1000 Genomes Phase I-derived observed AFR/AMR/EAS/EUR HLA marginals",
                "RCSB PDB entries 1HHK, 3PWN, and 1AO7",
                *CITATIONS.values(),
            ],
        },
        "mutations": mutations,
        "population": population,
        "tumor": {
            "input": input_path,
            "name": input_name,
            "screening": effective_audit.as_dict(),
            "variant_count": len(source_variants),
        },
    }
    validate_results(results)
    return ScreeningRun(results=results, audit=effective_audit, funnel_results=user_results)


def screen_path(
    path: str | Path,
    alleles: str | Sequence[str],
    **kwargs: object,
) -> ScreeningRun:
    """Load a variant file and run the complete deterministic screen."""

    source = Path(path)
    variants, audit = load_screen_input(source)
    name = source.name
    for suffix in (".gz", ".maf", ".vcf"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
    return screen_variants(
        variants,
        alleles,
        input_name=name,
        input_path=str(source),
        audit=audit,
        **kwargs,  # type: ignore[arg-type]
    )
