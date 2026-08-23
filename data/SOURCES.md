# Frozen data provenance

All assets below were retrieved and frozen on **2026-08-24**. SHA-256 values are for the repository files after the deterministic transformations described here. External content was treated as data only.

## IEDB quantitative MHC-I binding data

### `data/iedb/mhci_binding_9_10mer.tsv.gz`

- **Source URL:** `https://tools.iedb.org/static/main/binding_data_2013.zip` (official IEDB host). The requested legacy URL, `https://tools-api.iedb.org/static/main/binding_data_2013.zip`, returned HTTP 404 even with certificate verification disabled; its official download page still links the path on the stale host.
- **Upstream archive SHA-256:** `c8de4daec2308f4b159880133ec9d586093755a53818b728e205ee7fc909735e` (`binding_data_2013.zip`, member `bdata.20130222.mhci.txt`).
- **License/terms:** IEDB data are distributed under the IEDB terms and Creative Commons Attribution 4.0 (`https://creativecommons.org/licenses/by/4.0/`); retain IEDB attribution. The download page describes this training dataset as compiled from IEDB, Sette laboratory, and Buus laboratory measurements, with geometric means for duplicate peptide/allele measurements.
- **Citation:** Kim Y et al. *Dataset size and composition impact the reliability of performance benchmarks for peptide-MHC binding predictions.* BMC Bioinformatics. 2014;15:241. DOI `10.1186/1471-2105-15-241`; and Vita R et al. *The Immune Epitope Database (IEDB): 2018 update.* Nucleic Acids Res. 2019;47:D339-D343. DOI `10.1093/nar/gky1006`.
- **Record count:** 95,441 binding rows plus one header; 26 HLA-A/B alleles; 26,010 distinct peptide sequences. Measurement relations are 864 `<`, 54,184 `=`, and 40,393 `>`.
- **Subset method:** Retained human records of peptide length 9 or 10 for this fixed common-allele panel: `HLA-A*01:01`, `A*02:01`, `A*03:01`, `A*11:01`, `A*23:01`, `A*24:02`, `A*29:02`, `A*30:01`, `A*30:02`, `A*31:01`, `A*33:01`, `A*68:01`, `HLA-B*07:02`, `B*08:01`, `B*15:01`, `B*18:01`, `B*27:05`, `B*35:01`, `B*40:01`, `B*44:02`, `B*44:03`, `B*46:01`, `B*51:01`, `B*53:01`, `B*57:01`, and `B*58:01`. Rows are sorted by allele, length, peptide, inequality, and original measurement text. Original measured IC50 values and censoring inequalities are preserved; gzip uses compression level 9 and `mtime=0`.
- **SHA-256:** `13dc16c84e645540e18d2ca38dcfa88a5b01ff7393697dfabca6570c256a6479`.

## UniProt human self-peptidome

### `data/self_peptidome/up000005640_human_9mers.txt.gz`

- **Source URL:** `https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Eukaryota/UP000005640/UP000005640_9606.fasta.gz` (official UniProt FTP service over HTTPS).
- **Upstream archive SHA-256:** `cf49a88c4812dabbd934cb3e2e00b449e70375816e4d47cda7cc5b77b0754024`.
- **License/terms:** UniProt data are available under Creative Commons Attribution 4.0; see `https://www.uniprot.org/help/license`.
- **Citation:** The UniProt Consortium. *UniProt: the Universal Protein Knowledgebase in 2025.* Nucleic Acids Res. 2025. DOI `10.1093/nar/gkae1010`.
- **Record count:** Exactly 500,000 distinct canonical-amino-acid 9-mers, one peptide per line and no header. The source contained 20,652 FASTA records, 11,453,425 residues, and 10,418,589 distinct 9-mers containing only `ACDEFGHIKLMNPQRSTVWY`.
- **Subset method:** Enumerated all overlapping length-9 windows, discarded windows containing non-standard residues, deduplicated them, ordered the universe lexicographically, sampled 500,000 distinct indices with Python `random.Random(1729).sample(range(10418589), 500000)`, and emitted selected peptides in lexical order. Gzip uses compression level 9 and `mtime=0`.
- **SHA-256:** `d12fee3749f832b5055403b9a0162dc42f7dece52d0385f78af5dd8405799c43`.

