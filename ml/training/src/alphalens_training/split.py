"""One chronological development holdout with availability-based conservative purge."""

from collections import Counter
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from alphalens_data.errors import DataContractError
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.contracts import RowMetadata, TrainingConfig, boundary, verify_dataset

Matrix = NDArray[np.float64]


@dataclass(frozen=True)
class Holdout:
    x_train: Matrix
    x_validation: Matrix
    y_train: Matrix
    y_validation: Matrix
    feature_columns: tuple[str, ...]
    removed_features: tuple[str, ...]
    train_metadata: tuple[RowMetadata, ...]
    validation_metadata: tuple[RowMetadata, ...]
    exclusion_counts: dict[str, int]
    excluded_rows: int


def split(data: SupervisedDataset, config: TrainingConfig) -> Holdout:
    metadata = verify_dataset(data, config)
    train: list[int] = []
    validation: list[int] = []
    reasons: Counter[str] = Counter()
    excluded = 0
    start = boundary(config.validation_start)
    for index, meta in enumerate(metadata):
        why: set[str] = set()
        if meta.training_eligibility != "TRAINING_ELIGIBLE":
            why.update(meta.reason_codes)
        if meta.session_date < config.validation_start:
            if meta.decision_time > config.training_cutoff:
                why.add("FEATURE_DECISION_AFTER_TRAINING_CUTOFF")
            if meta.label_available_at is None:
                why.add("LABEL_AVAILABILITY_UNKNOWN")
            else:
                if meta.label_available_at > config.training_cutoff:
                    why.add("LABEL_AFTER_TRAINING_CUTOFF")
                if meta.label_available_at >= start:
                    why.add("TARGET_OVERLAP_PURGED")
            destination = train
        elif meta.session_date <= config.validation_end:
            if meta.decision_time <= config.training_cutoff:
                why.add("VALIDATION_DECISION_BEFORE_BOUNDARY")
            destination = validation
        else:
            why.add("OUTSIDE_VALIDATION_INTERVAL")
            destination = validation
        if why:
            excluded += 1
            reasons.update(why)
        else:
            destination.append(index)
    if (
        len(train) < config.minimum_training_rows
        or len(validation) < config.minimum_validation_rows
    ):
        raise DataContractError("INSUFFICIENT_MATURE_HOLDOUT_ROWS")
    columns = data.feature_columns

    def matrix(indices: list[int]) -> Matrix:
        return np.asarray(
            [[data.rows[i].features[n] for n in columns] for i in indices], dtype="float64"
        )

    x_train, x_validation = matrix(train), matrix(validation)
    keep = np.ptp(x_train, axis=0) != 0
    if not keep.any():
        raise DataContractError("NO_NONCONSTANT_TRAIN_FEATURES")
    name = "direction" if config.task == "classification" else "forward_return"
    target = f"target_{name}_{config.horizon}"

    def targets(indices: list[int]) -> Matrix:
        values = np.asarray(
            [float(str(data.rows[i].targets[target])) for i in indices], dtype="float64"
        )
        if not np.isfinite(values).all():
            raise DataContractError("NONFINITE_TARGET_CONVERSION")
        return values

    return Holdout(
        x_train=x_train[:, keep],
        x_validation=x_validation[:, keep],
        y_train=targets(train),
        y_validation=targets(validation),
        feature_columns=tuple(n for n, k in zip(columns, keep, strict=True) if k),
        removed_features=tuple(n for n, k in zip(columns, keep, strict=True) if not k),
        train_metadata=tuple(metadata[i] for i in train),
        validation_metadata=tuple(metadata[i] for i in validation),
        exclusion_counts=dict(sorted(reasons.items())),
        excluded_rows=excluded,
    )
