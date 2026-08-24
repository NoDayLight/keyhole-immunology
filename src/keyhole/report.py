"""Deterministic self-contained offline HTML report assembly."""

# ruff: noqa: E501

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from html import escape
from pathlib import Path

from keyhole.assets import packaged_directory
from keyhole.contracts import PROJECT_SEED, SCHEMA_VERSION
from keyhole.data import pdb_path
from keyhole.schema import validate_results
from keyhole.structure import schematic_peptide_scene, structure_payload, summarize_pdb
from keyhole.vendor import vendored_runtime

SCRIPT_ORDER = (
    "figure.js",
    "projection.js",
    "pdb.js",
    "scene.js",
    "molecule3d.js",
    "globe.js",
    "charts.js",
    "funnel.js",
    "atlas.js",
    "theater.js",
    "main.js",
)
STYLESHEET = "style.css"


def web_root() -> Path:
    """Resolve wheel-installed browser assets without a network or build step."""

    candidate = packaged_directory("web")
    required = (*SCRIPT_ORDER, STYLESHEET)
    if not all((candidate / name).is_file() for name in required):
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


def assemble_report_scenes(results: Mapping[str, object]) -> dict[str, object]:
    """Assemble report-only structures and candidate scene payloads."""
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


NARRATIVE = (
    "Every cell displays fragments of its own proteins like ID cards for immune "
    "inspection; cancer corrupts some of those cards. KEYHOLE reads a real tumour file, "
    "scores every mutation-derived card it can defend, and shows which ones this set of "
    "HLA keyholes could actually display."
)

#: The narrative spine. Section indices exist only here and in the rail, never repeated
#: as a decorative kicker above each heading. The second field is the short rail
#: station label, kept brief so a navigation label never wraps; the third is the
#: section heading, which carries the full question.
SECTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "funnel",
        "Funnel",
        "Watch every candidate pass the inspection gates",
        "One particle is one real serialized candidate. Gate outcomes and rejection "
        "colours come only from the reason codes already computed in Python, so the "
        "animation can explain a rejection but can never decide one.",
    ),
    (
        "atlas",
        "Coverage",
        "Who else carries a compatible keyhole?",
        "Coverage is limited to the observed AFR, AMR, EAS, and EUR marginals in the "
        "frozen panel and to the 26-allele model set. Geography is presentation only, "
        "and ALL_OBSERVED is a cohort-weighted aggregate rather than a worldwide "
        "estimate.",
    ),
    (
        "structures",
        "Structures",
        "Look through the keyhole at measured coordinates",
        "Experimental scenes draw untouched packaged PDB coordinates. Candidate scenes "
        "keep the measured 1HHK backbone visibly separate from illustrative side-chain "
        "geometry.",
    ),
    (
        "literature",
        "Reality check",
        "Does this agree with published T-cell results?",
        "Published T-cell positivity and KEYHOLE visibility are different endpoints. "
        "Composition-preserving shuffled controls are synthetic decoys, never assayed "
        "negatives, specificity, or clinical validation.",
    ),
    (
        "methods",
        "Methods",
        "Every method label, source, and refusal",
        "Each number in this report carries the label of the method that produced it. "
        "This section lists those labels, the frozen sources behind them, and the "
        "claims KEYHOLE explicitly does not make.",
    ),
)


def _rail() -> str:
    """Render the narrative spine: one ordered station list, numbered exactly once.

    The report is a linear argument, so its navigation is a progress spine rather than a
    panel of links. It carries no logo and no provenance metadata: the masthead already
    identifies the report and the footer already states schema, seed, and offline status.
    """

    stations = [("overview", "Overview")]
    stations.extend((anchor, name) for anchor, name, _title, _caveat in SECTIONS)
    items = "".join(
        f'<li><a href="#{anchor}"><span class="n">{index:02d}</span>'
        f'<span class="t">{escape(name)}</span></a></li>'
        for index, (anchor, name) in enumerate(stations)
    )
    return (
        '<aside class="rail"><nav class="rail-nav" aria-label="Report sections">'
        '<span class="rail-spine" aria-hidden="true"><i class="rail-spine-fill"></i></span>'
        f'<ol class="rail-list">{items}</ol>'
        "</nav></aside>"
    )


def _sections() -> str:
    """Render each section shell with exactly one heading and one standing caveat."""

    return "".join(
        f'<section id="{anchor}" class="panel"><div class="wrap">'
        f'<header class="sec-head"><h2>{escape(title)}</h2>'
        f'<p class="caveat">{escape(caveat)}</p></header>'
        f'<div id="{anchor}-app"></div></div></section>'
        for anchor, _name, title, caveat in SECTIONS
    )


def _command_line(tumor: Mapping[str, object], allele_list: str) -> str:
    """Render the exact reproducing command with flags highlighted."""

    parts = [
        '<span class="prompt">$ </span>keyhole screen ',
        '<span class="flag">--maf</span> ',
        escape(str(tumor["input"])),
        ' <span class="flag">--hla</span> ',
        escape(f"\'{allele_list}\'"),
        ' <span class="flag">--report</span> report.html',
    ]
    return "".join(parts)


def _verdict_strip(counts: Mapping[str, int], total: int) -> str:
    cells = (
        ("VISIBLE_CLEAR", "visible-clear", "predicted visible, clearly", "clear"),
        ("VISIBLE_FAINT", "visible-faint", "predicted visible, faintly", "faint"),
        ("INVISIBLE", "invisible", "predicted not displayed", "invisible"),
    )
    share = total if total else 1
    return '<div class="verdict-strip">' + "".join(
        f'<div class="verdict-cell {css}"><strong>{counts[key]}</strong>'
        f"<span>{label}</span>"
        f'<em>{counts[key] * 100 // share}% of {total}</em></div>'
        for key, css, label, _short in cells
    ) + "</div>"


