# R0 Requirements — Audit hygiene

## User story

As a maintainer, I need concise project guidance, an operative source-check hook, and a minimal reviewed runtime closure so later post-audit work starts from a clean, reproducible boundary.

## EARS acceptance criteria

1. THE REPOSITORY SHALL provide one-page-or-shorter product, technology, and structure steering distilled from the governing invariants, README, and implemented architecture.
2. WHEN a current Kiro mutation tool changes Python under `src/` or `tests/`, THE PostToolUse hook SHALL preserve its JSON stdin and run Ruff plus fail-fast pytest.
3. THE REPOSITORY SHALL attempt to ignore generated data/build/venv/cache/Pages artifacts through `.kiroignore`; any permission denial SHALL be logged and only that action skipped.
4. THE DECISION LOG SHALL reference the package-owned validation fixture and source citations SHALL use one DOI spelling.
5. THE SYSTEM SHALL remove only the named zero-caller aliases/functions, unused residue-template asset, orphan metadata, and empty top-level data scaffolds while retaining `funnel.run_funnel` for R7 delegation.
6. Package-data and resource tests SHALL enumerate the remaining reviewed runtime closure without changing binder artifacts, metrics, provenance hashes, or published README metrics.
7. Full pytest, Ruff, and whitespace validation SHALL pass before one R0 commit.
