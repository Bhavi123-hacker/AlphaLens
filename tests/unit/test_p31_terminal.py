"""TEST_ONLY exact mapping, quote chronology and transient memory boundaries."""

import gzip
import json
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from workers.providers import upstox_terminal as terminal
from workers.providers.store import ProviderStore
from workers.providers.transient import expire_after
from workers.providers.upstox import Reply, UpstoxClient, instrument_master

from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_contracts import Instrument

AT = datetime(2026, 10, 14, 16, tzinfo=UTC)


def test_generic_master_does_not_depend_on_a_special_reliance_entry() -> None:
    i = identity()
    body = gzip.compress(
        json.dumps(
            [
                {
                    "exchange": "NSE",
                    "segment": "NSE_EQ",
                    "instrument_type": "EQ",
                    "instrument_key": i.provider_key,
                    "isin": i.isin,
                    "trading_symbol": i.symbol,
                    "name": i.name,
                }
            ]
        ).encode()
    )
    reply = Reply(200, body, AT, "ACCEPTED")
    instruments, metadata = instrument_master(reply, require_reliance=False)
    assert len(instruments) == 1 and instruments[0].provider_key == i.provider_key
    assert metadata["reliance_identity_verified"] is False
    with pytest.raises(DataContractError):
        instrument_master(reply)


def identity(number: int = 1) -> Instrument:
    isin = f"INE00000000{number}"
    return Instrument(
        provider="upstox",
        provider_key="NSE_EQ|" + isin,
        exchange="NSE",
        segment="NSE_EQ",
        symbol=f"TEST_ONLY_{number}",
        isin=isin,
        name="TEST_ONLY constructed identity",
        instrument_type="EQ",
        observed_at=AT,
        identity_evidence="TEST_ONLY_CURRENT_MASTER",
        revision_sha256="a" * 64,
    )


def payload(**changes: Any) -> bytes:
    i = identity()
    value = {
        "instrument_token": i.provider_key,
        "symbol": i.symbol,
        "timestamp": (AT - timedelta(seconds=1)).isoformat(),
        "last_trade_time": str(int((AT - timedelta(hours=6)).timestamp() * 1000)),
        "last_price": "978.9252499999999",
        "prev_close_price": "970.10",
        **changes,
    }
    return json.dumps({"status": "success", "data": {"NSE_EQ:" + i.symbol: value}}).encode()


def test_exact_change_uses_documented_previous_close_not_ohlc_close() -> None:
    result = terminal.quote(Reply(200, payload(ohlc={"close": 50}), AT, "ACCEPTED"), identity())
    assert result["state"] == "VALIDATED_SNAPSHOT" and result["ltp"] == "978.9252499999999"
    assert result["previous_close"] == "970.10"
    assert Decimal(result["change"]) == Decimal("978.9252499999999") - Decimal("970.10")
    assert result["is_final_eod_close"] is False


@pytest.mark.parametrize(
    "stamp",
    [
        (AT + timedelta(microseconds=1)).isoformat(),
        AT.replace(tzinfo=None).isoformat(),
        "not-a-time",
    ],
)
def test_future_naive_malformed_time_never_returns_ltp(stamp: str) -> None:
    result = terminal.quote(Reply(200, payload(timestamp=stamp), AT, "ACCEPTED"), identity())
    assert result["state"] in {"QUOTE_TIME_REJECTED", "QUOTE_SCHEMA_OR_VALUE_REJECTED"}
    assert "ltp" not in result


def test_https_server_skew_does_not_allow_future_quotes() -> None:
    result = terminal.quote(
        Reply(
            200,
            payload(timestamp=(AT + timedelta(seconds=1)).isoformat()),
            AT,
            "ACCEPTED",
            server_at=AT + timedelta(seconds=2),
        ),
        identity(),
    )
    assert result["state"] == "QUOTE_TIME_REJECTED"
    assert result["clock"]["server_minus_local_seconds"] == 2 and "ltp" not in result


@pytest.mark.parametrize(
    "changes",
    [
        {"instrument_token": identity(2).provider_key},
        {"symbol": "TEST_ONLY_OTHER"},
        {"last_price": True},
        {"last_price": "NaN"},
        {"last_price": "-1"},
        {"last_trade_time": "wrong"},
        {"last_trade_time": str(int((AT + timedelta(seconds=1)).timestamp() * 1000))},
    ],
)
def test_identity_price_and_last_trade_validation(changes: dict[str, Any]) -> None:
    result = terminal.quote(Reply(200, payload(**changes), AT, "ACCEPTED"), identity())
    assert result["state"] != "VALIDATED_SNAPSHOT" and "ltp" not in result


def test_missing_previous_close_does_not_fall_back_to_candles() -> None:
    result = terminal.quote(Reply(200, payload(prev_close_price=None), AT, "ACCEPTED"), identity())
    assert result["state"] == "VALIDATED_SNAPSHOT" and result["change_percent"] is None


