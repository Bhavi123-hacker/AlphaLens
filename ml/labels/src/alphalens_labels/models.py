"""Targets have their own namespace, observation cutoff, maturity and exact evidence."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, field_validator, model_validator

from alphalens_data.canonical.models import Availability, reject_float
from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import stable_json

VERSION: Literal["p7.labels.v1"] = "p7.labels.v1"


class LabelPlan(Contract):
    outcome_cutoff: AwareDatetime
    outcome_end: date
    horizons: tuple[Annotated[int, Field(ge=1, le=20, strict=True)], ...] = (1, 5, 10, 20)
    quality_policy: Literal["VALID_ONLY", "ALLOW_DEGRADED"] = "ALLOW_DEGRADED"

    @model_validator(mode="after")
    def chronology(self) -> Self:
        if not self.horizons or list(self.horizons) != sorted(set(self.horizons)):
            raise ValueError("Unique ascending nonempty session horizons required")
        if self.outcome_end > self.outcome_cutoff.astimezone(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("Outcome scope cannot extend beyond observed exchange-local date")
        return self


class LabelDefinition(Contract):
    label_name: NonEmpty
    direction_name: NonEmpty
    label_version: NonEmpty = VERSION
    horizon: Annotated[int, Field(ge=1, le=20, strict=True)]
    target_type: Literal["RAW_RETURN_AND_BINARY_DIRECTION"] = "RAW_RETURN_AND_BINARY_DIRECTION"
    entry_convention: Literal["NEXT_VERIFIED_SESSION_OPEN"] = "NEXT_VERIFIED_SESSION_OPEN"
    exit_convention: Literal["H_TH_VERIFIED_FUTURE_SESSION_CLOSE"] = (
        "H_TH_VERIFIED_FUTURE_SESSION_CLOSE"
    )
    decision_timing_policy: Literal["CUTOFF_BEFORE_ENTRY_LOCAL_DATE_START"] = (
        "CUTOFF_BEFORE_ENTRY_LOCAL_DATE_START"
    )
    price_basis: Literal["UNADJUSTED", "ADJUSTED"]
    cost_assumption_status: Literal["RAW_MARKET_OUTCOME_NO_COSTS"] = "RAW_MARKET_OUTCOME_NO_COSTS"
    required_future_observations: tuple[NonEmpty, ...] = (
        "entry.open",
        "exit.close",
        "complete_session_grid",
        "window.quality",
        "window.membership",
    )
    null_policy: Literal["NULL_WITH_REASON_NO_FILL"] = "NULL_WITH_REASON_NO_FILL"
    quality_policy: Literal["VALID_ONLY", "ALLOW_DEGRADED"]
    decimal_precision: Literal[38] = 38
    decimal_rounding: Literal["ROUND_HALF_EVEN"] = "ROUND_HALF_EVEN"
    direction_policy: Literal["POSITIVE_1_NONPOSITIVE_0"] = "POSITIVE_1_NONPOSITIVE_0"


class LabelRow(Contract):
    security_id: NonEmpty
    session_date: date
    decision_time: AwareDatetime
    horizon: int
    entry_session: date | None
    target_session: date | None
    label_name: NonEmpty
    direction_name: NonEmpty
    label_definition_version: NonEmpty = VERSION
    return_value: Decimal | None
    direction_value: Literal[0, 1] | None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    exact_numerator: Decimal | None = None
    exact_denominator: Decimal | None = None
    maturity: Literal["MATURE", "NOT_YET_MATURE", "UNAVAILABLE", "TERMINAL_EVENT"]
    label_available_at: AwareDatetime | None
    quality_state: Availability
    reason_codes: tuple[NonEmpty, ...]
    canonical_dataset_id: Hash
    feature_canonical_dataset_id: Hash
    universe_snapshot_id: Hash
    input_revision_keys: tuple[Hash, ...]
    classification: Classification
    price_basis: Literal["UNADJUSTED", "ADJUSTED"]

    @field_validator(
        "return_value",
        "entry_price",
        "exit_price",
        "exact_numerator",
        "exact_denominator",
        mode="before",
    )
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def maturity_contract(self) -> Self:
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production labels not cleared")
        if (self.maturity == "MATURE") != (self.return_value is not None):
            raise ValueError("Only mature targets have values")
        if self.return_value is not None:
            if (
                not self.return_value.is_finite()
                or self.label_available_at is None
                or self.target_session is None
            ):
                raise ValueError("Finite mature outcome requires target and evidenced availability")
            if self.label_available_at <= self.decision_time:
                raise ValueError("Supervised outcome cannot be known at the feature decision")
            if (
                self.entry_session is None
                or self.entry_session <= self.session_date
                or self.target_session < self.entry_session
            ):
                raise ValueError("Entry/exit must belong to future sessions")
            if self.quality_state == Availability.UNAVAILABLE:
                raise ValueError("Mature numerical target requires usable quality")
            expected = 1 if self.return_value > 0 else 0
            if self.direction_value != expected:
                raise ValueError("Direction must follow positive/nonpositive policy")
        elif self.direction_value is not None:
            raise ValueError("Unavailable continuous target cannot have direction")
        elif self.label_available_at is not None or self.quality_state != Availability.UNAVAILABLE:
            raise ValueError("Unavailable outcome cannot claim numerical availability")
        if self.maturity != "MATURE" and not self.reason_codes:
            raise ValueError("Missing/terminal outcomes require reasons")
        return self


class LabelDataset(Contract):
    label_set_id: Hash
    schema_version: Literal["p7.labels.v1"] = VERSION
    canonical_dataset_id: Hash
    canonical_input_id: Hash
    feature_set_id: Hash
    classification: Classification
    universe_definition_version: NonEmpty
    plan: LabelPlan
    definitions: tuple[LabelDefinition, ...]
    rows: tuple[LabelRow, ...]
    production_claims_permitted: Literal[False] = False
    corporate_action_coverage: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"

    @model_validator(mode="after")
    def aligned(self) -> Self:
        if self.classification == Classification.PRODUCTION or any(
            r.classification != self.classification for r in self.rows
        ):
            raise ValueError("Development classification must propagate unchanged")
        keys = [(r.session_date, r.security_id, r.horizon) for r in self.rows]
        if keys != sorted(set(keys)):
            raise ValueError("Unique stable session/security/horizon order required")
        return self

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))
