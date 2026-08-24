"""Frozen schema-v1 validation for the pipeline-to-renderer contract."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any, NoReturn

SCHEMA_VERSION = 1
PROJECT_SEED = 1729


class Verdict(StrEnum):
    """Permitted candidate visibility conclusions."""

    VISIBLE_CLEAR = "VISIBLE_CLEAR"
    VISIBLE_FAINT = "VISIBLE_FAINT"
    INVISIBLE = "INVISIBLE"


class SchemaError(ValueError):
    """Raised when a result artifact violates schema v1."""


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


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        _fail(path, "expected number")
    return float(value)


def _required(obj: dict[str, Any], keys: set[str], path: str) -> None:
    missing = sorted(keys - obj.keys())
    if missing:
        _fail(path, f"missing keys: {', '.join(missing)}")


def _validate_binding(binding: Any, path: str) -> None:
    values = _mapping(binding, path)
    if not values:
        _fail(path, "at least one allele is required")
    for allele, score in values.items():
        _text(allele, f"{path}.<allele>")
        score_obj = _mapping(score, f"{path}.{allele}")
        _required(score_obj, {"ic50", "rank"}, f"{path}.{allele}")
        if _number(score_obj["ic50"], f"{path}.{allele}.ic50") <= 0:
            _fail(f"{path}.{allele}.ic50", "must be positive")
        rank = _number(score_obj["rank"], f"{path}.{allele}.rank")
        if not 0 <= rank <= 100:
            _fail(f"{path}.{allele}.rank", "must be in [0, 100]")


def _validate_peptide(peptide: Any, path: str) -> None:
    obj = _mapping(peptide, path)
    _required(
        obj,
        {
            "seq",
            "wt_seq",
            "position",
            "source",
            "scores",
            "agretopicity",
            "foreignness",
            "verdict",
            "reason_codes",
            "plain_language",
        },
        path,
    )
    seq = _text(obj["seq"], f"{path}.seq")
    wt_seq = _text(obj["wt_seq"], f"{path}.wt_seq", allow_empty=True)
    if len(seq) not in {9, 10}:
        _fail(f"{path}.seq", "expected a 9-mer or 10-mer")
    if wt_seq and len(wt_seq) != len(seq):
        _fail(f"{path}.wt_seq", "must be empty or match mutant peptide length")
    if isinstance(obj["position"], bool) or not isinstance(obj["position"], int):
        _fail(f"{path}.position", "expected integer")
    if obj["position"] < 0 or obj["position"] >= len(seq):
        _fail(f"{path}.position", "must index the mutant residue in seq")
    if obj["source"] not in {"missense", "frameshift"}:
        _fail(f"{path}.source", "expected missense or frameshift")
    scores = _mapping(obj["scores"], f"{path}.scores")
    _required(scores, {"binding", "tap", "cleavage"}, f"{path}.scores")
    _validate_binding(scores["binding"], f"{path}.scores.binding")
    for name in ("tap", "cleavage"):
        value = _number(scores[name], f"{path}.scores.{name}")
        if not 0 <= value <= 1:
            _fail(f"{path}.scores.{name}", "must be in [0, 1]")
    _number(obj["agretopicity"], f"{path}.agretopicity")
    _number(obj["foreignness"], f"{path}.foreignness")
    try:
        Verdict(obj["verdict"])
    except (TypeError, ValueError):
        _fail(f"{path}.verdict", "unknown verdict")
    reasons = _list(obj["reason_codes"], f"{path}.reason_codes")
    if not reasons:
        _fail(f"{path}.reason_codes", "at least one reason is required")
    for index, reason in enumerate(reasons):
        _text(reason, f"{path}.reason_codes[{index}]")
    _text(obj["plain_language"], f"{path}.plain_language")


def validate_results(document: Any) -> dict[str, Any]:
    """Validate and return a schema-v1 result document without mutating it."""

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
    _list(meta["sources"], "results.meta.sources")
    _mapping(meta["methods"], "results.meta.methods")

    tumor = _mapping(root["tumor"], "results.tumor")
    _required(tumor, {"name", "input", "variant_count"}, "results.tumor")
    _text(tumor["name"], "results.tumor.name")
    _text(tumor["input"], "results.tumor.input")
    if not isinstance(tumor["variant_count"], int) or tumor["variant_count"] < 0:
        _fail("results.tumor.variant_count", "expected non-negative integer")

    alleles = _list(root["alleles"], "results.alleles")
    if not alleles:
        _fail("results.alleles", "at least one allele is required")
    for index, allele in enumerate(alleles):
        _text(allele, f"results.alleles[{index}]")

    mutations = _list(root["mutations"], "results.mutations")
    for index, mutation in enumerate(mutations):
        path = f"results.mutations[{index}]"
        obj = _mapping(mutation, path)
        _required(obj, {"gene", "change", "protein_effect", "peptides"}, path)
        _text(obj["gene"], f"{path}.gene")
        _text(obj["change"], f"{path}.change")
        _text(obj["protein_effect"], f"{path}.protein_effect")
        for peptide_index, peptide in enumerate(_list(obj["peptides"], f"{path}.peptides")):
            _validate_peptide(peptide, f"{path}.peptides[{peptide_index}]")

    population = _mapping(root["population"], "results.population")
    _required(population, {"per_candidate_coverage", "peptide_allele_matrix"}, "results.population")
    _mapping(population["per_candidate_coverage"], "results.population.per_candidate_coverage")
    _mapping(population["peptide_allele_matrix"], "results.population.peptide_allele_matrix")

    literature = _mapping(root["literature"], "results.literature")
    _required(literature, {"entries", "agreement_stats"}, "results.literature")
    _list(literature["entries"], "results.literature.entries")
    _mapping(literature["agreement_stats"], "results.literature.agreement_stats")
    return root


def load_results(path: str | Path) -> dict[str, Any]:
    """Load UTF-8 JSON from *path* and enforce schema v1."""

    with Path(path).open(encoding="utf-8") as handle:
        return validate_results(json.load(handle))


def _dump_validated_results(document: dict[str, Any], path: str | Path) -> None:
    """Write a pipeline-validated document without repeating schema traversal."""

    Path(path).write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def dump_results(document: Any, path: str | Path) -> None:
    """Validate and write canonical deterministic schema-v1 JSON."""

    _dump_validated_results(validate_results(document), path)
