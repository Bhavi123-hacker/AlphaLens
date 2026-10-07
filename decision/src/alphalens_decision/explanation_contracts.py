"""Offline local attribution and three-layer explanation contracts; no causal claims."""

import json
from datetime import date, datetime
from math import isclose
from typing import Any, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_decision.models import Horizon, Number, PredictionEvidence
from alphalens_decision.signal_contracts import State
from alphalens_evaluation.contracts import digest, disclaimer


class ExplanationPolicy(Contract):
    version: Literal["p14.explanation_policy.v1"] = "p14.explanation_policy.v1"
    revision: str = Field(default="initial", min_length=1)
    top_factors: int = Field(default=5, ge=1, le=20)
    display_digits: int = Field(default=6, ge=2, le=12)
    numeric_tolerance: float = Field(default=1e-6, gt=0, le=1e-4)
    tree_fallback: Literal["ORDERED_TRAIN_MEDIAN_PATH"] = "ORDERED_TRAIN_MEDIAN_PATH"
    reference_policy: Literal["FITTED_TRAINING_STATISTICS_ONLY"] = "FITTED_TRAINING_STATISTICS_ONLY"
    interpretation: Literal["ASSOCIATION_NOT_CAUSATION"] = "ASSOCIATION_NOT_CAUSATION"


class FeatureContribution(Contract):
    feature_name: str
    actual_value: Number | None
    effective_value: Number
    transformed_value: Number
    training_reference: Number | None
    contribution: Number
    direction: Literal["POSITIVE", "NEGATIVE", "ZERO"]
    raw_availability: str
    imputed: bool

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.imputed != (self.actual_value is None) or self.direction != (
            "POSITIVE" if self.contribution > 0 else "NEGATIVE" if self.contribution < 0 else "ZERO"
        ):
            raise ValueError("Local contribution direction/missingness contradiction")
        return self


class LocalAttribution(Contract):
    attribution_id: Hash
    version: Literal["p14.local_attribution.v1"] = "p14.local_attribution.v1"
    policy: ExplanationPolicy
    prediction: PredictionEvidence
    feature_row_id: Hash
    model_identity_json: str
    fitted_evidence_id: Hash
    method: Literal["LINEAR_COEFFICIENT", "NATIVE_TREE_SHAP", "ORDERED_TRAIN_MEDIAN_PATH"]
    scope: Literal["LOCAL_PREDICTION"] = "LOCAL_PREDICTION"
    output_space: Literal["LOG_ODDS", "PROBABILITY", "RETURN"]
    base_value: Number
    explained_output: Number
    prediction_value: Number
    contributions: tuple[FeatureContribution, ...]
    limitations: tuple[str, ...]
    classification: Classification
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        from scipy.special import expit

        prediction = self.prediction
        output = (
            float(expit(self.explained_output))
            if self.output_space == "LOG_ODDS"
            else (self.explained_output)
        )
        expected = (
            prediction.probability
            if prediction.task == "classification"
            else (prediction.prediction)
        )
        names = tuple(c.feature_name for c in self.contributions)
        identity = json.loads(self.model_identity_json)
        expected_method = (
            "LINEAR_COEFFICIENT"
            if prediction.family in {"logistic", "ridge"}
            else "NATIVE_TREE_SHAP"
            if prediction.family in {"lightgbm", "catboost", "xgboost"}
            else "ORDERED_TRAIN_MEDIAN_PATH"
        )
        expected_space = (
            "RETURN"
            if prediction.task == "regression"
            else "PROBABILITY"
            if expected_method == "ORDERED_TRAIN_MEDIAN_PATH"
            else "LOG_ODDS"
        )
        if (
            self.classification == Classification.PRODUCTION
            or self.classification != prediction.classification
            or self.disclaimer != disclaimer(self.classification)
            or digest(identity) != prediction.model_run_id
            or identity.get("evaluation_id") != prediction.evaluation_id
            or identity.get("model_family") != prediction.family
            or datetime.fromisoformat(identity["effective_training_cutoff"])
            != prediction.training_cutoff
            or identity["configuration"]["task"] != prediction.task
            or identity["configuration"]["horizon"] != prediction.horizon
            or tuple(identity.get("feature_order", ())) != names
            or names != tuple(dict.fromkeys(names))
            or not names
            or self.method != expected_method
            or self.output_space != expected_space
            or self.output_space == "RETURN"
            and prediction.task != "regression"
            or self.output_space != "RETURN"
            and prediction.task != "classification"
            or not isclose(
                self.base_value + sum(c.contribution for c in self.contributions),
                self.explained_output,
                abs_tol=self.policy.numeric_tolerance,
                rel_tol=self.policy.numeric_tolerance,
            )
            or expected is None
            or not isclose(output, expected, abs_tol=self.policy.numeric_tolerance)
            or self.prediction_value != expected
            or self.attribution_id
            != digest(self.model_dump(mode="json", exclude={"attribution_id"}))
        ):
            raise ValueError("Local attribution identity/additivity/prediction contradiction")
        return self


class EvidenceFactor(Contract):
    code: str
    text: str
    source_reference: str
    evidence: dict[str, Any]


class ChartAnnotation(Contract):
    session: date
    signal: State
    horizon: Horizon
    signal_snapshot_id: Hash
    explanation_id: Hash
    classification: Classification


class ExplainabilitySnapshot(Contract):
    explanation_id: Hash
    version: Literal["p14.explainability.v1"] = "p14.explainability.v1"
    policy: ExplanationPolicy
    signal_snapshot_id: Hash
    security_id: str
    symbol: str | None
    session_date: date
    knowledge_cutoff: AwareDatetime
    horizon: Horizon
    state: State
    headline: str
    plain_language_summary: tuple[str, ...]
    positive_factors: tuple[EvidenceFactor, ...]
    negative_factors: tuple[EvidenceFactor, ...]
    risk_factors: dict[str, Any]
    missing_evidence: tuple[EvidenceFactor, ...]
    feature_values: dict[str, Any]
    feature_contributions: tuple[LocalAttribution, ...]
    model_evidence: dict[str, Any]
    ranking_breakdown: dict[str, Any]
    invalidation_conditions: dict[str, Any]
    state_transition_conditions: dict[str, Any]
    data_freshness: dict[str, Any]
    lineage: dict[str, Any]
    classification: Classification
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.classification == Classification.PRODUCTION
            or self.disclaimer != disclaimer(self.classification)
            or any(a.classification != self.classification for a in self.feature_contributions)
            or self.lineage.get("signal_snapshot_id") != self.signal_snapshot_id
            or any(
                a.prediction.available_at > self.knowledge_cutoff
                or a.prediction.security_id != self.security_id
                or a.prediction.horizon != self.horizon
                or a.prediction.session_date != self.session_date
                for a in self.feature_contributions
            )
            or len({a.prediction.evidence_id for a in self.feature_contributions})
            != len(self.feature_contributions)
            or self.explanation_id
            != digest(self.model_dump(mode="json", exclude={"explanation_id"}))
        ):
            raise ValueError("Explanation identity/lineage/classification contradiction")
        return self

    def annotation(self) -> ChartAnnotation:
        return ChartAnnotation(
            session=self.session_date,
            signal=self.state,
            horizon=self.horizon,
            signal_snapshot_id=self.signal_snapshot_id,
            explanation_id=self.explanation_id,
            classification=self.classification,
        )
