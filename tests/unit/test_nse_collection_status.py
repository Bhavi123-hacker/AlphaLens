"""TEST_ONLY read-only collection diagnosis and strict saved-calendar evidence."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from test_nse_market import AT, Transport, fixture, identity
from workers.experimental_nse.acquire import PERMISSION, digest
from workers.nse_market import daily, engine, reliability
from workers.providers.store import ProviderStore


def timing(root: Path, day: str, *, raw_hash: str | None = None) -> None:
    reply = Transport().get("timings", end=date.fromisoformat(day))
    folder = root / "calendar"
    folder.mkdir(exist_ok=True)
    engine._checked(
        folder / (day + ".json"),
        {
            "raw_hex": reply.body.hex(),
            "raw_sha256": raw_hash or digest(reply.body),
            "received_at": reply.received_at.isoformat(),
        },
    )


def filesystem(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): digest(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }


def test_saved_calendar_requires_all_intervening_dates_without_weekday_inference(
    tmp_path: Path,
) -> None:
    timing(tmp_path, "2025-01-03")
    value = reliability.expected_session(tmp_path, at=AT)
    assert value["expected_trading_session"] is None
    assert value["latest_saved_completed_session_fact"] == "2025-01-03"
    assert value["missing_calendar_dates"] == ["2025-01-04"]
    timing(tmp_path, "2025-01-04")
    value = reliability.expected_session(tmp_path, at=AT)
    assert value["expected_trading_session"] == "2025-01-03"
    assert value["calendar_complete_to_latest_fact"] is True


def test_calendar_raw_tampering_and_naive_clock_are_rejected(tmp_path: Path) -> None:
    timing(tmp_path, "2025-01-04", raw_hash="a" * 64)
    with pytest.raises(ValueError, match="EVIDENCE_REJECTED"):
        reliability.expected_session(tmp_path, at=AT)
    with pytest.raises(ValueError, match="AWARE_STATUS_CLOCK_REQUIRED"):
        reliability.expected_session(tmp_path, at=datetime(2025, 1, 4))


def test_known_nontrading_days_do_not_authorize_unverified_older_future_calendar(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "calendar"
    folder.mkdir()
    reply = Transport().get("timings", end=date(2025, 1, 4))
    engine._checked(
        folder / "2025-01-04.json",
        {
            "raw_hex": reply.body.hex(),
            "raw_sha256": digest(reply.body),
            "received_at": (AT - timedelta(days=10)).isoformat(),
        },
    )
    timing(tmp_path, "2025-01-03")
    value = reliability.expected_session(tmp_path, at=AT)
    assert value["expected_trading_session"] is None
    assert value["missing_calendar_dates"] == ["2025-01-04"]


def test_missing_reasons_reservations_and_forecast_freshness_are_separate_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    timing(root, "2025-01-04")
    timing(root, "2025-01-03")
    # Supply a qualified TEST_ONLY frame so no model inference or provider call can hide here.
    frame: dict[str, Any] = {
        "sessions": ["2025-01-03"],
        "dataset_id": "c" * 64,
        "rows": [{"key": identity(1).provider_key, "session": "2025-01-03"}],
    }
    monkeypatch.setattr(engine, "snapshot", lambda unused: frame)
    folder = root / "daily/2025-01-03" / str(identity(2).isin) / "publication-attempts"
    folder.mkdir(parents=True)
    engine._checked(
        folder / "TEST_ONLY.json",
        {
            "state": "PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE",
            "received_at": AT.isoformat(),
        },
    )
    runs = root / "operational/runs"
    runs.mkdir(parents=True)
    engine._checked(
        runs / "TEST_ONLY_crashed.started.json",
        {"run_id": "TEST_ONLY_crashed", "quota_day": "2025-01-04", "reserved_requests": 600},
    )
    engine._checked(
        runs / "TEST_ONLY_success.done.json",
        {
            "run_id": "TEST_ONLY_success",
            "completed_at": AT.isoformat(),
            "state": "PARTIAL_OR_PUBLICATION_PENDING",
            "source_requests_last_run": 3,
            "outcome": {"new_daily_observations": 1},
        },
    )
    score_path = root / "TEST_ONLY_scores.json"
    engine._checked(
        score_path,
        {
            "dataset_id": "b" * 64,
            "observation_session": "2025-01-02",
            "candidates": [{"TEST_ONLY": True}],
        },
    )
    engine._pointer(root, "scores-latest.json", score_path)
    before = filesystem(root)
    value = reliability.report(
        root,
        at=AT,
        task_observation={
            "observed_at": AT.isoformat(),
            "next_run_at": (AT + timedelta(hours=1)).isoformat(),
        },
    )
    assert filesystem(root) == before
    assert value["provider_requests"] == 0 and value["tasks_modified"] is False
    assert value["expected_trading_session"] == "2025-01-03"
    assert value["accepted_securities"] == 1 and value["missing_securities"] == 2
    assert value["missing_data_reasons"] == {
        "PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE": 1,
        "NOT_QUERIED_FOR_SESSION_NO_ACCEPTED_SOURCE_RECORD": 1,
    }
    assert value["reserved_quota_by_ist_day"] == {"2025-01-04": 600}
    assert value["reservation_runs_without_terminal_receipt"] == ["TEST_ONLY_crashed"]
    assert value["last_successful_run"]["run_id"] == "TEST_ONLY_success"
    assert value["terminal_reported_actual_attempts"] == 3
    assert value["forecast_freshness"]["fresh_for_expected_session"] is False
    assert value["next_scheduled_run_verified_current"] is True
    assert value["daily_update_success_rate"] is None


def test_actual_shared_ledger_attempts_are_neither_reservations_nor_successful_candles(
    tmp_path: Path,
) -> None:
    store = ProviderStore(tmp_path / "TEST_ONLY_provider")
    store.initialize()
    with store.connection() as connection, connection:
        connection.executemany(
            "INSERT INTO attempts VALUES('upstox',?,1,?,?,NULL)",
            [
                ("TEST_ONLY_success", AT.timestamp(), "SUCCEEDED"),
                ("TEST_ONLY_crashed", AT.timestamp(), "PENDING"),
            ],
        )
    before = (store.path).read_bytes()
    value = reliability._request_counts(store.root)
    assert value["shared_actual_api_attempts_total"] == 2
    assert value["shared_outcomes"] == {"SUCCEEDED": 1, "PENDING": 1}
    assert value["shared_actual_api_attempts_by_ist_day"] == {"2025-01-04": 2}
    assert store.path.read_bytes() == before


def test_status_replays_realistic_saved_acceptance_without_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    transport = Transport(empty=True)
    daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        permission_reference=PERMISSION,
        meter=transport,
    )
    before = filesystem(root)
    calls = transport.calls
    result = reliability.report(root, at=AT)
    assert filesystem(root) == before and transport.calls == calls
    assert result["coverage_is_expected_session"] is True
    assert result["latest_retained_session"] == "2025-01-02"
    assert result["accepted_securities"] == 0 and result["missing_securities"] == 3
    assert result["missing_data_reasons"] == {"PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE": 3}


def test_failed_run_remaining_capacity_and_known_failures_are_reported_without_new_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    timing(root, "2025-01-04")
    timing(root, "2025-01-03")
    monkeypatch.setattr(
        engine,
        "snapshot",
        lambda unused: {"sessions": ["2025-01-03"], "dataset_id": "a" * 64, "rows": []},
    )
    runs = root / "operational/runs"
    runs.mkdir(parents=True)
    for index in range(3):
        engine._checked(
            runs / (str(index) + ".started.json"),
            {"run_id": str(index), "quota_day": "2025-01-04", "reserved_requests": 600},
        )
    engine._checked(
        runs / "failed.done.json",
        {
            "run_id": "failed",
            "state": "FAILED",
            "completed_at": AT.isoformat(),
            "error_code": "DAILY_INDEPENDENT_CLOCK_UNAVAILABLE",
            "source_requests_last_run": 0,
            "policy": {
                "max_requests_per_day": 1800,
                "max_requests_per_run": 600,
                "max_runs_per_day": 3,
            },
            "outcome": {
                "session": "2025-01-03",
                "failures": [{"key": identity(1).provider_key, "reason": "RATE_LIMITED"}],
                "identity_exclusions_pending_review": [identity(2).provider_key],
            },
        },
    )
    before = filesystem(root)
    value = reliability.report(root, at=AT)
    assert filesystem(root) == before
    assert value["last_failed_run"]["error_code"] == "DAILY_INDEPENDENT_CLOCK_UNAVAILABLE"
    assert value["quota"]["reserved_requests_remaining"] == 0
    assert value["quota"]["run_slots_remaining"] == 0
    assert value["quota"]["shared_attempts_used_today"] is None
    assert value["missing_data_reasons"] == {
        "RATE_LIMITED": 1,
        "CURRENT_IDENTITY_EXCLUDED_PENDING_REVIEW": 1,
        "NOT_QUERIED_FOR_SESSION_NO_ACCEPTED_SOURCE_RECORD": 1,
    }
