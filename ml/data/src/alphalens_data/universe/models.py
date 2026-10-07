"""Revision-preserving effective facts with independently evidenced knowledge times."""

from datetime import date
from enum import StrEnum
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, model_validator

from alphalens_data.contracts import AvailabilityBasis, Contract, NonEmpty
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import (
    VALIDATOR_VERSION,
    QualityStatus,
    ValidationReport,
    ValidationSeverity,
)

IDENTITY_VERSION = "p4.identity.v1"
MEMBERSHIP_VERSION = "p4.membership.v1"
UNIVERSE_VERSION = "p4.universe.v1"


class SecurityType(StrEnum):
    COMMON_EQUITY = "COMMON_EQUITY"
    ETF = "ETF"
    REIT = "REIT"
    INVIT = "INVIT"
    PREFERENCE = "PREFERENCE"
    DEBT = "DEBT"
    UNKNOWN = "UNKNOWN"


class FactProvenance(Contract):
    source: NonEmpty
    artifact_reference: NonEmpty
    artifact_sha256: Hash
    evidence_reference: NonEmpty
    classification: Classification
    rights_evidence: NonEmpty | None = None
    ingested_at: AwareDatetime
    published_at: AwareDatetime | None = None
    available_at: AwareDatetime | None = None
    availability_basis: AvailabilityBasis = AvailabilityBasis.UNKNOWN

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production historical-universe use is not cleared")
        if (
            self.classification
            in (
                Classification.RESEARCH_FIXTURE,
                Classification.RESEARCH_ONLY,
            )
            and not self.rights_evidence
        ):
            raise ValueError("Research evidence requires accepted rights/attribution reference")
        if any(
            "://" in value
            for value in (self.source, self.artifact_reference, self.evidence_reference)
        ):
            raise ValueError("Use non-secret references, not provider request URLs")
        if (self.available_at is None) != (self.availability_basis == AvailabilityBasis.UNKNOWN):
            raise ValueError("Known availability requires an explicit supported basis")
        if self.available_at and self.available_at > self.ingested_at:
            raise ValueError("Availability cannot follow ingestion")
        if self.published_at and (
            self.published_at > self.ingested_at
            or (self.available_at and self.published_at > self.available_at)
        ):
            raise ValueError("Publication/availability/ingestion inversion")
        return self


class EffectiveFact(Contract):
    fact_id: NonEmpty
    revision_id: NonEmpty
    supersedes_revision_id: NonEmpty | None = None
    security_id: NonEmpty
    effective_from: date
    effective_to: date | None = None
    provenance: FactProvenance

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.effective_to and self.effective_from >= self.effective_to:
            raise ValueError("Effective intervals must be positive half-open intervals")
        return self


class IdentityFact(EffectiveFact):
    source_security_id: NonEmpty
    symbol: NonEmpty
    series: NonEmpty | None = None
    isin: NonEmpty | None = None
    aliases: tuple[NonEmpty, ...] = ()
    identity_version: Literal["p4.identity.v1"] = "p4.identity.v1"


class MembershipFact(EffectiveFact):
    listing_status: Literal["LISTED", "DELISTED", "NOT_YET_LISTED", "UNKNOWN"]
    security_type: SecurityType
    membership_version: Literal["p4.membership.v1"] = "p4.membership.v1"


class UniverseDefinition(Contract):
    universe_id: Literal["TEST_DYNAMIC_CASH_UNIVERSE", "RESEARCH_DYNAMIC_NSE_CASH"]
    version: Literal["p4.universe.v1"] = "p4.universe.v1"
    classification: Classification
    evidence_scope: Literal["HISTORICAL_EVIDENCE", "CURRENT_SNAPSHOT_ONLY"]
    coverage_status: Literal["VERIFIED", "PARTIALLY_VERIFIED", "UNKNOWN", "NOT_SUPPORTED"]
    coverage_reference: NonEmpty

    @model_validator(mode="after")
    def development_scope(self) -> Self:
        allowed = (
            {Classification.TEST_ONLY}
            if self.universe_id == "TEST_DYNAMIC_CASH_UNIVERSE"
            else {Classification.RESEARCH_FIXTURE, Classification.RESEARCH_ONLY}
        )
        if self.classification not in allowed:
            raise ValueError("Universe definition/classification mismatch")
        return self


