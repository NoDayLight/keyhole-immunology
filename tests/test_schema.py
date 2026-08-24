"""Contract tests for schema v1.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from keyhole.assets import packaged_file
from keyhole.schema import PROJECT_SEED, SCHEMA_VERSION, SchemaError, dump_results, validate_results

FIXTURE = packaged_file("validation/results.sample.json")


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_frozen_fixture_is_a_complete_empty_v11_contract() -> None:
    result = validate_results(load_fixture())
    assert result["meta"]["schema_version"] == SCHEMA_VERSION == "1.1"
    assert result["meta"]["seed"] == PROJECT_SEED == 1729
    assert result["mutations"] == []
    assert result["tumor"]["screening"]["input_row_count"] == 0


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


def test_public_dump_still_rejects_invalid_documents(tmp_path: Path) -> None:
    document = copy.deepcopy(load_fixture())
    document["meta"]["schema_version"] = 2
    destination = tmp_path / "invalid.json"
    with pytest.raises(SchemaError, match="schema_version"):
        dump_results(document, destination)
    assert not destination.exists()


def test_schema_rejects_missing_or_inconsistent_audit() -> None:
    missing = copy.deepcopy(load_fixture())
    del missing["tumor"]["screening"]
    with pytest.raises(SchemaError, match="screening"):
        validate_results(missing)

    inconsistent = copy.deepcopy(load_fixture())
    inconsistent["tumor"]["screening"]["input_row_count"] = 1
    with pytest.raises(SchemaError, match="ignored_class_count"):
        validate_results(inconsistent)

    for name in ("missing_canonical_context_count", "unsupported_frameshift_count"):
        inflated = copy.deepcopy(load_fixture())
        inflated["tumor"]["screening"][name] = 1
        with pytest.raises(SchemaError, match="do not cover unsupported changes"):
            validate_results(inflated)

    uncovered = copy.deepcopy(load_fixture())
    uncovered["tumor"]["variant_count"] = 1
    uncovered["tumor"]["screening"].update(
        input_row_count=1,
        supported_change_count=1,
    )
    with pytest.raises(SchemaError, match="do not cover unsupported changes"):
        validate_results(uncovered)

    for missing_count, frameshift_count in ((1, 0), (0, 1), (1, 1)):
        accounted = copy.deepcopy(uncovered)
        accounted["tumor"]["screening"].update(
            missing_canonical_context_count=missing_count,
            unsupported_frameshift_count=frameshift_count,
        )
        validate_results(accounted)


def test_schema_requires_text_method_names_and_values() -> None:
    for path in (("meta", "methods"), ("literature", "meta", "methods")):
        document = copy.deepcopy(load_fixture())
        methods = document
        for name in path:
            methods = methods[name]
        methods["binder"] = 42
        with pytest.raises(SchemaError, match="methods.binder"):
            validate_results(document)
