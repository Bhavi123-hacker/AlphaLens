"""TEST_ONLY persistent quota and approval tests; no provider or scheduler calls."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError
from workers.experimental_nse.acquire import initialize
from workers.nse_market import daily, engine, operational
from workers.providers import universe

from alphalens_data.providers.multi_contracts import Instrument


def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> operational.Config:
    root = tmp_path / "TEST_ONLY_private_market"
    initialize(root)
    plans = root / "plans"
    plans.mkdir()
    path = plans / ("a" * 64 + ".json")
    engine._checked(path, {"plan_id": "a" * 64, "identities": [{"key": "TEST_ONLY"}]})
    engine._pointer(root, "plan-latest.json", path)
    result = operational.Config(
        root=root,
        provider_root=tmp_path / "TEST_ONLY_provider",
        v2_root=tmp_path / "TEST_ONLY_v2",
        expected_plan_id="a" * 64,
        expected_securities=1,
        run_user="TEST_ONLY_OPERATOR",
    )
    monkeypatch.setattr(
        operational,
        "readiness",
        lambda unused: {"running_user_matches": True, "protected_credential_available": True},
    )
    monkeypatch.setattr(
        operational, "_refresh_identities", lambda *args: (None, {"TEST_ONLY": True})
    )
    monkeypatch.setattr(
        daily,
        "run",
        lambda *args, **kwargs: {
            "state": "TEST_ONLY_COMPLETE",
            "api_calls": 1 if kwargs["collect"] else 0,
        },
    )
    return result


def clock(monkeypatch: pytest.MonkeyPatch, now: datetime) -> None:
    monkeypatch.setattr(
        operational,
        "guard",
        lambda: {
            "session_date": str(now.date()),
            "lower_at": now.isoformat(),
            "upper_at": (now + timedelta(seconds=1)).isoformat(),
        },
    )


def test_dry_run_does_not_reserve_requests_or_enable_scheduler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = config(tmp_path, monkeypatch)
    clock(monkeypatch, datetime(2025, 1, 3, 12, tzinfo=UTC))
    result = operational.run(cfg, session=date(2025, 1, 2))
    assert result["state"] == "TEST_ONLY_COMPLETE"
    assert result["source_requests_last_run"] == 0
    assert result["automatic_acquisition_enabled"] is False
    assert not list((cfg.root / "operational/runs").glob("*.started.json"))


def test_scheduled_path_requires_explicit_exact_approval_before_collection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = config(tmp_path, monkeypatch)
    clock(monkeypatch, datetime(2025, 1, 3, 12, tzinfo=UTC))
    result = operational.run(cfg, session=date(2025, 1, 2), scheduled=True)
    assert result["state"] == "FAILED"
    assert result["error_code"] == "EXPLICIT_EXPANDED_RECURRING_OPERATOR_APPROVAL_REQUIRED"
    assert result["source_requests_last_run"] == 0


def test_independent_cooldown_and_daily_attempt_limit_survive_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = config(tmp_path, monkeypatch)
    at = datetime(2025, 1, 3, 12, tzinfo=UTC)
    clock(monkeypatch, at)
    assert (
        operational.run(cfg, session=date(2025, 1, 2), collect=True)["state"]
        == "TEST_ONLY_COMPLETE"
    )
    clock(monkeypatch, at + timedelta(minutes=59))
    assert (
        operational.run(cfg, session=date(2025, 1, 2), collect=True)["error_code"]
        == "EXPANDED_MINIMUM_60_MINUTE_COOLDOWN"
    )
    clock(monkeypatch, at + timedelta(minutes=61))
    assert (
        operational.run(cfg, session=date(2025, 1, 2), collect=True)["state"]
        == "TEST_ONLY_COMPLETE"
    )
    clock(monkeypatch, at + timedelta(minutes=122))
    assert (
        operational.run(cfg, session=date(2025, 1, 2), collect=True)["state"]
        == "TEST_ONLY_COMPLETE"
    )
    clock(monkeypatch, at + timedelta(minutes=183))
    assert (
        operational.run(cfg, session=date(2025, 1, 2), collect=True)["error_code"]
        == "EXPANDED_DAILY_ATTEMPT_LIMIT"
    )
    assert len(list((cfg.root / "operational/runs").glob("*.started.json"))) == 3


def test_crashed_attempt_reservation_survives_without_done_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = config(tmp_path, monkeypatch)
    now = datetime(2025, 1, 3, 12, tzinfo=UTC)
    clock(monkeypatch, now)
    runs = cfg.root / "operational/runs"
    runs.mkdir(parents=True)
    engine._checked(
        runs / "TEST_ONLY_CRASH.started.json",
        {
            "quota_day": "2025-01-03",
            "clock_lower_at": now.isoformat(),
            "clock_upper_at": now.isoformat(),
            "reserved_requests": 1800,
        },
    )
    clock(monkeypatch, now + timedelta(hours=2))
    result = operational.run(cfg, session=date(2025, 1, 2), collect=True)
    assert result["error_code"] == "EXPANDED_DAILY_REQUEST_RESERVATION_LIMIT"


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_requests_per_run", True),
        ("max_runs_per_day", "3"),
        ("cooldown_minutes", 59),
        ("max_stocks_per_run", 251),
    ],
)
def test_strict_limits_reject_coercion_and_oversized_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    cfg = config(tmp_path, monkeypatch)
    values = cfg.model_dump()
    values[field] = value
    with pytest.raises(ValidationError):
        operational.Config.model_validate(values)


@pytest.mark.parametrize("stale,expected_calls", [(False, 0), (True, 1)])
def test_fresh_master_revalidation_is_bounded_and_does_not_expand_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stale: bool, expected_calls: int
) -> None:
    refresh = operational._refresh_identities
    cfg = config(tmp_path, monkeypatch)
    now = datetime.now(UTC)
    item = Instrument(
        provider="upstox",
        provider_key="NSE_EQ|INE002A01018",
        exchange="NSE",
        segment="NSE_EQ",
        symbol="TEST_ONLY_NEW_SYMBOL",
        isin="INE002A01018",
        series="EQ",
        instrument_type="EQ",
        observed_at=now - timedelta(minutes=1),
        identity_evidence="TEST_ONLY",
        revision_sha256="a" * 64,
    )
    unrelated = item.model_copy(
        update={
            "provider_key": "NSE_EQ|INE009A01021",
            "isin": "INE009A01021",
            "symbol": "TEST_ONLY_NOT_IN_SCOPE",
        }
    )
    plan = {"identities": [{**item.model_dump(mode="json"), "symbol": "TEST_ONLY_OLD_SYMBOL"}]}
    monkeypatch.setattr(engine, "_pointed", lambda *args: plan)
    fresh = SimpleNamespace(
        observed_at=now - timedelta(minutes=1), eligible=(item, unrelated), snapshot_id="b" * 64
    )
    older = SimpleNamespace(
        observed_at=now - timedelta(hours=25), eligible=(item,), snapshot_id="c" * 64
    )
    monkeypatch.setattr(universe, "load", lambda unused: older if stale else fresh)

    class Meter:
        calls = 0

    meter = Meter()

    def new_master(root: Path, provider_root: Path, *, client: Any) -> Any:
        client.calls += 1
        return fresh

    monkeypatch.setattr(universe, "refresh", new_master)
    selected, receipt = refresh(cfg, meter, {"upper_at": now.isoformat()})
    assert list(selected) == [item.provider_key]
    assert receipt["metadata_gets"] == expected_calls and meter.calls == expected_calls
    assert receipt["new_unapproved_keys_added"] == 0
    assert receipt["changed"][0]["historical_identity_not_rewritten"] is True


def test_auto_session_selection_uses_explicit_special_session_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2025, 1, 4, 12, tzinfo=UTC)
    checked = []

    def timing(root: Path, day: date, meter: Any) -> dict[str, Any] | None:
        checked.append(day)
        if day == date(2025, 1, 3):
            return {"close_at": "2025-01-03T11:30:00+00:00"}
        return None

    monkeypatch.setattr(daily, "_timing", timing)
    assert operational._latest_completed(
        tmp_path, {"session_date": "2025-01-04", "lower_at": now.isoformat()}, None
    ) == date(2025, 1, 3)
    assert checked == [date(2025, 1, 4), date(2025, 1, 3)]
