"""TEST_ONLY sanitized acquisition evidence, without clock-policy or retry changes."""

import socket
import time
from datetime import UTC, datetime
from typing import Any

import pytest
from workers.providers import daily_clock, quote_clock


@pytest.mark.parametrize(
    "error,code",
    [
        (TimeoutError("TEST_ONLY_PRIVATE_MESSAGE"), "NTP_TRANSPORT_TIMEOUT"),
        (socket.gaierror("TEST_ONLY_PRIVATE_MESSAGE"), "NTP_DNS_RESOLUTION_FAILED"),
        (OSError("TEST_ONLY_PRIVATE_MESSAGE"), "NTP_TRANSPORT_OS_ERROR"),
        (ValueError("NTP_SOURCES_DISAGREE"), "NTP_SOURCES_DISAGREE"),
        (ValueError("TEST_ONLY_PRIVATE_MESSAGE"), "NTP_ACQUISITION_INVALID"),
    ],
)
def test_missing_clock_keeps_sanitized_cause_and_original_throttle(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: str
) -> None:
    monkeypatch.setattr(quote_clock, "_attempted", float("-inf"))
    monkeypatch.setattr(quote_clock, "_cached", None)
    monkeypatch.setattr(quote_clock, "_last_failure", {})
    monkeypatch.setattr(time, "perf_counter", lambda: 1000.0)
    monkeypatch.setattr(quote_clock, "precise_utc", lambda: datetime(2026, 1, 1, tzinfo=UTC))
    probes = []

    def failed(source: str) -> Any:
        probes.append(source)
        raise error

    monkeypatch.setattr(quote_clock, "probe", failed)
    assert quote_clock.recent() is None
    count = len(probes)
    assert count <= 2
    diagnostic = quote_clock.last_failure()
    assert diagnostic["reason"] == code
    assert "TEST_ONLY_PRIVATE_MESSAGE" not in str(diagnostic)
    assert quote_clock.recent() is None and len(probes) == count
    assert quote_clock.last_failure() == diagnostic
    monkeypatch.setattr(daily_clock, "_capture", lambda: {})
    with pytest.raises(daily_clock.ClockGateError) as caught:
        daily_clock.guard()
    assert str(caught.value) == "DAILY_INDEPENDENT_CLOCK_UNAVAILABLE"
    context = caught.value.evidence["context"]
    assert isinstance(context, dict)
    assert context["reason"] == code