## UniProt canonical proteins for mutation reference residues

### `data/residues/famous_proteins.json`

- **Source URLs:** Official UniProt canonical FASTA records `https://rest.uniprot.org/uniprotkb/P15056.fasta` (BRAF), `https://rest.uniprot.org/uniprotkb/P01116.fasta` (KRAS), and `https://rest.uniprot.org/uniprotkb/P04637.fasta` (TP53), retrieved 2026-08-24.
- **License/terms:** UniProt data are available under Creative Commons Attribution 4.0; see `https://www.uniprot.org/help/license`.
- **Citation:** The UniProt Consortium. *UniProt: the Universal Protein Knowledgebase in 2025.* Nucleic Acids Res. 2025. DOI `10.1093/nar/gkae1010`.
- **Record count:** Three canonical human protein records: P15056/BRAF (766 residues), P01116/KRAS (189 residues), and P04637/TP53 (393 residues).
- **Subset method:** Retrieved each accession from the official UniProt REST endpoint, removed only the FASTA header and line wrapping, sorted records by accession, and serialized indented JSON with sorted keys. Accession and `GN` header fields were checked, sequences were restricted to the 20 canonical amino-acid codes, and the mutation reference residues were verified directly as BRAF V600, KRAS G12, and TP53 R175.
- **SHA-256:** `21f38b47b76f756d7cfcbdd262398505dddc4392c490a3fb0d687568d13a0e45`.

## HLA-A/B population frequencies (documented narrowed subset)

### `data/hla_freq/1000g_hla_ab_two_field_frequencies.tsv`

- **Source URLs:** Published-study source typing `https://raw.githubusercontent.com/deboraycb/reliability_hla_1000g/ec555b4c62e183c0ae1e9ea73ef7ea06e7e38606/data/mhc.tab`; Phase I population panel `https://raw.githubusercontent.com/deboraycb/reliability_hla_1000g/ec555b4c62e183c0ae1e9ea73ef7ea06e7e38606/data/phase1_integrated_calls.20101123.ALL.panel`. Repository commit `ec555b4c62e183c0ae1e9ea73ef7ea06e7e38606`.
- **Upstream SHA-256:** `e140bc410b211782fd7c05807a9f186c98ab6a550903579edd722aba419538b7` (`mhc.tab`) and `012a6ef25498101b392c942e8d3e42bab1ee3c23573002f88c5f95dff026c829` (population panel).
- **License/terms:** The PLOS ONE article is Creative Commons Attribution. The authors' public GitHub repository does not declare a separate data/software license; this snapshot therefore records provenance and attribution and does not assert broader rights beyond the underlying public sources.
- **Citation:** Gourraud P-A et al. *HLA Diversity in the 1000 Genomes Dataset.* PLOS ONE. 2014;9:e97282. DOI `10.1371/journal.pone.0097282`; Brandt DYC et al. *Mapping Bias Overestimates Reference Allele Frequencies at the HLA Genes in the 1000 Genomes Project Phase I Data.* G3. 2015;5:931-941. DOI `10.1534/g3.115.016949`.
- **Record count:** 230 allele-frequency rows from 878 direct sample-ID matches: AFR 176 individuals, AMR 170, EAS 260, EUR 272. Resolved HLA-A/HLA-B allele-copy denominators are AFR 205/218, AMR 72/165, EAS 181/254, and EUR 66/159.
- **Subset method:** Applied the requested narrowing rule because no defensible published five-superpopulation HLA table with SAS was available from an official endpoint. Joined source typings to the Phase I panel by exact sample ID; mapped its historical `ASN` code to `EAS`; retained AFR/AMR/EAS/EUR and HLA-A/B only. SAS is absent because this Phase I panel predates the SAS superpopulation. Each slash-delimited ambiguous genotype was reduced to two fields only when every listed alternative had the same first two fields; otherwise that allele copy was excluded rather than guessed. Frequencies are observed allele count divided by resolved allele copies within population and locus, rounded to 10 decimal places. No frequencies were invented or imputed.
- **SHA-256:** `4462a03cc538ab5dc62d4cf07ee1b8c3a544bf962b2f06e8af6f5180aabdd033`.

