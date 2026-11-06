"""Original offline provider adapters. No SDK, cookie workaround or outbound transport."""

import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.parsing import ParsedRow
from alphalens_data.normalization import checksum

from .multi_contracts import Access, Candle, Instrument, Outcome, ProviderName, Quote, RequestPlan

IST = ZoneInfo("Asia/Kolkata")
RATES: dict[ProviderName, dict[str, int | None]] = {
    "upstox": {
        "second": 50,
        "minute": 500,
        "half_hour": 2000,
        "day": None,
        "candle_batch": 1,
        "quote_batch": 500,
    },
    "indstocks": {
        "second": 5,
        "minute": None,
        "half_hour": None,
        "day": 100000,
        "candle_batch": 5,
        "quote_batch": 1000,
    },
    "angel-one": {
        "second": 3,
        "minute": 180,
        "half_hour": None,
        "day": None,
        "hour": 5000,
        "candle_batch": 1,
        "quote_batch": 50,
    },
    "alpha-vantage": {
        "second": None,
        "minute": None,
        "half_hour": None,
        "day": 25,
        "candle_batch": 1,
        "quote_batch": None,
    },
    "yahoo": {
        "second": None,
        "minute": None,
        "half_hour": None,
        "day": None,
        "candle_batch": None,
        "quote_batch": None,
    },
    "tejhq": {
        "second": None,
        "minute": None,
        "half_hour": None,
        "day": None,
        "candle_batch": None,
        "quote_batch": None,
    },
}


def decoded(payload: bytes) -> dict[str, Any]:
    if len(payload) > 2_000_000:
        raise DataContractError("PROVIDER_PAYLOAD_LIMIT")
    try:
        value = json.loads(payload, parse_float=Decimal, parse_constant=lambda _: None)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise DataContractError("PROVIDER_SCHEMA_INVALID") from None


