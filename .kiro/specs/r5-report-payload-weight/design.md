# R5 Design — Report-only PDB compaction

## Root cause and transform

`structure_payload()` continues to return untouched packaged PDB text. At `_scene_envelope`, report.py makes a new descriptor and compacts only its `pdb_text`. A fixed-column pass retains `ATOM` records only when their chain is in `display_chains`, occupancy is positive, residue is not water, and element is not hydrogen. It preserves all eligible alternate locations so `pdb.js::chooseConformers` behaves unchanged. Coordinates are parsed as finite floats and rewritten into columns 31–54 with `8.3f` formatting. Retained atom serials then filter/rebuild `CONECT` records; all other record types are omitted.

The report descriptor records the original byte count, original selected-site count from `summarize_pdb`, compact byte count, and an explicit subset description. `scene.js` uses `source_selected_atom_sites` for its existing legend sentence, preserving visible source accounting while the browser parser receives only the rendering subset.

## Regression evidence

Tests assert report payload record types, display chains, positive occupancy, non-water/non-hydrogen selection, coordinate fixed-column formatting, retained CONECT references, original package bytes/ignored records, deterministic compaction, and source-count metadata. The size envelope is updated only after measuring fixture and representative fixed-epoch reports; no padding is introduced. `docs/index.html` is regenerated from the real SKCM example with `SOURCE_DATE_EPOCH=1787529600`.

R5 intentionally changes report/Pages bytes but not results. Full tests, Ruff, JS syntax, diff checks, fixed-epoch JSON byte comparison, and package-original hash comparison close the boundary.