## Published tumor epitope/HLA records

### `data/literature/tumor_epitopes.tsv`

- **Source URL:** IEDB IQ-API `https://query-api.iedb.org/api/v1/tcell_export`, queried for the listed peptide sequences and projected fields for epitope, positive T-cell assay, MHC restriction, disease context, PMID, and reference title.
- **License/terms:** IEDB data are distributed under Creative Commons Attribution 4.0 with IEDB and original-publication attribution.
- **Citation:** The ten source PMIDs are `22021080`, `23926201`, `11684128`, `27959684`, `10759561`, `23032742`, `25003657`, `22565484`, `29386195`, and `17644531`; full titles and stable IEDB epitope/assay IRIs are retained in the file. IEDB database citation: Vita R et al., DOI `10.1093/nar/gky1006`.
- **Record count:** Exactly 10 distinct peptide/HLA records, each backed by a positive IEDB T-cell assay and PMID.
- **Subset method:** Used a fixed candidate set of well-published tumor-associated or tumor-neoantigen peptides, retained only exact two-field `HLA-A*02:01`, `HLA-A*01:01`, or `HLA-C*08:02` restrictions with an IEDB result beginning `Positive`, selected the smallest numeric assay ID for each preselected peptide/PMID pair, and sorted by peptide. The KRAS G12D record is the real `HLA-C*08:02`-restricted `GADGVGKSAL` record; no allele or reference values were inferred.
- **SHA-256:** `d03fe7e8388267a3f1c6549903946d461330b086b8e5d2bc0b210938687ae7d0`.

## TCGA PanCancer Atlas variants via cBioPortal

The API operation was `POST https://www.cbioportal.org/api/molecular-profiles/{profile}/mutations/fetch?projection=DETAILED&pageSize=10000000&pageNumber=0` with JSON body `{"sampleListId":"{study}_sequenced"}` and `Accept: application/json`.

- **License/terms:** These are public TCGA open-access study data delivered by cBioPortal. cBioPortal states that individual study data remain subject to the terms and citation requirements of their original publications; follow NCI Genomic Data Commons/TCGA data-use policies (`https://gdc.cancer.gov/access-data/data-access-processes-and-tools`).
- **Citations:** Hoadley KA et al. *Cell-of-Origin Patterns Dominate the Molecular Classification of 10,000 Tumors from 33 Types of Cancer.* Cell. 2018;173:291-304.e6. DOI `10.1016/j.cell.2018.03.022`; Cerami E et al. *The cBio Cancer Genomics Portal.* Cancer Discov. 2012;2:401-404. DOI `10.1158/2159-8290.CD-12-0095`; Gao J et al. *Integrative analysis of complex cancer genomics and clinical profiles using the cBioPortal.* Sci Signal. 2013;6:pl1. DOI `10.1126/scisignal.2004088`.

### `data/examples/tcga_skcm_mutations.json.gz`

- **Source identifiers:** Study `skcm_tcga_pan_can_atlas_2018`, profile `skcm_tcga_pan_can_atlas_2018_mutations`, sample list `skcm_tcga_pan_can_atlas_2018_sequenced`.
- **Record count:** 325,843 detailed mutation records.
- **Subset method:** Complete API response; no record filtering. Original JSON bytes were gzip-compressed at level 9 with `mtime=0`.
- **SHA-256:** `6914c99d2763e210990bbf089b31102c0060fc3a93ad1c668064e73db40c0428`.

### `data/examples/tcga_skcm.maf`

- **Source identifiers:** Same SKCM profile above.
- **Record count:** Exactly 100 distinct mutation rows plus MAF version comment and header: one BRAF V600E anchor, the sole TP53 R175H profile record, and 98 background rows.
- **Subset method:** Sorted the full response by sample ID, chromosome, start/end, reference/alternate allele, Entrez ID, and protein change. For each requested event, selected the first matching API row in that stable order (BRAF V600E sample `TCGA-BF-A1PU-01`; TP53 R175H sample `TCGA-D3-A5GR-06`), excluded all BRAF V600E and TP53 R175H event rows from the background universe, sampled 98 distinct background row indices without replacement using `random.Random(1729)`, then stable-sorted the combined 100 rows for output. Only API-provided fields were mapped to MAF columns; no values or rows were invented.
- **SHA-256:** `cd21d90139821da4d587fef023be163d25416da8b19d09dd03e2aea2f7ee098d`.

