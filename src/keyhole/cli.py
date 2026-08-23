"""Command-line entry point; completed incrementally through S7."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the stable top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="keyhole",
        description="Explain which tumor protein fragments an immune system can see.",
    )
    parser.add_argument("--version", action="version", version="KEYHOLE 0.1.0")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
