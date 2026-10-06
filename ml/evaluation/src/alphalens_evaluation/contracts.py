"""Versioned expanding-fold and genuine OOS contracts; no production promotion."""

from datetime import date
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_training.contracts import Task, boundary

VERSION: Literal["p9.walk_forward.v1"] = "p9.walk_forward.v1"
Family = Literal[
    "logistic",
    "ridge",
    "random_forest",
    "hist_gradient_boosting",
    "lightgbm",
    "catboost",
    "xgboost",
]


def digest(value: object) -> str:
    return checksum(stable_json(value))


def disclaimer(classification: Classification) -> str:
    return (
        "TEST_ONLY — NOT A PERFORMANCE CLAIM"
        if classification == Classification.TEST_ONLY
        else "RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED"
    )


class Fold(Contract):
    fold_id: str = Field(min_length=1)
    training_cutoff: AwareDatetime
    test_start: date
    test_end: date

    @model_validator(mode="after")
    def temporal(self) -> Self:
        if self.test_end < self.test_start or self.training_cutoff >= boundary(self.test_start):
            raise ValueError("Training knowledge must precede test local date start")
        return self


class WalkForwardDefinition(Contract):
    evaluation_version: Literal["p9.walk_forward.v1"] = VERSION
    model_contract_version: Literal["p9.fold_model.v1"] = "p9.fold_model.v1"
    feature_set_id: Hash
    label_set_id: Hash
    canonical_dataset_id: Hash
    supervised_dataset_id: Hash
    training_dataset_ids: dict[str, Hash]
    task: Task
    horizon: Literal[1, 5, 10, 20]
    model_families: tuple[Family, ...]
    folds: tuple[Fold, ...]
    window: Literal["EXPANDING"] = "EXPANDING"
    purge_policy: Literal["LABEL_AVAILABLE_BY_CUTOFF_BEFORE_TEST_DATE"] = (
        "LABEL_AVAILABLE_BY_CUTOFF_BEFORE_TEST_DATE"
    )
    embargo_seconds: int = Field(default=0, ge=0)
    retraining_policy: Literal["FRESH_MODEL_AND_PREPROCESSOR_EVERY_FOLD"] = (
        "FRESH_MODEL_AND_PREPROCESSOR_EVERY_FOLD"
    )
    selection_policy: Literal["PREDEFINED_CONFIGURATIONS_NO_OUTER_TEST_TUNING"] = (
        "PREDEFINED_CONFIGURATIONS_NO_OUTER_TEST_TUNING"
    )
    random_seed: int = Field(default=1729, ge=0, le=2**32 - 1)
    minimum_training_rows: int = Field(default=10, ge=2)
    minimum_test_rows: int = Field(default=4, ge=2)
    ranking_minimum_securities: int = Field(default=5, ge=5)
    ranking_quantile: float = Field(default=0.2, ge=0.2, le=0.2)
    uncertainty_minimum_folds: Literal[10] = 10
    uncertainty_minimum_sessions: Literal[60] = 60
    data_classification: Classification
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def safe(self) -> Self:
        if self.data_classification == Classification.PRODUCTION:
            raise ValueError("Production data clearance remains open")
        if len(self.folds) < 2 or not self.model_families:
            raise ValueError("Multiple folds and at least one predefined family required")
        if len(set(self.model_families)) != len(self.model_families):
            raise ValueError("Unique model families required")
        if (self.task == "classification" and "ridge" in self.model_families) or (
            self.task == "regression" and "logistic" in self.model_families
        ):
            raise ValueError("Family/task mismatch")
        if len({f.fold_id for f in self.folds}) != len(self.folds):
            raise ValueError("Unique fold IDs required")
        if set(self.training_dataset_ids) != {f.fold_id for f in self.folds}:
            raise ValueError("Every fold requires a cutoff-specific P7 training dataset")
        for previous, current in zip(self.folds, self.folds[1:], strict=False):
            if (
                current.test_start <= previous.test_end
                or current.training_cutoff <= previous.training_cutoff
            ):
                raise ValueError("Ordered disjoint outer tests and expanding knowledge required")
        return self


class OOSPrediction(Contract):
    prediction_id: Hash
    evaluation_id: Hash
    role: Literal["FOLD_TEST"] = "FOLD_TEST"
    security_id: str
    session_date: date
    decision_time: AwareDatetime
    prediction_available_at: AwareDatetime
    fold_id: str
    model_run_id: Hash
    model_family: Family
    task: Task
    horizon: Literal[1, 5, 10, 20]
    prediction: float = Field(allow_inf_nan=False)
    probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    actual_target: float | None = Field(default=None, allow_inf_nan=False)
    actual_forward_return: str | None
    target_available_at: AwareDatetime | None
    scoring_status: Literal["SCORABLE", "OUTCOME_EXCLUDED"]
    outcome_reason_codes: tuple[str, ...]
    feature_set_id: Hash
    label_set_id: Hash
    supervised_dataset_id: Hash
    canonical_input_id: Hash
    feature_canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    classification: Classification
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def safe(self) -> Self:
        if (
            self.classification == Classification.PRODUCTION
            or self.prediction_available_at != self.decision_time
            or self.target_available_at is not None
            and self.target_available_at <= self.decision_time
            or self.scoring_status == "SCORABLE"
            and (self.actual_target is None or self.target_available_at is None)
            or self.scoring_status == "OUTCOME_EXCLUDED"
            and not self.outcome_reason_codes
            or (self.task == "classification") != (self.probability is not None)
        ):
            raise ValueError("OOS temporal/classification/probability contradiction")
        if self.prediction_id != digest(self.model_dump(mode="json", exclude={"prediction_id"})):
            raise ValueError("OOS prediction checksum mismatch")
        return self