### `data/examples/tcga_paad_mutations.json.gz`

- **Source identifiers:** Study `paad_tcga_pan_can_atlas_2018`, profile `paad_tcga_pan_can_atlas_2018_mutations`, sample list `paad_tcga_pan_can_atlas_2018_sequenced`.
- **Record count:** 20,703 detailed mutation records.
- **Subset method:** Complete API response; no record filtering. Original JSON bytes were gzip-compressed at level 9 with `mtime=0`.
- **SHA-256:** `d369f83face38020c118f1f3c7034d47c96216442fc86cec5f597315e488f4d7`.

### `data/examples/tcga_paad.maf`

- **Source identifiers:** Same PAAD profile above.
- **Record count:** Exactly 100 distinct mutation rows plus MAF version comment and header: one KRAS G12D anchor and 99 background rows.
- **Subset method:** Applied the same stable ordering, selected the first KRAS G12D API row in that order (sample `TCGA-2J-AABF-01`), excluded all KRAS G12D event rows from the background universe, sampled 99 distinct background row indices without replacement with an independent `random.Random(1729)`, then stable-sorted the combined 100 rows for output. Only API-provided fields were written; no values or rows were invented.
- **SHA-256:** `215439b427bcc8c4e7c466b66a38fbee75918ec7263952ca4f26cbbce1d2191d`.

## RCSB PDB structures

- **License/terms:** RCSB PDB/wwPDB structure data are dedicated to the public domain under CC0 1.0; see `https://www.rcsb.org/pages/policies`.
- **Repository citation:** Berman HM et al. *The Protein Data Bank.* Nucleic Acids Res. 2000;28:235-242. DOI `10.1093/nar/28.1.235`.

### `data/pdb/1HHK.pdb`

- **Source URL:** `https://files.rcsb.org/download/1HHK.pdb`.
- **Citation:** Madden DR, Garboczi DN, Wiley DC. *The antigenic identity of peptide-MHC complexes...* Cell. 1993. DOI `10.1016/0092-8674(93)90490-H`; PMID `7694806`.
- **Record count:** 6,965 PDB text lines; 6,322 `ATOM`/`HETATM` coordinate records.
- **Subset method:** Unmodified RCSB PDB text.
- **SHA-256:** `9511878db0222f69eaaddad7219b97a4f70bc1495ca0e8f27cf78e49141521a7`.

### `data/pdb/3PWN.pdb`

- **Source URL:** `https://files.rcsb.org/download/3PWN.pdb`.
- **Citation:** Borbulevych OY, Piepenbrink KH, Baker BM. *Conformational Melding Permits a Conserved Binding Geometry in TCR Recognition of Foreign and Self Molecular Mimics.* J Immunol. 2011. DOI `10.4049/jimmunol.1003150`; PMID `21282516`.
- **Record count:** 14,391 PDB text lines; 7,215 `ATOM`/`HETATM` coordinate records.
- **Subset method:** Unmodified RCSB PDB text.
- **SHA-256:** `d6057150db7ed1db03df3d50b6ae4f2ccc97d2819f97274388b03529a4fc88cb`.

### `data/pdb/1AO7.pdb`

- **Source URL:** `https://files.rcsb.org/download/1AO7.pdb`.
- **Citation:** Garboczi DN et al. *Structure of the complex between human T-cell receptor, viral peptide and HLA-A2.* Nature. 1996. DOI `10.1038/384134a0`; PMID `8906788`.
- **Record count:** 6,532 PDB text lines; 5,711 `ATOM`/`HETATM` coordinate records.
- **Subset method:** Unmodified RCSB PDB text. `1AO7` deliberately replaces suggested `1AKJ`: RCSB identifies `1AKJ` as an HLA-A2/CD8 co-receptor complex, whereas `1AO7` is a verified TCR-Tax peptide-HLA-A*02:01 complex.
- **SHA-256:** `67a5ffb179bc5bad13710984293b1fa543c027473531c558ce6ea42ea545131c`.

