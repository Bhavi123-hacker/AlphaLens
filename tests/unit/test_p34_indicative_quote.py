"""TEST_ONLY classifications, adversarial display boundaries and consumer isolation."""

import inspect
import json
import time
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from test_p31_terminal import AT, identity
from test_p34_quote_clock import observation
from workers.personal.analytics import mark, provider_request_failed
from workers.providers import upstox_terminal as terminal
from workers.providers.indicative import STATE, expire_field, uncertain_quote, visible
from workers.providers.upstox import Reply
from workers.providers.watchlist import cached


def ambiguous(**updates: Any) -> Reply:
    reply = observation()
    body = json.loads(reply.body)
    body["data"]["NSE_EQ:" + identity().symbol].update(
        {"timestamp": (AT + timedelta(seconds=0.20)).isoformat(), **updates}
    )
    return replace(reply, body=json.dumps(body).encode())


def test_strict_verified_validator_is_byte_for_byte_unchanged_from_1261977() -> None:
    assert sha256(inspect.getsource(terminal.quote).encode()).hexdigest() == (
        "cec00eb40aa4c9c6f01ecbad2c3a55c4af6bc42b7bb5ae196ce505ea8326d5b1"
    )


def test_strict_rejection_remains_and_indicative_price_is_explicitly_separate() -> None:
    reply = ambiguous()
    strict = terminal.quote(reply, identity())
    original = json.dumps(strict, sort_keys=True)
    display = uncertain_quote(reply, identity(), strict)
    assert display and display["state"] == STATE
    assert strict["state"] == "QUOTE_TIME_REJECTED" and "ltp" not in strict
    assert json.dumps(strict, sort_keys=True) == original
    assert display["ltp"] == "978.9252499999999" and display["previous_close"] == "970.10"
    assert display["display_only"] is True and display["strict_verified"] is False
    assert display["financial_input_eligible"] is False and not display["is_final_eod_close"]
    assert display["clock"]["local_received_at"] == AT.isoformat()
    assert display["raw_provider_timestamp"] == (AT + timedelta(seconds=0.20)).isoformat()


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0.15, "VERIFIED"),
        (0.18, "VERIFIED"),
        (0.180001, "INDICATIVE"),
        (0.20, "INDICATIVE"),
        (0.22, "INDICATIVE"),
        (0.220001, "REJECTED"),
        (1, "REJECTED"),
        (-31, "REJECTED"),
    ],
)
def test_three_states_at_exact_interval_boundaries(seconds: float, expected: str) -> None:
    reply = ambiguous(
        timestamp=(AT + timedelta(seconds=seconds)).isoformat(),
        last_trade_time=str(int((AT - timedelta(seconds=60)).timestamp() * 1000)),
    )
    strict = terminal.quote(reply, identity())
    display = uncertain_quote(reply, identity(), strict)
    actual = (
        "VERIFIED"
        if strict["state"] == "VALIDATED_SNAPSHOT"
        else "INDICATIVE"
        if display
        else "REJECTED"
    )
    assert actual == expected


@pytest.mark.parametrize(
    "updates",
    [
        {"timestamp": "malformed"},
        {"timestamp": AT.replace(tzinfo=None).isoformat()},
        {"last_trade_time": True},
        {"last_trade_time": str(int((AT + timedelta(seconds=0.21)).timestamp() * 1000))},
        {"last_price": "NaN"},
        {"last_price": "Infinity"},
        {"last_price": True},
        {"last_price": "-1"},
        {"prev_close_price": 0},
        {"prev_close_price": True},
        {"instrument_token": identity(2).provider_key},
        {"symbol": "TEST_ONLY_WRONG"},
    ],
)
def test_invalid_quotes_never_fall_through_to_indicative(updates: dict[str, Any]) -> None:
    reply = ambiguous(**updates)
    strict = terminal.quote(reply, identity())
    assert uncertain_quote(reply, identity(), strict) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"clock_required": False},
        {"calibration": None},
        {"state": "AUTH_REJECTED"},
        {"status": 403},
        {"precise_received_at": AT + timedelta(seconds=1)},
    ],
)
def test_missing_authentication_or_clock_evidence_rejects(changes: dict[str, Any]) -> None:
    reply = replace(ambiguous(), **changes)
    assert uncertain_quote(reply, identity(), terminal.quote(reply, identity())) is None


def test_old_strict_result_cannot_authorize_replayed_indicative() -> None:
    reply = ambiguous()
    strict = terminal.quote(reply, identity())
    assert (
        uncertain_quote(
            replace(reply, received_monotonic=time.perf_counter() - 31), identity(), strict
        )
        is None
    )


def test_expiry_strips_indicative_price_passively() -> None:
    reply = ambiguous()
    display = uncertain_quote(reply, identity(), terminal.quote(reply, identity()))
    assert display and visible(display, 0)
    assert visible(display, 31) is None
    assert display["state"] == STATE and "ltp" in display


def test_passive_timer_purges_display_payload_without_chart_or_network_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    reply = ambiguous()
    item = {
        "indicative_quote": uncertain_quote(reply, identity(), terminal.quote(reply, identity())),
        "rows": ["TEST_ONLY_EOD"],
    }
    timers = []

    class Timer:
        def __init__(self, interval: float, function: Any) -> None:
            assert 0 <= interval <= 30
            self.function = function
            self.daemon = False
            timers.append(self)

        def start(self) -> None:
            pass

    monkeypatch.setattr("workers.providers.indicative.threading.Timer", Timer)
    expire_field(item, terminal._lock)
    timers[0].function()
    assert item["indicative_quote"] is None and item["rows"] == ["TEST_ONLY_EOD"]


@pytest.mark.parametrize(
    "update",
    [
        {"provider": "alpha_vantage"},
        {"exchange": "BSE"},
        {"segment": "BSE_EQ"},
        {"instrument_type": "ETF"},
        {"isin": None},
    ],
)
def test_foreign_source_or_instrument_scope_cannot_be_displayed(update: dict[str, Any]) -> None:
    reply = ambiguous()
    assert (
        uncertain_quote(
            reply, identity().model_copy(update=update), terminal.quote(reply, identity())
        )
        is None
    )


def test_internal_cache_and_portfolio_never_consume_display_quote(tmp_path: Path) -> None:
    reply = ambiguous()
    strict = terminal.quote(reply, identity())
    key = str(tmp_path.resolve()), identity().provider_key
    item: dict[str, Any] = {
        "quote": strict,
        "indicative_quote": uncertain_quote(reply, identity(), strict),
        "latest_close": None,
        "latest_session": None,
        "rows": [],
    }
    terminal._snapshots[key] = time.monotonic(), item
    try:
        internal = cached(tmp_path, (identity().provider_key,))[identity().provider_key]
        assert "indicative_quote" not in internal and "ltp" not in internal["quote"]
        assert mark(internal)["price"] is None
        assert provider_request_failed(internal) is None
    finally:
        terminal._snapshots.pop(key, None)