def test_mapping_requires_same_latest_isin_and_symbol() -> None:
    i = identity()
    alias = {"last_observed": "2026-10-06", "isin": i.isin, "symbol": i.symbol}
    assert terminal.resolve((i,), [alias]) == i
    for bad in (
        {**alias, "isin": None},
        {**alias, "symbol": "TEST_ONLY_CHANGED"},
        {**alias, "isin": identity(2).isin},
    ):
        with pytest.raises(DataContractError):
            terminal.resolve((i,), [bad])
    with pytest.raises(DataContractError, match="AMBIGUOUS"):
        terminal.resolve((i,), [alias, {**alias, "isin": identity(2).isin}])


def test_ohlc_sessions_are_separate_and_future_values_rejected() -> None:
    i = identity()
    row: dict[str, Any] = {
        "open": "100",
        "high": "110",
        "low": "90",
        "close": "105",
        "volume": 100,
        "ts": int((AT - timedelta(hours=12)).timestamp() * 1000),
    }

    def reply(current: dict[str, Any], prior: dict[str, Any] | None) -> Reply:
        return Reply(
            200,
            json.dumps(
                {
                    "status": "success",
                    "data": {
                        "NSE_EQ:" + i.symbol: {
                            "instrument_token": i.provider_key,
                            "live_ohlc": current,
                            "prev_ohlc": prior,
                        }
                    },
                }
            ).encode(),
            AT,
            "ACCEPTED",
        )

    result = terminal.ohlc(reply(row, {**row, "ts": row["ts"] - 86_400_000}), i)
    assert (
        result["current"]["session"] == "2026-10-14"
        and result["previous"]["session"] == "2026-10-13"
    )
    assert terminal.ohlc(reply(row, None), i)["previous"] is None
    for bad in (
        {**row, "ts": int((AT + timedelta(seconds=1)).timestamp() * 1000)},
        {**row, "low": "109"},
        {**row, "volume": True},
    ):
        result = terminal.ohlc(reply(bad, None), i)
        assert result["current"] is None and result["state"] != "VALIDATED_PROVIDER_OHLC"
    assert terminal.ohlc(reply(row, row), i)["state"] != "VALIDATED_PROVIDER_OHLC"


def test_pending_empty_candles_cache_without_price_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderStore(tmp_path / "TEST_ONLY_p31")
    store.initialize()
    monkeypatch.setattr(terminal, "master", lambda *a: (identity(),))
    monkeypatch.setattr(terminal, "market", lambda *a: {"state": "CLOSED", "session": "2026-10-14"})
    calls = []

    def fake(self: UpstoxClient, operation: str, **kwargs: Any) -> Reply:
        calls.append(operation)
        return (
            Reply(
                200,
                json.dumps({"status": "success", "data": {"candles": []}}).encode(),
                AT,
                "ACCEPTED",
            )
            if operation == "candles"
            else Reply(503, b"", AT, "PROVIDER_OUTAGE")
        )

    monkeypatch.setattr(UpstoxClient, "get", fake)
    item = terminal.snapshot(store.root, keys=(identity().provider_key,), now=AT)["items"][0]
    assert item["state"] == "NO_PROVIDER_CANDLES" and item["latest_close"] is None
    assert item["current_session_status"] == "MARKET_CLOSED_EOD_CANDLE_PENDING"
    assert (
        terminal.snapshot(store.root, keys=(identity().provider_key,), now=AT)["items"][0]["rows"]
        == []
    )
    assert len(calls) == 3 and not list(store.root.glob("*candle*"))


def test_credential_rejection_stops_price_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderStore(tmp_path / "TEST_ONLY_p31")
    store.initialize()
    monkeypatch.setattr(terminal, "master", lambda *a: (identity(),))
    monkeypatch.setattr(terminal, "market", lambda *a: {"state": "CLOSED", "session": "2026-10-14"})
    calls = []

    def fake(self: UpstoxClient, operation: str, **kwargs: Any) -> Reply:
        calls.append(operation)
        return Reply(401, b"", AT, "AUTH_REJECTED")

    monkeypatch.setattr(UpstoxClient, "get", fake)
    item = terminal.snapshot(store.root, keys=(identity().provider_key,), now=AT)["items"][0]
    assert calls == ["quote"] and item["rows"] == [] and item["retained"] is False


def test_memory_expiry_does_not_need_a_subsequent_read_or_remove_a_newer_snapshot() -> None:
    cache: dict[str, Any] = {"TEST_ONLY": (1.0, {"TEST_ONLY_PRICE": "100"})}
    lock = threading.Lock()
    expired = threading.Event()
    expire_after(cache, "TEST_ONLY", 1.0, lock, 0.01)
    expired.wait(0.1)
    assert not cache
    cache["TEST_ONLY"] = (2.0, {"TEST_ONLY_PRICE": "101"})
    expire_after(cache, "TEST_ONLY", 1.0, lock, 0.01)
    expired.wait(0.1)
    assert cache["TEST_ONLY"][0] == 2.0