### `data/pdb/rcsb_entry_metadata.json`

- **Source URLs:** `https://data.rcsb.org/rest/v1/core/entry/1HHK`, `https://data.rcsb.org/rest/v1/core/entry/3PWN`, and `https://data.rcsb.org/rest/v1/core/entry/1AO7`.
- **Citation/license:** Same entry citations and CC0 terms above.
- **Record count:** Three complete RCSB core-entry metadata objects.
- **Subset method:** Parsed the three API responses, sorted objects by `rcsb_id`, and serialized as indented JSON with keys sorted; no metadata fields were removed.
- **SHA-256:** `5125a056579c1a0a2a6ec90ba2987df656ea369e024cd6fcf65f1a70aa3d4c35`.

## RCSB CCD ideal amino-acid coordinates

### `data/residues/standard_amino_acid_ideal_coordinates.json`

- **Source URLs:** Official CCD component files at `https://files.rcsb.org/ligands/download/{COMP}.cif` for `ALA`, `ARG`, `ASN`, `ASP`, `CYS`, `GLN`, `GLU`, `GLY`, `HIS`, `ILE`, `LEU`, `LYS`, `MET`, `PHE`, `PRO`, `SER`, `THR`, `TRP`, `TYR`, and `VAL`. The official complete CCD archive was also checked at `https://files.wwpdb.org/pub/pdb/data/monomers/components.cif.gz`.
- **License/terms:** wwPDB/RCSB CCD data are CC0 1.0/public domain under the RCSB policies.
- **Citation:** Westbrook JD et al. *The Chemical Component Dictionary: complete descriptions of constituent molecules in experimentally determined 3D macromolecules in the Protein Data Bank.* Bioinformatics. 2015;31:1274-1278. DOI `10.1093/bioinformatics/btu789`.
- **Record count:** 20 standard amino-acid components and 387 atom templates, including hydrogen and terminal atoms present in CCD.
- **Subset method:** Parsed each `_chem_comp_atom` loop, retained atom ID, element, formal charge, aromatic/leaving/backbone flags, and the official `pdbx_model_Cartn_{x,y,z}_ideal` coordinates; mapped the 20 canonical one-letter codes; sorted components and atoms; serialized as one indented, key-sorted JSON file. Coordinates were not numerically altered.
- **SHA-256:** `ff776e56b0a9174482113972a0934aa712c5111a05cfba55ab82b7eba3039f1a`.

## Retrieval and transformation commands

Representative retrieval commands (all run on 2026-08-24):

```sh
# The requested IEDB host failed with HTTP 404 despite the documented certificate workaround.
curl -k -L --fail -o /tmp/binding_data_2013.zip https://tools-api.iedb.org/static/main/binding_data_2013.zip
# Official alternate IEDB host used for the frozen asset.
curl -L --fail -o /tmp/binding_data_2013.zip https://tools.iedb.org/static/main/binding_data_2013.zip

curl -L --fail -o /tmp/UP000005640_9606.fasta.gz \
  https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Eukaryota/UP000005640/UP000005640_9606.fasta.gz

curl -L --fail -H 'Content-Type: application/json' \
  -d '{"sampleListId":"skcm_tcga_pan_can_atlas_2018_sequenced"}' \
  'https://www.cbioportal.org/api/molecular-profiles/skcm_tcga_pan_can_atlas_2018_mutations/mutations/fetch?projection=DETAILED&pageSize=10000000&pageNumber=0'
# PAAD used the analogous paad_tcga_pan_can_atlas_2018 profile and sample-list IDs.

curl -L --fail -o 1HHK.pdb https://files.rcsb.org/download/1HHK.pdb
curl -L --fail -o 3PWN.pdb https://files.rcsb.org/download/3PWN.pdb
curl -L --fail -o 1AO7.pdb https://files.rcsb.org/download/1AO7.pdb
```

Transformations used only Python 3 standard-library facilities (`csv`, `gzip`, `json`, `random`, `sqlite3`, and `shlex`). Deterministic gzip files have zero timestamps. Validation re-opened every output, checked schema/content constraints, record and distinct counts, population-frequency sums, RCSB IDs, CCD component/atom counts, gzip timestamps, and every SHA-256 listed above.
