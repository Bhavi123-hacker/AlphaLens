"""Fail-closed eligibility helpers, not a full P3 quality/quarantine engine."""

from datetime import datetime
from typing import Literal

from alphalens_data.contracts import AvailabilityBasis, Record, UniverseMembership
from alphalens_data.errors import DataContractError


def eligible_at(
    record: Record, at: datetime, *, mode: Literal["historical", "live"] = "historical"
) -> bool:
    if at.tzinfo is None or at.utcoffset() is None:
        raise DataContractError("NAIVE_DECISION_TIMESTAMP")
    if mode not in {"historical", "live"}:
        raise DataContractError("INVALID_ELIGIBILITY_MODE")
    provenance = record.provenance
    if (
        provenance.available_at is None
        or provenance.availability_basis == AvailabilityBasis.UNKNOWN
        or provenance.available_at > at
    ):
        return False
    return mode == "historical" or provenance.ingested_at <= at


def member_at(record: UniverseMembership, at: datetime) -> bool:
    return (
        eligible_at(record, at)
        and record.effective_from <= at
        and (record.effective_to is None or at < record.effective_to)
    )
