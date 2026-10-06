"""Versioned feature definitions, explicit decision plans and pinned outputs."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.canonical.models import Availability
from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import stable_json

VERSION: Literal["p6.features.v1"] = "p6.features.v1"


class Decision(Contract):
    session_date: date
    knowledge_cutoff: AwareDatetime


class BuildPlan(Contract):
    history_start: date
    decisions: tuple[Decision, ...]
    benchmark_security_id: NonEmpty | None = None
    benchmark_evidence_reference: NonEmpty | None = None
    quality_policy: Literal["VALID_ONLY", "ALLOW_DEGRADED"] = "ALLOW_DEGRADED"
    price_basis: Literal["UNADJUSTED", "ADJUSTED"] = "UNADJUSTED"

    @model_validator(mode="after")
    def ordered(self) -> Self:
        dates = [d.session_date for d in self.decisions]
        if not dates or dates != sorted(set(dates)) or self.history_start > dates[0]:
            raise ValueError("Nonempty ordered unique decisions and historical start required")
        times = [d.knowledge_cutoff for d in self.decisions]
        if times != sorted(times):
            raise ValueError("Decision cutoffs must be chronological")
        if bool(self.benchmark_security_id) != bool(self.benchmark_evidence_reference):
            raise ValueError("Designated benchmark requires an evidence reference")
        return self


class FeatureDefinition(Contract):
    feature_name: NonEmpty
    feature_version: NonEmpty = VERSION
    feature_family: Literal[
        "RETURNS",
        "MOMENTUM",
        "TREND",
        "VOLATILITY",
        "VOLUME",
        "RELATIVE_STRENGTH",
        "MARKET_CONTEXT",
        "CROSS_SECTIONAL",
        "FUNDAMENTAL",
    ]
    required_inputs: tuple[NonEmpty, ...] = ("close",)
    lookback: Annotated[int, Field(ge=1, le=201)]
    minimum_history: Annotated[int, Field(ge=1, le=201)]
    cutoff_policy: Literal["EXPLICIT_AFTER_COMPLETED_SESSION"] = "EXPLICIT_AFTER_COMPLETED_SESSION"
    null_policy: Literal["NULL_WITH_REASON_NO_FILL"] = "NULL_WITH_REASON_NO_FILL"
    data_quality_policy: Literal["VALID_ONLY", "ALLOW_DEGRADED"]
    parameters: dict[str, int | str]
    formula: NonEmpty


class FeatureSet(Contract):
    feature_set_version: NonEmpty = VERSION
    definitions: tuple[FeatureDefinition, ...]
    plan: BuildPlan

    @model_validator(mode="after")
    def unique(self) -> Self:
        names = [d.feature_name for d in self.definitions]
        if len(names) != len(set(names)):
            raise ValueError("Unique feature names required")
        return self


class FeatureValue(Contract):
    value: Annotated[float, Field(allow_inf_nan=False)] | None
    state: Availability
    reason_codes: tuple[NonEmpty, ...] = ()

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if (self.value is None) != (self.state == Availability.UNAVAILABLE):
            raise ValueError("Null feature requires unavailable state; no placeholder values")
        if self.state != Availability.AVAILABLE and not self.reason_codes:
            raise ValueError("Unavailable/degraded features require reasons")
        return self


class FeatureRow(Contract):
    security_id: NonEmpty
    session_date: date
    decision_time: AwareDatetime
    knowledge_cutoff: AwareDatetime
    feature_set_version: NonEmpty = VERSION
    canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    input_versions: tuple[NonEmpty, ...]
    input_revision_keys: tuple[Hash, ...]
    classification: Classification
    price_basis: Literal["UNADJUSTED", "ADJUSTED"]
    quality_state: Availability
    analytical_eligible: bool
    reason_codes: tuple[NonEmpty, ...]
    corporate_action_keys: tuple[Hash, ...]
    values: dict[str, FeatureValue]

    @model_validator(mode="after")
    def development(self) -> Self:
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production feature use not cleared")
        if self.decision_time != self.knowledge_cutoff:
            raise ValueError("Explicit decision time is the feature knowledge cutoff")
        return self


class FeatureDataset(Contract):
    feature_set_id: Hash
    schema_version: Literal["p6.features.v1"] = VERSION
    canonical_dataset_id: Hash
    canonical_input_id: Hash
    classification: Classification
    universe_definition_version: NonEmpty
    feature_set: FeatureSet
    rows: tuple[FeatureRow, ...]
    fundamental_pit_data: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    production_claims_permitted: Literal[False] = False
    corporate_action_coverage: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"

    @model_validator(mode="after")
    def aligned(self) -> Self:
        if self.classification == Classification.PRODUCTION or any(
            r.classification != self.classification for r in self.rows
        ):
            raise ValueError("Development classification must propagate unchanged")
        keys = [(r.session_date, r.security_id) for r in self.rows]
        if keys != sorted(set(keys)):
            raise ValueError("Stable unique session/security ordering required")
        names = {d.feature_name for d in self.feature_set.definitions}
        if any(set(r.values) != names for r in self.rows):
            raise ValueError("Row feature columns must match versioned definitions")
        return self

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))
