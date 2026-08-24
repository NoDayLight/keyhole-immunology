"""Complete offline KEYHOLE command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from keyhole import __version__
from keyhole.assets import packaged_file
from keyhole.bind import ALLELES, load_binder, validate_binder
from keyhole.data import load_literature_records, pdb_path
from keyhole.parse import parse_famous
from keyhole.pipeline import InputAudit, normalize_hla_list, screen_path, screen_variants
from keyhole.population import frequency_panels
from keyhole.report import _write_validated_report
from keyhole.schema import _dump_validated_results, validate_results
from keyhole.structure import summarize_pdb


def build_parser() -> argparse.ArgumentParser:
    """Build the stable top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="keyhole",
        description="Explain which tumor protein fragments an immune system can see.",
    )
    parser.add_argument("--version", action="version", version=f"KEYHOLE {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="verify frozen assets and held-out metrics")
    validate.add_argument("--quick", action="store_true", help="skip held-out metric recomputation")
    validate.add_argument("--json", action="store_true", help="emit machine-readable status")

    screen = commands.add_parser("screen", help="screen a real MAF or annotated VCF")
    source = screen.add_mutually_exclusive_group(required=True)
    source.add_argument("--maf", type=Path)
    source.add_argument("--vcf", type=Path)
    screen.add_argument("--hla", required=True, help="comma-separated supported two-field alleles")
    screen.add_argument("--report", required=True, type=Path, help="standalone output HTML")
    screen.add_argument("--results", type=Path, help="optional canonical results.json")

    explain = commands.add_parser("explain", help="explain one frozen famous mutation")
    explain.add_argument("mutation", help="KRAS G12D, BRAF V600E, or TP53 R175H")
    explain.add_argument("--hla", required=True, help="comma-separated supported two-field alleles")
    explain.add_argument("--report", type=Path)
    explain.add_argument("--results", type=Path)

    open_command = commands.add_parser("open", help="open an offline report without a server")
    open_command.add_argument("path", nargs="?", type=Path, default=Path("out.html"))
    return parser


def _quick_validation() -> dict[str, object]:
    fixture = packaged_file("validation/results.sample.json")
    validate_results(json.loads(fixture.read_text(encoding="utf-8")))
    binder = load_binder()
    panels = frequency_panels()
    literature = load_literature_records()
    structures = [summarize_pdb(pdb_path(pdb_id)) for pdb_id in ("1HHK", "3PWN", "1AO7")]
    return {
        "binder_models": len(binder.models),
        "heldout_metrics": "skipped (--quick)",
        "literature_records": len(literature),
        "populations": sorted({panel.superpopulation for panel in panels}),
        "schema": 1,
        "seed": 1729,
        "structures": [summary.pdb_id for summary in structures],
        "status": "OK",
    }


def _run_validate(args: argparse.Namespace) -> int:
    status = _quick_validation()
    if not args.quick:
        status["heldout_metrics"] = validate_binder()
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print("KEYHOLE validation: OK")
        print(
            "schema=1 seed=1729 binder_models=26 structures=3 "
            "populations=AFR,AMR,EAS,EUR"
        )
        if args.quick:
            print("heldout_metrics=skipped (--quick)")
        else:
            reproduced = status["heldout_metrics"]
            assert isinstance(reproduced, dict)
            metrics = reproduced["metrics"]
            assert isinstance(metrics, dict)
            aggregate = metrics["aggregate"]
            print(
                "heldout_metrics=reproduced "
                f"spearman={aggregate['pooled_spearman']} "
                f"roc_auc_500nm={aggregate['pooled_roc_auc_500nm']}"
            )
    return 0


def _write_outputs(run, report_path: Path | None, results_path: Path | None) -> Path | None:  # type: ignore[no-untyped-def]
    if results_path is not None:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        _dump_validated_results(run.results, results_path)
    return (
        _write_validated_report(run.results, report_path)
        if report_path is not None
        else None
    )


def _run_screen(args: argparse.Namespace) -> int:
    source = args.maf or args.vcf
    run = screen_path(source, args.hla)
    report = _write_outputs(run, args.report, args.results)
    audit = run.audit
    print("KEYHOLE screen: OK")
    print(
        f"input_rows={audit.input_row_count} supported_changes={audit.supported_change_count} "
        f"screenable={audit.screenable_variant_count} "
        f"missing_canonical_context={audit.missing_canonical_context_count} "
        f"unsupported_frameshifts={audit.unsupported_frameshift_count} "
        f"ignored_classes={audit.ignored_class_count}"
    )
    print(
        f"candidates={len(run.funnel_results)} "
        f"user_alleles={','.join(normalize_hla_list(args.hla))} "
        f"population_model_alleles={len(ALLELES)}"
    )
    print(f"report={report}")
    return 0


def _run_explain(args: argparse.Namespace) -> int:
    variant = parse_famous(args.mutation)
    audit = InputAudit(1, 1, 1, 0, 0, 0)
    run = screen_variants(
        [variant],
        args.hla,
        input_name=f"{variant.gene}-{variant.protein_effect}",
        input_path=f"famous:{variant.gene} {variant.protein_effect}",
        audit=audit,
    )
    _write_outputs(run, args.report, args.results)
    print(f"KEYHOLE explain: {variant.gene} {variant.protein_effect} ({variant.change})")
    print(f"HLA: {','.join(normalize_hla_list(args.hla))}")
    print("SEQ        WT         POS  BEST_HLA  IC50_NM  RANK_PCT  VERDICT        REASONS")
    for result in run.funnel_results:
        best = result.binding[result.best_allele]
        print(
            f"{result.pair.seq:<10} {result.pair.wt_seq:<10} {result.pair.position:>3}  "
            f"{result.best_allele:<9} {best.ic50_nm:>8.1f}  {best.percentile_rank:>8.3f}  "
            f"{result.verdict.value:<14} {','.join(result.reason_codes)}"
        )
    return 0


def _run_open(args: argparse.Namespace) -> int:
    path = args.path.resolve()
    if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(f"offline HTML report does not exist: {path}")
    uri = path.as_uri()
    if not webbrowser.open(uri):
        raise RuntimeError("the default browser declined the report")
    print(f"Opened {uri}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and convert expected input failures to exit status 2."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _run_validate(args)
        if args.command == "screen":
            return _run_screen(args)
        if args.command == "explain":
            return _run_explain(args)
        if args.command == "open":
            return _run_open(args)
        raise RuntimeError(f"unknown command: {args.command}")
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        print(f"KEYHOLE error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
