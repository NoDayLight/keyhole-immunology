# R2 Design — 1HHK-backed candidate geometry

## Backbone mapping

`structure.py` owns a reviewed constant containing the nine chain-C Cα coordinates read directly from packaged PDB 1HHK. Nine-residue candidates map one-to-one. Ten-residue candidates use a deterministic piecewise-linear resampling rule: output point `i` maps to source index `i × 8/9`; floor/ceiling source points are interpolated by the fractional component. Thus output points 0 and 9 are the exact measured template termini and no extrapolation occurs.

The candidate sequence replaces residue identity only; it does not claim measured candidate coordinates. P2 (index 1) and PΩ (last index) receive `role: "anchor"`. Other backbone beads receive `role: "peptide"` and retain template-coordinate provenance metadata.

## Mutation marker

A separate side-chain endpoint shares the mutated residue number and carries `role: "mutation"`. A local frame is built from neighboring backbone vectors. The endpoint uses a fixed 109.5° ideal tetrahedral direction and a residue-specific idealized reach, with deterministic fallbacks for terminal/degenerate vectors. It is an illustrative marker, not a full atomistic rotamer. A bond joins Cα to the marker. This separate atom preserves both anchor and mutation roles when P2 or PΩ is mutated.

## Truth and rendering

Candidate payloads remain `kind: "schematic"` and use the exact persistent truth label `Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative`. Geometry detail distinguishes measured template backbone from candidate graft/interpolation/side-chain illustration. `scene.js` adds an anchor color before chain-role fallback; the existing mutation color and concentric glow remain.

Tests assert exact 9-mer coordinates, the 10-mer interpolation/termini rule, role semantics including an anchor mutation, deterministic ideal geometry, exact truth text, report embedding, and unchanged invalid-input behavior. Fixed-epoch SKCM JSON is compared byte-for-byte with the R1 oracle.
