"""TEST_ONLY deterministic clock renewal; sockets and provider calls forbidden."""

import socket
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from workers.providers import clock_continuity
from workers.providers import daily_clock as daily
from workers.providers import quote_clock as ntp

from alphalens_data.errors import DataContractError

AT = datetime(2026, 10, 25, 17, tzinfo=UTC)


class Clock:
    def __init__(self, at: datetime = AT) -> None:
        self.at = at
        self.mono = 1000.0
        self.sleeps: list[float] = []
        self.calls = 0
        self.mode = "valid"
        self.initial = self.calibration(0.063712)

    def wall(self) -> datetime:
        return self.at + timedelta(seconds=self.mono - 1000)

    def capture(self) -> dict[str, Any]:
        return {
            "policy": "daily.process-clock-continuity.v1",
            "platform": "win32",
            "boot_id": "00000000-0000-0000-0000-000000000001",
            "process_id": "00000000-0000-0000-0000-000000000002",
            "pid": 123,
            "wall_at": self.wall().isoformat(),
            "monotonic_seconds": self.mono,
            "suspend_inclusive_seconds": self.mono,
            "suspend_exclusive_seconds": self.mono,
            "tick_count_seconds": self.mono,
            "capture_span_seconds": 0.00001,
        }

    def calibration(self, width: float) -> ntp.Calibration:
        rows = tuple(
            ntp.Sample(source, self.wall(), self.mono, -width / 2, width / 2, 0.010)
            for source in ntp.SOURCES
            for _ in range(3)
        )
        return ntp.combine(rows, self.wall(), self.mono)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.mono += seconds

    def recent(self) -> ntp.Calibration | None:
        self.calls += 1
        if self.mode == "missing":
            return None
        if self.mode == "replayed" or self.mono < 1030.0005:
            return self.initial
        # Six genuinely new TEST_ONLY samples, not a changed expiry field.
        self.mono += 2
        fresh = self.calibration(0.040)
        if self.mode == "shifted":
            rows = tuple(
                replace(s, lower=s.lower + 0.5, upper=s.upper + 0.5) for s in fresh.samples
            )
            return ntp.combine(rows, self.wall(), self.mono)
        if self.mode == "invalid":
            return replace(fresh, lower=-0.001, upper=0.001)
        if self.mode == "slow":
            self.mono += 40
        return fresh


def setup(monkeypatch: pytest.MonkeyPatch, at: datetime = AT) -> tuple[Clock, dict[str, Any]]:
    clock = Clock(at)
    monkeypatch.setattr(daily, "recent", clock.recent)
    monkeypatch.setattr(daily, "precise_utc", clock.wall)
    monkeypatch.setattr(clock_continuity, "capture", clock.capture)
    monkeypatch.setattr(time, "perf_counter", lambda: clock.mono)
    monkeypatch.setattr(time, "sleep", clock.sleep)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("TEST_ONLY no clock/provider network")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    return clock, daily.guard()


@pytest.mark.parametrize("cooldown", [24.256058, 31.0, 45.0])
def test_expiring_or_expired_evidence_requires_new_samples(
    monkeypatch: pytest.MonkeyPatch, cooldown: float
) -> None:
    clock, previous = setup(monkeypatch)
    original = previous.copy()
    clock.sleep(cooldown)
    with pytest.raises(ValueError):
        clock.initial.receipt(clock.wall(), clock.mono)
    renewed = daily.refresh(previous, maximum_wait_seconds=60 - cooldown)
    assert renewed["refresh"]["state"] == "NEW_OBSERVATIONS_CONTINUITY_VERIFIED"
    assert renewed["calibration_id"] != previous["calibration_id"]
    assert renewed["calibration_monotonic"] > previous["calibration_monotonic"]
    assert renewed["ntp_evidence"]["evidence_age_seconds"] == 0
    assert len(renewed["ntp_evidence"]["samples"]) == 6
    assert previous == original and clock.initial.monotonic == 1000
    assert clock.calls == (3 if cooldown < 30 else 2)
    assert clock.mono - 1000 <= 60


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("missing", "DAILY_INDEPENDENT_CLOCK_REFRESH_UNAVAILABLE"),
        ("replayed", "DAILY_CLOCK_REFRESH_REPLAYED_EVIDENCE"),
        ("invalid", "DAILY_REFRESH_CALIBRATION_INVALID"),
        ("slow", "DAILY_CLOCK_REFRESH_BUDGET_EXHAUSTED"),
        ("shifted", "DAILY_REFRESH_INDEPENDENT_BOUNDS_DISAGREE"),
    ],
)
def test_missing_invalid_replayed_and_late_refresh_fail_closed(
    monkeypatch: pytest.MonkeyPatch, mode: str, reason: str
) -> None:
    clock, previous = setup(monkeypatch)
    clock.sleep(24.256058)
    clock.mode = mode
    with pytest.raises(DataContractError) as failure:
        daily.refresh(previous, maximum_wait_seconds=35)
    if isinstance(failure.value, daily.ClockGateError):
        assert failure.value.evidence["reason"] == reason
    else:
        assert str(failure.value) == reason