class DisabledAdapter:
    """Typed capability boundary; even forged activation flags never cause network I/O."""

    def __init__(self, provider: ProviderName, access: Access | None = None) -> None:
        self.provider = provider
        self.access = access or Access(provider=provider)
        if self.access.provider != provider:
            raise DataContractError("PROVIDER_ACCESS_MISMATCH")

    def get_instruments(self) -> Outcome[tuple[Instrument, ...]]:
        return Outcome("BLOCKED", "LIVE_ACQUISITION_DISABLED")

    def search_instrument(self, query: str) -> Outcome[tuple[Instrument, ...]]:
        return Outcome("BLOCKED", "LIVE_ACQUISITION_DISABLED")

    def get_daily_ohlcv(
        self, instruments: tuple[Instrument, ...], start: date, end: date
    ) -> Outcome[tuple[Candle, ...]]:
        return Outcome("BLOCKED", "LIVE_ACQUISITION_DISABLED")

    def get_latest_quote(self, instruments: tuple[Instrument, ...]) -> Outcome[tuple[Quote, ...]]:
        return Outcome("BLOCKED", "NO_PERMITTED_LIVE_QUOTE")

    def get_market_status(self) -> Outcome[dict[str, str]]:
        return Outcome("UNAVAILABLE", "NO_VERIFIED_PROVIDER_SESSION_CALENDAR")

    def get_corporate_actions(self, instrument: Instrument) -> Outcome[dict[str, str]]:
        return Outcome("UNAVAILABLE", "CORPORATE_ACTION_COVERAGE_NOT_VERIFIED")

    def get_rate_limit_status(self) -> dict[str, int | None]:
        return {**RATES[self.provider], "provider_remaining_daily_allowance": None}

    def get_provider_health(self, at: datetime) -> dict[str, object]:
        return {
            "provider": self.provider,
            "state": "BLOCKED",
            "blockers": self.access.blockers(at),
            "collection_enabled": False,
            "trading": "UNSUPPORTED",
        }

    def get_provider_capabilities(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "transport": "DISABLED",
            "daily_parser": self.provider in {"upstox", "indstocks", "angel-one"},
            "quote": "DOCUMENTED_NOT_TESTED"
            if self.provider in {"upstox", "indstocks", "angel-one"}
            else "UNAVAILABLE",
            "corporate_actions": "UNAVAILABLE",
            "orders": "UNSUPPORTED",
        }

    def plan_daily(
        self, instruments: tuple[Instrument, ...], start: date, end: date
    ) -> RequestPlan:
        if (
            not instruments
            or start > end
            or len(instruments) > (RATES[self.provider]["candle_batch"] or 0)
        ):
            raise DataContractError("PROVIDER_REQUEST_SCOPE_INVALID")
        for item in instruments:
            if item.provider != self.provider or item.exchange != "NSE" or not item.isin:
                raise DataContractError("EXACT_NSE_INSTRUMENT_REQUIRED")
        if self.provider == "upstox":
            if (end - start).days > 3650:
                raise DataContractError("UPSTOX_CONSERVATIVE_TEN_YEAR_WINDOW_REQUIRED")
            return RequestPlan(
                provider=self.provider,
                operation="daily_ohlcv",
                method="GET",
                host="api.upstox.com",
                path=(
                    f"/v3/historical-candle/{quote(instruments[0].provider_key, safe='')}"
                    f"/days/1/{end}/{start}"
                ),
                credential_location="AUTHORIZATION_HEADER",
            )
        if self.provider == "indstocks":
            if (end - start).days > 364:
                raise DataContractError("INDSTOCKS_ONE_YEAR_WINDOW_REQUIRED")
            if any(not re.fullmatch(r"NSE_\d+", i.provider_key) for i in instruments):
                raise DataContractError("INDSTOCKS_NSE_CASH_CODE_REQUIRED")
            a = datetime.combine(start, datetime.min.time(), IST)
            b = datetime.combine(end + timedelta(days=1), datetime.min.time(), IST)
            return RequestPlan(
                provider=self.provider,
                operation="daily_ohlcv",
                method="GET",
                host="api.indstocks.com",
                path="/market/historical/1day",
                parameters={
                    "scrip-codes": ",".join(i.provider_key for i in instruments),
                    "start_time": str(int(a.timestamp() * 1000)),
                    "end_time": str(int(b.timestamp() * 1000)),
                },
                credential_location="AUTHORIZATION_HEADER",
            )
        if self.provider == "angel-one":
            if not re.fullmatch(r"\d+", instruments[0].provider_key):
                raise DataContractError("ANGEL_NUMERIC_INSTRUMENT_TOKEN_REQUIRED")
            if (end - start).days > 31:
                raise DataContractError("ANGEL_CONSERVATIVE_OFFLINE_WINDOW_EXCEEDED")
            return RequestPlan(
                provider=self.provider,
                operation="daily_ohlcv",
                method="POST",
                host="apiconnect.angelone.in",
                path="/rest/secure/angelbroking/historical/v1/getCandleData",
                body={
                    "exchange": "NSE",
                    "symboltoken": instruments[0].provider_key,
                    "interval": "ONE_DAY",
                    "fromdate": str(start) + " 00:00",
                    "todate": str(end) + " 23:59",
                },
                credential_location="AUTHORIZATION_HEADER",
            )
        raise DataContractError("NSE_DAILY_REQUEST_NOT_CLEARED")


def upstox_instruments(payload: bytes, received_at: datetime) -> tuple[Instrument, ...]:
    if len(payload) > 10_000_000:
        raise DataContractError("INSTRUMENT_MASTER_LIMIT")
    try:
        rows = json.loads(payload)
        if not isinstance(rows, list) or len(rows) > 20000:
            raise ValueError
        result = []
        for row in rows:
            if (
                row.get("exchange") != "NSE"
                or row.get("segment") != "NSE_EQ"
                or row.get("instrument_type") != "EQ"
            ):
                continue
            result.append(
                Instrument(
                    provider="upstox",
                    provider_key=row["instrument_key"],
                    exchange="NSE",
                    segment=row["segment"],
                    symbol=row["trading_symbol"],
                    isin=row["isin"],
                    name=row.get("name"),
                    instrument_type=row["instrument_type"],
                    series=None,
                    observed_at=received_at,
                    identity_evidence="UPSTOX_CURRENT_BOD_INSTRUMENT_JSON",
                    revision_sha256=checksum(payload),
                )
            )
        if len({r.provider_key for r in result}) != len(result):
            raise ValueError
        return tuple(result)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise DataContractError("UPSTOX_INSTRUMENT_MASTER_REJECTED") from None


