"""TEST_ONLY presentation clock does not promote rejected timestamps."""

from dataclasses import replace
from typing import Any

import pytest
from test_p31_terminal import identity
from test_p34_indicative_quote import ambiguous
from workers.providers import delayed
from workers.providers.indicative import uncertain_quote
from workers.providers.upstox_terminal import quote


@pytest.mark.parametrize("elapsed", [0.0, 0.25, 1.5])
def test_minimum_delay_preserves_classification_and_receipt(
    monkeypatch: pytest.MonkeyPatch, elapsed: float
) -> None:
    reply = ambiguous()
    strict = quote(reply, identity())
    indicative = uncertain_quote(reply, identity(), strict)
    assert indicative is not None
    ticks = [100.0 + elapsed]
    waits = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        ticks[0] += seconds

    monkeypatch.setattr("workers.providers.delayed.time.perf_counter", lambda: ticks[0])
    monkeypatch.setattr("workers.providers.delayed.time.sleep", sleep)
    result = delayed.presentation(replace(reply, received_monotonic=100), strict, indicative)
    assert result and result["elapsed_since_network_receipt_seconds"] >= 1
    assert waits == ([1 - elapsed] if elapsed < 1 else [])
    assert result["classification"] == indicative["state"]
    assert result["local_network_received_at"] == reply.received_at.isoformat()
    assert result["delay_proves_chronology"] is False
    assert strict["state"] == "QUOTE_TIME_REJECTED" and "ltp" not in strict


@pytest.mark.parametrize(
    "state", ["QUOTE_TIME_REJECTED", "QUOTE_SCHEMA_OR_VALUE_REJECTED", "QUOTE_SNAPSHOT_STALE"]
)
def test_rejected_observations_never_become_delayed_prices(state: str) -> None:
    assert delayed.presentation(ambiguous(), {"state": state}, None) is None


def test_verified_classification_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = ambiguous()
    anchor = reply.received_monotonic
    assert anchor is not None
    monkeypatch.setattr("workers.providers.delayed.time.perf_counter", lambda: anchor + 2)
    result: Any = delayed.presentation(reply, {"state": "VALIDATED_SNAPSHOT"}, None)
    assert result["classification"] == "VALIDATED_SNAPSHOT"
    assert result["financial_input_eligible"] is False
