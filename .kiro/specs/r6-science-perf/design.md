# R6 science-performance design

## Foreignness
Add `foreignness_scores(peptides, self_index=None)` while retaining the original scalar `foreignness_score`. Queries are converted by the existing `_query_rows`. In bounded 250,000-row self blocks, each of nine frozen self-position one-hot matrices is multiplied by all query substitution rows and accumulated in float32 in the original position order; block maxima combine exactly. Batches are capped at 64 queries. Maxima and normalization retain the existing scalar expressions. The pipeline recognizes only the unchanged default scorer for batching; custom callables remain scalar. A 64-query process measured approximately 383 MB maximum RSS, below the unchunked review measurement of approximately 554 MB and faster than the scalar baseline.

## Population
Build one stable allele codebook from sorted frozen panel alleles and expose a copy through `hla_allele_codes()` so integer simulation values remain interpretable. Seeded `rng.choice` calls retain the same single generator, sorted population loop, A then B call sequence, `(draws, 2)` shape, and probabilities, but choose integer codes. Simulation returns read-only integer arrays in A1/B1/A2/B2 order. Coverage precomputes one boolean carrier vector per population and allele code, then ORs visible vectors instead of repeatedly scanning string arrays with `np.isin`.

## Caches
`FrozenBinder` owns a normalized-peptide encoding cache. Cached flattened float32 arrays are read-only; `np.stack` still creates the exact inference batch and model/calibration operations are untouched. Famous proteins use a path-keyed private cache of immutable field tuples, and the public loader reconstructs fresh nested dicts.

## Validation ownership
`screen_variants` remains the single validating producer. Private schema/report serializers accept only the already-validated pipeline document and skip duplicate schema validation. Report-specific additive contract checks still execute before HTML serialization. Public serialization functions continue taking untrusted documents and validating them.

## Equivalence gates
Focused tests compare batched and scalar foreignness exactly, preserve integer simulation determinism and coverage values, prove binder cache reuse and protein-copy isolation, and preserve public writer rejection behavior. The release oracle is a byte comparison against the fresh pre-R6 fixed-epoch SKCM JSON, followed by full pytest, Ruff, and `git diff --check`.