@pytest.mark.parametrize("budget", [0, -1, float("nan"), float("inf"), 61, 1])
def test_no_refresh_when_remaining_cooldown_budget_is_insufficient(
    monkeypatch: pytest.MonkeyPatch, budget: float
) -> None:
    clock, previous = setup(monkeypatch)
    clock.sleep(24)
    with pytest.raises(DataContractError, match="BUDGET_EXHAUSTED"):
        daily.refresh(previous, maximum_wait_seconds=budget)
    assert clock.sleeps == [24]


@pytest.mark.parametrize(
    "missing", ["continuity", "calibration_id", "calibration_monotonic", "receipt_monotonic"]
)
def test_missing_context_is_not_reconstructed_from_wall_time(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    clock, previous = setup(monkeypatch)
    del previous[missing]
    with pytest.raises(DataContractError, match="CONTEXT_MISSING"):
        daily.refresh(previous, maximum_wait_seconds=30)
    assert clock.calls == 1


@pytest.mark.parametrize(
    "field", ["boot_id", "process_id", "pid", "wall_at", "suspend_exclusive_seconds"]
)
def test_discontinuity_is_rejected_before_any_new_clock_probe(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    clock, previous = setup(monkeypatch)
    clock.sleep(24)
    before = previous["continuity"]
    if field in {"boot_id", "process_id"}:
        before[field] = "00000000-0000-0000-0000-000000000003"
    elif field == "wall_at":
        before[field] = (AT - timedelta(seconds=10)).isoformat()
    else:
        before[field] += 10
    with pytest.raises(daily.ClockGateError) as failure:
        daily.refresh(previous, maximum_wait_seconds=35)
    assert failure.value.evidence["stage"] == "CONTINUITY"
    assert clock.calls == 1 and clock.sleeps == [24]


@pytest.mark.parametrize(
    "at",
    [datetime(2026, 1, 1, 18, 29, 50, tzinfo=UTC), datetime(2026, 7, 1, 23, 59, 50, tzinfo=UTC)],
)
def test_fresh_ist_date_across_india_midnight_and_utc_rollover(
    monkeypatch: pytest.MonkeyPatch, at: datetime
) -> None:
    clock, previous = setup(monkeypatch, at)
    clock.sleep(31)
    fresh = daily.refresh(previous, maximum_wait_seconds=29)
    from zoneinfo import ZoneInfo

    assert fresh["session_date"] == str(clock.wall().astimezone(ZoneInfo("Asia/Kolkata")).date())


def test_uncertainty_straddling_ist_midnight_is_still_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(daily.ClockGateError) as failure:
        setup(monkeypatch, datetime(2026, 10, 25, 18, 30, tzinfo=UTC))
    assert failure.value.evidence["reason"] == "DAILY_IST_DATE_BOUNDS_DISAGREE"


@pytest.mark.parametrize("mode", ["valid", "missing", "invalid", "replayed", "quota"])
def test_real_refresh_precedes_immutable_reservation_and_provider_meter(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from test_nse_scheduled_preflight import prior
    from test_nse_scheduled_preflight import setup as scheduled_setup
    from workers.nse_market import engine, operational

    cfg, _, meters = scheduled_setup(tmp_path, monkeypatch, now=AT)
    clock, _ = setup(monkeypatch)
    monkeypatch.setattr(operational, "guard", daily.guard)
    monkeypatch.setattr(operational, "refresh", daily.refresh)
    monkeypatch.setattr(time, "monotonic", lambda: clock.mono)
    crash = prior(cfg, AT - timedelta(seconds=3575.743942))
    original = crash.read_bytes()
    if mode == "quota":
        prior(cfg, AT - timedelta(seconds=4000), reserved=1200, name="OTHER")
    before = list((cfg.root / "operational/runs").glob("*.started.json"))

    def sleeping(seconds: float) -> None:
        assert meters == []
        assert list((cfg.root / "operational/runs").glob("*.started.json")) == before
        clock.sleep(seconds)
        clock.mode = mode

    monkeypatch.setattr(time, "sleep", sleeping)
    result = operational.run(cfg, session=AT.date() - timedelta(days=1), scheduled=True)
    assert crash.read_bytes() == original
    receipts = list((cfg.root / "operational/runs").glob("*.started.json"))
    if mode == "valid":
        assert result["state"] == "TEST_ONLY_COMPLETE" and len(meters) == 1
        assert len(receipts) == 2
        assert result["clock"]["refresh"]["state"] == "NEW_OBSERVATIONS_CONTINUITY_VERIFIED"
        saved = next(engine._read(p) for p in receipts if p != crash)
        assert saved["reserved_requests"] == 600
    else:
        assert result["state"] == "FAILED" and meters == [] and receipts == before
        if mode == "invalid":
            assert result["clock_failure"]["reason"] == "DAILY_REFRESH_CALIBRATION_INVALID"
        if mode == "quota":
            assert result["error_code"] == "EXPANDED_DAILY_REQUEST_RESERVATION_LIMIT"
            assert clock.sleeps == []
