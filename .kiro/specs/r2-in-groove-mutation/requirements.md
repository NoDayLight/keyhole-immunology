# R2 Requirements — In-groove mutation

## User story

As a report reader, I need each candidate peptide scene to follow a real peptide-in-HLA backbone trace while remaining explicit that candidate identity and mutation side-chain geometry are illustrative.

## EARS acceptance criteria

1. A 9-mer candidate SHALL use the nine exact 1HHK chain-C Cα coordinates in residue order.
2. A 10-mer candidate SHALL deterministically interpolate ten ordered points at source index `i × 8/9`, preserving both 1HHK termini exactly.
3. THE CANDIDATE SHALL be grafted into the 1HHK peptide coordinate frame with P2 and PΩ backbone atoms tagged `role: "anchor"`.
4. THE MUTATED RESIDUE SHALL include an idealized local-backbone-frame side-chain endpoint tagged `role: "mutation"`, including when the mutated residue is itself an anchor.
5. EVERY candidate scene SHALL display exactly `Real backbone (PDB 1HHK) · mutated side chain ideal geometry — illustrative`.
6. THE SCENE DETAIL SHALL disclose that only the template backbone is experimentally measured and that candidate identity, interpolation, and side-chain placement are illustrative rather than docking or structure prediction.
7. `scene.js` SHALL color anchors distinctly while retaining the R1 mutation glow.
8. THE schema and scientific `results.json` SHALL remain unchanged; only the report scene payload and rendering SHALL change.
9. Full pytest, Ruff, JavaScript syntax, diff, and fixed-epoch byte-identity checks SHALL pass before one R2 commit.
