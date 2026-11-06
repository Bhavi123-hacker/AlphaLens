"""TEST_ONLY offline quota arithmetic and deterministic proposed coverage; no transport."""

from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

import pytest
from workers.nse_market.coverage_plan import plan
from workers.providers import universe

AT = datetime(2026, 10, 24, 18, tzinfo=UTC)
SESSION = date(2026, 10, 23)


def evidence() -> tuple[universe.Snapshot, dict[str, Any], dict[str, Any]]:
    records = tuple(
        {
            "instrument_key": f"NSE_EQ|TEST_ONLY_{i:04}",
            "isin": f"TEST_ONLY_{i:04}",
            "symbol": f"TEST_ONLY_{i:04}",
            "eligible_common_equity": True,
        }
        for i in range(1200)
    )
    master = universe.Snapshot("0" * 64, AT, (), records, {})
    view = {
        "dataset_id": "TEST_ONLY",
        "rows": [
            {
                "key": row["instrument_key"],
                "session": "2026-10-23" if i < 300 else "2026-10-22",
                "close": "100",
            }
            for i, row in enumerate(records[:500])
        ],
    }
    calendars = {
        "2026-10-23": {"close_at": "2026-10-23T10:00:00+00:00"},
        "2026-10-24": None,
        "2026-10-25": None,
        "2026-10-26": {"close_at": "2026-10-26T10:00:00+00:00"},
    }
    return master, view, calendars


def test_all_master_incremental_capacity_preserves_exact_existing_limits() -> None:
    master, view, calendars = evidence()
    result = plan(master, view, session=SESSION, at=AT, calendars=calendars)
    assert result["supported_equities"] == 1200 and result["pending_securities"] == 900
    assert result["new_unapproved_securities"] == 700
    assert result["known_success_path_candle_gets"] == 900
    assert result["action_gets_if_all_candles_valid"] == 900
    assert result["reserved_gets_all_pending_batches"] == 2400
    assert result["minimum_capacity_days_for_pending_batches"] == 2
    assert [len(batch["securities"]) for batch in result["batches"]] == [250, 250, 250, 150]
    assert result["full_universe_daily_reservation"] == 3000
    assert result["same_day_full_universe_supported"] is False
    assert result["status"] == "BLOCKED_APPROVAL" and result["activation_enabled"] is False
    assert result["actual_provider_requests"] == 0
    assert result["existing_policy"] == {
        "stocks_per_run": 250,
        "reserved_gets_per_run": 600,
        "reserved_gets_per_day": 1800,
        "maximum_runs_per_day": 3,
    }
    rows = [row for batch in result["batches"] for row in batch["securities"]]
    assert all(row["existing_approved_cohort"] for row in rows[:200])
    assert all(not row["acquisition_authorized_by_this_plan"] for row in rows)


def test_cache_savings_are_target_scoped_and_do_not_grant_reservation_expansion() -> None:
    master, view, calendars = evidence()
    key = master.records[300]["instrument_key"]
    result = plan(
        master,
        view,
        session=SESSION,
        at=AT,
        calendars=calendars,
        checkpoints={key: {"candle": True, "actions": False}},
    )
    assert result["known_success_path_candle_gets"] == 899
    assert result["action_gets_if_all_candles_valid"] == 900
    assert result["reserved_gets_all_pending_batches"] == 2400
    assert result["missing_calendar_gets_upper_bound_first_day"] == 0


def test_permutation_does_not_change_plan_or_stable_key_order() -> None:
    master, view, calendars = evidence()
    first = plan(master, view, session=SESSION, at=AT, calendars=calendars)
    second = plan(
        replace(master, records=tuple(reversed(master.records))),
        {**view, "rows": list(reversed(view["rows"]))},
        session=SESSION,
        at=AT,
        calendars=calendars,
    )
    assert first == second


def test_unknown_calendar_is_explicit_and_verified_closure_is_rejected() -> None:
    master, view, _ = evidence()
    result = plan(master, view, session=SESSION, at=AT, calendars={})
    assert result["target_session_qualified_by_saved_calendar"] is False
    assert result["missing_calendar_gets_upper_bound_first_day"] == 9
    with pytest.raises(ValueError, match="NON_TRADING"):
        plan(master, view, session=SESSION, at=AT, calendars={str(SESSION): None})
    with pytest.raises(ValueError, match="NONFUTURE"):
        plan(master, view, session=date(2026, 10, 26), at=AT, calendars={})
