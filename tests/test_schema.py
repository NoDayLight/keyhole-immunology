"""Contract tests for schema v1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from keyhole.schema import PROJECT_SEED, SCHEMA_VERSION, SchemaError, dump_results, validate_results

FIXTURE = Path(__file__).parent / "fixtures" / "results.sample.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_frozen_fixture_is_valid_and_covers_all_verdicts() -> None:
    result = validate_results(load_fixture())
    verdicts = {
        peptide["verdict"]
        for mutation in result["mutations"]
        for peptide in mutation["peptides"]
    }
    assert result["meta"]["schema_version"] == SCHEMA_VERSION == 1
    assert result["meta"]["seed"] == PROJECT_SEED == 1729
    assert verdicts == {"VISIBLE_CLEAR", "VISIBLE_FAINT", "INVISIBLE"}


def test_schema_rejects_unversioned_or_nondeterministic_documents() -> None:
    wrong_version = copy.deepcopy(load_fixture())
    wrong_version["meta"]["schema_version"] = 2
    with pytest.raises(SchemaError, match="schema_version"):
        validate_results(wrong_version)

    wrong_seed = copy.deepcopy(load_fixture())
    wrong_seed["meta"]["seed"] = 7
    with pytest.raises(SchemaError, match="deterministic seed"):
        validate_results(wrong_seed)


def test_dump_is_canonical_and_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    document = load_fixture()
    dump_results(document, first)
    dump_results(document, second)
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8")) == document


def test_schema_rejects_invalid_peptide_position() -> None:
    document = copy.deepcopy(load_fixture())
    document["mutations"][0]["peptides"][0]["position"] = 99
    with pytest.raises(SchemaError, match="must index"):
        validate_results(document)
