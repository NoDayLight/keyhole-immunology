"""Deterministic end-to-end screening orchestration for schema-v1 results."""

from __future__ import annotations

import math
import os
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from keyhole.bind import ALLELES, BindingPrediction, load_binder
from keyhole.data import normalize_allele, open_text
from keyhole.funnel import (
    CITATIONS,
    METHOD_LABELS,
    FunnelResult,
    foreignness_score,
    foreignness_scores,
    run_funnel,
)
from keyhole.literature import evaluate_literature_panel
from keyhole.parse import Variant, load_variants
from keyhole.peptides import variant_peptides
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
        allele = normalize_allele(item)
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


def _input_row_count(path: Path) -> int:
    with open_text(path) as handle:
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


@dataclass(frozen=True, slots=True)
class _PrecomputedBinder:
    predictions: Mapping[tuple[str, str], BindingPrediction]

    def predict(self, peptide: str, allele: str) -> BindingPrediction:
        key = (peptide, normalize_allele(allele))
        try:
            return self.predictions[key]
        except KeyError as error:
            raise PipelineError(
                f"missing precomputed binding prediction for {key[0]} and {key[1]}"
            ) from error


def _record_prediction_batch(
    destination: dict[tuple[str, str], BindingPrediction],
    model: BatchBinder,
    peptides: Sequence[str],
    allele: str,
) -> None:
    batch = tuple(model.predict_many(peptides, allele))
    if len(batch) != len(peptides):
        raise PipelineError(
            f"binder returned {len(batch)} predictions for {len(peptides)} requested peptides"
        )
    for expected, prediction in zip(peptides, batch, strict=True):
        if prediction.peptide != expected or prediction.allele != allele:
            raise PipelineError(
                "binder prediction order, peptide identity, or allele did not match the request"
            )
        key = (prediction.peptide, prediction.allele)
        previous = destination.get(key)
        if previous is not None and previous != prediction:
            raise PipelineError(
                f"conflicting binder predictions for {key[0]} and {key[1]}"
            )
        destination[key] = prediction


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
        _record_prediction_batch(predictions, model, mutant_sequences, allele)
        _record_prediction_batch(predictions, model, wild_sequences, allele)

    if foreignness_fn is foreignness_score:
        foreignness_values = dict(
            zip(mutant_sequences, foreignness_scores(mutant_sequences), strict=True)
        )
    else:
        foreignness_values = {
            peptide: foreignness_fn(peptide) for peptide in mutant_sequences
        }
    adapter = _PrecomputedBinder(predictions)
    user_results = tuple(
        run_funnel(
            pair,
            user_alleles,
            binder=adapter,  # type: ignore[arg-type]
            foreignness_fn=foreignness_values.__getitem__,
        )
        for pair in all_pairs
    )
    population_results = tuple(
        run_funnel(
            pair,
            ALLELES,
            binder=adapter,  # type: ignore[arg-type]
            foreignness_fn=foreignness_values.__getitem__,
        )
        for pair in all_pairs
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
