"""Serializable P8 configuration and strict P7-only matrix boundary."""

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_features.models import BuildPlan, Decision
from alphalens_features.registry import default_set
from alphalens_labels.alignment import METADATA_COLUMNS, SupervisedDataset

VERSION = "p8.baseline.v1"
Task = Literal["classification", "regression"]
Family = Literal["logistic", "ridge", "random_forest", "hist_gradient_boosting"]


def boundary(session: date) -> datetime:
    return datetime.combine(session, datetime.min.time(), ZoneInfo("Asia/Kolkata"))


def feature_families(config: "TrainingConfig") -> dict[str, str]:
    """Validate registry names/families only; never read or recompute feature data."""
    definitions = default_set(
        BuildPlan(
            history_start=config.validation_start,
            decisions=(
                Decision(
                    session_date=config.validation_start,
                    knowledge_cutoff=boundary(config.validation_start),
                ),
            ),
            benchmark_security_id="registry-name-validation-only",
            benchmark_evidence_reference="No data recomputation",
        )
    ).definitions
    return {d.feature_name: d.feature_family for d in definitions}


class TrainingConfig(Contract):
    schema_version: Literal["p8.baseline.v1"] = "p8.baseline.v1"
    model_version: Literal["1"] = "1"
    task: Task
    horizon: Literal[1, 5, 10, 20]
    model_family: Family
    training_cutoff: AwareDatetime
    validation_start: date
    validation_end: date
    random_seed: int = Field(default=1729, ge=0, le=2**32 - 1)
    minimum_training_rows: int = Field(default=10, ge=2)
    minimum_validation_rows: int = Field(default=4, ge=2)
    missing_policy: Literal["P7_ELIGIBILITY_THEN_TRAIN_MEDIAN"] = "P7_ELIGIBILITY_THEN_TRAIN_MEDIAN"
    feature_selection: Literal["P7_ORDER_TRAIN_CONSTANT_REMOVAL"] = (
        "P7_ORDER_TRAIN_CONSTANT_REMOVAL"
    )
    calibration_bins: Literal[5] = 5
    calibration_minimum_rows: Literal[20] = 20
    top_k_policy: Literal["UNAVAILABLE_P8_DISABLED"] = "UNAVAILABLE_P8_DISABLED"
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def valid(self) -> Self:
        if self.validation_start > self.validation_end:
            raise ValueError("Invalid validation interval")
        if self.training_cutoff >= boundary(self.validation_start):
            raise ValueError("Training cutoff must precede validation local date start")
        if (self.task == "classification" and self.model_family == "ridge") or (
            self.task == "regression" and self.model_family == "logistic"
        ):
            raise ValueError("Model family/task mismatch")
        return self


class RowMetadata(Contract):
    security_id: str
    session_date: date
    decision_time: AwareDatetime
    feature_canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    label_available_at: AwareDatetime | None
    classification: Classification
    training_eligibility: Literal["TRAINING_ELIGIBLE", "NOT_TRAINING_ELIGIBLE"]
    reason_codes: tuple[str, ...]


def verify_dataset(data: SupervisedDataset, config: TrainingConfig) -> tuple[RowMetadata, ...]:
    """Never join/recompute P6/P7 values or override upstream eligibility."""
    data = SupervisedDataset.model_validate(data.model_dump())
    digest = checksum(stable_json(data.model_dump(mode="json", exclude={"supervised_dataset_id"})))
    if digest != data.supervised_dataset_id:
        raise DataContractError("SUPERVISED_DATASET_ID_MISMATCH")
    if data.horizon != config.horizon or config.training_cutoff > data.training_as_of:
        raise DataContractError("HORIZON_OR_KNOWLEDGE_MISMATCH")
    expected = (f"target_forward_return_{data.horizon}", f"target_direction_{data.horizon}")
    if data.target_columns != expected or data.metadata_columns != METADATA_COLUMNS:
        raise DataContractError("P7_COLUMN_CONTRACT_REQUIRED")
    if len(data.feature_columns) != len(set(data.feature_columns)):
        raise DataContractError("DUPLICATE_FEATURE_COLUMNS")
    registered = set(feature_families(config))
    if not set(data.feature_columns) <= registered:
        raise DataContractError("ONLY_P6_FEATURE_NAMES_ALLOWED")
    metadata = tuple(RowMetadata.model_validate(r.metadata) for r in data.rows)
    keys = [(m.session_date, m.security_id) for m in metadata]
    if keys != sorted(set(keys)):
        raise DataContractError("UNIQUE_CHRONOLOGICAL_P7_ROWS_REQUIRED")
    for row, meta in zip(data.rows, metadata, strict=True):
        if meta.decision_time.astimezone(ZoneInfo("Asia/Kolkata")).date() < meta.session_date:
            raise DataContractError("DECISION_BEFORE_SESSION")
        if any(v is not None and not math.isfinite(v) for v in row.features.values()):
            raise DataContractError("NONFINITE_FEATURE")
        ret, direction = (row.targets[n] for n in expected)
        if ret is not None:
            value = Decimal(str(ret))
            if not value.is_finite() or direction != int(value > 0):
                raise DataContractError("P7_TARGET_CONTRADICTION")
        elif direction is not None:
            raise DataContractError("P7_TARGET_CONTRADICTION")
        if meta.training_eligibility == "TRAINING_ELIGIBLE" and (
            meta.reason_codes
            or any(v is None for v in row.features.values())
            or ret is None
            or meta.label_available_at is None
            or meta.label_available_at > data.training_as_of
            or meta.label_available_at <= meta.decision_time
            or meta.decision_time > data.training_as_of
        ):
            raise DataContractError("P7_ELIGIBILITY_CONTRADICTION")
        if meta.training_eligibility == "NOT_TRAINING_ELIGIBLE" and not meta.reason_codes:
            raise DataContractError("P7_EXCLUSION_REASON_REQUIRED")
    return metadata
