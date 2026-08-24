"""Deterministic missense and frameshift 9/10-mer generation."""

from __future__ import annotations

from dataclasses import dataclass

from keyhole.contracts import canonical_sequence
from keyhole.parse import Variant


class PeptideGenerationError(ValueError):
    """Raised when protein context cannot support truthful peptide generation."""


@dataclass(frozen=True, slots=True)
class PeptidePair:
    """A mutant candidate and its position-matched wild-type counterpart."""

    seq: str
    wt_seq: str
    position: int
    protein_start: int
    source: str


def _canonical(sequence: str, label: str) -> str:
    try:
        return canonical_sequence(sequence, label=label)
    except (TypeError, ValueError) as error:
        raise PeptideGenerationError(str(error)) from error


def missense_peptides(
    protein_sequence: str,
    protein_position: int,
    alternate_amino_acid: str,
    *,
    lengths: tuple[int, ...] = (9, 10),
) -> tuple[PeptidePair, ...]:
    """Generate every position-matched 9/10-mer spanning a missense residue.

    ``protein_position`` is one-based. Output ``position`` and ``protein_start``
    are zero-based, matching schema-v1 peptide indexing and Python slicing.
    """

    wild_type = _canonical(protein_sequence, "protein sequence")
    alternate = _canonical(alternate_amino_acid, "alternate amino acid")
    if len(alternate) != 1:
        raise PeptideGenerationError("alternate amino acid must contain exactly one residue")
    mutation_index = protein_position - 1
    if mutation_index < 0 or mutation_index >= len(wild_type):
        raise PeptideGenerationError("protein position is outside the canonical sequence")
    mutant = wild_type[:mutation_index] + alternate + wild_type[mutation_index + 1 :]
    pairs: list[PeptidePair] = []
    for length in lengths:
        if length not in {9, 10}:
            raise PeptideGenerationError("schema v1.1 permits only 9-mer and 10-mer candidates")
        first_start = max(0, mutation_index - length + 1)
        last_start = min(mutation_index, len(wild_type) - length)
        for start in range(first_start, last_start + 1):
            pairs.append(
                PeptidePair(
                    seq=mutant[start : start + length],
                    wt_seq=wild_type[start : start + length],
                    position=mutation_index - start,
                    protein_start=start,
                    source="missense",
                )
            )
    return tuple(pairs)


def frameshift_peptides(
    protein_sequence: str,
    protein_position: int,
    novel_sequence: str,
    *,
    lengths: tuple[int, ...] = (9, 10),
) -> tuple[PeptidePair, ...]:
    """Generate candidates from a frameshift's novel stream through its first stop.

    ``novel_sequence`` begins at the affected one-based protein position and may
    contain ``*``; residues after the first stop are ignored. Every returned
    peptide contains at least one novel residue. A wild-type counterpart is
    emitted only when a complete position-matched window exists.
    """

    wild_type = _canonical(protein_sequence, "protein sequence")
    mutation_index = protein_position - 1
    if mutation_index < 0 or mutation_index > len(wild_type):
        raise PeptideGenerationError("protein position is outside the canonical sequence")
    novel_to_stop = novel_sequence.strip().upper().split("*", 1)[0]
    novel_to_stop = _canonical(novel_to_stop, "frameshift novel sequence")
    if not novel_to_stop:
        raise PeptideGenerationError("frameshift stream has no residues before its first stop")
    altered = wild_type[:mutation_index] + novel_to_stop
    pairs: list[PeptidePair] = []
    for length in lengths:
        if length not in {9, 10}:
            raise PeptideGenerationError("schema v1.1 permits only 9-mer and 10-mer candidates")
        first_start = max(0, mutation_index - length + 1)
        last_start = len(altered) - length
        for start in range(first_start, last_start + 1):
            if start + length <= mutation_index:
                continue
            wild_window = wild_type[start : start + length]
            pairs.append(
                PeptidePair(
                    seq=altered[start : start + length],
                    wt_seq=wild_window if len(wild_window) == length else "",
                    position=mutation_index - start,
                    protein_start=start,
                    source="frameshift",
                )
            )
    return tuple(pairs)


def variant_peptides(
    variant: Variant, *, frameshift_novel_sequence: str | None = None
) -> tuple[PeptidePair, ...]:
    """Generate candidates from a parsed variant with verified protein context."""

    if variant.protein_sequence is None:
        raise PeptideGenerationError(
            f"{variant.gene} {variant.protein_effect} has no frozen canonical protein context"
        )
    if variant.source == "missense":
        return missense_peptides(
            variant.protein_sequence,
            variant.protein_position,
            variant.alternate_amino_acid,
        )
    if frameshift_novel_sequence is None:
        raise PeptideGenerationError("frameshift generation requires a translated novel sequence")
    return frameshift_peptides(
        variant.protein_sequence,
        variant.protein_position,
        frameshift_novel_sequence,
    )