def _ledger(screening: Mapping[str, object], candidate_count: int) -> str:
    """Render the audit ladder from raw input rows down to scored candidates."""

    steps = (
        (
            int(screening["input_row_count"]),
            "rows read from the tumour file",
            f"{int(screening['ignored_class_count'])} ignored as silent or "
            "non-protein-changing classes",
        ),
        (
            int(screening["supported_change_count"]),
            "protein-changing mutations recognised",
            f"{int(screening['missing_canonical_context_count'])} dropped for having no "
            "frozen canonical protein context · "
            f"{int(screening['unsupported_frameshift_count'])} frameshifts disclosed "
            "rather than fabricated",
        ),
        (
            int(screening["screenable_variant_count"]),
            "variants carried into the funnel",
            "missense changes with a real reference protein sequence",
        ),
        (
            candidate_count,
            "candidate cards generated and fully scored",
            "every figure below is computed from exactly these peptides",
        ),
    )
    return '<ol class="ledger">' + "".join(
        f'<li><span class="num">{value}</span><span><b>{escape(label)}</b>'
        f"<small>{escape(detail)}</small></span></li>"
        for value, label, detail in steps
    ) + "</ol>"


def _render_report(
    document: Mapping[str, object], *, schema_validated: bool = False
) -> str:
    """Render a result into one network-free, sidecar-free HTML string."""

    results = dict(document) if schema_validated else validate_results(dict(document))
    scenes = assemble_report_scenes(results)
    root = web_root()
    runtime = vendored_runtime()
    stylesheet = (root / STYLESHEET).read_text(encoding="utf-8")
    scripts = "\n".join(
        f"/* inline:{name} */\n{(root / name).read_text(encoding='utf-8')}"
        for name in SCRIPT_ORDER
    )
    tumor = results["tumor"]
    assert isinstance(tumor, dict)
    screening = tumor["screening"]
    assert isinstance(screening, dict)
    mutations = results["mutations"]
    assert isinstance(mutations, list)
    mutation_count = len(mutations)
    candidate_count = sum(len(item["peptides"]) for item in mutations)
    verdict_counts: dict[str, int] = {
        "VISIBLE_CLEAR": 0,
        "VISIBLE_FAINT": 0,
        "INVISIBLE": 0,
    }
    for mutation in mutations:
        assert isinstance(mutation, dict)
        for peptide in mutation["peptides"]:
            assert isinstance(peptide, dict)
            verdict_counts[str(peptide["verdict"])] += 1
    alleles = results["alleles"]
    assert isinstance(alleles, list)
    allele_list = ",".join(str(allele) for allele in alleles)
    meta = results["meta"]
    assert isinstance(meta, dict)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="color-scheme" content="dark">
<meta name="robots" content="noindex">
<title>KEYHOLE — {escape(str(tumor['name']))}</title>
<style>{runtime.font_face_css}
{stylesheet}</style></head>
<body><a class="skip" href="#report">Skip to the report</a>
<div class="shell">{_rail()}
<div class="flow">
<header class="masthead" id="overview"><div class="wrap">
<div class="masthead-grid">
<div>
<p class="eyebrow">Tumour visibility report · {escape(str(tumor['name']))} · {escape(allele_list)}</p>
<h1>Which corrupted cards can this immune system actually see?</h1>
<p class="lede">{escape(NARRATIVE)}</p>
{_verdict_strip(verdict_counts, candidate_count)}
<div class="boundary"><strong>Truth boundary.</strong> Peptide–HLA binding is a measured-data machine-learning prediction. Antigen processing, foreignness, verdicts, and unphased population coverage are transparent heuristic approximations. Nothing here is a diagnosis, a treatment recommendation, or evidence of immunogenicity.</div>
<div class="boundary"><strong>Demonstration input.</strong> The HLA alleles above were supplied on the command line to exercise the models. They are not a patient genotype, not a clinical HLA typing result, and not linked to any individual.</div>
</div>
<div id="hero-app"></div>
</div>
<div class="provenance">
<div><p class="kicker">This file was computed, not authored</p>
<div class="command"><code>{_command_line(tumor, allele_list)}</code></div>
<p class="fig-status">Seed {PROJECT_SEED} · schema v{SCHEMA_VERSION} · set SOURCE_DATE_EPOCH to reproduce these bytes exactly.</p></div>
<div><p class="kicker">Audit trail from input rows to scored cards</p>{_ledger(screening, candidate_count)}</div>
</div>
</div></header>
<main id="report">{_sections()}</main>
<noscript><div class="wrap"><strong>JavaScript is disabled.</strong> This offline file still contains {mutation_count} reported mutations, {candidate_count} validated candidates, all three packaged PDB coordinate sets, the complete population and literature evidence, and every citation. Local JavaScript is required only to draw the interactive figures.</div></noscript>
<footer><div class="wrap">KEYHOLE schema v{SCHEMA_VERSION} · deterministic seed {PROJECT_SEED} · generated {escape(str(meta['created_utc']))} · one offline file, no network access after creation</div></footer>
</div></div>
<script type="application/json" id="keyhole-results">{_json_text(results)}</script>
<script type="application/json" id="keyhole-scenes">{_json_text(scenes)}</script>{runtime.banner}<script>{runtime.classic_prelude}</script>
<script type="module">{runtime.three_module}</script>
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
