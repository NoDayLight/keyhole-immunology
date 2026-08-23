"""Tests for deterministic mutation-centered candidate generation."""

from __future__ import annotations

import pytest

from keyhole.parse import parse_famous
from keyhole.peptides import (
    PeptideGenerationError,
    frameshift_peptides,
    missense_peptides,
    variant_peptides,
)


def test_missense_generates_all_position_matched_9_and_10mers() -> None:
    braf = parse_famous("BRAF V600E")
    first = variant_peptides(braf)
    second = variant_peptides(braf)
    assert first == second
    assert len(first) == 19
    assert {len(item.seq) for item in first} == {9, 10}
    assert all(item.seq[item.position] == "E" for item in first)
    assert all(item.wt_seq[item.position] == "V" for item in first)
    assert [item.protein_start for item in first[:9]] == list(range(591, 600))


def test_frameshift_uses_only_novel_stream_before_first_stop() -> None:
    pairs = frameshift_peptides(
        "MABCDEFGHIJKLMNPQRSTVWY".replace("B", "N").replace("J", "I"),
        6,
        "RSTVWYACDE*IGNORED",
    )
    assert pairs
    assert all("*" not in item.seq and item.source == "frameshift" for item in pairs)
    assert all(item.protein_start + item.position == 5 for item in pairs)
    assert all(set(item.seq) <= set("ACDEFGHIKLMNPQRSTVWY") for item in pairs)


def test_generation_refuses_unmeasured_or_invalid_context() -> None:
    with pytest.raises(PeptideGenerationError, match="outside"):
        missense_peptides("ACDEFGHIK", 99, "V")
    with pytest.raises(PeptideGenerationError, match="translated novel sequence"):
        variant = parse_famous("KRAS G12D")
        object.__setattr__(variant, "source", "frameshift")
        variant_peptides(variant)
