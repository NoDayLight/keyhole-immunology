"""Deterministic allele-specific peptide--HLA binding models.

The frozen models use measured IEDB values. Censored rows are trained as their
reported boundary values; this is an explicit approximation, not a claim that
those bounds are exact measurements.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
import time
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from keyhole.assets import packaged_directory
from keyhole.contracts import (
    PROJECT_SEED,
    SUPPORTED_ALLELES,
    canonical_peptide,
    normalize_allele,
)
from keyhole.data import BindingRecord, data_root, iter_binding_records, iter_self_peptides

AA_ORDER = "ARNDCQEGHILKMFPSTWYV"
ALLELES = SUPPORTED_ALLELES
ARTIFACT_DIRECTORY = "iedb/binder"
MODEL_CARD_NAME = "model_card.json"
METRICS_NAME = "metrics.json"
CALIBRATION_SIZE = 10_000
DEFAULT_EPOCHS = 24
DEFAULT_LEARNING_RATE = 0.003
BINDER_THRESHOLD_NM = 500.0

# Henikoff & Henikoff BLOSUM62 in its conventional 20-residue order above.
BLOSUM62 = np.asarray(
    [
        [4, -1, -2, -2, 0, -1, -1, 0, -2, -1, -1, -1, -1, -2, -1, 1, 0, -3, -2, 0],
        [-1, 5, 0, -2, -3, 1, 0, -2, 0, -3, -2, 2, -1, -3, -2, -1, -1, -3, -2, -3],
        [-2, 0, 6, 1, -3, 0, 0, 0, 1, -3, -3, 0, -2, -3, -2, 1, 0, -4, -2, -3],
        [-2, -2, 1, 6, -3, 0, 2, -1, -1, -3, -4, -1, -3, -3, -1, 0, -1, -4, -3, -3],
        [0, -3, -3, -3, 9, -3, -4, -3, -3, -1, -1, -3, -1, -2, -3, -1, -1, -2, -2, -1],
        [-1, 1, 0, 0, -3, 5, 2, -2, 0, -3, -2, 1, 0, -3, -1, 0, -1, -2, -1, -2],
        [-1, 0, 0, 2, -4, 2, 5, -2, 0, -3, -3, 1, -2, -3, -1, 0, -1, -3, -2, -2],
        [0, -2, 0, -1, -3, -2, -2, 6, -2, -4, -4, -2, -3, -3, -2, 0, -2, -2, -3, -3],
        [-2, 0, 1, -1, -3, 0, 0, -2, 8, -3, -3, -1, -2, -1, -2, -1, -2, -2, 2, -3],
        [-1, -3, -3, -3, -1, -3, -3, -4, -3, 4, 2, -3, 1, 0, -3, -2, -1, -3, -1, 3],
        [-1, -2, -3, -4, -1, -2, -3, -4, -3, 2, 4, -2, 2, 0, -3, -2, -1, -2, -1, 1],
        [-1, 2, 0, -1, -3, 1, 1, -2, -1, -3, -2, 5, -1, -3, -1, 0, -1, -3, -2, -2],
        [-1, -1, -2, -3, -1, 0, -2, -3, -2, 1, 2, -1, 5, 0, -2, -1, -1, -1, -1, 1],
        [-2, -3, -3, -3, -2, -3, -3, -3, -1, 0, 0, -3, 0, 6, -4, -2, -2, 1, 3, -1],
        [-1, -2, -2, -1, -3, -1, -1, -2, -2, -3, -3, -1, -2, -4, 7, -1, -1, -4, -3, -2],
        [1, -1, 1, 0, -1, 0, 0, 0, -1, -2, -2, 0, -1, -2, -1, 4, 1, -3, -2, -2],
        [0, -1, 0, -1, -1, -1, -1, -2, -2, -1, -1, -1, -1, -2, -1, 1, 5, -2, -2, 0],
        [-3, -3, -4, -4, -2, -2, -3, -2, -2, -3, -2, -3, -1, 1, -4, -3, -2, 11, 2, -3],
        [-2, -2, -2, -3, -2, -1, -2, -3, 2, -1, -1, -2, -1, 3, -3, -2, -2, 2, 7, -1],
        [0, -3, -3, -3, -1, -2, -2, -3, -3, 3, 1, -2, 1, -1, -2, -2, 0, -3, -1, 4],
    ],
    dtype=np.float32,
)
_AA_TO_INDEX = {amino_acid: index for index, amino_acid in enumerate(AA_ORDER)}
_EXPECTED_ARRAYS = {
    "linear1_weight": (128, 189),
    "linear1_bias": (128,),
    "linear2_weight": (64, 128),
    "linear2_bias": (64,),
    "linear3_weight": (1, 64),
    "linear3_bias": (1,),
    "calibration_ic50_nm": (CALIBRATION_SIZE,),
}


@dataclass(frozen=True, slots=True)
class BindingPrediction:
    """One positive physical-scale prediction and its lower-is-better rank."""

    allele: str
    peptide: str
    ic50_nm: float
    percentile_rank: float

    @property
    def ic50(self) -> float:
        """Schema-compatible IC50 alias."""

        return self.ic50_nm

    @property
    def rank(self) -> float:
        """Schema-compatible percentile-rank alias."""

        return self.percentile_rank


class BindingMLP(nn.Module):
    """The frozen 189 -> 128 -> 64 -> 1 allele-specific architecture."""

    def __init__(self) -> None:
        super().__init__()
        self.flatten = nn.Flatten(start_dim=1)
        self.linear1 = nn.Linear(189, 128)
        self.relu1 = nn.ReLU()
        self.linear2 = nn.Linear(128, 64)
        self.relu2 = nn.ReLU()
        self.linear3 = nn.Linear(64, 1)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """Predict log10 IC50 from flattened 9 by 21 features."""

        hidden = self.relu1(self.linear1(self.flatten(features)))
        hidden = self.relu2(self.linear2(hidden))
        return self.linear3(hidden)


def _validate_peptide(peptide: str) -> str:
    return canonical_peptide(peptide, label="binding peptide")


def encode_peptide(peptide: str) -> np.ndarray:
    """Encode a 9/10-mer as a fixed ``(9, 21)`` float32 BLOSUM62 tensor.

    Ten-mers preserve both termini by mean-pooling residue vectors 5 and 6
    (one-based) into slot 5. The final channel is zero for 9-mers and one for
    10-mers at every output position.
    """

    peptide = _validate_peptide(peptide)
    residue_rows = BLOSUM62[[ _AA_TO_INDEX[residue] for residue in peptide]]
    if len(peptide) == 10:
        residue_rows = np.concatenate(
            (residue_rows[:4], residue_rows[4:6].mean(axis=0, keepdims=True), residue_rows[6:])
        )
    length_channel = np.full((9, 1), float(len(peptide) == 10), dtype=np.float32)
    encoded = np.concatenate((residue_rows, length_channel), axis=1)
    if encoded.shape != (9, 21):
        raise RuntimeError("internal encoding shape violation")
    return np.ascontiguousarray(encoded, dtype=np.float32)


def assign_split(peptide: str, seed: int = PROJECT_SEED) -> str:
    """Assign a peptide globally to train/validation/test using an 80/10/10 hash."""

    peptide = _validate_peptide(peptide)
    digest = hashlib.sha256(
        f"{seed}:{peptide}".encode("ascii"), usedforsecurity=False
    ).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10_000
    if bucket < 8_000:
        return "train"
    if bucket < 9_000:
        return "validation"
    return "test"


def _normalize_supported_allele(allele: str) -> str:
    if not isinstance(allele, str):
        raise TypeError("allele must be a string")
    normalized = normalize_allele(allele)
    if normalized not in ALLELES:
        raise ValueError(f"unsupported allele: {allele!r}")
    return normalized


def _validated_records() -> list[BindingRecord]:
    records: list[BindingRecord] = []
    seen_alleles: set[str] = set()
    for record in iter_binding_records():
        allele = _normalize_supported_allele(record.allele)
        peptide = _validate_peptide(record.peptide)
        if record.inequality not in {"<", "=", ">"}:
            raise ValueError(f"invalid IEDB measurement inequality: {record.inequality!r}")
        if not math.isfinite(record.ic50_nm) or record.ic50_nm <= 0:
            raise ValueError("IEDB IC50 values must be finite and positive")
        records.append(BindingRecord(allele, peptide, record.ic50_nm, record.inequality))
        seen_alleles.add(allele)
    if seen_alleles != set(ALLELES):
        raise ValueError("IEDB allele panel does not match the frozen 26-allele contract")
    if not records:
        raise ValueError("IEDB binding dataset is empty")
    return records


def _configure_deterministic_torch() -> None:
    torch.manual_seed(PROJECT_SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def _allele_seed(allele: str) -> int:
    digest = hashlib.sha256(
        f"{PROJECT_SEED}:model:{allele}".encode("ascii"), usedforsecurity=False
    ).digest()
    return int.from_bytes(digest[:4], "big")


def _encode_cache(records: Iterable[BindingRecord]) -> dict[str, np.ndarray]:
    peptides = {record.peptide for record in records}
    return {peptide: encode_peptide(peptide).reshape(189) for peptide in peptides}


def _arrays_for_records(
    records: Sequence[BindingRecord], cache: Mapping[str, np.ndarray]
) -> tuple[np.ndarray, np.ndarray]:
    rows = [cache[record.peptide] for record in records]
    features = np.stack(rows).astype(np.float32, copy=False)
    targets = np.log10(np.asarray([record.ic50_nm for record in records], dtype=np.float32))
    return features, targets


def _train_one_model(
    allele: str,
    records: Sequence[BindingRecord],
    cache: Mapping[str, np.ndarray],
    *,
    epochs: int,
    learning_rate: float,
) -> BindingMLP:
    train_records = [record for record in records if assign_split(record.peptide) == "train"]
    if not train_records:
        raise ValueError(f"no training rows for {allele}")
    features, targets = _arrays_for_records(train_records, cache)
    model_seed = _allele_seed(allele)
    torch.manual_seed(model_seed)
    model = BindingMLP().cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_function = nn.MSELoss()
    generator = np.random.default_rng(model_seed)
    model.train()
    for _ in range(epochs):
        for start in range(0, len(features), 512):
            # A fresh deterministic permutation each epoch avoids source-order bias.
            if start == 0:
                order = generator.permutation(len(features))
            indices = order[start : start + 512]
            batch_features = torch.from_numpy(features[indices])
            batch_targets = torch.from_numpy(targets[indices])
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(batch_features).squeeze(1), batch_targets)
            loss.backward()
            optimizer.step()
    model.eval()
    return model


def _predict_log10(model: BindingMLP, features: np.ndarray) -> np.ndarray:
    predictions: list[np.ndarray] = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(features), 2_048):
            batch = torch.from_numpy(np.ascontiguousarray(features[start : start + 2_048]))
            predictions.append(model(batch).squeeze(1).cpu().numpy().astype(np.float64))
    return np.concatenate(predictions) if predictions else np.empty(0, dtype=np.float64)


def _physical_ic50(log10_values: np.ndarray) -> np.ndarray:
    # Clipping occurs only at the physical-scale conversion boundary.
    return np.power(10.0, np.clip(log10_values, -12.0, 12.0))


def _average_ranks(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return ranks


def spearman_correlation(observed: Sequence[float], predicted: Sequence[float]) -> float:
    """Compute Spearman correlation with average tie ranks, without SciPy."""

    observed_array = np.asarray(observed, dtype=np.float64)
    predicted_array = np.asarray(predicted, dtype=np.float64)
    if observed_array.shape != predicted_array.shape or observed_array.ndim != 1:
        raise ValueError("Spearman inputs must be equal-length one-dimensional arrays")
    if len(observed_array) < 2:
        raise ValueError("Spearman correlation requires at least two observations")
    observed_rank = _average_ranks(observed_array)
    predicted_rank = _average_ranks(predicted_array)
    observed_centered = observed_rank - observed_rank.mean()
    predicted_centered = predicted_rank - predicted_rank.mean()
    denominator = math.sqrt(
        float(np.dot(observed_centered, observed_centered))
        * float(np.dot(predicted_centered, predicted_centered))
    )
    if denominator == 0:
        raise ValueError("Spearman correlation is undefined for a constant input")
    return float(np.dot(observed_centered, predicted_centered) / denominator)


def roc_auc(labels: Sequence[bool], scores: Sequence[float]) -> float:
    """Compute binary ROC AUC from average ranks; larger scores mean positive."""

    label_array = np.asarray(labels, dtype=np.bool_)
    score_array = np.asarray(scores, dtype=np.float64)
    if label_array.shape != score_array.shape or label_array.ndim != 1:
        raise ValueError("ROC AUC inputs must be equal-length one-dimensional arrays")
    positives = int(label_array.sum())
    negatives = len(label_array) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("ROC AUC requires both positive and negative examples")
    ranks = _average_ranks(score_array)
    positive_rank_sum = float(ranks[label_array].sum())
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def _known_binder_label(record: BindingRecord) -> bool | None:
    """Return a threshold label only when the measured relation establishes it."""

    if record.inequality == "=":
        return record.ic50_nm <= BINDER_THRESHOLD_NM
    if record.inequality == "<" and record.ic50_nm <= BINDER_THRESHOLD_NM:
        return True
    if record.inequality == ">" and record.ic50_nm >= BINDER_THRESHOLD_NM:
        return False
    return None


def _heldout_metrics(
    models: Mapping[str, BindingMLP],
    records: Sequence[BindingRecord],
    cache: Mapping[str, np.ndarray],
) -> dict[str, object]:
    per_allele: dict[str, dict[str, float | int]] = {}
    aggregate_observed: list[float] = []
    aggregate_predicted: list[float] = []
    aggregate_roc_labels: list[bool] = []
    aggregate_roc_scores: list[float] = []
    aggregate_indeterminate = 0
    for allele in ALLELES:
        test_records = [
            record
            for record in records
            if record.allele == allele and assign_split(record.peptide) == "test"
        ]
        features, _ = _arrays_for_records(test_records, cache)
        predicted = _physical_ic50(_predict_log10(models[allele], features))
        observed = np.asarray([record.ic50_nm for record in test_records], dtype=np.float64)
        known_labels: list[bool] = []
        known_scores: list[float] = []
        for record, score in zip(test_records, -predicted, strict=True):
            label = _known_binder_label(record)
            if label is not None:
                known_labels.append(label)
                known_scores.append(float(score))
        indeterminate = len(test_records) - len(known_labels)
        spearman = spearman_correlation(observed, predicted)
        auc = roc_auc(known_labels, known_scores)
        if not math.isfinite(spearman) or not math.isfinite(auc):
            raise ValueError(f"non-finite held-out metric for {allele}")
        per_allele[allele] = {
            "roc_auc_500nm": auc,
            "roc_evaluable_rows": len(known_labels),
            "roc_indeterminate_rows": indeterminate,
            "spearman": spearman,
            "test_rows": len(test_records),
        }
        aggregate_observed.extend(observed.tolist())
        aggregate_predicted.extend(predicted.tolist())
        aggregate_roc_labels.extend(known_labels)
        aggregate_roc_scores.extend(known_scores)
        aggregate_indeterminate += indeterminate
    aggregate_observed_array = np.asarray(aggregate_observed, dtype=np.float64)
    aggregate_predicted_array = np.asarray(aggregate_predicted, dtype=np.float64)
    return {
        "aggregate": {
            "macro_roc_auc_500nm": float(
                np.mean([metrics["roc_auc_500nm"] for metrics in per_allele.values()])
            ),
            "macro_spearman": float(
                np.mean([metrics["spearman"] for metrics in per_allele.values()])
            ),
            "pooled_roc_auc_500nm": roc_auc(aggregate_roc_labels, aggregate_roc_scores),
            "pooled_spearman": spearman_correlation(
                aggregate_observed_array, aggregate_predicted_array
            ),
            "roc_evaluable_rows": len(aggregate_roc_labels),
            "roc_indeterminate_rows": aggregate_indeterminate,
            "test_rows": len(aggregate_observed),
        },
        "binder_threshold_nm": BINDER_THRESHOLD_NM,
        "per_allele": per_allele,
    }


def _calibration_peptides(size: int) -> list[str]:
    if size != CALIBRATION_SIZE:
        raise ValueError(f"calibration size is frozen at {CALIBRATION_SIZE}")
    selected_indices = set(random.Random(PROJECT_SEED).sample(range(500_000), size))
    selected: list[str] = []
    observed_count = 0
    for observed_count, peptide in enumerate(iter_self_peptides(), start=1):
        if observed_count - 1 in selected_indices:
            selected.append(_validate_peptide(peptide))
    if observed_count != 500_000 or len(selected) != size:
        raise ValueError("self-peptidome snapshot does not match its frozen 500,000-row contract")
    return selected


def _model_arrays(model: BindingMLP, calibration: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "linear1_weight": model.linear1.weight.detach().cpu().numpy().astype(np.float32),
        "linear1_bias": model.linear1.bias.detach().cpu().numpy().astype(np.float32),
        "linear2_weight": model.linear2.weight.detach().cpu().numpy().astype(np.float32),
        "linear2_bias": model.linear2.bias.detach().cpu().numpy().astype(np.float32),
        "linear3_weight": model.linear3.weight.detach().cpu().numpy().astype(np.float32),
        "linear3_bias": model.linear3.bias.detach().cpu().numpy().astype(np.float32),
        "calibration_ic50_nm": np.sort(calibration.astype(np.float32)),
    }


def _write_deterministic_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(
                info,
                buffer.getvalue(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_filename(allele: str) -> str:
    return allele.replace("*", "_").replace(":", "_") + ".npz"


def train_binder(
    output_dir: str | Path,
    *,
    epochs: int = DEFAULT_EPOCHS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
) -> dict[str, object]:
    """Train all 26 models into an explicit writable artifact directory."""

    if epochs <= 0:
        raise ValueError("epochs must be positive")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be finite and positive")
    destination = Path(output_dir).expanduser().resolve()
    frozen_data = packaged_directory("data").resolve()
    if destination == frozen_data or frozen_data in destination.parents:
        raise ValueError("training output cannot target installed frozen resources")
    start_time = time.perf_counter()
    _configure_deterministic_torch()
    records = _validated_records()
    cache = _encode_cache(records)
    by_allele: dict[str, list[BindingRecord]] = defaultdict(list)
    for record in records:
        by_allele[record.allele].append(record)
    models: dict[str, BindingMLP] = {}
    for allele in ALLELES:
        models[allele] = _train_one_model(
            allele,
            by_allele[allele],
            cache,
            epochs=epochs,
            learning_rate=learning_rate,
        )
    metrics = _heldout_metrics(models, records, cache)
    calibration_peptides = _calibration_peptides(CALIBRATION_SIZE)
    calibration_features = np.stack(
        [encode_peptide(peptide).reshape(189) for peptide in calibration_peptides]
    ).astype(np.float32, copy=False)
    artifact_hashes: dict[str, str] = {}
    for allele in ALLELES:
        calibration = _physical_ic50(_predict_log10(models[allele], calibration_features))
        filename = _artifact_filename(allele)
        path = destination / filename
        _write_deterministic_npz(path, _model_arrays(models[allele], calibration))
        artifact_hashes[filename] = _sha256_file(path)
    elapsed = time.perf_counter() - start_time
    metrics_document = {
        **metrics,
        "evaluation": "frozen global peptide-level held-out test split",
        "training_wall_seconds": elapsed,
    }
    _write_json(destination / METRICS_NAME, metrics_document)
    artifact_hashes[METRICS_NAME] = _sha256_file(destination / METRICS_NAME)
    inequality_counts = Counter(record.inequality for record in records)
    model_card = {
        "alleles": list(ALLELES),
        "architecture": [
            "Flatten(9x21)",
            "Linear(189,128)",
            "ReLU",
            "Linear(128,64)",
            "ReLU",
            "Linear(64,1)",
        ],
        "artifact_sha256": artifact_hashes,
        "blosum62": {
            "amino_acid_order": AA_ORDER,
            "citation": "Henikoff S, Henikoff JG. PNAS (1992). DOI 10.1073/pnas.89.22.10915",
        },
        "calibration": {
            "interpretation": (
                "percent of fixed self predictions at or below candidate IC50; lower is better"
            ),
            "sample_size": CALIBRATION_SIZE,
            "sampling": (
                f"random.Random({PROJECT_SEED}).sample(range(500000), 10000), "
                "sorted by source order"
            ),
            "source": f"frozen seed-{PROJECT_SEED} UniProt human self-peptidome sample",
        },
        "censoring": {
            "approximation": (
                "IEDB < and > rows are optimized as their observed reported censor-bound values "
                "with ordinary MSE; they are not asserted to be exact measurements"
            ),
            "measurement_inequality_counts": dict(sorted(inequality_counts.items())),
            "roc_handling": (
                "ROC uses a censored row only when its relation and bound establish its side of "
                "the 500 nM threshold; threshold-indeterminate rows are excluded from ROC only"
            ),
        },
        "dataset": {
            "citation": (
                "Kim Y et al. BMC Bioinformatics (2014), DOI 10.1186/1471-2105-15-241; "
                "Vita R et al. Nucleic Acids Res. (2019), DOI 10.1093/nar/gky1006"
            ),
            "name": "IEDB quantitative MHC-I binding data, frozen 9/10-mer HLA-A/B subset",
            "rows": len(records),
        },
        "encoding": (
            "20 BLOSUM62 score channels plus a constant 9mer=0/10mer=1 channel; "
            "10mer residue vectors 5 and 6 are mean-pooled into center slot 5"
        ),
        "format_version": 1,
        "output": "log10 IC50 nM; clipping only while converting to positive physical IC50",
        "seed": PROJECT_SEED,
        "split": {
            "assignment": (
                f"first 8 SHA256 bytes of '{PROJECT_SEED}:'+peptide modulo 10000"
            ),
            "fractions": {"test": 0.1, "train": 0.8, "validation": 0.1},
            "scope": "global peptide identity before allele grouping",
            "validation_usage": (
                "Reserved by deterministic assignment but unused for training, model "
                "selection, early stopping, hyperparameter tuning, calibration, or "
                "reported test metrics."
            ),
        },
        "training": {
            "device": "cpu",
            "deterministic_algorithms": True,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "loss": "MSE on log10 observed IC50/censor-bound nM",
            "optimizer": "Adam",
            "wall_seconds": elapsed,
        },
    }
    _write_json(destination / MODEL_CARD_NAME, model_card)
    return {"metrics": metrics_document, "model_card": model_card}


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError(f"missing or implausibly large binder JSON artifact: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"binder JSON artifact must contain an object: {path}")
    return value


def _load_npz_arrays(path: Path) -> dict[str, np.ndarray]:
    expected_members = {f"{name}.npy" for name in _EXPECTED_ARRAYS}
    if not path.is_file() or path.stat().st_size > 5_000_000:
        raise ValueError(f"missing or implausibly large binder model artifact: {path}")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if (
            {member.filename for member in members} != expected_members
            or any(member.is_dir() or member.flag_bits & 1 for member in members)
            or sum(member.file_size for member in members) > 2_000_000
        ):
            raise ValueError(f"unsafe or unexpected NPZ contents: {path}")
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    if set(arrays) != set(_EXPECTED_ARRAYS):
        raise ValueError(f"unexpected arrays in binder model artifact: {path}")
    for name, expected_shape in _EXPECTED_ARRAYS.items():
        array = arrays[name]
        valid_array = (
            array.shape == expected_shape
            and array.dtype == np.float32
            and np.isfinite(array).all()
        )
        if not valid_array:
            raise ValueError(f"invalid {name} array in binder model artifact: {path}")
    calibration = arrays["calibration_ic50_nm"]
    if np.any(calibration <= 0) or np.any(calibration[1:] < calibration[:-1]):
        raise ValueError(f"invalid calibration distribution in binder model artifact: {path}")
    return arrays


def _model_from_arrays(arrays: Mapping[str, np.ndarray]) -> BindingMLP:
    model = BindingMLP().cpu()
    with torch.no_grad():
        model.linear1.weight.copy_(torch.from_numpy(arrays["linear1_weight"]))
        model.linear1.bias.copy_(torch.from_numpy(arrays["linear1_bias"]))
        model.linear2.weight.copy_(torch.from_numpy(arrays["linear2_weight"]))
        model.linear2.bias.copy_(torch.from_numpy(arrays["linear2_bias"]))
        model.linear3.weight.copy_(torch.from_numpy(arrays["linear3_weight"]))
        model.linear3.bias.copy_(torch.from_numpy(arrays["linear3_bias"]))
    model.eval()
    return model


class FrozenBinder:
    """Loaded immutable collection of the 26 allele-specific frozen models."""

    def __init__(
        self,
        models: Mapping[str, BindingMLP],
        calibrations: Mapping[str, np.ndarray],
        model_card: Mapping[str, object],
    ) -> None:
        if set(models) != set(ALLELES) or set(calibrations) != set(ALLELES):
            raise ValueError("a frozen binder must cover exactly all 26 alleles")
        self.models = dict(models)
        self.calibrations = {
            allele: np.array(values, dtype=np.float32, copy=True)
            for allele, values in calibrations.items()
        }
        for values in self.calibrations.values():
            values.setflags(write=False)
        self.model_card = dict(model_card)
        self._encoding_cache: dict[str, np.ndarray] = {}

    def _encoded_peptide(self, peptide: str) -> np.ndarray:
        encoded = self._encoding_cache.get(peptide)
        if encoded is None:
            encoded = encode_peptide(peptide).reshape(189)
            encoded.setflags(write=False)
            self._encoding_cache[peptide] = encoded
        return encoded

    def predict(self, peptide: str, allele: str) -> BindingPrediction:
        """Predict positive IC50 nM and a lower-is-better self percentile."""

        peptide = _validate_peptide(peptide)
        allele = _normalize_supported_allele(allele)
        features = np.stack((self._encoded_peptide(peptide),))
        predicted = float(_physical_ic50(_predict_log10(self.models[allele], features))[0])
        calibration = self.calibrations[allele]
        percentile = float(
            np.searchsorted(calibration, predicted, side="right") * 100.0 / len(calibration)
        )
        if not math.isfinite(predicted) or predicted <= 0 or not 0 <= percentile <= 100:
            raise RuntimeError("binder produced an invalid physical prediction")
        return BindingPrediction(allele, peptide, predicted, percentile)

    def predict_many(self, peptides: Sequence[str], allele: str) -> tuple[BindingPrediction, ...]:
        """Predict a sequence of peptides in stable input order."""

        allele = _normalize_supported_allele(allele)
        normalized = [_validate_peptide(peptide) for peptide in peptides]
        if not normalized:
            return ()
        features = np.stack([self._encoded_peptide(peptide) for peptide in normalized])
        physical = _physical_ic50(_predict_log10(self.models[allele], features))
        calibration = self.calibrations[allele]
        ranks = np.searchsorted(calibration, physical, side="right") * 100.0 / len(calibration)
        return tuple(
            BindingPrediction(allele, peptide, float(ic50), float(rank))
            for peptide, ic50, rank in zip(normalized, physical, ranks, strict=True)
        )


def load_binder(artifact_dir: str | Path | None = None) -> FrozenBinder:
    """Load and strictly validate all frozen safe-NPZ binder artifacts."""

    directory = Path(artifact_dir) if artifact_dir is not None else data_root() / ARTIFACT_DIRECTORY
    model_card = _read_json(directory / MODEL_CARD_NAME)
    if model_card.get("format_version") != 1 or model_card.get("alleles") != list(ALLELES):
        raise ValueError("binder model card does not match the frozen contract")
    hashes = model_card.get("artifact_sha256")
    if not isinstance(hashes, dict):
        raise ValueError("binder model card lacks artifact hashes")
    models: dict[str, BindingMLP] = {}
    calibrations: dict[str, np.ndarray] = {}
    for allele in ALLELES:
        filename = _artifact_filename(allele)
        path = directory / filename
        if hashes.get(filename) != _sha256_file(path):
            raise ValueError(f"binder artifact hash mismatch: {filename}")
        arrays = _load_npz_arrays(path)
        models[allele] = _model_from_arrays(arrays)
        calibrations[allele] = arrays["calibration_ic50_nm"]
    return FrozenBinder(models, calibrations, model_card)


def _verify_no_split_leakage(records: Sequence[BindingRecord]) -> dict[str, int]:
    split_peptides: dict[str, set[str]] = {name: set() for name in ("train", "validation", "test")}
    peptide_assignments: dict[str, str] = {}
    for record in records:
        split = assign_split(record.peptide)
        prior = peptide_assignments.setdefault(record.peptide, split)
        if prior != split:
            raise ValueError(f"peptide split changed across rows: {record.peptide}")
        split_peptides[split].add(record.peptide)
    if (
        split_peptides["train"] & split_peptides["validation"]
        or split_peptides["train"] & split_peptides["test"]
        or split_peptides["validation"] & split_peptides["test"]
    ):
        raise ValueError("global peptide split leakage detected")
    return {name: len(peptides) for name, peptides in split_peptides.items()}


def _assert_metrics_match(stored: Mapping[str, object], reproduced: Mapping[str, object]) -> None:
    stored_aggregate = stored.get("aggregate")
    reproduced_aggregate = reproduced.get("aggregate")
    stored_per_allele = stored.get("per_allele")
    reproduced_per_allele = reproduced.get("per_allele")
    metric_groups = (
        stored_aggregate,
        reproduced_aggregate,
        stored_per_allele,
        reproduced_per_allele,
    )
    if not all(isinstance(value, dict) for value in metric_groups):
        raise ValueError("stored or reproduced binder metrics have an invalid structure")
    for stored_group, reproduced_group in (
        (stored_aggregate, reproduced_aggregate),
        (stored_per_allele, reproduced_per_allele),
    ):
        if stored_group.keys() != reproduced_group.keys():
            raise ValueError("stored and reproduced binder metric keys differ")
    assert isinstance(stored_aggregate, dict)
    assert isinstance(reproduced_aggregate, dict)
    for key, value in reproduced_aggregate.items():
        stored_value = stored_aggregate[key]
        if isinstance(value, float):
            if not math.isclose(float(stored_value), value, rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"aggregate metric did not reproduce: {key}")
        elif stored_value != value:
            raise ValueError(f"aggregate metric did not reproduce: {key}")
    assert isinstance(stored_per_allele, dict)
    assert isinstance(reproduced_per_allele, dict)
    for allele in ALLELES:
        stored_metrics = stored_per_allele[allele]
        reproduced_metrics = reproduced_per_allele[allele]
        if not isinstance(stored_metrics, dict) or not isinstance(reproduced_metrics, dict):
            raise ValueError(f"invalid per-allele metrics for {allele}")
        for key, value in reproduced_metrics.items():
            stored_value = stored_metrics.get(key)
            if isinstance(value, float):
                if not math.isclose(float(stored_value), value, rel_tol=0, abs_tol=1e-12):
                    raise ValueError(f"metric did not reproduce for {allele}: {key}")
            elif stored_value != value:
                raise ValueError(f"metric did not reproduce for {allele}: {key}")


def validate_binder(artifact_dir: str | Path | None = None) -> dict[str, object]:
    """Reload frozen weights and reproduce held-out metrics without retraining."""

    directory = Path(artifact_dir) if artifact_dir is not None else data_root() / ARTIFACT_DIRECTORY
    binder = load_binder(directory)
    records = _validated_records()
    split_counts = _verify_no_split_leakage(records)
    cache = _encode_cache(records)
    reproduced = _heldout_metrics(binder.models, records, cache)
    stored = _read_json(directory / METRICS_NAME)
    _assert_metrics_match(stored, reproduced)
    return {
        "metrics": reproduced,
        "split_unique_peptides": split_counts,
        "stored_metrics_reproduced": True,
    }
