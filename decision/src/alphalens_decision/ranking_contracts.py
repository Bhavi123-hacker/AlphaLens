"""Versioned transparent opportunity contracts; scores are never trading actions."""

from datetime import date
from math import tanh
from typing import Annotated, Any, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.canonical.models import Availability
from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.quality.models import QualityStatus
from alphalens_decision.models import Horizon, Number
from alphalens_decision.risk_contracts import Level, Positive, RiskPolicy
from alphalens_evaluation.contracts import Family, digest, disclaimer

Weight = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class RankingPolicy(Contract):
    version: Literal["p12.ranking_policy.v1"] = "p12.ranking_policy.v1"
    horizon: Horizon
    classifier: Family = "logistic"
    regressor: Family = "ridge"
    selection_policy: Literal["FIXED_CONFIGURED_FAMILY_PER_TASK_HORIZON"] = (
        "FIXED_CONFIGURED_FAMILY_PER_TASK_HORIZON"
    )
    risk_policy: RiskPolicy = RiskPolicy()
    probability_weight: Weight = 0.45
    return_weight: Weight = 0.45
    context_weight: Weight = 0.10
    return_scale: Positive = 0.05
    risk_penalty_weight: Weight = 0.35
    uncertainty_penalty_weight: Weight = 0.20
    quality_penalty_weight: Weight = 0.10
    evidence_penalty_weight: Weight = 0.10
    missing_component_penalty: Annotated[float, Field(ge=0, le=0.5, allow_inf_nan=False)] = 0.05
    tie_policy: Literal["SCORE_DESCENDING_SECURITY_ID_ASCENDING"] = (
        "SCORE_DESCENDING_SECURITY_ID_ASCENDING"
    )
    research_selection_gate: Literal["INSUFFICIENT_SELECTION_EVIDENCE_BLOCKS_NON_TEST_ONLY"] = (
        "INSUFFICIENT_SELECTION_EVIDENCE_BLOCKS_NON_TEST_ONLY"
    )

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.classifier == "ridge"
            or self.regressor == "logistic"
            or self.probability_weight + self.return_weight <= 0
            or abs(self.probability_weight + self.return_weight + self.context_weight - 1) > 1e-12
            or self.risk_penalty_weight <= 0
            or self.uncertainty_penalty_weight <= 0
        ):
            raise ValueError(
                "Invalid task families/weights; risk and uncertainty must influence rank"
            )
        return self

    @property
    def policy_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class RankedCandidate(Contract):
    rank: int = Field(ge=1)
    security_id: str
    symbol: str | None
    session_date: date
    horizon: Horizon
    probability: Annotated[float, Field(ge=0, le=1)] | None
    predicted_return: Number | None
    components: dict[str, Number | None]
    raw_opportunity_score: Annotated[float, Field(ge=0, le=1)]
    penalties: dict[str, Weight]
    risk_adjusted_score: Number
    overall_risk: Level
    model_confidence: Literal["INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    quality_state: QualityStatus
    evidence_state: Literal["INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    availability: Availability
    observed_price_available_at: AwareDatetime | None
    reasons: tuple[str, ...]
    prediction_evidence_ids: tuple[Hash, ...]
    model_run_ids: tuple[Hash, ...]
    evaluation_ids: tuple[Hash, ...]
    feature_set_id: Hash
    canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    risk_snapshot_id: Hash
    previous_rank: int | None = Field(default=None, ge=1)
    rank_change: int | None = None
    previous_rank_snapshot_id: Hash | None = None
    sector: Literal[None] = None
    sector_state: Literal["UNAVAILABLE"] = "UNAVAILABLE"

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.overall_risk == "UNAVAILABLE"
            or self.quality_state == QualityStatus.REJECTED
            or self.probability is None
            and self.predicted_return is None
            or abs(
                self.risk_adjusted_score
                - (self.raw_opportunity_score - sum(self.penalties.values()))
            )
            > 1e-12
            or self.reasons != tuple(sorted(set(self.reasons)))
            or set(self.components)
            != {"probability", "normalized_return", "p6_momentum_percentile"}
            or set(self.penalties)
            != {"risk", "uncertainty", "quality", "evidence", "missing_components"}
            or any(value is not None and not 0 <= value <= 1 for value in self.components.values())
            or (self.previous_rank is None) != (self.previous_rank_snapshot_id is None)
            or self.rank_change != (self.previous_rank - self.rank if self.previous_rank else None)
        ):
            raise ValueError("Ranked candidate eligibility/score/history contradiction")
        return self


class ExcludedCandidate(Contract):
    security_id: str
    symbol: str | None
    reasons: tuple[str, ...]
    risk_snapshot_id: Hash | None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if not self.reasons or self.reasons != tuple(sorted(set(self.reasons))):
            raise ValueError("Exclusion requires stable explicit reasons")
        return self


class RankSnapshot(Contract):
    rank_snapshot_id: Hash
    ranking_version: Literal["p12.ranking.v1"] = "p12.ranking.v1"
    session_date: date
    knowledge_cutoff: AwareDatetime
    horizon: Horizon
    policy: RankingPolicy
    classification: Classification
    feature_set_id: Hash
    canonical_input_id: Hash
    canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    universe_definition_id: str
    prediction_set_id: Hash
    risk_snapshot_ids: tuple[Hash, ...]
    model_selection_status: Literal["TEST_ONLY_SELECTED_CANDIDATE", "INSUFFICIENT_EVIDENCE"]
    model_selection_evidence: Literal["INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    model_comparison: dict[str, Any]
    ranked: tuple[RankedCandidate, ...]
    excluded: tuple[ExcludedCandidate, ...]
    previous_snapshot_id: Hash | None
    downstream_references: dict[str, str]
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        keys = [r.security_id for r in self.ranked] + [r.security_id for r in self.excluded]
        expected = sorted(self.ranked, key=lambda r: (-r.risk_adjusted_score, r.security_id))
        for row in self.ranked:
            expected_return = (
                0.5 + 0.5 * tanh(row.predicted_return / self.policy.return_scale)
                if row.predicted_return is not None
                else None
            )
            weights = (
                self.policy.probability_weight,
                self.policy.return_weight,
                self.policy.context_weight,
            )
            values = (row.probability, expected_return, row.components["p6_momentum_percentile"])
            observed = [
                (v, w) for v, w in zip(values, weights, strict=True) if v is not None and w > 0
            ]
            if (
                not observed
                or row.components["probability"] != row.probability
                or row.components["normalized_return"] != expected_return
                or abs(
                    row.raw_opportunity_score
                    - sum(v * w for v, w in observed) / sum(w for _, w in observed)
                )
                > 1e-12
                or row.penalties["evidence"] != self.policy.evidence_penalty_weight
                or abs(
                    row.penalties["missing_components"]
                    - self.policy.missing_component_penalty * sum(v is None for v in values)
                )
                > 1e-12
            ):
                raise ValueError("Ranking component/configuration contradiction")
        if (
            self.classification == Classification.PRODUCTION
            or self.classification != Classification.TEST_ONLY
            and self.ranked
            or self.disclaimer != disclaimer(self.classification)
            or self.policy.horizon != self.horizon
            or self.model_selection_status
            != ("TEST_ONLY_SELECTED_CANDIDATE" if self.ranked else "INSUFFICIENT_EVIDENCE")
            or len(keys) != len(set(keys))
            or list(self.ranked) != expected
            or [r.rank for r in self.ranked] != list(range(1, len(self.ranked) + 1))
            or [r.security_id for r in self.excluded]
            != sorted(r.security_id for r in self.excluded)
            or self.risk_snapshot_ids != tuple(sorted(set(self.risk_snapshot_ids)))
            or any(
                r.session_date != self.session_date
                or r.horizon != self.horizon
                or r.feature_set_id != self.feature_set_id
                or r.canonical_dataset_id != self.canonical_dataset_id
                or r.universe_snapshot_id != self.universe_snapshot_id
                or r.risk_snapshot_id not in self.risk_snapshot_ids
                or r.previous_rank_snapshot_id not in (None, self.previous_snapshot_id)
                for r in self.ranked
            )
            or self.rank_snapshot_id
            != digest(self.model_dump(mode="json", exclude={"rank_snapshot_id"}))
        ):
            raise ValueError("Ranking identity/classification/order contradiction")
        return self

    def top(self, count: int) -> tuple[RankedCandidate, ...]:
        if count < 1:
            raise ValueError("Top-N must be positive")
        return self.ranked[:count]
