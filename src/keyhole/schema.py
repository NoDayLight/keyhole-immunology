"""Schema-v1.1 validation for the complete pipeline-to-renderer contract."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, NoReturn

from keyhole.contracts import (
    PROJECT_SEED,
    SCHEMA_VERSION,
    SUPPORTED_ALLELES,
    binary_roc_auc,
    binding_exposure,
    binding_order_key,
    canonical_peptide,
)


class Verdict(StrEnum):
    """Permitted candidate visibility conclusions."""

    VISIBLE_CLEAR = "VISIBLE_CLEAR"
    VISIBLE_FAINT = "VISIBLE_FAINT"
    INVISIBLE = "INVISIBLE"


class SchemaError(ValueError):
    """Raised when a result artifact violates schema v1.1."""


def _fail(path: str, message: str) -> NoReturn:
    raise SchemaError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "expected object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "expected array")
    return value


def _text(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        _fail(path, "expected non-empty string")
    return value


def _number(
    value: Any,
    path: str,
    *,
    minimum: float = -math.inf,
    maximum: float = math.inf,
    nullable: bool = False,
) -> float | None:
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        _fail(path, "expected number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        _fail(path, f"expected finite value in [{minimum}, {maximum}]")
    return result


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(path, f"expected integer >= {minimum}")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, "expected boolean")
    return value


def _required(obj: dict[str, Any], keys: set[str], path: str) -> None:
    missing = sorted(keys - obj.keys())
    if missing:
        _fail(path, f"missing keys: {', '.join(missing)}")


def _text_mapping(value: Any, path: str) -> dict[str, Any]:
    mapping = _mapping(value, path)
    for name, text in mapping.items():
        _text(name, f"{path}.<name>")
        _text(text, f"{path}.{name}")
    return mapping


def _canonical(value: Any, path: str, *, allow_empty: bool = False) -> str:
    text = _text(value, path, allow_empty=allow_empty)
    if allow_empty and not text:
        return text
    try:
        normalized = canonical_peptide(text, label=path)
    except (TypeError, ValueError) as error:
        _fail(path, str(error))
    if normalized != text:
        _fail(path, "expected normalized uppercase canonical peptide")
    return text


def _validate_binding(binding: Any, alleles: list[str], path: str) -> dict[str, Any]:
    values = _mapping(binding, path)
    if set(values) != set(alleles):
        _fail(path, "binding alleles must exactly match results.alleles")
    for allele, score in values.items():
        score_path = f"{path}.{allele}"
        score_obj = _mapping(score, score_path)
        _required(score_obj, {"ic50", "rank"}, score_path)
        _number(score_obj["ic50"], f"{score_path}.ic50", minimum=0.0)
        _number(score_obj["rank"], f"{score_path}.rank", minimum=0.0, maximum=100.0)
    return values


def _validate_peptide(peptide: Any, alleles: list[str], path: str) -> str:
    obj = _mapping(peptide, path)
    _required(
        obj,
        {
            "seq",
            "wt_seq",
            "position",
            "protein_start",
            "source",
            "scores",
            "agretopicity",
            "foreignness",
            "best_allele",
            "candidate_key",
            "verdict",
            "reason_codes",
            "plain_language",
        },
        path,
    )
    seq = _canonical(obj["seq"], f"{path}.seq")
    wt_seq = _canonical(obj["wt_seq"], f"{path}.wt_seq", allow_empty=True)
    if wt_seq and len(wt_seq) != len(seq):
        _fail(f"{path}.wt_seq", "must be empty or match mutant peptide length")
    position = _integer(obj["position"], f"{path}.position")
    if position >= len(seq):
        _fail(f"{path}.position", "must index the mutant residue in seq")
    _integer(obj["protein_start"], f"{path}.protein_start")
    if obj["source"] not in {"missense", "frameshift"}:
        _fail(f"{path}.source", "expected missense or frameshift")
    scores = _mapping(obj["scores"], f"{path}.scores")
    _required(scores, {"binding", "tap", "cleavage"}, f"{path}.scores")
    bindings = _validate_binding(scores["binding"], alleles, f"{path}.scores.binding")
    for name in ("tap", "cleavage"):
        _number(scores[name], f"{path}.scores.{name}", minimum=0.0, maximum=1.0)
    _number(obj["agretopicity"], f"{path}.agretopicity", minimum=0.0)
    _number(obj["foreignness"], f"{path}.foreignness", minimum=0.0, maximum=1.0)
    try:
        verdict = Verdict(obj["verdict"])
    except (TypeError, ValueError):
        _fail(f"{path}.verdict", "unknown verdict")
    reasons = _list(obj["reason_codes"], f"{path}.reason_codes")
    if not reasons:
        _fail(f"{path}.reason_codes", "at least one reason is required")
    for index, reason in enumerate(reasons):
        _text(reason, f"{path}.reason_codes[{index}]")
    _text(obj["plain_language"], f"{path}.plain_language")
    best_allele = _text(obj["best_allele"], f"{path}.best_allele")
    if best_allele not in bindings:
        _fail(f"{path}.best_allele", "missing serialized binding evidence")
    winner = min(
        bindings,
        key=lambda allele: binding_order_key(
            bindings[allele]["rank"], bindings[allele]["ic50"], allele
        ),
    )
    if best_allele != winner:
        _fail(f"{path}.best_allele", "does not match serialized binding winner")
    candidate_key = _text(obj["candidate_key"], f"{path}.candidate_key")
    if not re.fullmatch(r"[A-Z]{9,10}(?:#[2-9][0-9]*)?", candidate_key):
        _fail(f"{path}.candidate_key", "invalid stable candidate key")
    if not candidate_key.startswith(seq):
        _fail(f"{path}.candidate_key", "must be derived from peptide sequence")
    if verdict is Verdict.INVISIBLE and not reasons:
        _fail(f"{path}.reason_codes", "invisible result requires evidence")
    return candidate_key


def _validate_audit(tumor: dict[str, Any], mutation_count: int) -> None:
    path = "results.tumor"
    _required(tumor, {"name", "input", "variant_count", "screening"}, path)
    _text(tumor["name"], f"{path}.name")
    _text(tumor["input"], f"{path}.input")
    variant_count = _integer(tumor["variant_count"], f"{path}.variant_count")
    screening = _mapping(tumor["screening"], f"{path}.screening")
    names = {
        "ignored_class_count",
        "input_row_count",
        "missing_canonical_context_count",
        "screenable_variant_count",
        "supported_change_count",
        "unsupported_frameshift_count",
    }
    _required(screening, names, f"{path}.screening")
    counts = {
        name: _integer(screening[name], f"{path}.screening.{name}") for name in names
    }
    if counts["screenable_variant_count"] > counts["supported_change_count"]:
        _fail(f"{path}.screening", "screenable count exceeds supported count")
    if counts["supported_change_count"] > counts["input_row_count"]:
        _fail(f"{path}.screening", "supported count exceeds input count")
    if counts["ignored_class_count"] != (
        counts["input_row_count"] - counts["supported_change_count"]
    ):
        _fail(f"{path}.screening.ignored_class_count", "does not reconcile input rows")
    unresolved = counts["supported_change_count"] - counts["screenable_variant_count"]
    missing = counts["missing_canonical_context_count"]
    frameshifts = counts["unsupported_frameshift_count"]
    if not max(missing, frameshifts) <= unresolved <= missing + frameshifts:
        _fail(
            f"{path}.screening",
            "missing-context and frameshift counts do not cover unsupported changes",
        )
    if variant_count != counts["supported_change_count"]:
        _fail(f"{path}.variant_count", "must equal supported_change_count")
    if mutation_count != counts["screenable_variant_count"]:
        _fail("results.mutations", "count must equal screenable_variant_count")


def _validate_population(population: Any, candidate_keys: list[str]) -> None:
    path = "results.population"
    obj = _mapping(population, path)
    _required(obj, {"per_candidate_coverage", "peptide_allele_matrix", "meta"}, path)
    meta = _mapping(obj["meta"], f"{path}.meta")
    _required(meta, {"assumption", "draws", "method", "seed", "superpopulations"}, f"{path}.meta")
    _text(meta["assumption"], f"{path}.meta.assumption")
    _text(meta["method"], f"{path}.meta.method")
    _integer(meta["draws"], f"{path}.meta.draws", minimum=1)
    if _integer(meta["seed"], f"{path}.meta.seed") != PROJECT_SEED:
        _fail(f"{path}.meta.seed", f"expected {PROJECT_SEED}")
    populations = _list(meta["superpopulations"], f"{path}.meta.superpopulations")
    if populations != ["AFR", "AMR", "EAS", "EUR"]:
        _fail(f"{path}.meta.superpopulations", "expected frozen AFR/AMR/EAS/EUR order")
    coverage = _mapping(obj["per_candidate_coverage"], f"{path}.per_candidate_coverage")
    matrix = _mapping(obj["peptide_allele_matrix"], f"{path}.peptide_allele_matrix")
    expected_keys = set(candidate_keys)
    if set(coverage) != expected_keys or set(matrix) != expected_keys:
        _fail(path, "candidate keys must align with mutation peptides")
    population_names = {"AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"}
    for candidate_key in candidate_keys:
        values = _mapping(coverage[candidate_key], f"{path}.coverage.{candidate_key}")
        if set(values) != population_names:
            _fail(f"{path}.coverage.{candidate_key}", "expected four cohorts and ALL_OBSERVED")
        for name, value in values.items():
            _number(value, f"{path}.coverage.{candidate_key}.{name}", minimum=0.0, maximum=100.0)
        cells = _mapping(matrix[candidate_key], f"{path}.matrix.{candidate_key}")
        if set(cells) != set(SUPPORTED_ALLELES):
            _fail(f"{path}.matrix.{candidate_key}", "expected all 26 modeled alleles")
        for allele, cell_value in cells.items():
            cell_path = f"{path}.matrix.{candidate_key}.{allele}"
            cell = _mapping(cell_value, cell_path)
            _required(
                cell,
                {"ic50", "method", "rank", "reason_codes", "verdict", "visible"},
                cell_path,
            )
            _number(cell["ic50"], f"{cell_path}.ic50", minimum=0.0)
            _number(cell["rank"], f"{cell_path}.rank", minimum=0.0, maximum=100.0)
            _text(cell["method"], f"{cell_path}.method")
            reasons = _list(cell["reason_codes"], f"{cell_path}.reason_codes")
            for index, reason in enumerate(reasons):
                _text(reason, f"{cell_path}.reason_codes[{index}]")
            try:
                verdict = Verdict(cell["verdict"])
            except (TypeError, ValueError):
                _fail(f"{cell_path}.verdict", "unknown verdict")
            visible = _boolean(cell["visible"], f"{cell_path}.visible")
            if visible != (verdict is not Verdict.INVISIBLE):
                _fail(f"{cell_path}.visible", "does not agree with verdict")


@dataclass(frozen=True, slots=True)
class _PredictionEvidence:
    verdict: Verdict | None
    percentile_rank: float | None
    reason_codes: tuple[str, ...]

    @property
    def evaluable(self) -> bool:
        return self.percentile_rank is not None


@dataclass(slots=True)
class _LiteratureEvidence:
    positive_total: int = 0
    positive_verdicts: list[Verdict] = field(default_factory=list)
    decoy_verdicts: list[Verdict] = field(default_factory=list)
    positive_ranks: list[float] = field(default_factory=list)
    decoy_ranks: list[float] = field(default_factory=list)
    paired_rank_wins: int = 0
    split_counts: Counter[str] = field(default_factory=Counter)

    def add(
        self,
        split: str,
        positive: _PredictionEvidence,
        negative: _PredictionEvidence,
    ) -> None:
        self.positive_total += 1
        self.split_counts[split] += 1
        if not positive.evaluable:
            return
        assert positive.verdict is not None and positive.percentile_rank is not None
        assert negative.verdict is not None and negative.percentile_rank is not None
        self.positive_verdicts.append(positive.verdict)
        self.decoy_verdicts.append(negative.verdict)
        self.positive_ranks.append(positive.percentile_rank)
        self.decoy_ranks.append(negative.percentile_rank)
        if positive.percentile_rank < negative.percentile_rank:
            self.paired_rank_wins += 1

    def summary(self, *, aggregate: bool = False) -> dict[str, Any]:
        visible = {Verdict.VISIBLE_CLEAR, Verdict.VISIBLE_FAINT}
        evaluable = len(self.positive_verdicts)
        visible_count = sum(verdict in visible for verdict in self.positive_verdicts)
        rejected = sum(verdict is Verdict.INVISIBLE for verdict in self.decoy_verdicts)
        labels = [True] * evaluable + [False] * evaluable
        scores = [-rank for rank in self.positive_ranks + self.decoy_ranks]
        values: dict[str, Any] = {
            "published_positive_total": self.positive_total,
            "published_positive_evaluable": evaluable,
            "positive_visible_count": visible_count,
            "matched_decoy_evaluable": len(self.decoy_verdicts),
            "matched_decoy_rejected_count": rejected,
            "paired_binding_rank_wins": self.paired_rank_wins,
            "positive_split_counts": {
                name: self.split_counts[name] for name in ("train", "validation", "test")
            },
            "synthetic_decoy_binding_roc_auc": (
                round(binary_roc_auc(labels, scores), 6) if evaluable else None
            ),
        }
        if aggregate:
            values.update(
                {
                    "published_positive_not_evaluable": self.positive_total - evaluable,
                    "positive_invisible_count": evaluable - visible_count,
                    "positive_agreement_rate": _rate(visible_count, evaluable),
                    "positive_verdict_counts": {
                        verdict.value: self.positive_verdicts.count(verdict)
                        for verdict in Verdict
                    },
                    "matched_decoy_total": self.positive_total,
                    "matched_decoy_rejection_rate": _rate(
                        rejected, len(self.decoy_verdicts)
                    ),
                    "paired_binding_rank_win_rate": _rate(
                        self.paired_rank_wins, evaluable
                    ),
                }
            )
            values.pop("positive_split_counts")
        return values


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _validate_prediction(
    value: Any,
    path: str,
    evaluation_status: str,
) -> _PredictionEvidence:
    prediction = _mapping(value, path)
    _required(prediction, {"binding", "plain_language", "reason_codes", "verdict"}, path)
    _text(prediction["plain_language"], f"{path}.plain_language")
    reasons = _list(prediction["reason_codes"], f"{path}.reason_codes")
    if not reasons:
        _fail(f"{path}.reason_codes", "at least one reason is required")
    reason_codes = tuple(
        _text(reason, f"{path}.reason_codes[{index}]")
        for index, reason in enumerate(reasons)
    )

    if evaluation_status == "not_evaluable":
        if prediction["binding"] is not None or prediction["verdict"] is not None:
            _fail(path, "not-evaluable prediction must have null binding and verdict")
        return _PredictionEvidence(None, None, reason_codes)

    binding = _mapping(prediction["binding"], f"{path}.binding")
    _required(binding, {"ic50_nm", "method", "percentile_rank"}, f"{path}.binding")
    _number(binding["ic50_nm"], f"{path}.binding.ic50_nm", minimum=0.0)
    percentile_rank = _number(
        binding["percentile_rank"],
        f"{path}.binding.percentile_rank",
        minimum=0.0,
        maximum=100.0,
    )
    assert percentile_rank is not None
    _text(binding["method"], f"{path}.binding.method")
    try:
        verdict = Verdict(prediction["verdict"])
    except (TypeError, ValueError):
        _fail(f"{path}.verdict", "unknown verdict")
    return _PredictionEvidence(verdict, percentile_rank, reason_codes)


def _validate_reconciled_summary(
    value: Any,
    path: str,
    expected: dict[str, Any],
    *,
    aggregate: bool,
) -> None:
    obj = _mapping(value, path)
    _required(obj, set(expected), path)
    count_names = {
        "published_positive_total",
        "published_positive_evaluable",
        "positive_visible_count",
        "matched_decoy_evaluable",
        "matched_decoy_rejected_count",
        "paired_binding_rank_wins",
    }
    if aggregate:
        count_names |= {
            "published_positive_not_evaluable",
            "positive_invisible_count",
            "matched_decoy_total",
        }
    for name in count_names:
        _integer(obj[name], f"{path}.{name}")
    _number(
        obj["synthetic_decoy_binding_roc_auc"],
        f"{path}.synthetic_decoy_binding_roc_auc",
        minimum=0.0,
        maximum=1.0,
        nullable=True,
    )
    if aggregate:
        for name in (
            "positive_agreement_rate",
            "matched_decoy_rejection_rate",
            "paired_binding_rank_win_rate",
        ):
            _number(obj[name], f"{path}.{name}", minimum=0.0, maximum=1.0)
        verdict_counts = _mapping(obj["positive_verdict_counts"], f"{path}.positive_verdict_counts")
        if set(verdict_counts) != {verdict.value for verdict in Verdict}:
            _fail(f"{path}.positive_verdict_counts", "expected all verdicts")
        for verdict, count in verdict_counts.items():
            _integer(count, f"{path}.positive_verdict_counts.{verdict}")
    else:
        splits = _mapping(obj["positive_split_counts"], f"{path}.positive_split_counts")
        if set(splits) != {"train", "validation", "test"}:
            _fail(f"{path}.positive_split_counts", "expected train/validation/test")
        for name, count in splits.items():
            _integer(count, f"{path}.positive_split_counts.{name}")
    for name, expected_value in expected.items():
        if obj[name] != expected_value:
            _fail(f"{path}.{name}", "does not match literature entry evidence")


def _validate_literature(literature: Any) -> None:
    path = "results.literature"
    obj = _mapping(literature, path)
    _required(obj, {"entries", "agreement_stats", "meta"}, path)
    meta = _mapping(obj["meta"], f"{path}.meta")
    _required(
        meta,
        {"seed", "methods", "citations", "negative_control", "limitations"},
        f"{path}.meta",
    )
    if _integer(meta["seed"], f"{path}.meta.seed") != PROJECT_SEED:
        _fail(f"{path}.meta.seed", f"expected {PROJECT_SEED}")
    _text_mapping(meta["methods"], f"{path}.meta.methods")
    _text(meta["negative_control"], f"{path}.meta.negative_control")
    _text_mapping(meta["citations"], f"{path}.meta.citations")
    limitations = _list(meta["limitations"], f"{path}.meta.limitations")
    for index, limitation in enumerate(limitations):
        _text(limitation, f"{path}.meta.limitations[{index}]")

    aggregate = _LiteratureEvidence()
    by_exposure = {
        name: _LiteratureEvidence()
        for name in ("train", "held_out", "not_in_binding_dataset")
    }
    unsupported_records: list[dict[str, str]] = []
    not_evaluable_reasons: Counter[str] = Counter()
    entries = _list(obj["entries"], f"{path}.entries")
    for entry_index, entry_value in enumerate(entries):
        entry_path = f"{path}.entries[{entry_index}]"
        entry = _mapping(entry_value, entry_path)
        _required(
            entry,
            {
                "allele",
                "binder_split",
                "binding_dataset_overlap",
                "evaluation_status",
                "external_facts",
                "matched_negative",
                "peptide",
                "prediction",
            },
            entry_path,
        )
        allele = _text(entry["allele"], f"{entry_path}.allele")
        peptide = _canonical(entry["peptide"], f"{entry_path}.peptide")
        split = entry["binder_split"]
        if split not in {"train", "validation", "test"}:
            _fail(f"{entry_path}.binder_split", "unknown binder split")
        overlap = _boolean(
            entry["binding_dataset_overlap"], f"{entry_path}.binding_dataset_overlap"
        )
        status = entry["evaluation_status"]
        if status not in {"evaluable", "not_evaluable"}:
            _fail(f"{entry_path}.evaluation_status", "unknown evaluation status")
        facts = _mapping(entry["external_facts"], f"{entry_path}.external_facts")
        _required(
            facts,
            {
                "assay_result",
                "disease_context",
                "pmid",
                "reference_title",
                "source_molecule",
            },
            f"{entry_path}.external_facts",
        )
        for name in ("assay_result", "pmid", "reference_title"):
            _text(facts[name], f"{entry_path}.external_facts.{name}")
        for name in ("disease_context", "source_molecule"):
            _text(
                facts[name],
                f"{entry_path}.external_facts.{name}",
                allow_empty=True,
            )
        positive = _validate_prediction(
            entry["prediction"], f"{entry_path}.prediction", status
        )

        negative_path = f"{entry_path}.matched_negative"
        negative = _mapping(entry["matched_negative"], negative_path)
        _required(
            negative,
            {
                "allele",
                "binder_split",
                "binding_dataset_overlap",
                "evaluation_status",
                "experimental_assay_result",
                "kind",
                "peptide",
                "prediction",
            },
            negative_path,
        )
        negative_allele = _text(negative["allele"], f"{negative_path}.allele")
        if negative_allele != allele:
            _fail(f"{negative_path}.allele", "must match published restriction")
        _canonical(negative["peptide"], f"{negative_path}.peptide")
        if negative["binder_split"] not in {"train", "validation", "test"}:
            _fail(f"{negative_path}.binder_split", "unknown binder split")
        _boolean(
            negative["binding_dataset_overlap"],
            f"{negative_path}.binding_dataset_overlap",
        )
        negative_status = negative["evaluation_status"]
        if negative_status not in {"evaluable", "not_evaluable"}:
            _fail(f"{negative_path}.evaluation_status", "unknown evaluation status")
        if negative_status != status:
            _fail(negative_path, "positive and matched-negative evaluability must agree")
        if negative["experimental_assay_result"] is not None:
            _fail(
                f"{negative_path}.experimental_assay_result",
                "synthetic control must not claim an experimental result",
            )
        _text(negative["kind"], f"{negative_path}.kind")
        decoy = _validate_prediction(
            negative["prediction"], f"{negative_path}.prediction", negative_status
        )
        if positive.evaluable != decoy.evaluable:
            _fail(negative_path, "positive and matched-negative evidence must agree")

        aggregate.add(split, positive, decoy)
        exposure = binding_exposure(overlap, split)
        by_exposure[exposure].add(split, positive, decoy)
        if not positive.evaluable:
            unsupported_records.append({"allele": allele, "peptide": peptide})
            not_evaluable_reasons.update(positive.reason_codes)

    stats_path = f"{path}.agreement_stats"
    stats = _mapping(obj["agreement_stats"], stats_path)
    expected_aggregate = aggregate.summary(aggregate=True)
    _required(
        stats,
        set(expected_aggregate)
        | {"not_evaluable_by_reason", "unsupported_records", "by_binding_exposure"},
        stats_path,
    )
    _validate_reconciled_summary(
        stats, stats_path, expected_aggregate, aggregate=True
    )

    reasons = _mapping(
        stats["not_evaluable_by_reason"], f"{stats_path}.not_evaluable_by_reason"
    )
    normalized_reasons: dict[str, int] = {}
    for reason, count in reasons.items():
        reason_name = _text(reason, f"{stats_path}.not_evaluable_by_reason.<name>")
        reason_count = _integer(
            count, f"{stats_path}.not_evaluable_by_reason.{reason_name}"
        )
        if reason_count:
            normalized_reasons[reason_name] = reason_count
    if normalized_reasons != dict(not_evaluable_reasons):
        _fail(
            f"{stats_path}.not_evaluable_by_reason",
            "does not match literature entry evidence",
        )

    unsupported = _list(stats["unsupported_records"], f"{stats_path}.unsupported_records")
    for index, record_value in enumerate(unsupported):
        record_path = f"{stats_path}.unsupported_records[{index}]"
        record = _mapping(record_value, record_path)
        _required(record, {"allele", "peptide"}, record_path)
        _text(record["allele"], f"{record_path}.allele")
        _canonical(record["peptide"], f"{record_path}.peptide")
    if unsupported != unsupported_records:
        _fail(
            f"{stats_path}.unsupported_records",
            "does not match literature entry evidence",
        )

    strata = _mapping(stats["by_binding_exposure"], f"{stats_path}.by_binding_exposure")
    if set(strata) != set(by_exposure):
        _fail(f"{stats_path}.by_binding_exposure", "expected exposure strata")
    for name, evidence in by_exposure.items():
        _validate_reconciled_summary(
            strata[name],
            f"{stats_path}.by_binding_exposure.{name}",
            evidence.summary(),
            aggregate=False,
        )


def validate_results(document: Any) -> dict[str, Any]:
    """Validate and return one complete schema-v1.1 document without mutation."""

    root = _mapping(document, "results")
    _required(
        root,
        {"meta", "tumor", "alleles", "mutations", "population", "literature"},
        "results",
    )

    meta = _mapping(root["meta"], "results.meta")
    _required(meta, {"schema_version", "seed", "created_utc", "sources", "methods"}, "results.meta")
    if meta["schema_version"] != SCHEMA_VERSION:
        _fail("results.meta.schema_version", f"expected {SCHEMA_VERSION}")
    if meta["seed"] != PROJECT_SEED:
        _fail("results.meta.seed", f"expected deterministic seed {PROJECT_SEED}")
    _text(meta["created_utc"], "results.meta.created_utc")
    sources = _list(meta["sources"], "results.meta.sources")
    for index, source in enumerate(sources):
        _text(source, f"results.meta.sources[{index}]")
    _text_mapping(meta["methods"], "results.meta.methods")

    allele_values = _list(root["alleles"], "results.alleles")
    alleles = [
        _text(value, f"results.alleles[{index}]")
        for index, value in enumerate(allele_values)
    ]
    if not alleles:
        _fail("results.alleles", "at least one allele is required")
    unsupported = any(allele not in SUPPORTED_ALLELES for allele in alleles)
    if len(alleles) != len(set(alleles)) or unsupported:
        _fail("results.alleles", "expected unique supported HLA-A/B alleles")

    mutations = _list(root["mutations"], "results.mutations")
    candidate_keys: list[str] = []
    for index, mutation in enumerate(mutations):
        path = f"results.mutations[{index}]"
        obj = _mapping(mutation, path)
        _required(obj, {"gene", "change", "protein_effect", "peptides"}, path)
        _text(obj["gene"], f"{path}.gene")
        _text(obj["change"], f"{path}.change")
        _text(obj["protein_effect"], f"{path}.protein_effect")
        peptides = _list(obj["peptides"], f"{path}.peptides")
        for peptide_index, peptide in enumerate(peptides):
            candidate_keys.append(
                _validate_peptide(peptide, alleles, f"{path}.peptides[{peptide_index}]")
            )
    if len(candidate_keys) != len(set(candidate_keys)):
        _fail("results.mutations", "candidate keys must be globally unique")

    _validate_audit(_mapping(root["tumor"], "results.tumor"), len(mutations))
    _validate_population(root["population"], candidate_keys)
    _validate_literature(root["literature"])
    return root


def load_results(path: str | Path) -> dict[str, Any]:
    """Load UTF-8 JSON from *path* and enforce schema v1.1."""

    with Path(path).open(encoding="utf-8") as handle:
        return validate_results(json.load(handle))


def _dump_validated_results(document: dict[str, Any], path: str | Path) -> None:
    """Write a pipeline-validated document without repeating schema traversal."""

    Path(path).write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def dump_results(document: Any, path: str | Path) -> None:
    """Validate and write canonical deterministic schema-v1.1 JSON."""

    _dump_validated_results(validate_results(document), path)
