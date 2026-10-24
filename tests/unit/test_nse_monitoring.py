"""TEST_ONLY saved monitoring evidence; no provider HTTP or production stores."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from workers.nse_market import engine
from workers.providers.store import ProviderStore

from alphalens_api.auth.permissions import restrict
from alphalens_api.nse_market import _bounded
from alphalens_api.nse_monitoring import task_run_evidence


@pytest.mark.parametrize("last_result", [0, 3221225786])
def test_launcher_only_exit_cannot_inherit_an_older_terminal_receipt(last_result: int) -> None:
    result = task_run_evidence(
        {
            "windows_task": {
                "last_run_at": "2025-01-04T15:00:00+00:00",
                "state": "Ready",
                "last_result": last_result,
                "stale": False,
            },
            "last_completed": {"completed_at": "2025-01-03T15:02:00+00:00"},
            "unfinished_attempts_total": 0,
        },
        at=datetime(2025, 1, 4, 16, tzinfo=UTC),
    )
    assert result["state"] == "MISSING_TERMINAL_RECEIPT"
    assert result["candle_acquisition_verified"] is False
    assert result["actual_get_attempts"] is None


@pytest.mark.parametrize(
    "task_state,completed,expected",
    [
        ("Running", "2025-01-03T15:02:00+00:00", "AWAITING_TERMINAL_RECEIPT"),
        ("Ready", "2025-01-04T15:02:00+00:00", "TERMINAL_TIME_NOT_OLDER_THAN_TASK_START"),
        ("Ready", "2025-01-04T15:02:00", "UNAVAILABLE"),
        ("Ready", "2025-01-05T15:02:00+00:00", "UNAVAILABLE"),
    ],
)
def test_task_receipt_monitoring_keeps_uncertainty(
    task_state: str, completed: str, expected: str
) -> None:
    result = task_run_evidence(
        {
            "windows_task": {
                "last_run_at": "2025-01-04T15:00:00+00:00",
                "state": task_state,
                "stale": True,
            },
            "last_completed": {"completed_at": completed},
        },
        at=datetime(2025, 1, 4, 16, tzinfo=UTC),
    )
    assert result["state"] == expected
    assert result["candle_acquisition_verified"] is False
    assert result["actual_get_attempts"] is None


def test_session_coverage_is_calculated_before_pagination() -> None:
    rows = [
        {"key": f"TEST_ONLY_{i}", "last": "2025-01-03" if i < 499 else "2025-01-02"}
        for i in range(500)
    ]
    data: dict[str, Any] = {
        "coverage": {"end": "2025-01-03", "configured_securities": 500, "per_security": rows}
    }
    for page, size in ((1, 5), (1, 20), (10, 20)):
        result = _bounded(data, page, size)
        assert len(result["coverage"]["per_security"]) == size
        assert result["coverage"]["latest_session_coverage"] == {
            "session": "2025-01-03",
            "verified_securities": 499,
            "configured_securities": 500,
            "pending_securities": 1,
            "basis": "FULL_CONFIGURED_COHORT_BEFORE_PAGINATION",
        }
    assert len(data["coverage"]["per_security"]) == 500


def test_shared_usage_reads_ist_day_and_preserves_unfinished_reservations(tmp_path: Path) -> None:
    store = ProviderStore(tmp_path / "TEST_ONLY_shared")
    store.initialize()
    local = ProviderStore(tmp_path / "TEST_ONLY_client")
    local.initialize()
    link = local.root / "upstox-shared-quota.json"
    link.write_text(json.dumps({"version": "provider.shared_quota.v1", "root": str(store.root)}))
    restrict(link)
    # Midnight IST is 18:30 UTC. Reserved intents are not proof of successful HTTP.
    for i, stamp in enumerate(
        ("2025-01-02T18:29:00+00:00", "2025-01-02T18:31:00+00:00", "2025-01-02T18:32:00+00:00")
    ):
        at = datetime.fromisoformat(stamp).timestamp()
        key = f"{i:064x}"
        assert local.reserve("upstox", key, 1, at)
        if i != 2:
            local.finish("upstox", key, 1, at, 200)
    result = local.upstox_day_usage(datetime(2025, 1, 3, 1, tzinfo=UTC))
    assert result["ist_day"] == "2025-01-03"
    assert result["recorded_get_attempts"] == 2
    assert result["completed_get_attempts"] == 1
    assert result["unresolved_attempts"] == 1
    assert result["http_200_responses"] == 1
    assert result["last_attempt_at"] == "2025-01-02T18:32:00+00:00"
    assert result["provider_requests"] == 0
    assert local.upstox_day_usage(datetime(2025, 1, 3, 1, tzinfo=UTC)) == result
    with pytest.raises(ValueError, match="PROVIDER_CLOCK_INVALID"):
        local.upstox_day_usage(datetime(2025, 1, 3))


def test_unfinished_workflow_does_not_inherit_completed_run_get_count(tmp_path: Path) -> None:
    root = tmp_path / "TEST_ONLY_market"
    runs = root / "operational/runs"
    runs.mkdir(parents=True)
    started = {
        "run_id": "TEST_ONLY_interrupted",
        "started_at": "2025-01-03T16:00:00+00:00",
        "quota_day": datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat(),
        "reserved_requests": 600,
    }
    engine._checked(runs / "TEST_ONLY_interrupted.started.json", started)
    done = runs / "TEST_ONLY_failed.done.json"
    engine._checked(
        done,
        {
            "run_id": "TEST_ONLY_failed",
            "state": "FAILED",
            "source_requests_last_run": 0,
            "completed_at": "2025-01-03T17:00:00+00:00",
        },
    )
    engine._pointer(root, "operational-latest.json", done)
    result = engine._operations(root)
    assert result["last_completed"]["state"] == "FAILED"
    assert result["last_completed"]["source_requests_last_run"] == 0
    assert result["reservations"]["reserved_get_attempts"] == 600
    assert result["unfinished_attempts_total"] == 1
    attempt = result["unfinished_attempts"][0]
    assert attempt["state"] == "INCOMPLETE_NO_TERMINAL_RECEIPT"
    assert attempt["reserved_get_attempts"] == 600
    assert attempt["actual_get_attempts"] is None
