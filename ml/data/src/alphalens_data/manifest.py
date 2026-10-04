"""Bounded P1 sample evidence. No fake counts, coverage or production freshness claims."""

from typing import Annotated, Literal

from pydantic import Field

from alphalens_data.contracts import Contract, HistoryRequest, NonEmpty


class SampleManifest(Contract):
    provider_id: NonEmpty
    request: HistoryRequest
    record_count: Annotated[int, Field(ge=0)]
    raw_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    normalized_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    origin: Literal["REAL_PROVIDER", "TEST_ONLY"]
    normalization_version: Literal["p1.canonical.v1"] = "p1.canonical.v1"
    evidence_scope: Literal["BOUNDED_PRICE_SAMPLE_NOT_FULL_P1_ACCEPTANCE"] = (
        "BOUNDED_PRICE_SAMPLE_NOT_FULL_P1_ACCEPTANCE"
    )
