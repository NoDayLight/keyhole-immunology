# S6 Requirements — KEYHOLE-3D

## User story

As a user, I need to rotate and inspect real peptide–HLA/TCR atomic coordinates offline while never confusing an illustrative candidate layout with experimental geometry.

## EARS acceptance criteria

1. THE SYSTEM SHALL parse frozen legacy PDB text by fixed columns, including insertion codes, alternate locations, occupancy, HETATM, CONECT, TER, and first-model selection.
2. WHEN alternate atom locations exist, THE SYSTEM SHALL select blank location first, otherwise highest occupancy with lexical tie-breaking, and SHALL NOT draw duplicate conformers.
3. THE SYSTEM SHALL render the verified biological chains A/B/C for 1HHK and 3PWN and A/B/C/D/E for 1AO7 with explicit HLA, β2m, peptide, and TCR chain roles.
4. Every experimental scene SHALL visibly say exactly `Real crystal structure (PDB id)` and cite method, resolution, and source publication.
5. Candidate geometry SHALL be a deterministic residue-bead scene visibly labeled exactly `Schematic — data real, geometry illustrative` and SHALL state it is not measured, structure-predicted, or HLA-docked.
6. THE SYSTEM SHALL support pointer drag, wheel zoom, keyboard arrows, Home reset, a reset button, resize, and cleanup without any network or Node runtime.
7. A reduced-detail SVG molecular view with title, description, chain legend, and truth label SHALL always exist as fallback to canvas rendering.
8. Scene controls and status SHALL be keyboard reachable and accessibly named; canvas SHALL have an equivalent text/SVG representation.
9. Frozen structure integrity tests SHALL distinguish raw coordinates, selected atom sites, waters, heteroatoms, alternate conformers, residues, and insertion codes.
