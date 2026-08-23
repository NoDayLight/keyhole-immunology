# S2 Design — Candidate peptides and binding ML

## Candidate generation

`PeptidePair` carries mutant sequence, position-matched wild type, zero-based changed-residue index, zero-based protein start, and schema source. Missense generation slides all valid 9- and 10-residue windows over the mutation. Frameshift generation replaces sequence at the affected residue with a caller-supplied translated stream, truncates at the first `*`, and rejects missing translation. Input proteins and products are restricted to the 20 canonical amino acids.

## Encoding and model

Canonical amino-acid order is fixed in the model metadata. Each residue is its BLOSUM62 substitution-score row plus the peptide-length channel. A 10-mer maps to nine positions as residues 1–4, mean(residues 5–6), residues 7–10. The required PyTorch MLP is `Linear(189,128) → ReLU → Linear(128,64) → ReLU → Linear(64,1)`. Output is log10(IC50 nM), clipped only when converted to a positive physical-scale estimate.

BLOSUM62 citation: Henikoff S, Henikoff JG. *Amino acid substitution matrices from protein blocks.* PNAS. 1992;89:10915–10919. DOI `10.1073/pnas.89.22.10915`.

## Training, calibration, and validation

`sha256("1729:" + peptide)` assigns 80% train, 10% validation, 10% held-out test globally. Models use deterministic CPU operations and fixed initialization/order. The loss is MSE on log10 of the reported IEDB numeric affinity; inequality boundaries are not relabeled as exact measurements in output or documentation.

Percentile rank compares predicted IC50 with a fixed, seed-defined self-peptidome calibration sample for that allele; lower is stronger. Held-out Spearman uses average ranks, and ROC AUC uses the 500 nM measured-binding threshold. Safe NPZ stores arrays only; JSON stores architecture, source citations, split rules, training wall time, and real metrics. Validation loads weights, reconstructs held-out rows, checks split disjointness, and recomputes metrics without network or retraining.
