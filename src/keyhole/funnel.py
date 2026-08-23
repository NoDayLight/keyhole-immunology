"""Truth-labeled antigen-processing, binding, and nearest-self gauntlet."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from keyhole.bind import AA_ORDER, BLOSUM62, BindingPrediction, FrozenBinder, load_binder
from keyhole.data import iter_self_peptides
from keyhole.peptides import PeptidePair
from keyhole.schema import Verdict

METHOD_LABELS = {
    "binding": "measured ML",
    "cleavage": "heuristic approximation",
    "tap": "heuristic approximation",
    "agretopicity": "heuristic approximation",
    "foreignness": "heuristic approximation",
    "verdict": "heuristic approximation",
}

CITATIONS = {
    "cleavage": "Holzhütter et al. J Mol Biol. 1999. PMID 10656797",
    "processing": "Peters et al. J Immunol. 2005. PMID 15868101",
    "tap": "Peters et al. J Immunol. 2003;171:1741-1749",
    "foreignness": "Łuksza et al. Nature. 2017. DOI 10.1038/nature24473 (simplified adaptation)",
    "blosum62": "Henikoff & Henikoff. PNAS. 1992. DOI 10.1073/pnas.89.22.10915",
}

# Transparent hand-authored heuristic weights, not fitted measurements. The
# C-terminal signal dominates; upstream positions provide smaller context.
_CLEAVAGE_CTERM = {
    "A": 0.6,
    "C": 0.2,
    "D": -0.4,
    "E": -0.3,
    "F": 1.2,
    "G": 0.0,
    "H": 0.1,
    "I": 1.0,
    "K": -0.8,
    "L": 1.1,
    "M": 0.8,
    "N": -0.2,
    "P": -1.2,
    "Q": -0.2,
    "R": -0.6,
    "S": 0.1,
    "T": 0.2,
    "V": 0.9,
    "W": 1.0,
    "Y": 1.1,
}
_TAP_CTERM = {
    "A": 0.4,
    "C": 0.1,
    "D": -0.8,
    "E": -0.7,
    "F": 1.2,
    "G": -0.1,
    "H": 0.1,
    "I": 1.0,
    "K": 0.5,
    "L": 1.1,
    "M": 0.8,
    "N": -0.4,
    "P": -1.0,
    "Q": -0.3,
    "R": 0.5,
    "S": -0.2,
    "T": 0.0,
    "V": 0.9,
    "W": 1.1,
    "Y": 1.0,
}
_AA_INDEX = {amino_acid: index for index, amino_acid in enumerate(AA_ORDER)}


@dataclass(frozen=True, slots=True)
class FunnelResult:
    """Complete schema-ready evidence for one mutant peptide."""

    pair: PeptidePair
    binding: Mapping[str, BindingPrediction]
    wt_binding: Mapping[str, BindingPrediction]
    cleavage: float
    tap: float
    agretopicity: float
    foreignness: float
    best_allele: str
    verdict: Verdict
    reason_codes: tuple[str, ...]
    plain_language: str


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def cleavage_score(peptide: str) -> float:
    """Return a C-terminal PWM-like proteasome heuristic in [0, 1]."""

    if len(peptide) not in {9, 10}:
        raise ValueError("cleavage scoring requires a 9-mer or 10-mer")
    if set(peptide) - set(AA_ORDER):
        raise ValueError("cleavage scoring requires canonical amino acids")
    raw = (
        1.25 * _CLEAVAGE_CTERM[peptide[-1]]
        + 0.30 * _CLEAVAGE_CTERM[peptide[-2]]
        + 0.15 * _CLEAVAGE_CTERM[peptide[-3]]
    )
    return _sigmoid(raw)


def tap_score(peptide: str) -> float:
    """Return a position-weighted TAP transport heuristic in [0, 1]."""

    if len(peptide) not in {9, 10}:
        raise ValueError("TAP scoring requires a 9-mer or 10-mer")
    if set(peptide) - set(AA_ORDER):
        raise ValueError("TAP scoring requires canonical amino acids")
    raw = (
        1.30 * _TAP_CTERM[peptide[-1]]
        + 0.20 * _TAP_CTERM[peptide[0]]
        + 0.10 * _TAP_CTERM[peptide[1]]
        - (0.35 if "P" in peptide[-3:] else 0.0)
    )
    return _sigmoid(raw)


def _query_rows(peptide: str) -> np.ndarray:
    indices = [_AA_INDEX[residue] for residue in peptide]
    rows = BLOSUM62[indices]
    if len(peptide) == 10:
        rows = np.concatenate((rows[:4], rows[4:6].mean(axis=0, keepdims=True), rows[6:]))
    return rows


@lru_cache(maxsize=1)
def _self_index() -> np.ndarray:
    """Load the frozen self sample as compact amino-acid indices exactly once."""

    peptides = list(iter_self_peptides())
    if len(peptides) != 500_000:
        raise ValueError("foreignness requires the frozen 500,000-peptide self sample")
    index = np.fromiter(
        (_AA_INDEX[residue] for peptide in peptides for residue in peptide),
        dtype=np.uint8,
        count=500_000 * 9,
    ).reshape(500_000, 9)
    index.setflags(write=False)
    return index


def foreignness_score(peptide: str, *, self_index: np.ndarray | None = None) -> float:
    """Return normalized BLOSUM62 distance from the nearest sampled self 9-mer.

    Higher values are more unlike sampled self. Ten-mer central residues are
    pooled using the same explicit fixed-width approximation as the binder.
    """

    if len(peptide) not in {9, 10} or set(peptide) - set(AA_ORDER):
        raise ValueError("foreignness scoring requires a canonical 9-mer or 10-mer")
    index = _self_index() if self_index is None else np.asarray(self_index)
    if index.ndim != 2 or index.shape[1] != 9 or np.any(index >= 20):
        raise ValueError("self index must have shape (n, 9) with amino-acid indices 0..19")
    query = _query_rows(peptide)
    similarities = np.zeros(len(index), dtype=np.float32)
    for position in range(9):
        similarities += query[position, index[:, position]]
    nearest = float(similarities.max())
    maximum = float(query.max(axis=1).sum())
    minimum = float(query.min(axis=1).sum())
    if maximum == minimum:
        return 0.0
    return min(1.0, max(0.0, (maximum - nearest) / (maximum - minimum)))


def differential_agretopicity(
    mutant: BindingPrediction, wild_type: BindingPrediction | None
) -> float:
    """Return WT IC50 / mutant IC50 for the same allele, or 0 when undefined."""

    if wild_type is None:
        return 0.0
    return wild_type.ic50_nm / mutant.ic50_nm


def verdict_engine(
    *,
    cleavage: float,
    tap: float,
    binding_rank: float,
    binding_ic50: float,
    foreignness: float,
    agretopicity: float,
    has_wt: bool = True,
) -> tuple[Verdict, tuple[str, ...], str]:
    """Apply fixed transparent thresholds and generate reason-coded language."""

    reasons: list[str] = []
    if cleavage < 0.35:
        reasons.append("LOW_CLEAVAGE")
    if tap < 0.35:
        reasons.append("LOW_TAP_TRANSPORT")
    if reasons:
        return (
            Verdict.INVISIBLE,
            tuple(reasons),
            (
                "This altered protein card never gets displayed because processing is "
                "predicted to fail."
            ),
        )

    strong_binding = binding_rank <= 2.0 and binding_ic50 <= 500.0
    faint_binding = binding_rank <= 10.0 and binding_ic50 <= 5_000.0
    if not faint_binding:
        return (
            Verdict.INVISIBLE,
            ("WEAK_BINDING",),
            "This altered protein card doesn't fit your keyhole strongly enough for display.",
        )
    reasons.append("STRONG_BINDING" if strong_binding else "BORDERLINE_BINDING")

    if foreignness < 0.04:
        reasons.append("SELF_LIKE")
        return (
            Verdict.INVISIBLE,
            tuple(reasons),
            (
                "This displayed card looks too much like yourself to stand out in the sampled "
                "self scan."
            ),
        )
    reasons.append("FOREIGN_LIKE" if foreignness >= 0.10 else "PARTLY_SELF_LIKE")
    if not has_wt:
        reasons.append("NO_WT_COUNTERPART")
    elif agretopicity >= 1.5:
        reasons.append("MUTANT_BINDS_BETTER")
    else:
        reasons.append("LIMITED_DIFFERENTIAL_BINDING")

    clear = strong_binding and foreignness >= 0.10 and (not has_wt or agretopicity >= 1.5)
    if clear:
        return (
            Verdict.VISIBLE_CLEAR,
            tuple(reasons),
            (
                "This altered protein card is predicted to be displayed clearly and look unlike "
                "sampled self."
            ),
        )
    return (
        Verdict.VISIBLE_FAINT,
        tuple(reasons),
        "This altered protein card may be displayed, but one or more visibility signals are faint.",
    )


def run_funnel(
    pair: PeptidePair,
    alleles: Sequence[str],
    *,
    binder: FrozenBinder | None = None,
    self_index: np.ndarray | None = None,
) -> FunnelResult:
    """Run one real candidate through heuristic processing and measured-data ML."""

    if not alleles:
        raise ValueError("the funnel requires at least one HLA allele")
    model = load_binder() if binder is None else binder
    binding: dict[str, BindingPrediction] = {}
    wt_binding: dict[str, BindingPrediction] = {}
    for allele in alleles:
        mutant_prediction = model.predict(pair.seq, allele)
        binding[mutant_prediction.allele] = mutant_prediction
        if pair.wt_seq:
            wild_prediction = model.predict(pair.wt_seq, allele)
            wt_binding[wild_prediction.allele] = wild_prediction
    best = min(binding.values(), key=lambda item: (item.percentile_rank, item.ic50_nm, item.allele))
    wild_type = wt_binding.get(best.allele)
    agretopicity = differential_agretopicity(best, wild_type)
    cleavage = cleavage_score(pair.seq)
    tap = tap_score(pair.seq)
    foreignness = foreignness_score(pair.seq, self_index=self_index)
    conclusion, reasons, language = verdict_engine(
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
        verdict=conclusion,
        reason_codes=reasons,
        plain_language=language,
    )
