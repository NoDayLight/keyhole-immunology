"""Deterministic self-contained offline HTML report assembly."""

# ruff: noqa: E501

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from html import escape
from pathlib import Path

from keyhole.assets import packaged_directory
from keyhole.bind import ALLELES
from keyhole.data import pdb_path
from keyhole.schema import Verdict, validate_results
from keyhole.structure import schematic_peptide_scene, structure_payload, summarize_pdb

SCRIPT_ORDER = (
    "projection.js",
    "pdb.js",
    "scene.js",
    "funnel.js",
    "atlas.js",
    "theater.js",
    "main.js",
)


def web_root() -> Path:
    """Resolve wheel-installed browser assets without a network or build step."""

    candidate = packaged_directory("web")
    if not all((candidate / name).is_file() for name in SCRIPT_ORDER):
        raise FileNotFoundError("KEYHOLE browser assets are incomplete")
    return candidate


def _json_text(value: object) -> str:
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _report_contract(
    document: Mapping[str, object], *, schema_validated: bool = False
) -> dict[str, object]:
    """Validate additive fields and cross-branch invariants consumed by browser modules."""

    results = dict(document) if schema_validated else validate_results(dict(document))

    def mapping(value: object, path: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValueError(f"{path}: report renderer requires an object")
        return value

    def sequence(value: object, path: str) -> list[object]:
        if not isinstance(value, list):
            raise ValueError(f"{path}: report renderer requires an array")
        return value

    def required(value: dict[str, object], names: set[str], path: str) -> None:
        missing = names - value.keys()
        if missing:
            raise ValueError(f"{path}: missing report fields: {', '.join(sorted(missing))}")

    def number(value: object, path: str, low: float, high: float) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{path}: report renderer requires a number")
        result = float(value)
        if not math.isfinite(result) or not low <= result <= high:
            raise ValueError(f"{path}: value must be finite and in [{low}, {high}]")
        return result

    def text(value: object, path: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{path}: report renderer requires non-empty text")
        return value

    alleles = sequence(results["alleles"], "results.alleles")
    if len(set(alleles)) != len(alleles) or any(allele not in ALLELES for allele in alleles):
        raise ValueError("results.alleles: report requires unique supported HLA-A/B alleles")
    candidate_keys: list[str] = []
    for mutation_index, mutation_value in enumerate(sequence(results["mutations"], "results.mutations")):
        mutation = mapping(mutation_value, f"results.mutations[{mutation_index}]")
        for peptide_index, peptide_value in enumerate(sequence(mutation["peptides"], "mutation.peptides")):
            path = f"results.mutations[{mutation_index}].peptides[{peptide_index}]"
            peptide = mapping(peptide_value, path)
            required(peptide, {"best_allele", "candidate_key"}, path)
            candidate_key = peptide["candidate_key"]
            if not isinstance(candidate_key, str) or not re.fullmatch(r"[A-Z]{9,10}(?:#[2-9][0-9]*)?", candidate_key):
                raise ValueError(f"{path}.candidate_key: invalid stable candidate key")
            if not candidate_key.startswith(str(peptide["seq"])):
                raise ValueError(f"{path}.candidate_key: must be derived from peptide sequence")
            bindings = mapping(mapping(peptide["scores"], f"{path}.scores")["binding"], f"{path}.scores.binding")
            if set(bindings) != set(alleles):
                raise ValueError(f"{path}.scores.binding: must match user-supplied alleles")
            if peptide["best_allele"] not in bindings:
                raise ValueError(f"{path}.best_allele: missing serialized binding evidence")
            best_allele = min(
                bindings,
                key=lambda allele: (
                    float(mapping(bindings[allele], f"{path}.scores.binding.{allele}")["rank"]),
                    float(mapping(bindings[allele], f"{path}.scores.binding.{allele}")["ic50"]),
                    allele,
                ),
            )
            if peptide["best_allele"] != best_allele:
                raise ValueError(f"{path}.best_allele: does not match serialized binding winner")
            candidate_keys.append(candidate_key)
    if len(candidate_keys) != len(set(candidate_keys)):
        raise ValueError("results.mutations: candidate keys must be globally unique")

    population = mapping(results["population"], "results.population")
    required(population, {"meta"}, "results.population")
    population_meta = mapping(population["meta"], "results.population.meta")
    required(population_meta, {"assumption", "draws", "method", "seed"}, "results.population.meta")
    text(population_meta["assumption"], "results.population.meta.assumption")
    text(population_meta["method"], "results.population.meta.method")
    number(population_meta["draws"], "results.population.meta.draws", 1.0, math.inf)
    number(population_meta["seed"], "results.population.meta.seed", 0.0, math.inf)
    coverage = mapping(population["per_candidate_coverage"], "results.population.per_candidate_coverage")
    matrix = mapping(population["peptide_allele_matrix"], "results.population.peptide_allele_matrix")
    if set(coverage) != set(candidate_keys) or set(matrix) != set(candidate_keys):
        raise ValueError("results.population: candidate keys must align with mutation peptides")
    population_names = {"AFR", "AMR", "EAS", "EUR", "ALL_OBSERVED"}
    for candidate_key in candidate_keys:
        values = mapping(coverage[candidate_key], f"coverage.{candidate_key}")
        if set(values) != population_names:
            raise ValueError(f"coverage.{candidate_key}: expected four cohorts and ALL_OBSERVED")
        for name, value in values.items():
            number(value, f"coverage.{candidate_key}.{name}", 0.0, 100.0)
        cells = mapping(matrix[candidate_key], f"matrix.{candidate_key}")
        if set(cells) != set(ALLELES):
            raise ValueError(f"matrix.{candidate_key}: expected all 26 modeled alleles")
        for allele, cell_value in cells.items():
            cell = mapping(cell_value, f"matrix.{candidate_key}.{allele}")
            required(cell, {"ic50", "method", "rank", "reason_codes", "verdict", "visible"}, f"matrix.{candidate_key}.{allele}")
            number(cell["ic50"], f"matrix.{candidate_key}.{allele}.ic50", 0.0, math.inf)
            number(cell["rank"], f"matrix.{candidate_key}.{allele}.rank", 0.0, 100.0)
            text(cell["method"], f"matrix.{candidate_key}.{allele}.method")
            sequence(cell["reason_codes"], f"matrix.{candidate_key}.{allele}.reason_codes")
            if not isinstance(cell["visible"], bool) or cell["verdict"] not in set(Verdict):
                raise ValueError(f"matrix.{candidate_key}.{allele}: invalid visibility evidence")

    literature = mapping(results["literature"], "results.literature")
    required(literature, {"meta"}, "results.literature")
    literature_meta = mapping(literature["meta"], "results.literature.meta")
    required(literature_meta, {"citations", "limitations"}, "results.literature.meta")
    citations = mapping(literature_meta["citations"], "results.literature.meta.citations")
    for name, citation in citations.items():
        text(name, "results.literature.meta.citations.<name>")
        text(citation, f"results.literature.meta.citations.{name}")
    limitations = sequence(literature_meta["limitations"], "results.literature.meta.limitations")
    for index, limitation in enumerate(limitations):
        text(limitation, f"results.literature.meta.limitations[{index}]")
    stats = mapping(literature["agreement_stats"], "results.literature.agreement_stats")
    count_names = {"matched_decoy_evaluable", "matched_decoy_rejected_count", "positive_visible_count", "published_positive_evaluable", "published_positive_total"}
    required(stats, count_names | {"synthetic_decoy_binding_roc_auc"}, "results.literature.agreement_stats")
    for name in count_names:
        number(stats[name], f"results.literature.agreement_stats.{name}", 0.0, math.inf)
    number(stats["synthetic_decoy_binding_roc_auc"], "results.literature.agreement_stats.synthetic_decoy_binding_roc_auc", 0.0, 1.0)
    for entry_index, entry_value in enumerate(sequence(literature["entries"], "results.literature.entries")):
        path = f"results.literature.entries[{entry_index}]"
        entry = mapping(entry_value, path)
        required(entry, {"allele", "binder_split", "binding_dataset_overlap", "evaluation_status", "external_facts", "matched_negative", "peptide", "prediction"}, path)
        for name in ("allele", "binder_split", "evaluation_status", "peptide"):
            text(entry[name], f"{path}.{name}")
        if not isinstance(entry["binding_dataset_overlap"], bool):
            raise ValueError(f"{path}.binding_dataset_overlap: report renderer requires a boolean")
        facts = mapping(entry["external_facts"], f"{path}.external_facts")
        required(facts, {"assay_result", "pmid", "reference_title"}, f"{path}.external_facts")
        for name in ("assay_result", "pmid", "reference_title"):
            text(facts[name], f"{path}.external_facts.{name}")
        prediction = mapping(entry["prediction"], f"{path}.prediction")
        required(prediction, {"plain_language", "verdict"}, f"{path}.prediction")
        text(prediction["plain_language"], f"{path}.prediction.plain_language")
        if prediction["verdict"] is not None:
            text(prediction["verdict"], f"{path}.prediction.verdict")
        negative = mapping(entry["matched_negative"], f"{path}.matched_negative")
        required(negative, {"peptide", "prediction"}, f"{path}.matched_negative")
        text(negative["peptide"], f"{path}.matched_negative.peptide")
        negative_prediction = mapping(negative["prediction"], f"{path}.matched_negative.prediction")
        required(negative_prediction, {"plain_language", "verdict"}, f"{path}.matched_negative.prediction")
        text(negative_prediction["plain_language"], f"{path}.matched_negative.prediction.plain_language")
        if negative_prediction["verdict"] is not None:
            text(negative_prediction["verdict"], f"{path}.matched_negative.prediction.verdict")
    return results


def _compact_pdb_text(pdb_text: str, display_chains: set[str]) -> str:
    """Serialize only browser-displayable PDB atoms and their retained explicit bonds."""

    source_lines = pdb_text.splitlines()
    candidates: list[tuple[str, tuple[str, ...], float, str]] = []
    grouped: dict[tuple[str, ...], list[tuple[float, str]]] = {}
    for line in source_lines:
        if line[:6].strip() != "ATOM":
            continue
        padded = line.ljust(80)
        chain = padded[21].strip() or "_"
        residue = padded[17:20].strip()
        supplied_element = padded[76:78].strip().upper()
        atom_letters = "".join(character for character in padded[12:16] if character.isalpha())
        element = supplied_element or (atom_letters[:1].upper() if atom_letters else "C")
        if chain not in display_chains or residue in {"HOH", "WAT"} or element == "H":
            continue
        occupancy = float(padded[54:60].strip() or "0")
        alternate = padded[16].strip()
        site = (
            chain,
            padded[22:26],
            padded[26],
            residue,
            padded[12:16].strip(),
        )
        candidates.append((padded, site, occupancy, alternate))
        grouped.setdefault(site, []).append((occupancy, alternate))

    displayed_sites: set[tuple[str, ...]] = set()
    for site, alternatives in grouped.items():
        blanks = [record for record in alternatives if not record[1]]
        selected = min(blanks or alternatives, key=lambda record: (-record[0], record[1] or " "))
        if selected[0] > 0:
            displayed_sites.add(site)

    atom_lines: list[str] = []
    retained_serials: set[int] = set()
    for padded, site, occupancy, _alternate in candidates:
        if site not in displayed_sites or occupancy <= 0:
            continue
        x = float(padded[30:38])
        y = float(padded[38:46])
        z = float(padded[46:54])
        if not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError("report PDB compaction encountered non-finite coordinates")
        retained_serials.add(int(padded[6:11]))
        atom_lines.append(
            f"{padded[:30]}{x:8.3f}{y:8.3f}{z:8.3f}{padded[54:80]}".rstrip()
        )

    conect_lines: list[str] = []
    for line in source_lines:
        if line[:6].strip() != "CONECT":
            continue
        serials = [
            int(line[offset : offset + 5])
            for offset in range(6, len(line), 5)
            if line[offset : offset + 5].strip()
        ]
        if not serials or serials[0] not in retained_serials:
            continue
        connected = [serial for serial in serials[1:] if serial in retained_serials]
        if connected:
            conect_lines.append(
                f"CONECT{serials[0]:5d}" + "".join(f"{serial:5d}" for serial in connected)
            )
    return "\n".join([*atom_lines, *conect_lines]) + "\n"


def _report_structure_payload(pdb_id: str) -> dict[str, object]:
    payload = structure_payload(pdb_id)
    raw_text = str(payload["pdb_text"])
    display_chains = {str(chain) for chain in payload["display_chains"]}
    compact_text = _compact_pdb_text(raw_text, display_chains)
    payload["source_pdb_bytes"] = len(raw_text.encode("utf-8"))
    payload["source_selected_atom_sites"] = summarize_pdb(pdb_path(pdb_id)).selected_atom_sites
    payload["embedded_pdb_bytes"] = len(compact_text.encode("utf-8"))
    payload["report_pdb_subset"] = (
        "display-chain positive-occupancy non-water non-hydrogen ATOM plus retained CONECT; "
        "coordinates serialized at 3 decimals"
    )
    payload["pdb_text"] = compact_text
    return payload


def _scene_envelope(results: Mapping[str, object]) -> dict[str, object]:
    structures = {
        pdb_id: _report_structure_payload(pdb_id) for pdb_id in ("1HHK", "3PWN", "1AO7")
    }
    schematics: dict[str, object] = {}
    mutations = results["mutations"]
    assert isinstance(mutations, list)
    for mutation_index, mutation in enumerate(mutations):
        assert isinstance(mutation, dict)
        peptides = mutation["peptides"]
        assert isinstance(peptides, list)
        for peptide_index, peptide in enumerate(peptides):
            assert isinstance(peptide, dict)
            schematics[f"{mutation_index}:{peptide_index}"] = schematic_peptide_scene(
                str(peptide["seq"]), int(peptide["position"])
            )
    return {"schematics": schematics, "structures": structures}


_STYLE = r"""
:root{color-scheme:dark;--ink:#eaf2f7;--muted:#aebdca;--panel:#101e2b;--line:#294052;--teal:#50bfca;--gold:#f3bf4d;--red:#ec6b76;--green:#67cf9a;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#07111b;color:var(--ink);line-height:1.55}a{color:#8cdce2}header,main,footer{width:min(1180px,calc(100% - 2rem));margin:auto}header{padding:3rem 0 2rem}.eyebrow,.method{font-size:.76rem;letter-spacing:.08em;text-transform:uppercase;color:var(--teal);font-weight:750}h1{font-size:clamp(2.6rem,7vw,5.4rem);line-height:.92;margin:.4rem 0 1rem;letter-spacing:-.05em}.lede{font-size:clamp(1.05rem,2.2vw,1.4rem);max-width:900px;color:#d7e4ec}.notice{border-left:4px solid var(--gold);background:#1b2430;padding:1rem 1.2rem;border-radius:.35rem;margin:1rem 0}.audit{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:.75rem}.stat,.card,section.panel{background:linear-gradient(145deg,#122332,#0d1a27);border:1px solid var(--line);border-radius:1rem;padding:1rem}.stat strong{display:block;font-size:1.8rem;color:var(--gold)}nav{position:sticky;top:0;z-index:20;background:#07111bef;backdrop-filter:blur(12px);border-block:1px solid var(--line)}nav ul{width:min(1180px,calc(100% - 2rem));margin:auto;padding:.7rem 0;display:flex;gap:1rem;list-style:none;overflow:auto}nav a{text-decoration:none;white-space:nowrap}main{display:grid;gap:1.25rem;padding:1.5rem 0 4rem}section.panel{scroll-margin-top:4rem}h2{font-size:clamp(1.5rem,3vw,2.3rem);margin:.1rem 0 .5rem}h3{margin-top:1.2rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:1rem}.badge,.scene-truth{display:inline-block;border:1px solid currentColor;border-radius:999px;padding:.25rem .58rem;font-size:.75rem;font-weight:750}.visible-clear{color:var(--green)}.visible-faint{color:var(--gold)}.invisible{color:var(--red)}button,select{background:#152b3c;color:var(--ink);border:1px solid #416078;border-radius:.45rem;padding:.55rem .7rem;font:inherit}button:focus-visible,select:focus-visible,[tabindex]:focus-visible,summary:focus-visible{outline:3px solid var(--gold);outline-offset:3px}.sequence{font:700 1.05rem ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em}.mutation-residue{color:#fff;background:#c72f45;border-radius:.18rem;padding:.05rem .18rem}.flow-svg,.atlas-svg,.keyhole-scene-svg{width:100%;height:auto;min-height:180px;border-radius:.7rem;background:#08131e}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.86rem}th,td{text-align:left;border-bottom:1px solid var(--line);padding:.48rem;vertical-align:top}th{color:#a9dce1}.score-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.55rem}.score-grid div{background:#0a1722;padding:.55rem;border-radius:.5rem}.keyhole-scene{margin-top:1rem}.keyhole-scene-canvas{display:block;max-width:100%;border-radius:.75rem;margin:.7rem 0}.scene-detail,.caveat,.scene-status{color:var(--muted);font-size:.9rem}.scene-controls{display:flex;flex-wrap:wrap;align-items:center;gap:.7rem}.scene-fallback{margin:.7rem 0}.scene-chain-legend{columns:2;padding-left:1.2rem}.matrix-cell.yes{color:var(--green)}.matrix-cell.no{color:#718496}.literature-card{border-top:3px solid var(--teal)}.limitations{color:var(--muted)}details{border:1px solid var(--line);border-radius:.65rem;padding:.65rem;margin:.6rem 0}summary{cursor:pointer;font-weight:700}footer{padding:2rem 0 4rem;color:var(--muted)}noscript{display:block;background:#3b1e25;padding:1rem}.fatal{border:2px solid var(--red);padding:1rem}.screen-reader{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}@media(max-width:650px){.scene-chain-legend{columns:1}.audit{grid-template-columns:repeat(2,1fr)}}@media print{body{background:#fff;color:#111}nav,button,.keyhole-scene-canvas{display:none!important}.card,section.panel{background:#fff;border-color:#bbb}.scene-fallback{display:block}.scene-fallback>div{display:block}.scene-truth{color:#111}}
"""


def _render_report(
    document: Mapping[str, object], *, schema_validated: bool = False
) -> str:
    """Render a result into one network-free, sidecar-free HTML string."""

    results = _report_contract(document, schema_validated=schema_validated)
    scenes = _scene_envelope(results)
    root = web_root()
    scripts = "\n".join(
        f"/* inline:{name} */\n{(root / name).read_text(encoding='utf-8')}"
        for name in SCRIPT_ORDER
    )
    tumor = results["tumor"]
    assert isinstance(tumor, dict)
    screening = tumor.get("screening", {})
    assert isinstance(screening, dict)
    mutation_count = len(results["mutations"])
    candidate_count = sum(len(item["peptides"]) for item in results["mutations"])
    audit_items = "".join(
        f'<div class="stat"><strong>{int(value)}</strong>{escape(key.replace("_", " "))}</div>'
        for key, value in sorted(screening.items())
    )
    narrative = (
        "Every cell displays fragments of its own proteins like ID cards for immune inspection; "
        "cancer corrupts some of those cards; KEYHOLE reads a real tumor's corrupted cards and "
        "reports—in plain language, real 3D molecular structures, and population-wide "
        "coverage—which ones the immune system can actually see."
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'">
<title>KEYHOLE — {escape(str(tumor['name']))}</title><style>{_STYLE}</style></head>
<body><header><p class="eyebrow">Cancer immunology, made inspectable</p><h1>PROJECT<br>KEYHOLE</h1><p class="lede">{escape(narrative)}</p>
<div class="notice"><strong>Truth boundary:</strong> binding is measured-data ML. Processing, foreignness, verdicts, and unphased population coverage are transparent heuristic approximations—not clinical recommendations.</div>
<div class="audit">{audit_items}<div class="stat"><strong>{mutation_count}</strong>reported mutations</div><div class="stat"><strong>{candidate_count}</strong>candidate cards</div></div></header>
<nav aria-label="Report sections"><ul><li><a href="#funnel">Visibility funnel</a></li><li><a href="#atlas">Population atlas</a></li><li><a href="#structures">Molecular keyhole</a></li><li><a href="#literature">Published panel</a></li><li><a href="#methods">Methods</a></li></ul></nav>
<main id="report"><section id="funnel" class="panel"><h2>Which corrupted cards get displayed?</h2><p class="caveat">Select a real mutation-derived peptide. Every stage below is rendered from validated results.json values.</p><div id="funnel-app"></div></section>
<section id="atlas" class="panel"><h2>Who carries a compatible keyhole?</h2><p class="caveat">Coverage is limited to AFR/AMR/EAS/EUR observed marginals and the frozen 26-allele model panel. ALL_OBSERVED is not a worldwide estimate.</p><div id="atlas-app"></div></section>
<section id="structures" class="panel"><h2>Look through the molecular keyhole</h2><p class="caveat">Real scenes use untouched experimental PDB coordinates. Candidate geometry is visibly separated as illustrative.</p><div id="structure-app" class="grid"></div></section>
<section id="literature" class="panel"><h2>Published-positive agreement panel</h2><p class="caveat">Published T-cell positivity and KEYHOLE visibility are different endpoints; synthetic controls are not assayed negatives.</p><div id="theater-app"></div></section>
<section id="methods" class="panel"><h2>Methods, citations, and limits</h2><div id="methods-app"></div></section>
<noscript><strong>JavaScript is disabled.</strong> This offline file still contains {mutation_count} mutations and {candidate_count} validated candidates, all three PDB coordinate files, and complete citations; local JavaScript is required only for interactive rendering.</noscript></main>
<footer>KEYHOLE schema v1 · deterministic seed 1729 · generated {escape(str(results['meta']['created_utc']))} · offline after creation</footer>
<script type="application/json" id="keyhole-results">{_json_text(results)}</script>
<script type="application/json" id="keyhole-scenes">{_json_text(scenes)}</script>
<script>{scripts}</script></body></html>"""


def render_report(document: Mapping[str, object]) -> str:
    """Validate and render one network-free, sidecar-free HTML string."""

    return _render_report(document)


def _write_validated_report(document: Mapping[str, object], path: str | Path) -> Path:
    """Write a pipeline-validated report while retaining additive contract checks."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        _render_report(document, schema_validated=True), encoding="utf-8"
    )
    return destination.resolve()


def write_report(document: Mapping[str, object], path: str | Path) -> Path:
    """Validate and write one standalone UTF-8 HTML report."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_report(document), encoding="utf-8")
    return destination.resolve()
