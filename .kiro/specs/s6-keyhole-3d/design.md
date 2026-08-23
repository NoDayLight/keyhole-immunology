# S6 Design — KEYHOLE-3D

## Structural truth boundary

`structure.py` owns verified chain-role descriptors and deterministic candidate scene payloads. Experimental payloads inline untouched frozen PDB text plus citation metadata. Candidate payloads contain one schematic bead per residue and sequential links; they never claim atomic chemistry, folding, docking, or a predicted HLA pose.

The real structures are 1HHK (Tax–HLA-A2 pMHC, display A/B/C), 3PWN (HuD G2L–HLA-A2 pMHC, display A/B/C despite TCR-related keywords), and 1AO7 (Tax–HLA-A2 with TCR α/β, display A/B/C/D/E). Duplicate crystallographic pMHC copies in 1HHK/3PWN are not displayed by default.

## Browser modules

`pdb.js` is a pure fixed-column parser IIFE. It preserves raw coordinates, deterministically chooses one conformer per atom site, tracks residue identity as chain + residue number + insertion code, parses explicit CONECT links, and conservatively infers only intra-residue covalent links plus close sequential C–N peptide links.

The local projection engine rotates real xyz coordinates without a third-party dependency or build step. `scene.js` mounts an accessible canvas scene and an always-created reduced-detail SVG fallback. Pointer/keyboard controls mutate view state only; they never compute scientific scores. S7 will inline these modules and payloads into the final report.

## Performance and fallback

Canvas draws depth-sorted atom circles and bond segments from projected 3D coordinates. Default structure views omit waters, heteroatoms, hydrogens, zero-occupancy atoms, and chains outside `display_chains`, while parser metadata retains them. SVG renders Cα traces plus all peptide/schematic beads to limit DOM size. It remains in the document and is shown if canvas initialization or drawing fails.
