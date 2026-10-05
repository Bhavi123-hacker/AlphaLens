"""Immutable quality contracts. All supplied reference evidence is scope-specific."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.ingestion.contracts import (
    CanonicalEOD,
    Classification,
    Hash,
    QuarantineRecord,
    RawManifest,
    RunReport,
)
from alphalens_data.ingestion.storage import stable_json

VALIDATOR_VERSION: Literal["p3.quality.v1"] = "p3.quality.v1"


class ValidationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class QualityStatus(StrEnum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    REJECTED = "REJECTED"


class ValidationRule(Contract):
    rule_id: NonEmpty
    severity: ValidationSeverity
    description: NonEmpty


class ValidationIssue(Contract):
    rule_id: NonEmpty
    severity: ValidationSeverity
    security_id: NonEmpty | None = None
    session_date: date | None = None
    artifact_id: Hash | None = None
    source: NonEmpty | None = None
    record_ids: tuple[Hash, ...] = ()
    normalized_record_ids: tuple[Hash, ...] = ()
    original_row_numbers: tuple[int, ...] = ()
    message: NonEmpty
    action_status: (
        Literal[
            "KNOWN_CORPORATE_ACTION",
            "POSSIBLE_CORPORATE_ACTION",
            "NO_ACTION_EVIDENCE",
            "ACTION_DATA_UNAVAILABLE",
        ]
        | None
    ) = None
    validator_version: Literal["p3.quality.v1"] = VALIDATOR_VERSION


class QualityPolicy(Contract):
    version: Literal["p3.policy.v1"] = "p3.policy.v1"
    absolute_return: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)] = Decimal("0.5")
    high_low_ratio: Annotated[Decimal, Field(gt=1, allow_inf_nan=False)] = Decimal("1.5")
    volume_multiple: Annotated[Decimal, Field(gt=1, allow_inf_nan=False)] = Decimal("10")
    repeated_ohlc_sessions: Annotated[int, Field(ge=2)] = 5


class ArtifactEvidence(Contract):
    manifest: RawManifest
    observed_sha256: Hash | None = None
    observed_byte_size: int | None = None
    normalized_sha256: Hash | None = None
    run: RunReport | None = None


class ReferenceSession(Contract):
    security_id: NonEmpty
    session_date: date
    status: Literal["TRADING", "NON_TRADING"]
    evidence_reference: NonEmpty


class TemporalEvidence(Contract):
    record_id: Hash
    available_at: AwareDatetime | None = None
    published_at: AwareDatetime | None = None
    session_close_at: AwareDatetime | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    evidence_reference: NonEmpty


class ActionEvidence(Contract):
    security_id: NonEmpty
    session_date: date
    status: Literal["KNOWN_CORPORATE_ACTION", "POSSIBLE_CORPORATE_ACTION", "NO_ACTION_EVIDENCE"]
    evidence_reference: NonEmpty


class ValidationInput(Contract):
    records: tuple[CanonicalEOD, ...] = ()
    quarantine: tuple[QuarantineRecord, ...] = ()
    artifacts: tuple[ArtifactEvidence, ...] = ()
    classification: Classification = Classification.TEST_ONLY
    start_session: date | None = None
    end_session: date | None = None
    decision_time: AwareDatetime | None = None
    reference_sessions: tuple[ReferenceSession, ...] = ()
    temporal_evidence: tuple[TemporalEvidence, ...] = ()
    action_evidence: tuple[ActionEvidence, ...] = ()
    policy: QualityPolicy = QualityPolicy()


class DatasetQualitySummary(Contract):
    record_count: int
    valid_record_count: int
    quarantined_record_count: int
    error_count: int
    fatal_count: int
    warning_count: int
    unique_security_count: int
    first_session: date | None
    last_session: date | None
    duplicate_count: int
    candidate_gap_count: int
    confirmed_missing_session_count: int
    zero_volume_count: int
    price_anomaly_count: int
    provenance_complete_count: int
    provenance_missing_count: int
    valid_record_ratio: Decimal | None


class SessionQuality(Contract):
    security_id: NonEmpty
    session_date: date
    status: QualityStatus
    record_ids: tuple[Hash, ...]
    reason_codes: tuple[NonEmpty, ...]


class ValidationReport(Contract):
    validator_version: Literal["p3.quality.v1"] = VALIDATOR_VERSION
    classification: Classification
    input_sha256: Hash
    policy: QualityPolicy
    status: QualityStatus
    dataset_blocked: bool
    session_calendar_status: Literal["UNAVAILABLE", "PARTIALLY_VERIFIED"]
    universe_input_status: Literal["UNAVAILABLE", "PARTIALLY_VERIFIED"]
    summary: DatasetQualitySummary
    issues: tuple[ValidationIssue, ...]
    sessions: tuple[SessionQuality, ...]
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def development_only(self) -> Self:
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production validation remains disabled")
        return self

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))
