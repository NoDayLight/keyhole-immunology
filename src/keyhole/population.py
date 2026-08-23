"""Seeded Monte Carlo HLA coverage from frozen observed frequencies."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from keyhole.data import FrequencyRecord, load_hla_frequencies, normalize_allele
from keyhole.funnel import FunnelResult, differential_agretopicity, verdict_engine
from keyhole.schema import PROJECT_SEED, Verdict

DEFAULT_DRAWS = 100_000
METHOD_LABEL = "heuristic approximation"
ASSUMPTION = (
    "Observed marginal HLA-A/B frequencies; A-B linkage equilibrium and Hardy-Weinberg "
    "sampling assumed because phased haplotypes are unavailable."
)


@dataclass(frozen=True, slots=True)
class FrequencyPanel:
    """One observed superpopulation/locus categorical allele distribution."""

    superpopulation: str
    locus: str
    alleles: tuple[str, ...]
    probabilities: tuple[float, ...]
    individuals: int


def frequency_panels(
    records: Sequence[FrequencyRecord] | None = None,
) -> tuple[FrequencyPanel, ...]:
    """Group frozen observed frequencies and correct only decimal-rounding drift."""

    source = load_hla_frequencies() if records is None else records
    grouped: dict[tuple[str, str], list[FrequencyRecord]] = defaultdict(list)
    for record in source:
        grouped[(record.superpopulation, record.locus)].append(record)
    panels: list[FrequencyPanel] = []
    for (population, locus), rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: row.allele)
        frequencies = np.asarray([row.frequency for row in ordered], dtype=np.float64)
        total = float(frequencies.sum())
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"{population} {locus} observed frequencies sum to {total}, not 1")
        probabilities = frequencies / total
        panels.append(
            FrequencyPanel(
                superpopulation=population,
                locus=locus,
                alleles=tuple(row.allele for row in ordered),
                probabilities=tuple(float(value) for value in probabilities),
                individuals=max(row.individuals for row in ordered),
            )
        )
    populations = {panel.superpopulation for panel in panels}
    if populations != {"AFR", "AMR", "EAS", "EUR"}:
        raise ValueError("frozen HLA panel must preserve its explicit AFR/AMR/EAS/EUR scope")
    missing_loci = any(
        {panel.locus for panel in panels if panel.superpopulation == population}
        != {"HLA-A", "HLA-B"}
        for population in populations
    )
    if missing_loci:
        raise ValueError("every observed population requires both HLA-A and HLA-B panels")
    return tuple(panels)


def simulate_haplotypes(
    *, draws: int = DEFAULT_DRAWS, seed: int = PROJECT_SEED
) -> dict[str, np.ndarray]:
    """Draw two independent A-B haplotypes per person from real marginals.

    Columns are A1, B1, A2, B2. Independence is a labeled heuristic because
    the frozen published source does not provide phased A-B haplotypes.
    """

    if draws <= 0:
        raise ValueError("Monte Carlo draws must be positive")
    rng = np.random.default_rng(seed)
    by_population: dict[str, dict[str, FrequencyPanel]] = defaultdict(dict)
    for panel in frequency_panels():
        by_population[panel.superpopulation][panel.locus] = panel
    simulations: dict[str, np.ndarray] = {}
    for population in sorted(by_population):
        a_panel = by_population[population]["HLA-A"]
        b_panel = by_population[population]["HLA-B"]
        a = rng.choice(a_panel.alleles, size=(draws, 2), p=a_panel.probabilities)
        b = rng.choice(b_panel.alleles, size=(draws, 2), p=b_panel.probabilities)
        genotypes = np.empty((draws, 4), dtype="<U12")
        genotypes[:, 0] = a[:, 0]
        genotypes[:, 1] = b[:, 0]
        genotypes[:, 2] = a[:, 1]
        genotypes[:, 3] = b[:, 1]
        genotypes.setflags(write=False)
        simulations[population] = genotypes
    return simulations


def _is_visible(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        return bool(value.get("visible", False))
    raise TypeError("matrix cells must be booleans or objects with a visible field")


def coverage_from_matrix(
    matrix: Mapping[str, Mapping[str, object]],
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = PROJECT_SEED,
) -> dict[str, dict[str, float]]:
    """Estimate per-candidate population coverage from a peptide×allele matrix."""

    genotypes = simulate_haplotypes(draws=draws, seed=seed)
    sample_sizes = {
        panel.superpopulation: panel.individuals
        for panel in frequency_panels()
        if panel.locus == "HLA-A"
    }
    output: dict[str, dict[str, float]] = {}
    for candidate, allele_values in matrix.items():
        visible = {
            normalize_allele(allele)
            for allele, value in allele_values.items()
            if _is_visible(value)
        }
        coverage: dict[str, float] = {}
        for population, simulated in genotypes.items():
            fraction = float(np.isin(simulated, tuple(sorted(visible))).any(axis=1).mean())
            coverage[population] = round(100.0 * fraction, 4)
        total_people = sum(sample_sizes.values())
        overall = sum(coverage[pop] * sample_sizes[pop] for pop in coverage) / total_people
        coverage["ALL_OBSERVED"] = round(overall, 4)
        output[candidate] = coverage
    return output


def peptide_allele_matrix(
    results: Sequence[FunnelResult],
) -> dict[str, dict[str, dict[str, object]]]:
    """Build schema-ready per-allele evidence, evaluating visibility per allele."""

    matrix: dict[str, dict[str, dict[str, object]]] = {}
    occurrences: dict[str, int] = defaultdict(int)
    for result in results:
        occurrences[result.pair.seq] += 1
        occurrence = occurrences[result.pair.seq]
        candidate = result.pair.seq if occurrence == 1 else f"{result.pair.seq}#{occurrence}"
        allele_cells: dict[str, dict[str, object]] = {}
        for allele, prediction in sorted(result.binding.items()):
            wild_type = result.wt_binding.get(allele)
            agretopicity = differential_agretopicity(prediction, wild_type)
            verdict, reasons, _language = verdict_engine(
                cleavage=result.cleavage,
                tap=result.tap,
                binding_rank=prediction.percentile_rank,
                binding_ic50=prediction.ic50_nm,
                foreignness=result.foreignness,
                agretopicity=agretopicity,
                has_wt=wild_type is not None,
            )
            allele_cells[allele] = {
                "ic50": prediction.ic50_nm,
                "rank": prediction.percentile_rank,
                "visible": verdict is not Verdict.INVISIBLE,
                "verdict": verdict.value,
                "reason_codes": list(reasons),
                "method": "measured ML + heuristic approximation",
            }
        matrix[candidate] = allele_cells
    return matrix


def population_summary(
    results: Sequence[FunnelResult],
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = PROJECT_SEED,
) -> dict[str, object]:
    """Build the complete schema-v1 population branch from funnel outputs."""

    matrix = peptide_allele_matrix(results)
    return {
        "per_candidate_coverage": coverage_from_matrix(matrix, draws=draws, seed=seed),
        "peptide_allele_matrix": matrix,
        "meta": {
            "assumption": ASSUMPTION,
            "draws": draws,
            "method": METHOD_LABEL,
            "seed": seed,
            "superpopulations": ["AFR", "AMR", "EAS", "EUR"],
        },
    }
