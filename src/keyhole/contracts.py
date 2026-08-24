"""Dependency-light constants and normalization shared across KEYHOLE contracts."""

from __future__ import annotations

from collections.abc import Collection, Sequence

SCHEMA_VERSION = "1.1"
PROJECT_SEED = 1729
CANONICAL_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
SUPPORTED_ALLELES = (
    "A*01:01",
    "A*02:01",
    "A*03:01",
    "A*11:01",
    "A*23:01",
    "A*24:02",
    "A*29:02",
    "A*30:01",
    "A*30:02",
    "A*31:01",
    "A*33:01",
    "A*68:01",
    "B*07:02",
    "B*08:01",
    "B*15:01",
    "B*18:01",
    "B*27:05",
    "B*35:01",
    "B*40:01",
    "B*44:02",
    "B*44:03",
    "B*46:01",
    "B*51:01",
    "B*53:01",
    "B*57:01",
    "B*58:01",
)


def normalize_allele(allele: str) -> str:
    """Normalize an HLA name without narrowing its locus."""

    if not isinstance(allele, str):
        raise TypeError("allele must be a string")
    normalized = allele.strip().upper()
    return normalized[4:] if normalized.startswith("HLA-") else normalized


def canonical_sequence(value: str, *, label: str = "sequence") -> str:
    """Normalize one amino-acid sequence and reject non-canonical residues."""

    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    normalized = value.strip().upper()
    invalid = sorted(set(normalized) - CANONICAL_AMINO_ACIDS)
    if invalid:
        raise ValueError(f"{label} contains non-canonical residues: {''.join(invalid)}")
    return normalized


def canonical_peptide(
    value: str,
    *,
    lengths: Collection[int] = (9, 10),
    label: str = "peptide",
) -> str:
    """Normalize a canonical peptide and enforce one of the allowed lengths."""

    peptide = canonical_sequence(value, label=label)
    allowed = tuple(sorted(set(lengths)))
    if len(peptide) not in allowed:
        choices = " or ".join(str(length) for length in allowed)
        raise ValueError(f"{label} must contain exactly {choices} residues")
    return peptide


def binding_order_key(rank: float, ic50_nm: float, allele: str) -> tuple[float, float, str]:
    """Return the frozen lower-is-better binding winner order."""

    return float(rank), float(ic50_nm), allele


def binary_roc_auc(labels: Sequence[bool], scores: Sequence[float]) -> float:
    """Compute binary ROC AUC with average ranks and no numerical dependencies."""

    if len(labels) != len(scores):
        raise ValueError("ROC AUC inputs must have equal length")
    positives = sum(bool(label) for label in labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("ROC AUC requires both positive and negative examples")

    ordered = sorted(range(len(scores)), key=lambda index: scores[index])
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and scores[ordered[end]] == scores[ordered[start]]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[ordered[position]] = average_rank
        start = end

    positive_rank_sum = sum(
        rank for label, rank in zip(labels, ranks, strict=True) if label
    )
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (
        positives * negatives
    )



def binding_exposure(overlap: bool, split: str) -> str:
    """Classify exact binder-source overlap into train, held-out, or unseen."""

    if not overlap:
        return "not_in_binding_dataset"
    return "train" if split == "train" else "held_out"