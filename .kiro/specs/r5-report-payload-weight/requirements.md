# R5 Requirements — Report payload weight

## Bug

The standalone report embeds 2.35 MB of raw PDB text, including headers, REMARKs, HETATM/waters, non-display chains, and 6,408 3PWN ANISOU records that the browser renderer ignores. This inflates transfer/storage and parse input without changing the displayed molecule.

## Acceptance criteria

1. Report assembly SHALL compact only the embedded copy of each PDB; package-owned original PDB files SHALL remain byte-unchanged.
2. The embedded PDB text SHALL contain only display-chain, positive-occupancy, non-water, non-hydrogen `ATOM` records and retained-serial `CONECT` records.
3. Embedded x/y/z fixed-column fields SHALL be serialized at exactly three decimal places while preserving their numeric coordinate values.
4. Alternate-location records SHALL remain available for the existing deterministic browser conformer selection; no displayed atom or bond behavior SHALL change.
5. The scene legend SHALL retain the original source selected-atom-site count rather than reporting the compact subset as if it were the source.
6. The standalone HTML size test SHALL use a measured honest post-compaction range and SHALL continue to forbid network paths and padding.
7. `docs/index.html` SHALL be regenerated through the fixed-epoch SKCM command.
8. Scientific `results.json`, package PDBs, frozen hashes, binder artifacts/metrics, and published scientific README metrics SHALL remain unchanged.
9. Full pytest, Ruff, JavaScript syntax, diff, deterministic result, and Pages checks SHALL pass before one R5 commit.
