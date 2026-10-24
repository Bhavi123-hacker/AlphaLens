"""TEST_ONLY offline capacity, monitoring and independent identity failure paths."""

import copy
import importlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from scripts.prepare_nse_1000_readiness import candidate_keys, capacity, simulate_pending
from workers.nse_market import engine
from workers.providers import universe

from alphalens_api import nse_market, nse_monitoring
from alphalens_api.core.domain_errors import APIError


def test_1000_cannot_fit_approved_daily_scope_or_reservations() -> None:
    assert capacity(500)["same_session_full_coverage_supported"] is True
    result = capacity(1000)
    assert result["minimum_successful_batches"] == 4
    assert result["reserved_capacity_required"] == 2400
    assert result["additional_daily_reserved_capacity_required"] == 600
    assert result["additional_successful_slots_required"] == 1
    assert result["stocks_per_day_upper_bound"] == 750
    assert result["same_session_full_coverage_supported"] is False
    assert (
        capacity(1000, slots=4, daily_budget=2400)["same_session_full_coverage_supported"] is True
    )


def test_candidate_selection_preserves_existing_and_is_order_independent() -> None:
    rows = [
        {"instrument_key": str(i), "isin": str(i), "eligible_common_equity": i != 4}
        for i in range(6)
    ]
    assert (
        candidate_keys(["3"], rows, 4)
        == candidate_keys(["3"], list(reversed(rows)), 4)
        == ["3", "0", "1", "2"]
    )
    with pytest.raises(ValueError):
        candidate_keys(["4"], rows, 4)
    with pytest.raises(ValueError):
        candidate_keys(["3", "3"], rows, 4)
    rows[1]["isin"] = rows[0]["isin"]
    with pytest.raises(ValueError, match="DUPLICATE_ISIN"):
        candidate_keys(["3"], rows, 4)


def test_persistent_empty_source_consumes_slots_without_fake_success() -> None:
    all_valid = simulate_pending(1000, 4, 0)
    assert all_valid["updated"] == 1000
    missing = simulate_pending(1000, 4, 1)
    assert missing["updated"] == 996 and missing["pending"] == 4
    assert missing["distinct_attempted"] == 997 and missing["never_attempted"] == 3
    recovery = simulate_pending(1000, 5, 1)
    assert recovery["updated"] == 999 and recovery["pending"] == 1
    assert recovery["distinct_attempted"] == 1000


def test_stale_master_does_not_hide_valid_saved_research(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    service: Any = SimpleNamespace(
        reader=SimpleNamespace(
            settings=SimpleNamespace(
                experimental_nse_v2_root=tmp_path / "TEST_ONLY_v2", providers_root=None
            )
        )
    )
    monkeypatch.setattr(
        engine,
        "workspace",
        lambda *args: {"accepted_current_rankings": 0, "candidates": []},
    )

    def stale(*args: Any) -> Any:
        raise ValueError("UNIVERSE_STALE_REFRESH_REQUIRED")

    monkeypatch.setattr(universe, "fresh", stale)
    monkeypatch.setattr(
        universe,
        "load",
        lambda *args: SimpleNamespace(
            observed_at=datetime.now(UTC) - timedelta(days=2),
            summary={"verified_eligible_common_equities": 99},
        ),
    )
    result = nse_market._read(service)
    assert result["identity_status"]["state"] == "STALE"
    assert result["identity_status"]["current_identity_actions_available"] is False
    # Dated identity discovery retains its independently verified denominator;
    # this does not make the master fresh enough for provider identity actions.
    assert result["counts"]["verified_eligible_common_equities"] == 99
    assert result["identity_status"]["observed_at"] is not None
    assert result["provider_requests"] == 0
    monkeypatch.setattr(engine, "workspace", stale)
    with pytest.raises(APIError):
        nse_market._read(service)


def test_task_query_timeout_marks_saved_snapshot_stale_and_keeps_receipt_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(nse_monitoring, "_CACHE", None)
    query = Mock(side_effect=TimeoutError("TEST_ONLY"))
    monkeypatch.setattr(nse_monitoring, "_bounded_query", query)
    at = datetime.now(UTC)
    saved = {
        "observed_at": (at - timedelta(days=1)).isoformat(),
        "state": "Ready",
        "last_result": 1,
    }
    result = nse_monitoring.windows_observation(saved, at=at)
    assert result["stale"] is True
    assert result["last_result"] == 1
    assert result["live_query_state"] == "UNAVAILABLE_OR_TIMEOUT"
    nse_monitoring.windows_observation(saved, at=at)
    assert query.call_count == 1
    assert saved.get("stale") is None


def test_local_com_proxies_release_before_apartment_uninitialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    events: list[str] = []

    class Task:
        State, Enabled, LastTaskResult = 3, True, 0
        LastRunTime = NextRunTime = datetime.now(UTC)

        def __del__(self) -> None:
            events.append("task_released")

    class Service:
        def Connect(self) -> None:
            events.append("connect_local")

        def GetFolder(self, name: str) -> Any:
            return SimpleNamespace(GetTask=lambda name: Task())

        def __del__(self) -> None:
            events.append("service_released")

    com = SimpleNamespace(
        CoInitialize=lambda: events.append("initialize"),
        CoUninitialize=lambda: events.append("uninitialize"),
    )
    client = SimpleNamespace(Dispatch=lambda name: Service())
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: com if name == "pythoncom" else client,
    )
    assert nse_monitoring._query_windows()["state"] == "Ready"
    assert events == [
        "initialize",
        "connect_local",
        "task_released",
        "service_released",
        "uninitialize",
    ]


def test_full_cohort_pending_is_not_prebatch_or_paginated(tmp_path: Path) -> None:
    value: dict[str, Any] = {
        "coverage": {
            "end": "2025-01-03",
            "configured_securities": 3,
            "per_security": [
                {"key": "a", "last": "2025-01-03"},
                {"key": "b", "last": "2025-01-02"},
                {"key": "c", "last": "2025-01-02"},
            ],
        },
        "operations": {
            "collection": {
                "pending_securities": 3,
                "failures": [
                    {"key": "b", "reason": "PUBLICATION_PENDING"},
                    {"key": "c", "reason": "INVALID_OHLCV"},
                ],
            }
        },
    }
    original = copy.deepcopy(value["coverage"])
    nse_monitoring.enrich(value, tmp_path, at=datetime.now(UTC))
    counts = value["operations"]["session_status"]
    assert counts["updated_or_already_verified"] == 1
    assert counts["pending_securities"] == 2
    assert counts["failed_securities"] == 1
    assert value["coverage"] == original
