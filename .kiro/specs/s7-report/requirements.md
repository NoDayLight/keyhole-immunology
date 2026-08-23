# S7 Requirements — Offline report and complete CLI

## User story

As a user, I need one deterministic offline HTML artifact that turns validated screening results into an inspectable visibility funnel, population atlas, molecular keyhole, and published-agreement view without silently recomputing science in the browser.

## EARS acceptance criteria

1. THE SYSTEM SHALL expose `validate`, `screen`, `explain`, and `open` CLI commands, with exactly one MAF or annotated VCF input for screening and strict supported-HLA normalization.
2. WHEN an input row lacks frozen canonical missense context, THE SYSTEM SHALL preserve it in explicit audit counts and SHALL NOT invent a sequence, candidate, or verdict.
3. THE SYSTEM SHALL batch mutant and wild-type predictions once per each of all 26 population-model alleles while patient conclusions use only user-supplied HLA alleles.
4. THE SYSTEM SHALL serialize one schema-v1 results document before rendering, with deterministic candidate keys, population evidence, literature evidence, methods, sources, and truth labels.
5. THE REPORT SHALL be one UTF-8 HTML file containing validated results JSON, all three untouched PDB texts, all candidate schematics, CSS, and seven local IIFE modules in dependency order.
6. THE REPORT SHALL use no external script/style, fetch, XHR, dynamic import, credentials, server, CDN, or runtime network request and SHALL enforce `connect-src 'none'`.
7. Embedded JSON SHALL escape HTML-significant characters and JavaScript line separators so data cannot terminate its script element.
8. WHEN `SOURCE_DATE_EPOCH` or an explicit creation timestamp is supplied, report generation SHALL be byte deterministic.
9. Every visual SHALL render serialized values only, retain measured-ML versus heuristic-approximation labels and citations, and preserve exact real/schematic molecular truth labels.
10. `keyhole open` SHALL open a local file URI in the default browser without starting a web server.
