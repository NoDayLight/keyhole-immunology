"""Published positive epitope agreement and deterministic synthetic controls."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

import numpy as np

from keyhole.bind import BindingPrediction, assign_split, load_binder
from keyhole.contracts import (
    PROJECT_SEED,
    SUPPORTED_ALLELES,
    binary_roc_auc,
    binding_exposure,
    canonical_peptide,
)
from keyhole.data import LiteratureRecord, iter_binding_records, load_literature_records
from keyhole.funnel import (
    CITATIONS,
    METHOD_LABELS,
    cleavage_score,
    foreignness_score,
    tap_score,
    verdict_engine,
)
from keyhole.schema import Verdict

IEDB_CITATION = (
    "Vita R et al. The Immune Epitope Database (IEDB): 2018 update. "
    "Nucleic Acids Res. 2019;47:D339-D343. DOI 10.1093/nar/gky1006"
)
NEGATIVE_KIND = "synthetic_composition_preserving_decoy"
UNSUPPORTED_REASON = "UNSUPPORTED_ALLELE"


class BinderLike(Protocol):
    """Minimal prediction interface used by the literature evaluator."""

    def predict(self, peptide: str, allele: str) -> BindingPrediction:
        """Predict one peptide against its published restriction."""


def generate_matched_negative(
    peptide: str,
    allele: str,
    *,
    seed: int = PROJECT_SEED,
    forbidden: Iterable[str] = (),
) -> str:
    """Return a deterministic length- and composition-matched shuffled control."""

    peptide = canonical_peptide(peptide, label="matched control peptide")
    excluded = set(forbidden) | {peptide}
    digest = hashlib.sha256(
        f"{seed}:literature-negative:{allele}:{peptide}".encode("ascii"),
        usedforsecurity=False,
    ).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    residues = list(peptide)
    for _ in range(10_000):
        rng.shuffle(residues)
        candidate = "".join(residues)
        if candidate not in excluded:
            return candidate
    raise ValueError("could not construct a distinct composition-matched control")


@lru_cache(maxsize=1)
def _binding_source_pairs() -> frozenset[tuple[str, str]]:
    return frozenset((record.peptide, record.allele) for record in iter_binding_records())


def _score_peptide(
    peptide: str,
    allele: str,
    *,
    binder: BinderLike,
    self_index: np.ndarray | None,
) -> tuple[dict[str, object], BindingPrediction | None, Verdict | None]:
    cleavage = cleavage_score(peptide)
    tap = tap_score(peptide)
    foreignness = foreignness_score(peptide, self_index=self_index)
    base: dict[str, object] = {
        "cleavage": {"value": cleavage, "method": METHOD_LABELS["cleavage"]},
        "tap": {"value": tap, "method": METHOD_LABELS["tap"]},
        "foreignness": {
            "value": foreignness,
            "method": METHOD_LABELS["foreignness"],
        },
        "wild_type": {
            "status": "not_available",
            "reason": "NO_WT_COUNTERPART",
        },
        "agretopicity": {
            "value": None,
            "status": "not_comparable",
            "method": METHOD_LABELS["agretopicity"],
        },
    }
    if allele not in SUPPORTED_ALLELES:
        base.update(
            {
                "binding": None,
                "verdict": None,
                "reason_codes": [UNSUPPORTED_REASON],
                "plain_language": (
                    f"The frozen binder has no model for {allele}; this record is not "
                    "evaluable and is excluded from agreement statistics."
                ),
            }
        )
        return base, None, None

    binding = binder.predict(peptide, allele)
    verdict, reasons, language = verdict_engine(
        cleavage=cleavage,
        tap=tap,
        binding_rank=binding.percentile_rank,
        binding_ic50=binding.ic50_nm,
        foreignness=foreignness,
        agretopicity=0.0,
        has_wt=False,
    )
    base.update(
        {
            "binding": {
                "ic50_nm": binding.ic50_nm,
                "percentile_rank": binding.percentile_rank,
                "method": METHOD_LABELS["binding"],
            },
            "verdict": verdict.value,
            "reason_codes": list(reasons),
            "plain_language": language,
        }
    )
    return base, binding, verdict


def _external_facts(record: LiteratureRecord) -> dict[str, str]:
    return {
        "assay_result": record.assay_result,
        "disease_context": record.disease_context,
        "iedb_assay": record.iedb_assay,
        "iedb_epitope": record.iedb_epitope,
        "pmid": record.pmid,
        "reference_title": record.reference_title,
        "source_molecule": record.source_molecule,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


@dataclass(slots=True)
class _AgreementAccumulator:
    positive_total: int = 0
    positive_verdicts: list[Verdict] = field(default_factory=list)
    decoy_verdicts: list[Verdict] = field(default_factory=list)
    positive_ranks: list[float] = field(default_factory=list)
    decoy_ranks: list[float] = field(default_factory=list)
    paired_rank_wins: int = 0
    split_counts: Counter[str] = field(default_factory=Counter)

    def add(
        self,
        *,
        split: str,
        positive_binding: BindingPrediction | None,
        positive_verdict: Verdict | None,
        decoy_binding: BindingPrediction | None,
        decoy_verdict: Verdict | None,
    ) -> None:
        self.positive_total += 1
        self.split_counts[split] += 1
        if positive_binding is None:
            return
        assert positive_verdict is not None
        assert decoy_binding is not None and decoy_verdict is not None
        self.positive_verdicts.append(positive_verdict)
        self.decoy_verdicts.append(decoy_verdict)
        self.positive_ranks.append(positive_binding.percentile_rank)
        self.decoy_ranks.append(decoy_binding.percentile_rank)
        if positive_binding.percentile_rank < decoy_binding.percentile_rank:
            self.paired_rank_wins += 1

    def summary(self, *, aggregate: bool = False) -> dict[str, object]:
        visible = {Verdict.VISIBLE_CLEAR, Verdict.VISIBLE_FAINT}
        evaluable = len(self.positive_verdicts)
        visible_count = sum(verdict in visible for verdict in self.positive_verdicts)
        rejected = sum(verdict is Verdict.INVISIBLE for verdict in self.decoy_verdicts)
        labels = [True] * evaluable + [False] * evaluable
        scores = [-rank for rank in self.positive_ranks + self.decoy_ranks]
        values: dict[str, object] = {
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


def evaluate_literature_panel(
    records: Sequence[LiteratureRecord] | None = None,
    *,
    binder: BinderLike | None = None,
    self_index: np.ndarray | None = None,
    seed: int = PROJECT_SEED,
) -> dict[str, object]:
    """Build the schema-v1 literature branch from real positives and synthetic controls."""

    panel = tuple(load_literature_records() if records is None else records)
    if not panel:
        raise ValueError("literature panel cannot be empty")
    if len({(record.peptide, record.allele) for record in panel}) != len(panel):
        raise ValueError("literature peptide/HLA records must be unique")

    model = load_binder() if binder is None else binder
    source_pairs = _binding_source_pairs()
    forbidden = {record.peptide for record in panel}
    entries: list[dict[str, object]] = []
    aggregate = _AgreementAccumulator()
    by_exposure = {
        name: _AgreementAccumulator()
        for name in ("train", "held_out", "not_in_binding_dataset")
    }
    unsupported: list[dict[str, str]] = []

    for record in panel:
        decoy = generate_matched_negative(
            record.peptide,
            record.allele,
            seed=seed,
            forbidden=forbidden,
        )
        forbidden.add(decoy)
        positive_result, positive_binding, positive_verdict = _score_peptide(
            record.peptide,
            record.allele,
            binder=model,
            self_index=self_index,
        )
        decoy_result, decoy_binding, decoy_verdict = _score_peptide(
            decoy,
            record.allele,
            binder=model,
            self_index=self_index,
        )
        evaluable = positive_binding is not None
        split = assign_split(record.peptide)
        overlap = (record.peptide, record.allele) in source_pairs
        exposure = binding_exposure(overlap, split)
        for accumulator in (aggregate, by_exposure[exposure]):
            accumulator.add(
                split=split,
                positive_binding=positive_binding,
                positive_verdict=positive_verdict,
                decoy_binding=decoy_binding,
                decoy_verdict=decoy_verdict,
            )
        if not evaluable:
            unsupported.append({"allele": record.allele, "peptide": record.peptide})

        entries.append(
            {
                "allele": record.allele,
                "peptide": record.peptide,
                "expected": {
                    "kind": "published_positive_tcell_assay",
                    "assay_result": record.assay_result,
                },
                "external_facts": _external_facts(record),
                "evaluation_status": "evaluable" if evaluable else "not_evaluable",
                "binding_dataset_overlap": overlap,
                "binder_split": split,
                "prediction": positive_result,
                "matched_negative": {
                    "peptide": decoy,
                    "allele": record.allele,
                    "kind": NEGATIVE_KIND,
                    "experimental_assay_result": None,
                    "evaluation_status": "evaluable" if evaluable else "not_evaluable",
                    "binding_dataset_overlap": (decoy, record.allele) in source_pairs,
                    "binder_split": assign_split(decoy),
                    "prediction": decoy_result,
                },
            }
        )

    agreement_stats = aggregate.summary(aggregate=True)
    agreement_stats.update(
        {
            "not_evaluable_by_reason": {UNSUPPORTED_REASON: len(unsupported)},
            "unsupported_records": unsupported,
            "by_binding_exposure": {
                name: accumulator.summary()
                for name, accumulator in by_exposure.items()
            },
        }
    )
    return {
        "entries": entries,
        "agreement_stats": agreement_stats,
        "meta": {
            "seed": seed,
            "methods": dict(METHOD_LABELS),
            "citations": {"iedb": IEDB_CITATION, **CITATIONS},
            "negative_control": (
                "Deterministic length- and composition-preserving peptide shuffle; synthetic "
                "and not experimentally assayed as negative."
            ),
            "limitations": [
                "The literature panel was selected for published positive T-cell assays only.",
                "Synthetic shuffled controls are not experimentally measured negatives.",
                (
                    "Agreement measures model visibility versus T-cell positivity, "
                    "different endpoints."
                ),
                "No position-matched wild type is available; agretopicity is not comparable.",
                "HLA-C*08:02 is outside the frozen 26-allele HLA-A/B binder and is not evaluable.",
                (
                    "Binding-source overlap and peptide split are disclosed per entry; this is "
                    "not an independent clinical validation. Exposure strata distinguish "
                    "overlapping train, overlapping held-out, and source-unseen positives."
                ),
            ],
        },
    }
