"""Target-free model evidence with explicit availability and preserved classification."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_evaluation.contracts import Family, digest
from alphalens_training.contracts import Task

Number = Annotated[float, Field(allow_inf_nan=False)]
Horizon = Literal[1, 5, 10, 20]
Origin = Literal["P9_FOLD_TEST", "TEST_ONLY_AUTHORED"]


class PredictionEvidence(Contract):
    """P9 projection deliberately excludes outcomes and outcome-dependent row hashes."""

    origin: Origin
    evaluation_id: Hash
    model_run_id: Hash
    family: Family
    task: Task
    horizon: Horizon
    security_id: str
    session_date: date
    decision_time: AwareDatetime
    available_at: AwareDatetime
    training_cutoff: AwareDatetime
    feature_set_id: Hash
    canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    prediction: Number
    probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    classification: Classification
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def safe(self) -> Self:
        if (
            self.classification == Classification.PRODUCTION
            or self.origin == "TEST_ONLY_AUTHORED"
            and self.classification != Classification.TEST_ONLY
            or self.available_at != self.decision_time
            or self.training_cutoff >= self.decision_time
            or (self.task == "classification") != (self.probability is not None)
        ):
            raise ValueError("Invalid historical prediction evidence")
        return self

    @property
    def evidence_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class ModelDiagnostic(Contract):
    origin: Origin
    evaluation_id: Hash
    model_run_id: Hash
    family: Family
    task: Task
    horizon: Horizon
    fold_id: str
    period_end: date
    available_at: AwareDatetime
    report_checksum: Hash
    sample_count: int = Field(ge=0)
    primary_metric: Number | None
    naive_improvement: Number | None
    brier_score: Annotated[float, Field(ge=0, le=1)] | None = None
    calibration_available: bool = False
    evidence_status: Literal["INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    classification: Classification

    @model_validator(mode="after")
    def safe(self) -> Self:
        from alphalens_training.contracts import boundary

        if (
            self.classification == Classification.PRODUCTION
            or self.origin == "TEST_ONLY_AUTHORED"
            and self.classification != Classification.TEST_ONLY
            or self.available_at < boundary(self.period_end)
        ):
            raise ValueError("Invalid historical diagnostic availability/classification")
        return self

    @property
    def evidence_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class ModelEvidence(Contract):
    version: Literal["p11.model_evidence.v1"] = "p11.model_evidence.v1"
    classification: Classification
    predictions: tuple[PredictionEvidence, ...] = ()
    diagnostics: tuple[ModelDiagnostic, ...] = ()

    @model_validator(mode="after")
    def safe(self) -> Self:
        if (
            self.classification == Classification.PRODUCTION
            or any(row.classification != self.classification for row in self.predictions)
            or any(row.classification != self.classification for row in self.diagnostics)
        ):
            raise ValueError("Evidence classification must propagate unchanged")
        keys = [
            (p.session_date, p.security_id, p.horizon, p.task, p.family) for p in self.predictions
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Ambiguous predictions: one configured vintage per family/decision")
        ids = [d.evidence_id for d in self.diagnostics]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate model diagnostics")
        folds = [
            (d.evaluation_id, d.family, d.task, d.horizon, d.fold_id) for d in self.diagnostics
        ]
        if len(folds) != len(set(folds)):
            raise ValueError("Ambiguous diagnostic vintages must not multiply sample counts")
        return self
