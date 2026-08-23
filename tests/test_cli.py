"""Tests for the complete offline command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from keyhole import cli
from keyhole.pipeline import InputAudit


def test_open_uses_file_uri_without_starting_a_server(
    tmp_path: Path, monkeypatch, capsys
) -> None:  # type: ignore[no-untyped-def]
    report = tmp_path / "offline report.html"
    report.write_text("<!doctype html><title>KEYHOLE</title>", encoding="utf-8")
    opened: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda uri: opened.append(uri) or True)

    assert cli.main(["open", str(report)]) == 0
    assert opened == [report.resolve().as_uri()]
    assert "Opened file://" in capsys.readouterr().out


def test_open_rejects_missing_or_non_html_paths(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert cli.main(["open", str(tmp_path / "missing.html")]) == 2
    existing = tmp_path / "results.json"
    existing.write_text("{}", encoding="utf-8")
    assert cli.main(["open", str(existing)]) == 2
    assert "offline HTML report does not exist" in capsys.readouterr().err


def test_validate_json_is_machine_readable(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    expected = {
        "binder_models": 26,
        "heldout_metrics": "skipped (--quick)",
        "schema": 1,
        "seed": 1729,
        "status": "OK",
    }
    monkeypatch.setattr(cli, "_quick_validation", lambda: dict(expected))
    assert cli.main(["validate", "--quick", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_full_validate_prints_censor_aware_metric_keys(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "_quick_validation", lambda: {"status": "OK"})
    monkeypatch.setattr(
        cli,
        "validate_binder",
        lambda: {
            "metrics": {
                "aggregate": {
                    "pooled_spearman": 0.7,
                    "pooled_roc_auc_500nm": 0.9,
                }
            }
        },
    )
    assert cli.main(["validate"]) == 0
    output = capsys.readouterr().out
    assert "spearman=0.7 roc_auc_500nm=0.9" in output


def test_screen_routes_one_input_and_reports_audit(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "input.maf"
    source.write_text("unused by mocked pipeline", encoding="utf-8")
    report = tmp_path / "out.html"
    audit = InputAudit(100, 89, 2, 87, 0, 11)
    run = SimpleNamespace(audit=audit, funnel_results=(1, 2, 3), results={})
    seen: list[tuple[Path, str]] = []

    def fake_screen(path: Path, hla: str):  # type: ignore[no-untyped-def]
        seen.append((path, hla))
        return run

    monkeypatch.setattr(cli, "screen_path", fake_screen)
    monkeypatch.setattr(cli, "_write_outputs", lambda *_args: report.resolve())
    assert (
        cli.main(
            [
                "screen",
                "--maf",
                str(source),
                "--hla",
                "A*02:01,B*07:02",
                "--report",
                str(report),
            ]
        )
        == 0
    )
    assert seen == [(source, "A*02:01,B*07:02")]
    output = capsys.readouterr().out
    assert "input_rows=100 supported_changes=89 screenable=2" in output
    assert "unsupported_frameshifts=0 ignored_classes=11" in output
    assert "candidates=3 user_alleles=A*02:01,B*07:02 population_model_alleles=26" in output
