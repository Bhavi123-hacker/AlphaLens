"""Explicit provider/calendar gates and independently versioned daily lineage."""

from datetime import date, datetime
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import CanonicalEOD, Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum

VERSION: Literal["p19.incremental.v1"] = "p19.incremental.v1"
Mode = Literal["DAILY", "HISTORICAL_REPLAY", "TEST_ONLY"]
State = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "BLOCKED_SOURCE",
    "BLOCKED_EVIDENCE",
    "FAILED",
    "RETRYABLE_FAILURE",
]


class Provider(Contract):
    source: str = "tejhq"
    dataset: str = "indian-markets"
    revision: str
    status: Literal[
        "SOURCE_APPROVED_FOR_RESEARCH",
        "SOURCE_CONDITIONALLY_SUPPORTED",
        "SOURCE_NOT_CLEARED",
        "SOURCE_UNAVAILABLE",
    ]
    automation_permitted: bool = False
    retention_permitted: bool = False
    research_permitted: bool = False
    evidence_reference: str
    reasons: tuple[str, ...] = ()

    def allowed(self, mode: Mode) -> bool:
        return mode != "DAILY" or (
            self.status == "SOURCE_APPROVED_FOR_RESEARCH"
            and self.automation_permitted
            and self.retention_permitted
            and self.research_permitted
        )


class Session(Contract):
    session: date
    status: Literal["TRADING", "NON_TRADING"]
    known_at: AwareDatetime
    evidence_reference: str
    evidence_type: Literal["OFFICIAL_VERIFIED_SESSION", "OBSERVED_DATASET_SESSION", "TEST_ONLY"]


class Calendar(Contract):
    version: Literal["p19.calendar.v1"] = "p19.calendar.v1"
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    sessions: tuple[Session, ...]
    completeness: str = "SCOPED_EVIDENCE_NOT_AUTHORITATIVE_COMPLETE"

    @model_validator(mode="after")
    def ordered(self) -> Self:
        dates = [s.session for s in self.sessions]
        if not dates or dates != sorted(set(dates)):
            raise ValueError("CALENDAR_REQUIRES_ORDERED_UNIQUE_SESSIONS")
        return self

    @property
    def identity(self) -> str:
        return checksum(stable_json(self.model_dump(mode="json")))

    def status(self, session: date, at: datetime) -> str:
        item = next((s for s in self.sessions if s.session == session and s.known_at <= at), None)
        return item.status if item else "UNKNOWN_SESSION_STATUS"

    def trailing(self, session: date, at: datetime, count: int) -> tuple[date, ...]:
        dates = tuple(
            s.session
            for s in self.sessions
            if s.session <= session and s.known_at <= at and s.status == "TRADING"
        )
        return dates[-count:]

    def expected(self, at: datetime) -> date | None:
        local = at.astimezone(ZoneInfo(self.timezone)).date()
        dates = [
            s.session
            for s in self.sessions
            if s.status == "TRADING" and s.session < local and s.known_at <= at
        ]
        return max(dates) if dates else None


class Request(Contract):
    version: Literal["p19.incremental.v1"] = VERSION
    execution_revision: Literal["p19.engine.v2"] = "p19.engine.v2"
    canonical_version: Literal["p19.canonical.v2"] = "p19.canonical.v2"
    mode: Mode
    session: date
    provider: Provider
    calendar: Calendar
    payload_sha256: Hash | None = None
    baseline_identity: Hash
    feature_registry_id: Hash
    decision_policy_id: Hash = "ef2d46837b347f1b6516ad942a0eca46b6785e4adfc41cc322673061152cf906"
    context_sha256: Hash = checksum(stable_json([]))
    source_filename: str = "nse_eod.parquet"
    expected_security_ids: tuple[str, ...] = ()
    feature_security_ids: tuple[str, ...] = Field(default=(), max_length=128)
    coverage_scope: str = "SOURCE_RELEASE_ONLY_NOT_ALL_NSE_EQUITIES"
    source_received_at: AwareDatetime
    timeout_seconds: int = Field(default=300, ge=1, le=3600)

    @model_validator(mode="after")
    def scope(self) -> Self:
        if self.mode == "TEST_ONLY" and any(
            s.evidence_type != "TEST_ONLY" for s in self.calendar.sessions
        ):
            raise ValueError("TEST_ONLY_CALENDAR_REQUIRED")
        if "://" in self.provider.evidence_reference or "://" in self.source_filename:
            raise ValueError("NONSECRET_REFERENCE_IDENTIFIERS_REQUIRED")
        if self.session > self.source_received_at.astimezone(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("SESSION_AFTER_RECEIPT")
        return self

    @property
    def run_id(self) -> str:
        # Receipt time is acquisition evidence, not a timestamp-only identity.
        return checksum(stable_json(self.model_dump(mode="json", exclude={"source_received_at"})))


class Observation(Contract):
    version: Literal["p19.canonical.v2"] = "p19.canonical.v2"
    source: CanonicalEOD
    stable_security_id: str
    analytical_type: str
    identity_reason: str
    quality: Literal["VALID", "DEGRADED", "REJECTED"]
    quality_reasons: tuple[str, ...]
    availability_basis: Literal["ACTUAL_RECEIPT_NOT_EXCHANGE_PUBLICATION"] = (
        "ACTUAL_RECEIPT_NOT_EXCHANGE_PUBLICATION"
    )
    price_basis: Literal["RAW_UNADJUSTED"] = "RAW_UNADJUSTED"

    @property
    def identity(self) -> str:
        identity = self.model_dump(mode="json")
        # Capture clocks remain in provenance, not economic content identity.
        identity["source"].pop("acquired_at")
        return checksum(stable_json(identity))