class QualityEvidence(Contract):
    source: NonEmpty
    session_date: date
    report: ValidationReport
    report_sha256: Hash
    available_at: AwareDatetime | None = None
    ingested_at: AwareDatetime
    evidence_reference: NonEmpty

    @model_validator(mode="after")
    def integrity(self) -> Self:
        if checksum(self.report.to_bytes()) != self.report_sha256:
            raise ValueError("P3 report checksum mismatch")
        if any(i.validator_version != self.report.validator_version for i in self.report.issues):
            raise ValueError("P3 issue/report validator versions disagree")
        if any(s.session_date != self.session_date for s in self.report.sessions):
            raise ValueError("Quality evidence must be scoped to one session")
        if len({s.security_id for s in self.report.sessions}) != len(self.report.sessions):
            raise ValueError("Duplicate P3 session assessments")
        blocking = {ValidationSeverity.ERROR, ValidationSeverity.FATAL}
        dataset_blocked = any(
            i.severity in blocking and i.security_id is None for i in self.report.issues
        )
        expected = (
            QualityStatus.REJECTED
            if any(i.severity in blocking for i in self.report.issues)
            else QualityStatus.DEGRADED
            if any(i.severity == ValidationSeverity.WARNING for i in self.report.issues)
            else QualityStatus.VALID
        )
        if self.report.status != expected or self.report.dataset_blocked != dataset_blocked:
            raise ValueError("P3 gate contradicts recorded severities")
        by_record = {rid: s.security_id for s in self.report.sessions for rid in s.record_ids}
        rejected_securities = {
            i.security_id
            for i in self.report.issues
            if i.severity in blocking and i.session_date in (None, self.session_date)
        }
        rejected_securities.update(
            by_record[rid]
            for i in self.report.issues
            if i.severity in blocking
            for rid in i.record_ids
            if rid in by_record
        )
        for s in self.report.sessions:
            if (
                s.security_id in rejected_securities or dataset_blocked
            ) and s.status != QualityStatus.REJECTED:
                raise ValueError("P3 session gate contradicts blocking issues")
        if self.available_at and (
            self.available_at > self.ingested_at
            or (self.available_at.astimezone(ZoneInfo("Asia/Kolkata")).date() < self.session_date)
        ):
            raise ValueError("Quality availability contradicts session/receipt")
        return self


class UniverseInput(Contract):
    definition: UniverseDefinition
    identities: tuple[IdentityFact, ...]
    memberships: tuple[MembershipFact, ...]
    quality: tuple[QualityEvidence, ...] = ()


class UniverseEntry(Contract):
    security_id: NonEmpty
    universe_membership: bool
    membership_reason: NonEmpty
    identity: IdentityFact | None
    membership_evidence: MembershipFact | None
    evidence_status: Literal["VERIFIED", "PARTIALLY_VERIFIED", "UNKNOWN"]
    data_quality_status: QualityStatus | Literal["UNAVAILABLE"]
    data_quality_reasons: tuple[NonEmpty, ...]
    analysis_eligible: bool
    analysis_reason: NonEmpty


class UniverseSnapshot(Contract):
    snapshot_id: Hash
    session_date: date
    decision_time: AwareDatetime
    knowledge_mode: Literal["historical", "live"]
    universe_definition: UniverseDefinition
    identity_version: Literal["p4.identity.v1"] = "p4.identity.v1"
    membership_version: Literal["p4.membership.v1"] = "p4.membership.v1"
    validator_version: Literal["p3.quality.v1", "p3.quality.v2"] = VALIDATOR_VERSION
    input_sha256: Hash
    known_evidence_sha256: Hash
    historical_universe_status: Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"]
    eligible_securities: tuple[UniverseEntry, ...]
    excluded_securities: tuple[UniverseEntry, ...]
    input_artifact_references: tuple[NonEmpty, ...]
    production_claims_permitted: Literal[False] = False

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))


class SurvivorshipAudit(Contract):
    classification: Classification
    snapshot_ids: tuple[Hash, ...]
    unique_historical_security_count: int
    entries: int
    exits: int
    symbol_changes: int
    exclusions_by_reason: dict[str, int]
    unknown_classification_count: int
    unavailable_membership_evidence_count: int
    historically_present_absent_at_end: tuple[NonEmpty, ...]
    data_quality_exclusion_count: int
    limitations: tuple[str, ...] = (
        "Counts describe requested snapshots, not unobserved exchange sessions",
        "Fixture evidence does not establish real NSE survivorship-bias control",
    )
    production_claims_permitted: Literal[False] = False

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))
