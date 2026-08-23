# S1 Requirements — Frozen real data and parsing

## User story

As a KEYHOLE user, I need the tool to operate offline on real, cited biological measurements and tumor variants so every downstream statement is traceable and reproducible.

## EARS acceptance criteria

1. THE SYSTEM SHALL freeze 50,000–100,000 measured IEDB MHC-I binding records for common HLA-A/B and retain peptide, allele, censor relation, and IC50.
2. THE SYSTEM SHALL freeze exactly 500,000 distinct canonical human 9-mers sampled from UniProt with seed 1729.
3. THE SYSTEM SHALL load observed HLA-A/B frequencies by available superpopulation and SHALL NOT impute an unavailable population.
4. THE SYSTEM SHALL freeze about ten published positive tumor peptide/HLA records with IEDB and PMID identifiers.
5. THE SYSTEM SHALL retain complete cBioPortal SKCM and PAAD mutation profiles plus deterministic 100-record MAF examples containing real processable driver anchors.
6. THE SYSTEM SHALL freeze two peptide-HLA crystal structures, a verified TCR-pMHC structure, and 20 CCD ideal residue templates with source metadata.
7. WHEN a valid MAF or annotated VCF is supplied, THE SYSTEM SHALL produce stable missense/frameshift variants and skip protein effects outside schema v1.
8. WHEN KRAS G12D, BRAF V600E, or TP53 R175H is requested, THE SYSTEM SHALL return the real genomic event and verified canonical UniProt context.
9. WHEN data are narrowed because a required source is unavailable, THE SYSTEM SHALL document the absent information and SHALL NOT invent or impute values.
