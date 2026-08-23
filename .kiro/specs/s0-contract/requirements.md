# S0 Requirements — Direct execution and frozen contract

## User story

As a KEYHOLE contributor, I need a deterministic, validated pipeline-to-renderer contract and complete repository skeleton so every later feature can land without silently changing scientific meaning.

## EARS acceptance criteria

1. WHEN the sample result fixture is loaded, THE SYSTEM SHALL validate schema version 1 and all required contract branches.
2. WHEN any schema-v1 artifact is written twice, THE SYSTEM SHALL produce byte-identical canonical JSON.
3. WHEN the seed or schema version differs, THE SYSTEM SHALL reject the artifact with a path-specific error.
4. THE sample fixture SHALL contain three real-format mutations and all three verdict values.
5. WHEN Python source is changed, THE repository hook SHALL run Ruff and fail-fast tests.
6. WHEN an agent run ends, THE repository hook SHALL run the full suite and report smoke command.
