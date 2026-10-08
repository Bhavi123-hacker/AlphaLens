"""P5 research wrapper retaining P2 exact values and P3 states without PIT upgrades."""

from typing import Any, Literal
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, model_validator

from alphalens_data.canonical.models import EODValues
from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import CanonicalEOD, Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchAssessment, ResearchProfile, require_research


class ResearchObservation(Contract):
    schema_version: Literal["p5.research.canonical.v1"] = "p5.research.canonical.v1"
    profile: ResearchProfile
    canonical_record_id: Hash
    source: CanonicalEOD
    values: EODValues
    quality: Literal["VALID", "DEGRADED", "REJECTED"]
    quality_reasons: tuple[str, ...]
    assessment: ResearchAssessment
    assumed_available_at: AwareDatetime | None
    availability_basis: Literal["ASSUMED_NEXT_SESSION_AVAILABILITY"] = (
        "ASSUMED_NEXT_SESSION_AVAILABILITY"
    )
    price_basis: Literal["RAW_UNADJUSTED"] = "RAW_UNADJUSTED"
    basis_reference: Literal["PINNED_TEJHQ_NATIVE_RAW_PRICE_TREE"] = (
        "PINNED_TEJHQ_NATIVE_RAW_PRICE_TREE"
    )

    @model_validator(mode="after")
    def original(self) -> "ResearchObservation":
        require_research(self.profile, self.source.classification)
        if self.assumed_available_at is not None and (
            self.assumed_available_at.astimezone(ZoneInfo("Asia/Kolkata")).date()
            <= self.source.session_date
        ):
            raise ValueError("RESEARCH_AVAILABILITY_MUST_FOLLOW_SOURCE_SESSION")
        if any(
            getattr(self.values, n) != getattr(self.source, n)
            for n in ("open", "high", "low", "close", "volume")
        ):
            raise ValueError("RESEARCH_CANONICAL_MUST_PRESERVE_P2_VALUES")
        expected = checksum(
            stable_json(self.model_dump(mode="json", exclude={"canonical_record_id"}))
        )
        if self.canonical_record_id != expected:
            raise ValueError("RESEARCH_CANONICAL_ID_MISMATCH")
        return self


def save_manifest(connection: psycopg.Connection[Any], data: dict[str, Any]) -> None:
    """Durable immutable manifest referencing checksum-pinned local Parquet partitions."""
    identity = data["identity"]
    profile = ResearchProfile.model_validate(identity["research_profile"])
    if checksum(stable_json(identity)) != data["dataset_id"] or (
        identity["research_profile_id"] != profile.profile_id
    ):
        raise ValueError("RESEARCH_REGISTRY_IDENTITY_MISMATCH")
    connection.execute(
        "INSERT INTO research.datasets "
        "(dataset_id,profile_id,classification,final_vintage,payload) "
        "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (dataset_id) DO NOTHING",
        (
            data["dataset_id"],
            profile.profile_id,
            "RESEARCH_ONLY",
            profile.final_vintage,
            Jsonb(data),
        ),
    )
    stored = connection.execute(
        "SELECT payload FROM research.datasets WHERE dataset_id=%s", (data["dataset_id"],)
    ).fetchone()
    if stored is None or stored[0] != data:
        raise ValueError("RESEARCH_REGISTRY_IMMUTABLE_PAYLOAD_CONFLICT")
