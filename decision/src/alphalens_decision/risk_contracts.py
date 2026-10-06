"""Transparent risk assumptions, components and immutable snapshots; no actions."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.canonical.models import Availability
from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.quality.models import QualityStatus
from alphalens_decision.models import Horizon, Number
from alphalens_evaluation.contracts import digest, disclaimer

Level = Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH", "UNAVAILABLE"]
Metric = Number | int | str | None
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]


def level(score: float | None) -> Level:
    return (
        "UNAVAILABLE"
        if score is None
        else (
            "LOW"
            if score < 0.25
            else "MEDIUM"
            if score < 0.5
            else "HIGH"
            if score < 0.75
            else "VERY_HIGH"
        )
    )


class RiskPolicy(Contract):
    version: Literal["p11.risk_policy.v1"] = "p11.risk_policy.v1"
    window: Literal[20] = 20
    minimum_history: Literal[21] = 21
    sufficient_history: int = Field(default=61, ge=21)
    volatility_scale: Positive = 0.05
    atr_ratio_scale: Positive = 0.10
    drawdown_scale: Positive = 0.30
    zero_volume_scale: Positive = 0.10
    volume_cv_scale: Positive = 2.0
    absolute_gap_scale: Positive = 0.05
    large_gap_threshold: Positive = 0.05
    gap_frequency_scale: Positive = 0.20
    relative_volatility_excess_scale: Positive = 2.0
    probability_dispersion_scale: Positive = 0.25
    return_dispersion_scale: Positive = 0.05
    brier_scale: Positive = 0.25
    minimum_validation_rows: int = Field(default=100, ge=2)
    missing_optional_severity: Annotated[float, Field(ge=0.5, le=1)] = 0.5
    missing_model_severity: Annotated[float, Field(ge=1, le=1)] = 1.0
    overall_policy: Literal["WORST_COMPONENT_ESSENTIAL_FAILURE_UNAVAILABLE"] = (
        "WORST_COMPONENT_ESSENTIAL_FAILURE_UNAVAILABLE"
    )
    severity_bands: Literal["0.25_0.50_0.75"] = "0.25_0.50_0.75"


class RiskComponent(Contract):
    metrics: dict[str, Metric]
    severity: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None
    level: Level
    availability: Availability
    reasons: tuple[str, ...]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.level != level(self.severity)
            or (self.severity is None) != (self.availability == Availability.UNAVAILABLE)
            or list(self.reasons) != sorted(set(self.reasons))
        ):
            raise ValueError("Risk component severity/availability/reason contradiction")
        return self


class RiskSnapshot(Contract):
    risk_snapshot_id: Hash
    risk_engine_version: Literal["p11.risk.v1"] = "p11.risk.v1"
    security_id: str
    symbol: str | None
    session_date: date
    decision_time: AwareDatetime
    knowledge_cutoff: AwareDatetime
    horizon: Horizon
    feature_set_id: Hash
    canonical_input_id: Hash
    canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    universe_definition_id: str
    observed_price_available_at: AwareDatetime | None
    source_quality: QualityStatus | Literal["UNAVAILABLE"]
    feature_availability: Availability
    classification: Classification
    policy: RiskPolicy
    components: dict[str, RiskComponent]
    overall_level: Level
    model_confidence: Literal["INSUFFICIENT_EVIDENCE", "DESCRIPTIVE_DIAGNOSTICS_ONLY"]
    evidence_sufficiency: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT"]
    analysis_permitted: bool
    availability: Availability
    reasons: tuple[str, ...]
    prediction_evidence_ids: tuple[Hash, ...]
    diagnostic_evidence_ids: tuple[Hash, ...]
    model_run_ids: tuple[Hash, ...]
    evaluation_ids: tuple[Hash, ...]
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        expected_components = {
            "volatility_risk",
            "drawdown_risk",
            "liquidity_proxy_risk",
            "gap_risk",
            "market_risk",
            "model_uncertainty",
            "data_quality_risk",
            "corporate_action_risk",
            "historical_evidence",
        }
        worst = max(
            (
                c.severity if c.severity is not None else self.policy.missing_optional_severity
                for c in self.components.values()
            ),
            default=1.0,
        )
        if (
            self.classification == Classification.PRODUCTION
            or set(self.components) != expected_components
            or self.disclaimer != disclaimer(self.classification)
            or self.decision_time != self.knowledge_cutoff
            or list(self.reasons) != sorted(set(self.reasons))
            or self.source_quality == QualityStatus.REJECTED
            and self.analysis_permitted
            or self.overall_level == "UNAVAILABLE"
            and self.analysis_permitted
            or self.overall_level != (level(worst) if self.analysis_permitted else "UNAVAILABLE")
            or not self.analysis_permitted
            and self.availability != Availability.UNAVAILABLE
            or self.analysis_permitted
            and (
                self.evidence_sufficiency == "INSUFFICIENT"
                or self.source_quality not in {QualityStatus.VALID, QualityStatus.DEGRADED}
                or self.components["volatility_risk"].severity is None
                or self.components["drawdown_risk"].severity is None
                or "KNOWN_UNADJUSTED_CORPORATE_ACTION" in self.reasons
            )
            or self.risk_snapshot_id
            != digest(self.model_dump(mode="json", exclude={"risk_snapshot_id"}))
        ):
            raise ValueError("Risk snapshot classification/identity/eligibility contradiction")
        return self
