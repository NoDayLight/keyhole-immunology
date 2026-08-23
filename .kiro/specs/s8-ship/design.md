# S8 Design — Package-owned offline release

## Resource closure

Reviewed runtime assets live under `src/keyhole/resources/{data,web,validation}` and are explicitly enumerated as setuptools package data. `assets.py` rejects absolute, parent-traversing, backslash, and root-escaping paths. `data.py` uses only an explicit `KEYHOLE_DATA` override or package-owned data; it never trusts the process current directory. Browser modules and the validation fixture are always package-owned.

Top-level `data/examples/` retains the two real 100-row demonstration MAFs and complete cBioPortal source archives, preserving the documented clone quickstart without bloating the wheel with unused mutation archives. The full provenance record ships in the wheel; the top-level source note links to it.

## Distribution proof

The release gate builds one wheel, inspects member names and exactly 26 NPZs, installs into a new Python 3.11 virtual environment, changes to an unrelated directory, unsets `KEYHOLE_DATA`, and invokes only the installed console script. It runs full metric reproduction and the real SKCM command, extracts and validates embedded JSON, checks script/PDB truth labels and network absence, checks the 2–6 MB envelope, and compares fixed-epoch output bytes with the source build.

## Judge-facing artifacts

`README.md` leads with a three-command path from clone to local report and then discloses input constraints, supported alleles, method labels, limitations, provenance, and release gates. `docs/index.html` is the fixed-epoch self-contained SKCM report and can be served directly as GitHub Pages without a build system. `docs/VIDEO.md` scripts a short demo that never presents heuristics, synthetic decoys, population assumptions, or schematic geometry as measured facts.
