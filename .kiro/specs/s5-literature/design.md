# S5 Design — Published agreement panel

## Evaluation

The ten real positive IEDB records are publication-centered entries. Allele-independent S3 processing and foreignness heuristics run for every peptide and control. For the nine A*01:01/A*02:01 records, the S2 binder predicts only the published restriction and S3's fixed verdict engine evaluates visibility without a wild-type comparison. The real KRAS G12D/HLA-C*08:02 record remains present but binding and verdict are null because S2 intentionally has no HLA-C model.

## Controls

Each positive receives a local SHA-256-derived seed-1729 shuffle preserving peptide length and residue multiset. Controls cannot collide with a positive or earlier control. These sequences are synthetic composition-preserving decoys, not experimentally observed negatives. Statistics therefore call their behavior separation/rejection, never specificity or clinical validation.

## Statistics and provenance

Published-positive agreement is the fraction of nine evaluable positives receiving either visible verdict. The unsupported record is a third state, not a model error. Separate statistics report decoy rejection, positive-vs-decoy percentile-rank wins, and rank ROC AUC. Each entry discloses whether its peptide/restriction appears in S2's measured affinity source and its global peptide split. External publication facts remain verbatim and carry IEDB plus method citations.
