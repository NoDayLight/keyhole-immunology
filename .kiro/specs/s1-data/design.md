# S1 Design — Frozen real data and parsing

## Data boundary

`data/SOURCES.md` is the human-readable provenance manifest. Every frozen asset records an official/published endpoint, retrieval date, reuse terms, citation, deterministic subset method, record count, and SHA-256. Compressed text uses gzip with `mtime=0`. Browser code cannot access these files directly; later pipeline modules convert them to schema-v1 results.

`data.py` provides immutable typed records and streaming loaders. Resolution order is `KEYHOLE_DATA`, repository working directory, then the package's source-checkout parent. It never downloads data. HLA names normalize from `HLA-A*02:01` to contract form `A*02:01` without changing specificity.

## Variant parsing

`parse.py` uses one immutable `Variant` shape. MAF accepts schema-supported missense and frameshift classifications and deliberately ignores other classifications because the frozen contract cannot represent their peptide source. Annotated VCF accepts explicit `GENE`/`HGVSP` fields or standard `ANN`. Famous driver aliases resolve against real TCGA PanCancer coordinates and are enriched from frozen canonical UniProt sequences; a reference-residue mismatch is fatal.

## Explicit limitation

The published HLA Phase-I source yields AFR/AMR/EAS/EUR but predates SAS. Ambiguous genotype copies are excluded, not guessed. Population output must preserve that absence. This is logged under law 7.
