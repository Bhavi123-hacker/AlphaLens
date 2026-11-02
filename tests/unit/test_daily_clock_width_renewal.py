"""TEST_ONLY aged valid cache renewal; no real clocks, sockets or provider requests."""

import time
from dataclasses import replace
from typing import Any

import pytest
from test_daily_clock_refresh import setup
from workers.providers import clock_continuity
from workers.providers import daily_clock as daily


def aged(monkeypatch: pytest.MonkeyPatch) -> Any:
    clock, _ = setup(monkeypatch)
    clock.initial = clock.calibration(0.08136915329773908)
    clock.sleep(13.270733600016683)
    return clock


def test_valid_cache_exhausted_width_waits_cadence_for_six_new_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = aged(monkeypatch)
    original = clock.initial
    result = daily.guard()
    assert result["refresh"]["trigger"] == "VALID_CACHE_WIDTH_EXHAUSTED_BY_AGE"
    assert result["refresh"]["maximum_seconds"] == 32
    assert len(clock.sleeps) == 2 and clock.mono >= 1032
    assert clock.sleeps[-1] == pytest.approx(30 - 13.270733600016683 + 0.001)
    assert clock.calls == 4  # Initial, cached guard, cached refresh, one new acquisition.
    assert result["calibration_monotonic"] > original.monotonic
    assert len(result["ntp_evidence"]["samples"]) == 6
    assert result["ntp_evidence"]["evidence_age_seconds"] == 0
    assert clock.initial == original  # Original evidence is not edited or extended.


@pytest.mark.parametrize("cause", ["NTP_PACKET_REJECTED", "NTP_SOURCES_DISAGREE"])
def test_failed_new_observations_propagate_without_another_attempt(
    monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    clock = aged(monkeypatch)
    original_sleep = clock.sleep

    def sleeping(seconds: float) -> None:
        original_sleep(seconds)
        clock.mode = "missing"

    monkeypatch.setattr(time, "sleep", sleeping)
    monkeypatch.setattr(daily, "last_failure", lambda: {"reason": cause})
    with pytest.raises(daily.ClockGateError) as failure:
        daily.guard()
    assert str(failure.value) == "DAILY_INDEPENDENT_CLOCK_REFRESH_UNAVAILABLE"
    assert failure.value.evidence["context"]["reason"] == cause
    assert clock.calls == 4 and len(clock.sleeps) == 2


def test_altered_or_invalid_anchor_is_never_renewed(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = aged(monkeypatch)
    clock.initial = replace(clock.initial, upper=clock.initial.upper + 0.010)
    with pytest.raises(daily.ClockGateError) as failure:
        daily.guard()
    assert failure.value.evidence["reason"] == "NTP_RECEIPT_INTERVAL_TOO_WIDE"
    assert clock.calls == 2 and len(clock.sleeps) == 1


def test_local_wall_discontinuity_is_not_a_width_renewal_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import timedelta

    clock = aged(monkeypatch)
    monkeypatch.setattr(daily, "precise_utc", lambda: clock.wall() + timedelta(seconds=1))
    with pytest.raises(daily.ClockGateError) as failure:
        daily.guard()
    assert failure.value.evidence["reason"] == "NTP_EVIDENCE_STALE_OR_LOCAL_CLOCK_DISCONTINUITY"
    assert clock.calls == 2 and len(clock.sleeps) == 1


def test_suspension_during_wait_is_rejected_before_new_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = aged(monkeypatch)
    capture = clock.capture
    discontinuous = False
    original_sleep = clock.sleep

    def sleeping(seconds: float) -> None:
        nonlocal discontinuous
        original_sleep(seconds)
        discontinuous = True

    def observe() -> dict[str, Any]:
        result: dict[str, Any] = capture()
        if discontinuous:
            result["suspend_exclusive_seconds"] -= 5
        return result

    monkeypatch.setattr(time, "sleep", sleeping)
    monkeypatch.setattr(clock_continuity, "capture", observe)
    with pytest.raises(daily.ClockGateError) as failure:
        daily.guard()
    assert failure.value.evidence["stage"] == "CONTINUITY"
    assert clock.calls == 3  # No new probe after the interrupted native interval.


def test_wait_interruption_propagates_without_new_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = aged(monkeypatch)

    def interrupted(seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(time, "sleep", interrupted)
    with pytest.raises(KeyboardInterrupt):
        daily.guard()
    assert clock.calls == 3 and len(clock.sleeps) == 1
