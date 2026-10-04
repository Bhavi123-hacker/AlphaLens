"""P1 canonical EOD contracts. Constructed test records must carry TEST_ONLY origin."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

NonEmpty = Annotated[str, Field(min_length=1, max_length=256)]
PositiveDecimal = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="after")
    @classmethod
    def normalize_instants(cls, value: object) -> object:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        return value


class CapabilityStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    VERIFIED_SUPPORTED = "VERIFIED_SUPPORTED"
    VERIFIED_UNSUPPORTED = "VERIFIED_UNSUPPORTED"


class Capability(StrEnum):
    EOD_PRICES = "EOD_PRICES"
    FUNDAMENTALS = "FUNDAMENTALS"
    CORPORATE_ACTIONS = "CORPORATE_ACTIONS"
    HISTORICAL_MEMBERSHIP = "HISTORICAL_MEMBERSHIP"
    DEPARTED_SECURITIES = "DEPARTED_SECURITIES"
    PUBLICATION_TIMESTAMPS = "PUBLICATION_TIMESTAMPS"
    REVISIONS = "REVISIONS"
    LICENSED_SAMPLE_USE = "LICENSED_SAMPLE_USE"


class CapabilityEvidence(Contract):
    capability: Capability
    status: CapabilityStatus = CapabilityStatus.UNKNOWN
    evidence_reference: NonEmpty | None = None
    verified_at: AwareDatetime | None = None
    scope: NonEmpty | None = None

    @model_validator(mode="after")
    def require_evidence(self) -> Self:
        if self.status != CapabilityStatus.UNKNOWN and (
            self.evidence_reference is None or self.verified_at is None or self.scope is None
        ):
            raise ValueError("Verified status needs scoped evidence and verification time")
        return self


class ProviderCapabilities(Contract):
    provider_id: NonEmpty
    evidence: tuple[CapabilityEvidence, ...] = ()

    @model_validator(mode="after")
    def unique_capabilities(self) -> Self:
        keys = [item.capability for item in self.evidence]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate capability evidence")
        return self

    def status(self, capability: Capability) -> CapabilityStatus:
        return next(
            (item.status for item in self.evidence if item.capability == capability),
            CapabilityStatus.UNKNOWN,
        )


class AvailabilityBasis(StrEnum):
    UNKNOWN = "UNKNOWN"
    VERIFIED_PUBLICATION = "VERIFIED_PUBLICATION"
    CONSERVATIVE_BOUND = "CONSERVATIVE_BOUND"


class Provenance(Contract):
    source_id: NonEmpty
    source_record_id: NonEmpty
    revision_id: NonEmpty
    ingested_at: AwareDatetime
    available_at: AwareDatetime | None = None
    published_at: AwareDatetime | None = None
    availability_basis: AvailabilityBasis = AvailabilityBasis.UNKNOWN
    availability_evidence: NonEmpty | None = None
    origin: Literal["REAL_PROVIDER", "TEST_ONLY"]
    schema_version: Literal["p1.v1"] = "p1.v1"

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.available_at is None:
            if self.availability_basis != AvailabilityBasis.UNKNOWN:
                raise ValueError("Unknown availability cannot have a verified basis")
        else:
            if (
                self.availability_basis == AvailabilityBasis.UNKNOWN
                or not self.availability_evidence
            ):
                raise ValueError("Known availability requires evidence and basis")
            if self.available_at > self.ingested_at:
                raise ValueError("Availability cannot be later than recorded ingestion")
            if self.published_at is not None and self.available_at < self.published_at:
                raise ValueError("Availability cannot precede publication")
        if self.published_at is not None and self.published_at > self.ingested_at:
            raise ValueError("Publication cannot be later than ingestion")
        return self


class Record(Contract):
    security_id: NonEmpty
    exchange: Literal["NSE"] = "NSE"
    currency: Literal["INR"] = "INR"
    provenance: Provenance


class PriceBar(Record):
    session_date: date
    session_close_at: AwareDatetime
    interval: Literal["1D"] = "1D"
    open: PositiveDecimal
    high: PositiveDecimal
    low: PositiveDecimal
    close: PositiveDecimal
    volume: Annotated[int, Field(ge=0, strict=True)]
    turnover: NonNegativeDecimal | None = None
    adjusted_close: PositiveDecimal | None = None
    adjustment_method_version: NonEmpty | None = None

    @model_validator(mode="after")
    def valid_bar(self) -> Self:
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("OHLC outside high/low bounds")
        if self.low > self.high:
            raise ValueError("Low exceeds high")
        if self.session_close_at.astimezone(ZoneInfo("Asia/Kolkata")).date() != self.session_date:
            raise ValueError("Session date does not match NSE local close date")
        available = self.provenance.available_at
        if available is not None and self.session_close_at > available:
            raise ValueError("Completed bar cannot be available before session close")
        if self.session_close_at > self.provenance.ingested_at:
            raise ValueError("Completed bar cannot be ingested before session close")
        if (self.adjusted_close is None) != (self.adjustment_method_version is None):
            raise ValueError("Adjusted close and methodology must be supplied together")
        return self


class FundamentalValue(Contract):
    name: Literal["revenue", "eps", "net_income", "free_cash_flow", "roe", "roce", "pe", "pb"]
    value: Annotated[Decimal, Field(allow_inf_nan=False)] | None
    unit: NonEmpty


class FundamentalRecord(Record):
    period_end: date
    values: tuple[FundamentalValue, ...]

    @model_validator(mode="after")
    def unique_metrics(self) -> Self:
        names = [value.name for value in self.values]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate fundamental metric")
        return self


class CorporateAction(Record):
    action_id: NonEmpty
    action_type: Literal["SPLIT", "DIVIDEND", "BONUS", "MERGER", "DEMERGER", "DELISTING"]
    event_at: AwareDatetime
    effective_from: AwareDatetime
    effective_to: AwareDatetime | None = None
    ratio: PositiveDecimal | None = None
    cash_amount: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("Effective interval must be positive")
        return self


class UniverseMembership(Record):
    universe_id: Literal["NIFTY_500"]
    effective_from: AwareDatetime
    effective_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("Effective interval must be positive")
        return self


class HistoryRequest(Contract):
    security_ids: Annotated[tuple[NonEmpty, ...], Field(min_length=1)]
    start_session: date
    end_session: date
    as_of: AwareDatetime

    @model_validator(mode="after")
    def valid_request(self) -> Self:
        if self.start_session > self.end_session:
            raise ValueError("Start session exceeds end session")
        if len(self.security_ids) != len(set(self.security_ids)):
            raise ValueError("Duplicate requested security IDs")
        return self


class UniverseRequest(Contract):
    universe_id: Literal["NIFTY_500"]
    as_of: AwareDatetime
