"""Immutable decision states, with explicit development and position boundaries."""

from datetime import date
from typing import Annotated, Any, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_decision.models import Horizon, Number
from alphalens_decision.risk_contracts import Level
from alphalens_evaluation.contracts import digest, disclaimer

State = Literal[
    "WATCH", "SETUP_FORMING", "ENTRY_SIGNAL", "HOLD", "TAKE_PROFIT_REVIEW", "EXIT_SIGNAL", "EXITED"
]
Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class SignalPolicy(Contract):
    version: Literal["p13.signal_policy.v1"] = "p13.signal_policy.v1"
    revision: str = Field(default="initial", min_length=1)
    threshold_status: Literal["DEVELOPMENT_ASSUMPTION"] = "DEVELOPMENT_ASSUMPTION"
    horizon: Horizon
    entry_maximum_rank: int = Field(default=5, ge=1)
    retain_maximum_rank: int = Field(default=10, ge=1)
    entry_minimum_score: Number = 0.30
    retain_minimum_score: Number = 0.20
    setup_minimum_score: Number = 0.10
    entry_minimum_probability: Unit = 0.60
    retain_minimum_probability: Unit = 0.55
    entry_minimum_return: Number = 0.005
    retain_minimum_return: Number = 0.0
    maximum_risk: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    maximum_model_uncertainty: Unit = 0.50
    positive_momentum_percentile: Unit = 0.75
    require_valid_quality: bool = True
    require_sufficient_history: Literal[True] = True
    confirmation_observations: int = Field(default=2, ge=1, le=20)
    maximum_history_gap_days: int = Field(default=7, ge=1, le=31)
    review_horizon: Horizon | None = None
    test_only_state_demonstration: bool = False
    price_invalidation_policy: Literal["UNAVAILABLE_NO_APPROVED_PRICE_POLICY"] = (
        "UNAVAILABLE_NO_APPROVED_PRICE_POLICY"
    )

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.retain_maximum_rank < self.entry_maximum_rank
            or self.retain_minimum_score > self.entry_minimum_score
            or self.setup_minimum_score > self.entry_minimum_score
            or self.retain_minimum_probability > self.entry_minimum_probability
            or self.retain_minimum_return > self.entry_minimum_return
            or self.review_horizon is not None
            and self.review_horizon > self.horizon
        ):
            raise ValueError("Invalid entry/retention/review threshold ordering")
        return self

    @property
    def policy_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class PositionEvidence(Contract):
    """Explicit synthetic lifecycle evidence, not a holding/accounting subsystem."""

    context_id: str = Field(min_length=1)
    security_id: str = Field(min_length=1)
    horizon: Horizon
    entry_at: AwareDatetime
    available_at: AwareDatetime
    exit_at: AwareDatetime | None = None
    profit_review_requested: bool = False
    evidence_reference: str = Field(min_length=1)
    classification: Literal["TEST_ONLY"] = "TEST_ONLY"
    origin: Literal["EXPLICIT_SYNTHETIC_TEST_ONLY_POSITION"] = (
        "EXPLICIT_SYNTHETIC_TEST_ONLY_POSITION"
    )

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if (
            self.available_at < self.entry_at
            or self.exit_at is not None
            and (self.exit_at < self.entry_at or self.available_at < self.exit_at)
        ):
            raise ValueError("Position event must precede its evidenced availability")
        return self

    @property
    def evidence_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class SignalSnapshot(Contract):
    signal_snapshot_id: Hash
    signal_engine_version: Literal["p13.signals.v1"] = "p13.signals.v1"
    security_id: str
    symbol: str | None
    session_date: date
    decision_time: AwareDatetime
    knowledge_cutoff: AwareDatetime
    horizon: Horizon
    policy: SignalPolicy
    context: Literal["MARKET_OPPORTUNITY_STATE", "POSITION_DECISION_STATE"]
    state: State
    previous_state: State | None
    previous_signal_snapshot_id: Hash | None
    confirmation_count: int = Field(ge=0)
    entry_conditions: dict[str, bool]
    retention_conditions: dict[str, bool]
    opportunity_rank: int | None
    raw_score: Number | None
    risk_adjusted_score: Number | None
    risk_level: Level
    model_confidence: str
    signal_confidence: Literal["INSUFFICIENT_EVIDENCE", "TEST_ONLY_DEVELOPMENT_EVIDENCE"]
    probability: Unit | None
    expected_return_estimate: Number | None
    expected_return_label: Literal["MODEL ESTIMATE — NOT GUARANTEED"] = (
        "MODEL ESTIMATE — NOT GUARANTEED"
    )
    prediction_horizon: Horizon
    preferred_review_horizon: Horizon | None
    technical_invalidation_price: Literal[None] = None
    invalidation_conditions: dict[str, Any]
    positive_reasons: tuple[str, ...]
    negative_reasons: tuple[str, ...]
    transition_reasons: tuple[str, ...]
    ranking_snapshot_id: Hash
    risk_snapshot_id: Hash | None
    prediction_ids: tuple[Hash, ...]
    model_run_ids: tuple[Hash, ...]
    evaluation_ids: tuple[Hash, ...]
    feature_set_id: Hash
    canonical_input_id: Hash
    canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    universe_definition_id: str
    observed_price_available_at: AwareDatetime | None
    data_freshness: Literal["EOD_COMPLETE", "STALE", "UNAVAILABLE"]
    availability: Literal["DEGRADED", "UNAVAILABLE"]
    quality: str
    classification: Classification
    position_evidence: PositionEvidence | None
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        position = self.position_evidence
        required_checks = {
            "eligible",
            "risk",
            "uncertainty",
            "quality",
            "history",
            "model_evidence",
            "freshness",
            "corporate_action",
            "rank",
            "score",
            "probability",
            "return",
        }
        if (
            self.classification == Classification.PRODUCTION
            or self.disclaimer != disclaimer(self.classification)
            or self.decision_time != self.knowledge_cutoff
            or self.horizon != self.policy.horizon
            or self.prediction_horizon != self.horizon
            or self.preferred_review_horizon != self.policy.review_horizon
            or set(self.entry_conditions) != required_checks
            or set(self.retention_conditions) != required_checks
            or self.state in {"ENTRY_SIGNAL", "HOLD", "TAKE_PROFIT_REVIEW"}
            and not self.policy.test_only_state_demonstration
            or self.classification != Classification.TEST_ONLY
            and self.policy.test_only_state_demonstration
            or (self.previous_state is None) != (self.previous_signal_snapshot_id is None)
            or any(
                reasons != tuple(sorted(set(reasons)))
                for reasons in (
                    self.positive_reasons,
                    self.negative_reasons,
                    self.transition_reasons,
                )
            )
            or self.context
            != ("POSITION_DECISION_STATE" if position else "MARKET_OPPORTUNITY_STATE")
            or position is not None
            and (
                position.security_id != self.security_id
                or position.horizon != self.horizon
                or position.available_at > self.knowledge_cutoff
                or position.entry_at >= self.decision_time
                or self.classification != Classification.TEST_ONLY
            )
            or self.state in {"HOLD", "TAKE_PROFIT_REVIEW", "EXIT_SIGNAL", "EXITED"}
            and position is None
            or self.state == "EXITED"
            and (position is None or position.exit_at is None)
            or position is not None
            and position.exit_at is not None
            and self.state != "EXITED"
            or self.state in {"HOLD", "TAKE_PROFIT_REVIEW"}
            and not all(self.retention_conditions.values())
            or self.state == "ENTRY_SIGNAL"
            and (
                not self.entry_conditions
                or not (
                    all(self.entry_conditions.values())
                    and self.confirmation_count >= self.policy.confirmation_observations
                    or self.previous_state == "ENTRY_SIGNAL"
                    and all(self.retention_conditions.values())
                )
                or position is not None
            )
            or self.signal_confidence == "TEST_ONLY_DEVELOPMENT_EVIDENCE"
            and not (
                self.policy.test_only_state_demonstration
                and self.classification == Classification.TEST_ONLY
            )
            or not self.transition_reasons
            or self.signal_snapshot_id
            != digest(self.model_dump(mode="json", exclude={"signal_snapshot_id"}))
        ):
            raise ValueError("Signal identity/context/evidence/classification contradiction")
        return self
