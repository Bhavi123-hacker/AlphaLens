"""Exchange-explicit, read-only provider preparation; no network or policy promotion."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Protocol, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Hash

ProviderName = Literal["upstox", "indstocks", "angel-one", "alpha-vantage", "yahoo", "tejhq"]
Operation = Literal[
    "instruments", "search", "daily_ohlcv", "latest_quote", "market_status", "corporate_actions"
]


class AuthenticationKind(StrEnum):
    READ_ONLY_ANALYTICS = "READ_ONLY_ANALYTICS"


@dataclass(frozen=True)
class Outcome[T]:
    state: Literal["AVAILABLE", "UNAVAILABLE", "BLOCKED"]
    reason: str
    value: T | None = None


class Access(Contract):
    provider: ProviderName
    account_status: Literal["NOT_CONFIGURED", "UNDER_REVIEW", "INACTIVE", "ACTIVE"] = (
        "NOT_CONFIGURED"
    )
    credential_configured: bool = False
    permission_reference: str | None = None
    automation_permitted: bool = False
    retention_permitted: bool = False
    research_permitted: bool = False
    display_permitted: bool = False
    nse_verified: bool = False
    token_kind: Literal["NONE", "READ_ONLY_ANALYTICS", "PROVIDER_ACCESS"] = "NONE"
    token_expires_at: AwareDatetime | None = None
    operator_activation: bool = False

    def blockers(self, at: datetime) -> tuple[str, ...]:
        if at.tzinfo is None:
            raise ValueError("AWARE_PROVIDER_CHECK_TIME_REQUIRED")
        reasons = []
        if self.account_status != "ACTIVE":
            reasons.append("ACCOUNT_" + self.account_status)
        if not self.credential_configured and self.provider in {
            "upstox",
            "indstocks",
            "angel-one",
            "alpha-vantage",
        }:
            reasons.append("CREDENTIAL_NOT_CONFIGURED")
        if self.provider == "upstox" and self.token_kind != AuthenticationKind.READ_ONLY_ANALYTICS:
            reasons.append("READ_ONLY_ANALYTICS_TOKEN_REQUIRED")
        if self.token_expires_at is not None and self.token_expires_at <= at:
            reasons.append("TOKEN_EXPIRED")
        if not self.permission_reference or not all(
            (self.automation_permitted, self.retention_permitted, self.research_permitted)
        ):
            reasons.append("SOURCE_USAGE_NOT_CLEARED")
        if not self.nse_verified:
            reasons.append("NSE_EXCHANGE_NOT_VERIFIED")
        if not self.operator_activation:
            reasons.append("OPERATOR_ACTIVATION_DISABLED")
        return tuple(reasons)


class Instrument(Contract):
    provider: ProviderName
    provider_key: str = Field(min_length=1, max_length=128)
    exchange: Literal["NSE", "BSE", "UNKNOWN"]
    segment: str = Field(min_length=1, max_length=32)
    symbol: str = Field(min_length=1, max_length=64)
    isin: str | None = None
    series: str | None = None
    name: str | None = None
    instrument_type: str | None = None
    observed_at: AwareDatetime
    identity_evidence: str
    revision_sha256: Hash
    canonical_security_id: str | None = None
    identity_semantics: Literal["CURRENT_MASTER_NOT_HISTORICAL_MEMBERSHIP"] = (
        "CURRENT_MASTER_NOT_HISTORICAL_MEMBERSHIP"
    )

    @model_validator(mode="after")
    def scoped(self) -> Self:
        if self.isin is not None and (
            len(self.isin) != 12 or not self.isin.isalnum() or self.isin != self.isin.upper()
        ):
            raise ValueError("ISIN_FORMAT_INVALID")
        if (
            self.exchange == "NSE"
            and self.provider == "upstox"
            and (
                self.segment != "NSE_EQ"
                or not self.isin
                or self.provider_key != "NSE_EQ|" + self.isin
            )
        ):
            raise ValueError("NSE_INSTRUMENT_KEY_ISIN_MISMATCH")
        if self.provider == "yahoo" and (
            self.exchange == "NSE"
            and not self.provider_key.endswith(".NS")
            or self.exchange == "BSE"
            and not self.provider_key.endswith(".BO")
        ):
            raise ValueError("YAHOO_EXCHANGE_SUFFIX_MISMATCH")
        if (
            self.provider == "alpha-vantage"
            and self.provider_key.endswith(".BSE")
            and self.exchange != "BSE"
        ):
            raise ValueError("BSE_CANNOT_SUBSTITUTE_FOR_NSE")
        return self


class Candle(Contract):
    provider: ProviderName
    instrument: Instrument
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = Field(ge=0, strict=True)
    currency: Literal["INR"] = "INR"
    price_basis: Literal["RAW_UNADJUSTED", "ADJUSTED", "UNKNOWN"] = "UNKNOWN"
    event_time: AwareDatetime
    event_time_semantics: Literal["CANDLE_OPEN_NOT_PUBLICATION"] = "CANDLE_OPEN_NOT_PUBLICATION"
    received_at: AwareDatetime
    publication_time: AwareDatetime | None = None
    source_revision: str | None = None
    raw_sha256: Hash
    classification: Literal["TEST_ONLY", "RESEARCH_ONLY"]
    action_status: Literal["UNAVAILABLE", "TEST_ONLY_VERIFIED"] = "UNAVAILABLE"

    @model_validator(mode="after")
    def lineage(self) -> Self:
        if self.instrument.provider != self.provider:
            raise ValueError("PROVIDER_IDENTITY_MISMATCH")
        if self.session != self.event_time.astimezone(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("SESSION_CANDLE_DATE_MISMATCH")
        if any(not v.is_finite() or v <= 0 for v in (self.open, self.high, self.low, self.close)):
            raise ValueError("NONPOSITIVE_OR_NONFINITE_OHLC")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("OHLC_RANGE_INVALID")
        if self.event_time > self.received_at or self.instrument.observed_at > self.received_at:
            raise ValueError("FUTURE_PROVIDER_EVIDENCE")
        if self.publication_time is not None and self.publication_time > self.received_at:
            raise ValueError("PUBLICATION_AFTER_RECEIPT")
        if self.classification != "TEST_ONLY" and self.action_status == "TEST_ONLY_VERIFIED":
            raise ValueError("TEST_ONLY_ACTION_EVIDENCE_CANNOT_UPGRADE_REAL_DATA")
        return self


class RequestPlan(Contract):
    provider: ProviderName
    operation: Operation
    method: Literal["GET", "POST"]
    host: str
    path: str
    parameters: dict[str, str] = Field(default_factory=dict)
    body: dict[str, str] = Field(default_factory=dict)
    credential_location: Literal["NONE", "AUTHORIZATION_HEADER", "API_KEY_QUERY"]
    enabled: Literal[False] = False
    contains_credentials: Literal[False] = False


class Quote(Contract):
    provider: ProviderName
    instrument: Instrument
    price: Decimal = Field(gt=0)
    kind: Literal["INTRADAY_LTP", "DELAYED_QUOTE", "VERIFIED_EOD"]
    price_basis: Literal["RAW_UNADJUSTED", "ADJUSTED", "UNKNOWN"] = "UNKNOWN"
    exchange_event_time: AwareDatetime | None = None
    received_at: AwareDatetime
    source_revision: str | None = None
    raw_sha256: Hash

    @model_validator(mode="after")
    def scoped_quote(self) -> Self:
        if self.provider != self.instrument.provider or not self.price.is_finite():
            raise ValueError("QUOTE_PROVIDER_OR_VALUE_INVALID")
        if self.exchange_event_time and self.exchange_event_time > self.received_at:
            raise ValueError("QUOTE_EVENT_AFTER_RECEIPT")
        return self


class MarketProvider(Protocol):
    def get_instruments(self) -> Outcome[tuple[Instrument, ...]]: ...
    def search_instrument(self, query: str) -> Outcome[tuple[Instrument, ...]]: ...
    def get_daily_ohlcv(
        self, instruments: tuple[Instrument, ...], start: date, end: date
    ) -> Outcome[tuple[Candle, ...]]: ...
    def get_latest_quote(
        self, instruments: tuple[Instrument, ...]
    ) -> Outcome[tuple[Quote, ...]]: ...
    def get_market_status(self) -> Outcome[dict[str, str]]: ...
    def get_corporate_actions(self, instrument: Instrument) -> Outcome[dict[str, str]]: ...
    def get_rate_limit_status(self) -> dict[str, int | None]: ...
    def get_provider_health(self, at: datetime) -> dict[str, object]: ...
    def get_provider_capabilities(self) -> dict[str, object]: ...
