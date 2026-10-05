"""Versioned P2 artifact and EOD lineage contracts, independent of vendor APIs."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract, NonEmpty

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]


class Classification(StrEnum):
    TEST_ONLY = "TEST_ONLY"
    RESEARCH_FIXTURE = "RESEARCH_FIXTURE"
    PRODUCTION = "PRODUCTION"


class Versions(Contract):
    parser: NonEmpty
    normalization: Literal["p2.eod.v1"] = "p2.eod.v1"
    schema_version: Literal["p2.v1"] = "p2.v1"


class ArtifactSpec(Contract):
    source: Slug
    dataset: Slug
    source_identifier: NonEmpty
    source_session_date: date | None = None
    original_filename: NonEmpty
    content_type: NonEmpty = "text/csv"
    classification: Classification
    currency: Literal["INR"] | None = None
    currency_evidence: NonEmpty | None = None
    rights_evidence: NonEmpty | None = None

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if (self.currency is None) != (self.currency_evidence is None):
            raise ValueError("Currency and supporting evidence must be supplied together")
        if self.classification == Classification.PRODUCTION:
            raise ValueError("P1_PRODUCTION_DATA_CLEARANCE = OPEN; production capture is disabled")
        if self.classification == Classification.RESEARCH_FIXTURE and not self.rights_evidence:
            raise ValueError("Research fixture requires accepted rights/attribution reference")
        # Persist identifiers, not request URLs that might contain credentials.
        if "://" in self.source_identifier:
            raise ValueError("Use a non-secret source identifier, not a request URL")
        return self


class RawManifest(Contract):
    artifact_id: Hash
    nominal_id: Hash
    spec: ArtifactSpec
    acquired_at: AwareDatetime
    raw_path: NonEmpty
    byte_size: Annotated[int, Field(ge=0)]
    sha256: Hash
    versions: Versions
    prior_revision_ids: tuple[Hash, ...] = ()


class CanonicalEOD(Contract):
    record_id: Hash
    normalized_record_id: Hash
    artifact_id: Hash
    raw_sha256: Hash
    source: Slug
    source_version: Hash
    versions: Versions
    classification: Classification
    security_id: NonEmpty
    identity_basis: Literal["SOURCE_SECURITY_ID", "SOURCE_SCOPED_SYMBOL"]
    symbol: NonEmpty | None
    isin: NonEmpty | None
    series: NonEmpty | None
    source_row_identifier: NonEmpty
    source_filename: NonEmpty
    source_row_number: int
    source_row_sha256: Hash
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    currency: Literal["INR"] | None
    acquired_at: AwareDatetime
    session_close_at: None = None
    published_at: None = None
    available_at: None = None
    adjustment_basis: None = None
    production_claims_permitted: Literal[False] = False


class QuarantineRecord(Contract):
    artifact_id: Hash
    raw_sha256: Hash
    versions: Versions
    classification: Classification
    source_row_number: int
    original_row: tuple[str, ...]
    validation_rule: NonEmpty
    reason: NonEmpty
    timestamp: AwareDatetime


class RunReport(Contract):
    run_id: Hash
    artifact_id: Hash
    versions: Versions
    classification: Classification
    canonical_sha256: Hash
    quarantine_sha256: Hash
    canonical_count: int
    quarantined_row_count: int
    validation_error_count: int
    status: Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"]
    production_claims_permitted: Literal[False] = False
