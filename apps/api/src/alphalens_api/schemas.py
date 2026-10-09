"""Read-only P17 contracts. Missing economic values remain null, never zero."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

Horizon = Literal[1, 5, 10, 20]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Classification(Contract):
    data_reality: str = "REAL_MARKET_OBSERVATIONS"
    usage_classification: str = "RESEARCH_ONLY"
    final_vintage: str | None = "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
    research_profile: str | None = "RESEARCH_EOD_FINAL_VINTAGE_V1"
    p1_production_data_clearance: Literal["OPEN"] = "OPEN"
    production_market_data_use: Literal["NOT_CLEARED"] = "NOT_CLEARED"


class Page(Contract):
    limit: int
    offset: int
    has_more: bool
    total: int | None = None


class Envelope[T](Contract):
    data: T
    source: str
    as_of_session: date | None = None
    classification: Classification = Field(default_factory=Classification)
    version: str = "p17.api.v1"
    artifact_id: str | None = None
    provenance: dict[str, JsonValue] = Field(default_factory=dict)
    evidence_status: str = "AVAILABLE"
    quality_status: str = "RESEARCH_ONLY_NOT_PRODUCTION_PIT"
    missing_data_reasons: tuple[str, ...] = ()
    page: Page | None = None


class Error(Contract):
    error_code: str
    message: str
    request_id: str


class PricePoint(Contract):
    session: date
    symbol: str | None = None
    isin: str | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int | None = None
    canonical_record_id: str | None = None
    quality: str
    quality_reasons: tuple[str, ...] = ()
    observation_status: str
    price_basis: Literal["RAW_UNADJUSTED"] = "RAW_UNADJUSTED"
    freshness: Literal["HISTORICAL_EOD"] = "HISTORICAL_EOD"
    availability_basis: str = "ASSUMED_NEXT_SESSION_AVAILABILITY"


class IndicatorPoint(Contract):
    session: date
    value: float | None
    state: str
    quality: str
    canonical_record_id: str


class PredictionPoint(Contract):
    security_id: str
    session_date: date
    decision_time: AwareDatetime
    prediction_id: str
    model_id: str
    task: str
    horizon: Horizon
    fold_id: str
    phase: str
    score: float | None
    prediction: float | None
    canonical_record_id: str
    role: Literal["FOLD_TEST"] = "FOLD_TEST"
    interpretation: Literal["PERSISTED_OOS_RESEARCH_NOT_LIVE_SIGNAL"] = (
        "PERSISTED_OOS_RESEARCH_NOT_LIVE_SIGNAL"
    )


class Evidence(Contract):
    """Variable domain payload validated as JSON, preserving exact Fraction/Decimal strings."""

    record: dict[str, JsonValue]
