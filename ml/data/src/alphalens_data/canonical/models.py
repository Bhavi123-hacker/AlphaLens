"""Versioned canonical contracts reuse P2 lineage, P3 reports and P4 facts."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, TypeAdapter, field_validator, model_validator

from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.ingestion.contracts import (
    Classification,
    Hash,
    QuarantineRecord,
    RawManifest,
    RunReport,
)
from alphalens_data.ingestion.normalizing import decimal_value
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import QualityStatus
from alphalens_data.universe.models import (
    FactProvenance,
    IdentityFact,
    MembershipFact,
    QualityEvidence,
    UniverseDefinition,
    UniverseSnapshot,
)

SCHEMA_VERSION: Literal["p5.canonical.v1"] = "p5.canonical.v1"


class Availability(StrEnum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class Security(Contract):
    security_id: NonEmpty
    exchange: Literal["NSE"] = "NSE"
    classification: Classification

    @model_validator(mode="after")
    def development(self) -> Self:
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production canonical data not cleared")
        return self


class ReadContext(Contract):
    knowledge_cutoff: AwareDatetime
    mode: Literal["historical", "live"] = "historical"
    earliest_acceptable_availability: AwareDatetime | None = None
    freshness_evidence_reference: NonEmpty | None = None

    @model_validator(mode="after")
    def freshness(self) -> Self:
        if (self.earliest_acceptable_availability is None) != (
            self.freshness_evidence_reference is None
        ):
            raise ValueError("Freshness bound requires explicit policy evidence")
        if (
            self.earliest_acceptable_availability
            and self.earliest_acceptable_availability > self.knowledge_cutoff
        ):
            raise ValueError("Freshness bound cannot follow cutoff")
        return self


class RevisionBase(Contract):
    schema_version: Literal["p5.canonical.v1"] = SCHEMA_VERSION
    logical_record_id: NonEmpty
    revision_id: NonEmpty
    revision_number: Annotated[int, Field(ge=1, strict=True)]
    supersedes_revision_id: NonEmpty | None = None
    security_id: NonEmpty | None
    effective_from: date
    effective_to: date | None = None
    provenance: FactProvenance

    @model_validator(mode="after")
    def temporal(self) -> Self:
        if self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("Positive half-open effective interval required")
        if (self.revision_number == 1) != (self.supersedes_revision_id is None):
            raise ValueError("Revision root must be number 1; later revisions need parent")
        return self


class IdentityRevision(RevisionBase):
    kind: Literal["IDENTITY"] = "IDENTITY"
    fact: IdentityFact
    display_name: NonEmpty | None = None
    currency: Literal["INR"] | None = None
    exchange_security_id: NonEmpty | None = None
    metadata_evidence_reference: NonEmpty | None = None

    @model_validator(mode="after")
    def original_fact(self) -> Self:
        _same_p4_fact(self, self.fact)
        if (
            any((self.display_name, self.currency, self.exchange_security_id))
            and not self.metadata_evidence_reference
        ):
            raise ValueError("Additional identity attributes require same-revision evidence")
        return self


class MembershipRevision(RevisionBase):
    kind: Literal["MEMBERSHIP"] = "MEMBERSHIP"
    fact: MembershipFact

    @model_validator(mode="after")
    def original_fact(self) -> Self:
        _same_p4_fact(self, self.fact)
        return self


def _same_p4_fact(record: RevisionBase, fact: IdentityFact | MembershipFact) -> None:
    if (
        record.logical_record_id != fact.fact_id
        or record.security_id != fact.security_id
        or record.revision_id != fact.revision_id
        or record.supersedes_revision_id != fact.supersedes_revision_id
        or record.provenance != fact.provenance
        or record.effective_from != fact.effective_from
        or record.effective_to != fact.effective_to
    ):
        raise ValueError("Canonical wrapper must preserve original P4 fact exactly")


class SessionRevision(RevisionBase):
    kind: Literal["SESSION"] = "SESSION"
    session_date: date
    exchange: Literal["NSE"] = "NSE"
    market_type: Literal["CASH"] = "CASH"
    session_type: Literal["EOD"] = "EOD"
    status: Literal[
        "VERIFIED_TRADING_SESSION", "VERIFIED_NON_TRADING_SESSION", "UNKNOWN_SESSION_STATUS"
    ]
    calendar_evidence_reference: NonEmpty | None = None
    session_close_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def session_evidence(self) -> Self:
        if self.security_id is not None or self.effective_from != self.session_date:
            raise ValueError("Session is exchange-level and starts on session_date")
        if self.status != "UNKNOWN_SESSION_STATUS" and not self.calendar_evidence_reference:
            raise ValueError("Verified calendar status requires scoped source evidence")
        if self.session_close_at and (
            self.session_close_at.astimezone(ZoneInfo("Asia/Kolkata")).date() != self.session_date
        ):
            raise ValueError("Close instant must match exchange-local session date")
        return self


class EODValues(Contract):
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Annotated[int, Field(ge=0, le=2**63 - 1, strict=True)]
    turnover: Decimal | None = None
    trade_count: Annotated[int, Field(ge=0, le=2**63 - 1, strict=True)] | None = None
    vwap: Decimal | None = None

    @field_validator("open", "high", "low", "close", "turnover", "vwap", mode="before")
    @classmethod
    def exact_input(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def financial(self) -> Self:
        for name in ("open", "high", "low", "close"):
            decimal_value(str(getattr(self, name)))  # P2 exact positive decimal policy
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close
        ):
            raise ValueError("P2 OHLC invariants violated")
        if self.turnover is not None:
            exact_decimal(self.turnover)
            if self.turnover < 0:
                raise ValueError("Turnover cannot be negative")
        if self.vwap is not None:
            decimal_value(str(self.vwap))
        return self


def exact_decimal(value: Decimal) -> None:
    if not value.is_finite():
        raise ValueError("Finite numeric required")
    _, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int) or exponent < -18 or len(digits) + exponent > 20:
        raise ValueError("Exact NUMERIC(38,18) capacity exceeded; no rounding")


def reject_float(value: object) -> object:
    if isinstance(value, float):
        raise ValueError("Persisted financial values require Decimal or exact decimal text")
    return value


class AdjustmentEvidence(Contract):
    method: NonEmpty
    version: NonEmpty
    factor: Decimal
    corporate_action_key: Hash
    original_price_key: Hash
    effective_date: date
    provenance: FactProvenance

    @field_validator("factor", mode="before")
    @classmethod
    def exact_input(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def factor_evidence(self) -> Self:
        decimal_value(str(self.factor))
        if self.provenance.available_at is None:
            raise ValueError("Adjustment requires evidenced availability")
        return self


class PriceRevision(RevisionBase):
    kind: Literal["BAR"] = "BAR"
    session_date: date
    price_basis: Literal["OBSERVED_UNKNOWN_BASIS", "RAW_UNADJUSTED", "ADJUSTED"]
    price_basis_evidence: NonEmpty | None = None
    values: EODValues | None
    currency: Literal["INR"] | None
    session_close_at: AwareDatetime | None = None
    quality_key: Hash | None = None
    rejection_reason_codes: tuple[NonEmpty, ...] = ()
    adjustment: AdjustmentEvidence | None = None

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if not self.security_id or self.effective_from != self.session_date:
            raise ValueError("Bar requires durable security and session date")
        if self.price_basis != "OBSERVED_UNKNOWN_BASIS" and not self.price_basis_evidence:
            raise ValueError("Known price basis requires source evidence")
        if (self.price_basis == "ADJUSTED") != (self.adjustment is not None):
            raise ValueError("Adjusted values require explicit adjustment evidence")
        if self.values is None and not self.rejection_reason_codes:
            raise ValueError("Unavailable values require explicit rejected-source reasons")
        if self.session_close_at:
            if (
                self.session_close_at.astimezone(ZoneInfo("Asia/Kolkata")).date()
                != self.session_date
            ):
                raise ValueError("Session close date mismatch")
            if self.session_close_at > self.provenance.ingested_at or (
                self.provenance.available_at
                and self.session_close_at > self.provenance.available_at
            ):
                raise ValueError("Completed EOD bar used before evidenced close")
        if self.provenance.available_at is not None and self.session_close_at is None:
            raise ValueError("Known completed-bar availability requires evidenced close")
        if self.adjustment and (
            self.provenance.available_at is None
            or self.adjustment.provenance.available_at is None
            or self.adjustment.provenance.available_at > self.provenance.available_at
        ):
            raise ValueError("Adjusted observation predates adjustment knowledge")
        return self


class ActionRevision(RevisionBase):
    kind: Literal["ACTION"] = "ACTION"
    corporate_action_id: NonEmpty
    event_type: Literal[
        "SPLIT",
        "BONUS",
        "DIVIDEND",
        "RIGHTS",
        "MERGER",
        "DEMERGER",
        "SYMBOL_CHANGE",
        "DELISTING",
        "OTHER",
    ]
    ex_date: date | None = None
    record_date: date | None = None
    payment_date: date | None = None
    factor: Decimal | None = None
    cash_value: Decimal | None = None
    currency: Literal["INR"] | None = None

    @field_validator("factor", "cash_value", mode="before")
    @classmethod
    def exact_input(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def action(self) -> Self:
        if not self.security_id:
            raise ValueError("Action requires durable security identity")
        if self.factor is not None:
            decimal_value(str(self.factor))
        if self.cash_value is not None:
            exact_decimal(self.cash_value)
            if self.cash_value < 0 or self.currency is None:
                raise ValueError("Cash event value requires nonnegative value and known currency")
        if self.record_date and self.payment_date and self.payment_date < self.record_date:
            raise ValueError("Payment cannot precede record date")
        return self


class FundamentalRevision(RevisionBase):
    kind: Literal["FUNDAMENTAL"] = "FUNDAMENTAL"
    fact_name: NonEmpty
    statement_type: Literal["BALANCE_SHEET", "INCOME_STATEMENT", "CASH_FLOW", "OTHER"]
    reporting_basis: Literal["STANDALONE", "CONSOLIDATED", "UNKNOWN"]
    period_start: date | None
    period_end: date
    unit: NonEmpty
    currency: Literal["INR"] | None = None
    value: Decimal | None
    restatement: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def exact_input(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def period(self) -> Self:
        if not self.security_id or self.period_start and self.period_start > self.period_end:
            raise ValueError("Invalid security/reporting period")
        if self.value is not None:
            exact_decimal(self.value)  # Signed values can be meaningful; no positivity rule.
        return self


class QualityRevision(RevisionBase):
    kind: Literal["QUALITY"] = "QUALITY"
    evidence: QualityEvidence

    @model_validator(mode="after")
    def report(self) -> Self:
        if (
            self.security_id is not None
            or self.effective_from != self.evidence.session_date
            or self.provenance.source != self.evidence.source
            or self.provenance.classification != self.evidence.report.classification
            or self.provenance.available_at != self.evidence.available_at
            or self.provenance.ingested_at != self.evidence.ingested_at
            or self.provenance.artifact_sha256 != self.evidence.report_sha256
        ):
            raise ValueError("Canonical quality must preserve P3/P4 evidence exactly")
        return self


Revision = Annotated[
    IdentityRevision
    | MembershipRevision
    | SessionRevision
    | PriceRevision
    | ActionRevision
    | FundamentalRevision
    | QualityRevision,
    Field(discriminator="kind"),
]
REVISION_ADAPTER: TypeAdapter[Revision] = TypeAdapter(Revision)


def revision_key(record: Revision) -> str:
    return checksum(
        stable_json(
            [
                record.kind,
                record.provenance.source,
                record.logical_record_id,
                record.revision_id,
                record.provenance.classification,
            ]
        )
    )


def revision_bytes(record: Revision) -> bytes:
    return stable_json(record.model_dump(mode="json"))


class NormalizedEvidence(Contract):
    normalized_record_id: Hash
    artifact_id: Hash
    normalization_version: NonEmpty
    payload: dict[str, object]


class QuarantineEvidence(Contract):
    quarantine_key: Hash
    record: QuarantineRecord


class RecordLineage(Contract):
    record_key: Hash
    artifact_id: Hash
    normalized_record_id: Hash | None = None
    source_record_id: Hash | None = None
    quarantine_key: Hash | None = None
    evidence_reference: NonEmpty

    @model_validator(mode="after")
    def path(self) -> Self:
        if (self.normalized_record_id is None) == (self.quarantine_key is None):
            raise ValueError("Lineage requires normalized evidence OR preserved P2 quarantine")
        return self


class CanonicalBatch(Contract):
    classification: Classification
    securities: tuple[Security, ...]
    definition: UniverseDefinition
    artifacts: tuple[RawManifest, ...]
    runs: tuple[RunReport, ...]
    normalized: tuple[NormalizedEvidence, ...]
    quarantine: tuple[QuarantineEvidence, ...]
    revisions: tuple[Revision, ...]
    lineage: tuple[RecordLineage, ...]

    def to_bytes(self) -> bytes:
        data = self.model_dump(mode="json")
        for key, identity in (
            ("securities", "security_id"),
            ("artifacts", "artifact_id"),
            ("runs", "run_id"),
            ("normalized", "normalized_record_id"),
            ("quarantine", "quarantine_key"),
        ):
            data[key].sort(key=lambda r: r[identity])
        data["revisions"] = [
            r.model_dump(mode="json") for r in sorted(self.revisions, key=revision_key)
        ]
        data["lineage"].sort(
            key=lambda link: (
                link["record_key"],
                link["artifact_id"],
                link["normalized_record_id"] or "",
                link["quarantine_key"] or "",
            )
        )
        return stable_json(data)

    @property
    def input_id(self) -> str:
        return checksum(self.to_bytes())


class CanonicalRead[T](Contract):
    availability: Availability
    records: tuple[T, ...]
    reason_codes: tuple[NonEmpty, ...] = ()


class PriceView(Contract):
    observation: PriceRevision
    quality: QualityStatus | Literal["UNAVAILABLE"]
    availability: Availability
    universe_membership: bool
    analysis_eligible: bool
    reason_codes: tuple[NonEmpty, ...]


class CanonicalDataset(Contract):
    dataset_id: Hash
    schema_version: Literal["p5.canonical.v1"] = SCHEMA_VERSION
    input_id: Hash
    classification: Classification
    context: ReadContext
    start_session: date
    end_session: date
    normalization_versions: tuple[NonEmpty, ...]
    validation_versions: tuple[NonEmpty, ...]
    universe_definition: UniverseDefinition
    artifact_hashes: tuple[Hash, ...]
    prices: tuple[PriceView, ...]
    identities: tuple[IdentityRevision, ...]
    sessions: tuple[SessionRevision, ...]
    corporate_actions: tuple[ActionRevision, ...]
    quality: tuple[QualityRevision, ...]
    universe_snapshots: tuple[UniverseSnapshot, ...]
    family_states: dict[str, Availability]
    production_claims_permitted: Literal[False] = False

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))