def _parse_daily(
    payload: bytes,
    instrument: Instrument,
    received_at: datetime,
    classification: Literal["RESEARCH_ONLY", "TEST_ONLY"] = "RESEARCH_ONLY",
) -> tuple[Candle, ...]:
    """Offline only. Preserve provider open timestamps; never invent publication/revision."""
    data = decoded(payload)
    if instrument.exchange != "NSE" or instrument.segment not in {"NSE_EQ", "NSE"}:
        raise DataContractError("NSE_CASH_EVIDENCE_REQUIRED")
    provider = instrument.provider
    if provider == "upstox":
        if data.get("status") != "success":
            raise DataContractError("UPSTOX_RESPONSE_REJECTED")
        source = data["data"]["candles"]
    elif provider == "indstocks":
        if data.get("success") is not True:
            raise DataContractError("INDSTOCKS_RESPONSE_REJECTED")
        entry = data.get("data", {}).get(instrument.provider_key)
        if not entry:
            raise DataContractError("EXPECTED_INSTRUMENT_MISSING_FROM_RELEASE")
        source = [
            [
                datetime.fromtimestamp(int(r["ts"]), IST).isoformat(),
                r["o"],
                r["h"],
                r["l"],
                r["c"],
                r["v"],
            ]
            for r in entry.get("candles") or []
        ]
    elif provider == "angel-one":
        if data.get("status") is not True:
            raise DataContractError("ANGEL_RESPONSE_REJECTED")
        source = data.get("data")
    else:
        raise DataContractError("OFFLINE_DAILY_PARSER_NOT_SUPPORTED")
    if not isinstance(source, list) or len(source) > 10000:
        raise DataContractError("DAILY_CANDLE_LIMIT")
    output = []
    for row in source:
        if not isinstance(row, list) or len(row) not in {6, 7}:
            raise DataContractError("PROVIDER_CANDLE_SCHEMA_INVALID")
        stamp = datetime.fromisoformat(row[0])
        if stamp.tzinfo is None:
            raise DataContractError("PROVIDER_TIMESTAMP_TIMEZONE_UNKNOWN")
        if stamp > received_at or instrument.observed_at > received_at:
            raise DataContractError("FUTURE_PROVIDER_EVIDENCE")
        if (
            isinstance(row[5], bool)
            or Decimal(str(row[5])) != Decimal(str(row[5])).to_integral_value()
        ):
            raise DataContractError("VOLUME_MUST_BE_INTEGER")
        output.append(
            Candle(
                provider=provider,
                instrument=instrument,
                session=stamp.astimezone(IST).date(),
                open=row[1],
                high=row[2],
                low=row[3],
                close=row[4],
                volume=int(row[5]),
                event_time=stamp,
                received_at=received_at,
                classification=classification,
                raw_sha256=checksum(payload),
            )
        )
    if len({r.session for r in output}) != len(output):
        raise DataContractError("DUPLICATE_PROVIDER_SESSION")
    return tuple(sorted(output, key=lambda r: r.session))


def parse_daily(
    payload: bytes,
    instrument: Instrument,
    received_at: datetime,
    classification: Literal["RESEARCH_ONLY", "TEST_ONLY"] = "RESEARCH_ONLY",
) -> tuple[Candle, ...]:
    """Reject malformed native bodies without echoing provider messages or payloads."""
    try:
        return _parse_daily(payload, instrument, received_at, classification)
    except DataContractError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, OverflowError):
        raise DataContractError("PROVIDER_CANDLE_SCHEMA_INVALID") from None


def p2_rows(candles: tuple[Candle, ...]) -> tuple[ParsedRow, ...]:
    """P2 interoperability requires evidenced series and raw basis, never silent upgrading."""
    result = []
    for number, row in enumerate(candles, 2):
        if (
            row.price_basis != "RAW_UNADJUSTED"
            or row.instrument.series is None
            or not row.instrument.isin
        ):
            raise DataContractError("RAW_PRICE_BASIS_AND_SERIES_EVIDENCE_REQUIRED")
        instrument = row.instrument
        fields = {
            "security_id": instrument.canonical_security_id
            or f"{row.provider}:isin:{instrument.isin}",
            "symbol": instrument.symbol,
            "isin": instrument.isin or "",
            "series": instrument.series or "",
            "session_date": row.session.isoformat(),
            "open": str(row.open),
            "high": str(row.high),
            "low": str(row.low),
            "close": str(row.close),
            "volume": str(row.volume),
            "source_row_identifier": "provider-candle:" + str(number - 2),
        }
        result.append(ParsedRow(number, tuple(fields.values()), tuple(fields.items())))
    return tuple(result)
