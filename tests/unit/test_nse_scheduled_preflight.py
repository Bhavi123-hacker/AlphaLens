"""TEST_ONLY clocks/stores. No provider, credentials, scheduler or actual sleep."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from test_nse_market_operational import config
from workers.nse_market import engine, operational

from alphalens_data.errors import DataContractError


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now
        self.mono = 0.0
        self.sleeps: list[float] = []
        self.calls = 0

    def guard(self) -> dict[str, str]:
        self.calls += 1
        return {
            "session_date": str(self.now.astimezone(ZoneInfo("Asia/Kolkata")).date()),
            "lower_at": self.now.isoformat(),
            "upper_at": self.now.isoformat(),
        }

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.mono += seconds
        self.now += timedelta(seconds=seconds)


def setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, now: datetime | None = None
) -> tuple[operational.Config, Clock, list[int]]:
    cfg = config(tmp_path, monkeypatch).model_copy(update={"recurring_acquisition_enabled": True})
    folder = cfg.root / "operational"
    folder.mkdir()
    engine._checked(
        folder / "collection-approval.json",
        {
            "policy_sha256": operational.policy(cfg)["policy_sha256"],
            "approved_by": "LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL",
            "approved_at": "2000-01-01T00:00:00+00:00",
        },
    )
    clock = Clock(now or datetime(2025, 1, 3, 16, tzinfo=UTC))
    monkeypatch.setattr(operational, "guard", clock.guard)
    monkeypatch.setattr(time, "monotonic", lambda: clock.mono)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    meters: list[int] = []

    def meter(*args: Any) -> object:
        meters.append(1)
        return object()

    monkeypatch.setattr(engine, "Meter", meter)
    return cfg, clock, meters


def prior(
    cfg: operational.Config, at: datetime, *, reserved: int = 600, name: str = "CRASH"
) -> Path:
    folder = cfg.root / "operational/runs"
    folder.mkdir(exist_ok=True)
    path = folder / ("TEST_ONLY_" + name + ".started.json")
    engine._checked(
        path,
        {
            "quota_day": str(at.astimezone(ZoneInfo("Asia/Kolkata")).date()),
            "clock_lower_at": at.isoformat(),
            "clock_upper_at": at.isoformat(),
            "reserved_requests": reserved,
        },
    )
    return path


def run(cfg: operational.Config, **kwargs: Any) -> dict[str, Any]:
    return operational.run(cfg, session=date(2025, 1, 2), **kwargs)


def test_exact_3600_seconds_is_eligible_without_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    prior(cfg, clock.now - timedelta(seconds=3600))
    result = run(cfg, scheduled=True)
    assert result["state"] == "TEST_ONLY_COMPLETE"
    assert clock.sleeps == [] and clock.calls == 1 and len(meters) == 1


def test_real_shortfall_waits_then_rechecks_before_any_reservation_or_meter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    crash = prior(cfg, clock.now - timedelta(seconds=3578.477946))
    original = crash.read_bytes()
    counts = {"approval": 0, "readiness": 0}
    approval = operational._approval

    def approved(*args: Any) -> None:
        counts["approval"] += 1
        approval(*args)

    def ready(*args: Any) -> dict[str, bool]:
        counts["readiness"] += 1
        return {"running_user_matches": True, "protected_credential_available": True}

    def sleeping(seconds: float) -> None:
        assert meters == []
        assert list((cfg.root / "operational/runs").glob("*.started.json")) == [crash]
        clock.sleep(seconds)

    monkeypatch.setattr(operational, "_approval", approved)
    monkeypatch.setattr(operational, "readiness", ready)
    monkeypatch.setattr(time, "sleep", sleeping)
    result = run(cfg, scheduled=True)
    assert result["state"] == "TEST_ONLY_COMPLETE"
    assert clock.sleeps == pytest.approx([21.522054])
    assert clock.calls == 2 and counts == {"approval": 2, "readiness": 2}
    assert result["cooldown_preflight"]["state"] == "SATISFIED"
    assert len(list((cfg.root / "operational/runs").glob("*.started.json"))) == 2
    assert crash.read_bytes() == original


@pytest.mark.parametrize(
    "scenario,code",
    [
        ("too_recent", "EXPANDED_COOLDOWN_WAIT_EXCEEDS_60_SECONDS"),
        ("timeout", "EXPANDED_COOLDOWN_WAIT_TIMEOUT"),
        ("rollback", "EXPANDED_INDEPENDENT_CLOCK_ROLLBACK"),
        ("clock_disagreement", "DAILY_DATE_OR_CLOCK_DISCONTINUITY"),
        ("stalled", "EXPANDED_COOLDOWN_WAIT_TIMEOUT"),
        ("credentials", "EXPANDED_OPERATOR_OR_PROTECTED_CREDENTIAL_NOT_READY"),
        ("approval", "EXPLICIT_EXPANDED_RECURRING_OPERATOR_APPROVAL_REQUIRED"),
    ],
)
def test_wait_failure_modes_never_create_meter_or_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str, code: str
) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    crash = prior(cfg, clock.now - timedelta(seconds=3500 if scenario == "too_recent" else 3590))
    initial = clock.now

    def sleeping(seconds: float) -> None:
        clock.sleep(seconds)
        if scenario == "timeout":
            clock.mono = 61
        if scenario == "rollback":
            clock.now = initial - timedelta(seconds=2)
        if scenario == "clock_disagreement":

            def bad_clock() -> dict[str, str]:
                raise ValueError("DAILY_DATE_OR_CLOCK_DISCONTINUITY")

            monkeypatch.setattr(operational, "guard", bad_clock)
        if scenario == "stalled":
            clock.now = initial
        if scenario == "credentials":
            monkeypatch.setattr(
                operational,
                "readiness",
                lambda cfg: {
                    "running_user_matches": True,
                    "protected_credential_available": False,
                },
            )
        if scenario == "approval":
            # TEST_ONLY revocation between checks; no protected real configuration is touched.
            object.__setattr__(cfg, "recurring_acquisition_enabled", False)

    monkeypatch.setattr(time, "sleep", sleeping)
    result = run(cfg, scheduled=True)
    assert result["state"] == "FAILED" and result["error_code"] == code
    assert meters == [] and sum(clock.sleeps) <= 60
    assert list((cfg.root / "operational/runs").glob("*.started.json")) == [crash]


def test_cross_midnight_reservation_uses_fresh_ist_day(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, clock, meters = setup(
        tmp_path, monkeypatch, now=datetime(2025, 1, 3, 23, 59, 45, tzinfo=ZoneInfo("Asia/Kolkata"))
    )
    crash = prior(cfg, clock.now - timedelta(seconds=3578.477946))
    result = run(cfg, scheduled=True)
    assert result["state"] == "TEST_ONLY_COMPLETE" and len(meters) == 1
    receipts = [
        engine._read(p)
        for p in (cfg.root / "operational/runs").glob("*.started.json")
        if p != crash
    ]
    assert len(receipts) == 1 and receipts[0]["quota_day"] == "2025-01-04"
    assert receipts[0]["reserved_requests"] == 600 and crash.exists()


@pytest.mark.parametrize("ceiling", ["attempts", "requests"])
def test_daily_limits_are_rechecked_after_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ceiling: str
) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    prior(cfg, clock.now - timedelta(seconds=3590))

    def sleeping(seconds: float) -> None:
        clock.sleep(seconds)
        if ceiling == "attempts":
            for i in range(2):
                prior(cfg, clock.now - timedelta(seconds=4000 + i), name=str(i))
        else:
            prior(cfg, clock.now - timedelta(seconds=4000), reserved=1200, name="OTHER")

    monkeypatch.setattr(time, "sleep", sleeping)
    result = run(cfg, scheduled=True)
    assert result["error_code"] == (
        "EXPANDED_DAILY_ATTEMPT_LIMIT"
        if ceiling == "attempts"
        else "EXPANDED_DAILY_REQUEST_RESERVATION_LIMIT"
    )
    assert meters == []


def test_manual_and_dry_runs_never_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    prior(cfg, clock.now - timedelta(seconds=3590))
    assert run(cfg, collect=True)["error_code"] == "EXPANDED_MINIMUM_60_MINUTE_COOLDOWN"
    assert run(cfg)["state"] == "TEST_ONLY_COMPLETE"
    assert clock.sleeps == [] and meters == []


def test_kernel_lock_excludes_concurrent_scheduled_worker_while_waiting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    crash = prior(cfg, clock.now - timedelta(seconds=3590))
    entered, release = threading.Event(), threading.Event()

    def sleeping(seconds: float) -> None:
        entered.set()
        assert release.wait(10), "TEST_ONLY synchronization timeout"
        clock.sleep(seconds)

    monkeypatch.setattr(time, "sleep", sleeping)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(run, cfg, scheduled=True)
        try:
            assert entered.wait(10)
            with pytest.raises(DataContractError, match="DAILY_WORKER_BUSY"):
                run(cfg, scheduled=True)
            assert meters == []
            assert list((cfg.root / "operational/runs").glob("*.started.json")) == [crash]
        finally:
            release.set()
        assert first.result(timeout=10)["state"] == "TEST_ONLY_COMPLETE"
    assert len(meters) == 1
