"""TEST_ONLY continuity fixtures; no NTP or market-data provider requests."""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from workers.providers import clock_continuity as continuity


def observation(elapsed: float = 0) -> dict[str, Any]:
    return {
        "policy": continuity.POLICY,
        "platform": "win32",
        "boot_id": "00000000-0000-0000-0000-000000000001",
        "process_id": "00000000-0000-0000-0000-000000000002",
        "pid": 100,
        "wall_at": (
            datetime(2026, 10, 25, 18, 29, 50, tzinfo=UTC) + timedelta(seconds=elapsed)
        ).isoformat(),
        "monotonic_seconds": 100 + elapsed,
        "suspend_inclusive_seconds": 200 + elapsed,
        "suspend_exclusive_seconds": 150 + elapsed,
        "tick_count_seconds": 200 + elapsed,
        "capture_span_seconds": 0.0001,
    }


@pytest.mark.parametrize("elapsed", [0, 0.001, 24.256058, 60, 120])
def test_consistent_interval_and_utc_ist_rollover(elapsed: float) -> None:
    continuity.validate(observation(), observation(elapsed))


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("boot_id", "00000000-0000-0000-0000-000000000003", "BOOT_CHANGED"),
        ("process_id", "00000000-0000-0000-0000-000000000003", "PROCESS_CHANGED"),
        ("pid", 101, "PROCESS_CHANGED"),
        ("platform", "linux", "PROCESS_CHANGED"),
        ("wall_at", "2026-10-25T18:30:30+00:00", "WALL_MONOTONIC"),
        ("wall_at", "2026-10-25T18:29:00+00:00", "WALL_MONOTONIC"),
        ("suspend_exclusive_seconds", 155, "SUSPEND_OR_TIMER"),
        ("suspend_inclusive_seconds", 240, "SUSPEND_OR_TIMER"),
        ("tick_count_seconds", 190, "SUSPEND_OR_TIMER"),
        ("monotonic_seconds", 99, "INTERVAL_INVALID"),
        ("monotonic_seconds", 221, "INTERVAL_INVALID"),
    ],
)
def test_adversarial_changes_fail_closed(field: str, value: Any, reason: str) -> None:
    current = observation(25)
    current[field] = value
    with pytest.raises(ValueError, match=reason):
        continuity.validate(observation(), current)


@pytest.mark.parametrize(
    "field,value",
    [
        ("wall_at", "2026-10-25T18:30:00"),
        ("wall_at", None),
        ("monotonic_seconds", float("nan")),
        ("monotonic_seconds", float("inf")),
        ("suspend_inclusive_seconds", -1),
        ("suspend_exclusive_seconds", True),
        ("capture_span_seconds", 0.006),
        ("capture_span_seconds", -0.1),
        ("boot_id", ""),
        ("process_id", "00000000-0000-0000-0000-000000000000"),
        ("pid", True),
        ("pid", 0),
        ("policy", "TEST_ONLY_UNREVIEWED_POLICY"),
        ("platform", "unknown"),
    ],
)
def test_missing_or_invalid_evidence_is_rejected(field: str, value: Any) -> None:
    invalid = observation()
    invalid[field] = value
    with pytest.raises(ValueError, match="MISSING_OR_INVALID"):
        continuity.validate(invalid, observation(1))
    missing = observation()
    del missing[field]
    with pytest.raises(ValueError, match="MISSING_OR_INVALID"):
        continuity.validate(observation(), missing)


def test_suspend_is_detected_even_when_wall_and_perf_both_advance() -> None:
    resumed = observation(60)
    resumed["suspend_exclusive_seconds"] -= 30
    with pytest.raises(ValueError, match="SUSPEND_OR_TIMER"):
        continuity.validate(observation(), resumed)


def test_exact_drift_envelope_is_retained() -> None:
    inside = observation(25)
    wall = datetime.fromisoformat(inside["wall_at"])
    inside["wall_at"] = (wall + timedelta(seconds=0.029)).isoformat()
    continuity.validate(observation(), inside)
    outside = dict(inside)
    outside["wall_at"] = (wall + timedelta(seconds=0.031)).isoformat()
    with pytest.raises(ValueError, match="WALL_MONOTONIC"):
        continuity.validate(observation(), outside)


@pytest.mark.skipif(sys.platform not in {"win32", "linux"}, reason="Native supported platforms")
def test_real_native_observations_are_serializable_and_same_process() -> None:
    first, second = continuity.capture(), continuity.capture()
    assert UUID(first["boot_id"]).int
    assert UUID(first["process_id"]).int
    assert first["pid"] == second["pid"] == os.getpid()
    assert first["platform"] == sys.platform
    continuity.validate(json.loads(json.dumps(first)), json.loads(json.dumps(second)))


def test_capture_fails_closed_without_boot_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> str:
        raise OSError("TEST_ONLY_BOOT_UNAVAILABLE")

    monkeypatch.setattr(continuity, "_boot_identity", unavailable)
    with pytest.raises(ValueError, match="CAPTURE_UNAVAILABLE"):
        continuity.capture()


def test_capture_fails_closed_without_suspend_timer(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> tuple[float, float, float]:
        raise AttributeError("TEST_ONLY_TIMER_UNAVAILABLE")

    monkeypatch.setattr(continuity, "_boot_identity", lambda: observation()["boot_id"])
    monkeypatch.setattr(continuity, "_suspend_timers", unavailable)
    with pytest.raises(ValueError, match="CAPTURE_UNAVAILABLE"):
        continuity.capture()
