"""Partition already aligned P7 rows, with separate cutoff-specific label knowledge."""

from collections import Counter

import numpy as np

from alphalens_data.errors import DataContractError
from alphalens_evaluation.contracts import Fold, WalkForwardDefinition
from alphalens_evaluation.engine_config import fold_config
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.contracts import boundary, verify_dataset
from alphalens_training.split import Holdout, Matrix


def fold_split(
    scoring: SupervisedDataset,
    training: SupervisedDataset,
    definition: WalkForwardDefinition,
    fold: Fold,
) -> Holdout:
    config = fold_config(definition, fold)
    if (
        training.supervised_dataset_id != definition.training_dataset_ids[fold.fold_id]
        or training.training_as_of > config.training_cutoff
        or training.feature_columns != scoring.feature_columns
        or training.target_columns != scoring.target_columns
        or training.classification != scoring.classification
        or training.horizon != scoring.horizon
    ):
        raise DataContractError("P9_FOLD_TRAINING_KNOWLEDGE_OR_CONTRACT_MISMATCH")
    train_metadata = verify_dataset(training, config)
    test_metadata = verify_dataset(scoring, config)
    train, test = [], []
    reasons: Counter[str] = Counter()
    excluded = 0
    scoring_features = {
        (m.session_date, m.security_id): r.features
        for m, r in zip(test_metadata, scoring.rows, strict=True)
    }
    scoring_metadata = {(m.session_date, m.security_id): m for m in test_metadata}
    for index, meta in enumerate(train_metadata):
        if meta.session_date >= fold.test_start:
            continue
        why = set(meta.reason_codes)
        if meta.decision_time > config.training_cutoff:
            why.add("FEATURE_DECISION_AFTER_TRAINING_CUTOFF")
        if meta.label_available_at is None:
            why.add("LABEL_AVAILABILITY_UNKNOWN")
        else:
            if meta.label_available_at > config.training_cutoff:
                why.add("LABEL_AFTER_TRAINING_CUTOFF")
            if meta.label_available_at >= boundary(fold.test_start):
                why.add("TARGET_OVERLAP_PURGED")
        if meta.training_eligibility != "TRAINING_ELIGIBLE" and not why:
            raise DataContractError("P7_EXCLUSION_REASON_REQUIRED")
        if (
            scoring_features.get((meta.session_date, meta.security_id))
            != training.rows[index].features
        ):
            raise DataContractError("P9_FOLD_FEATURES_CHANGED")
        original = scoring_metadata.get((meta.session_date, meta.security_id))
        if original is None or (
            meta.decision_time,
            meta.feature_canonical_dataset_id,
            meta.universe_snapshot_id,
        ) != (
            original.decision_time,
            original.feature_canonical_dataset_id,
            original.universe_snapshot_id,
        ):
            raise DataContractError("P9_FOLD_DECISION_OR_UNIVERSE_CHANGED")
        if why:
            excluded += 1
            reasons.update(why)
        else:
            train.append(index)
    for index, meta in enumerate(test_metadata):
        if meta.session_date < fold.test_start:
            continue
        # Outcome-side exclusions must not retroactively decide whether a prediction
        # could be issued. TRAIN eligibility stays unchanged; metrics still honor P7.
        outcome_reasons = {
            "LABEL_NOT_MATURE",
            "LABEL_UNAVAILABLE",
            "LABEL_QUALITY_NOT_ACCEPTED",
            "CORPORATE_ACTION_UNADJUSTED",
        }
        why = set(meta.reason_codes) - outcome_reasons
        if meta.session_date > fold.test_end:
            why.add("OUTSIDE_TEST_INTERVAL")
        if meta.decision_time <= config.training_cutoff:
            why.add("TEST_DECISION_BEFORE_BOUNDARY")
        if why:
            excluded += 1
            reasons.update(why)
        else:
            test.append(index)
    if len(train) < config.minimum_training_rows or len(test) < config.minimum_validation_rows:
        raise DataContractError("INSUFFICIENT_MATURE_HOLDOUT_ROWS")
    columns = scoring.feature_columns

    def matrix(data: SupervisedDataset, indices: list[int]) -> Matrix:
        return np.asarray(
            [[data.rows[i].features[n] for n in columns] for i in indices], dtype="float64"
        )

    xtrain, xtest = matrix(training, train), matrix(scoring, test)
    keep = np.ptp(xtrain, axis=0) != 0
    if not keep.any():
        raise DataContractError("NO_NONCONSTANT_TRAIN_FEATURES")
    name = "direction" if definition.task == "classification" else "forward_return"
    target = f"target_{name}_{definition.horizon}"

    def targets(data: SupervisedDataset, indices: list[int], scoring_only: bool = False) -> Matrix:
        result = np.asarray(
            [
                float(str(data.rows[i].targets[target]))
                if not scoring_only
                or data.rows[i].metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
                else np.nan
                for i in indices
            ],
            dtype="float64",
        )
        if not scoring_only and not np.isfinite(result).all():
            raise DataContractError("NONFINITE_TARGET_CONVERSION")
        return result

    return Holdout(
        xtrain[:, keep],
        xtest[:, keep],
        targets(training, train),
        targets(scoring, test, scoring_only=True),
        tuple(n for n, k in zip(columns, keep, strict=True) if k),
        tuple(n for n, k in zip(columns, keep, strict=True) if not k),
        tuple(train_metadata[i] for i in train),
        tuple(test_metadata[i] for i in test),
        dict(sorted(reasons.items())),
        excluded,
    )
