"""Reuse the P8 numerical preprocessing contract without changing P8 behavior."""

from datetime import timedelta

from alphalens_evaluation.contracts import Fold, WalkForwardDefinition
from alphalens_training.contracts import TrainingConfig


def fold_config(definition: WalkForwardDefinition, fold: Fold) -> TrainingConfig:
    return TrainingConfig(
        task=definition.task,
        horizon=definition.horizon,
        model_family="logistic" if definition.task == "classification" else "ridge",
        training_cutoff=fold.training_cutoff - timedelta(seconds=definition.embargo_seconds),
        validation_start=fold.test_start,
        validation_end=fold.test_end,
        random_seed=definition.random_seed,
        minimum_training_rows=definition.minimum_training_rows,
        minimum_validation_rows=definition.minimum_test_rows,
    )
