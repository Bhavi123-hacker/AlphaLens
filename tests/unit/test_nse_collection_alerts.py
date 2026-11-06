"""TEST_ONLY separate derived alerts, repeat/restart idempotency and fault isolation."""

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.alerts.contracts import Event
from workers.alerts.store import AlertStore
from workers.experimental_nse.acquire import digest, initialize
from workers.nse_market import collection_alerts, diagnostics, engine, operational, reliability

AT = datetime(2025, 1, 4, 12, tzinfo=UTC)


def status() -> dict[str, Any]:
    return {
        "read_at": AT.isoformat(),
        "coverage_session": "2025-01-03",
        "expected_trading_session": "2025-01-03",
        "accepted_securities": 1,
        "missing_securities": 2,
        "missing_data_reasons": {"TEST_ONLY_PENDING": 2},
        "last_failed_run": {"run_id": "TEST_ONLY_failure", "state": "FAILED"},
        "forecast_freshness": {
            "fresh_for_expected_session": False,
            "saved_predictions": 1,
            "observation_session": "2025-01-02",
        },
        "quota": {
            "ist_day": "2025-01-04",
            "reserved_requests_remaining": 0,
            "approved_run_reservation": 600,
            "run_slots_remaining": 0,
        },
    }


def test_derived_alerts_deduplicate_across_repeated_reads_and_process_restarts(
    tmp_path: Path,
) -> None:
    tmp_path = tmp_path / "TEST_ONLY_market"
    initialize(tmp_path)
    initial = status()
    assert (
        collection_alerts.publish(tmp_path, initial, at=AT, test_only=True)["alerts_published"] == 4
    )
    repeated = copy.deepcopy(initial)
    repeated["read_at"] = (AT + timedelta(minutes=1)).isoformat()
    assert (
        collection_alerts.publish(tmp_path, repeated, at=AT, test_only=True)["alerts_published"]
        == 0
    )
    listing = collection_alerts.listing(tmp_path, test_only=True)
    assert listing["total"] == 4
    assert {row["evidence"]["code"] for row in listing["alerts"]} == {
        "DATA_MISSING",
        "PIPELINE_FAILED",
        "INFERENCE_BLOCKED",
        "SOURCE_BLOCKED",
    }
    assert listing["provider_requests"] == 0 and listing["outbound_delivery"] is False
    assert collection_alerts.load(tmp_path) == repeated
    # A new object/process reads durable deduplication and cursor state.
    assert AlertStore(tmp_path / collection_alerts.DIRECTORY).listing(test_only=True)[1] == 4
    assert (
        collection_alerts.publish(tmp_path, repeated, at=AT, test_only=True)["alerts_published"]
        == 0
    )


def test_original_47_alert_payloads_are_preserved(tmp_path: Path) -> None:
    original = AlertStore(tmp_path / "TEST_ONLY_original_alerts")
    original.initialize()
    events = [
        Event(
            code="DATA_MISSING",
            component="P19",
            evidence_ref="TEST_ONLY",
            evidence_sha256="a" * 64,
            event_at=AT,
            time_basis="PERSISTED_EVENT_TIME",
            classification="TEST_ONLY",
            mode="TEST_ONLY",
            group="TEST_ONLY",
            identity=str(index),
        )
        for index in range(47)
    ]
    assert original.publish("TEST_ONLY_original", "a" * 64, events, now=AT) == 47
    protected = original.listing(limit=100, test_only=True)
    before = digest(original.path.read_bytes())
    market = tmp_path / "TEST_ONLY_market"
    initialize(market)
    collection_alerts.publish(market, status(), at=AT, test_only=True)
    assert original.listing(limit=100, test_only=True) == protected
    assert digest(original.path.read_bytes()) == before
    assert (market / collection_alerts.DIRECTORY / "alerts.sqlite3").is_file()


def test_quota_alert_uses_reserved_capacity_not_number_of_http_successes(tmp_path: Path) -> None:
    tmp_path = tmp_path / "TEST_ONLY_market"
    initialize(tmp_path)
    data = status()
    data.update(
        missing_securities=0,
        last_failed_run=None,
        forecast_freshness={"fresh_for_expected_session": True},
    )
    data["quota"]["reserved_requests_remaining"] = 599
    assert collection_alerts.publish(tmp_path, data, at=AT, test_only=True)["alerts_published"] == 1
    data["quota"].update(reserved_requests_remaining=600, run_slots_remaining=1)
    assert collection_alerts.publish(tmp_path, data, at=AT, test_only=True)["alerts_published"] == 0
    assert collection_alerts.listing(tmp_path, test_only=True)["total"] == 1


def test_failed_derived_alert_stage_keeps_original_terminal_and_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = tmp_path / "TEST_ONLY_market"
    initialize(tmp_path)
    terminal = {
        "run_id": "a" * 32,
        "launch_id": "b" * 32,
        "collection_requested": True,
        "state": "FAILED",
    }
    saved = tmp_path / "TEST_ONLY_terminal.json"
    engine._checked(saved, terminal)
    before = saved.read_bytes()
    monkeypatch.setattr(
        collection_alerts,
        "from_terminal",
        lambda *args: (_ for _ in ()).throw(OSError("TEST_ONLY_PRIVATE_TEXT")),
    )
    facts: list[Any] = []
    monkeypatch.setattr(diagnostics, "emit", lambda *args, **kwargs: facts.append(kwargs))
    operational._publish_monitoring(tmp_path, terminal)
    assert saved.read_bytes() == before
    assert facts[0]["code"] == "DERIVED_ALERT_PUBLICATION_FAILED"
    assert "TEST_ONLY_PRIVATE_TEXT" not in str(facts)


def test_read_only_alert_listing_does_not_initialize_or_publish(tmp_path: Path) -> None:
    assert collection_alerts.load(tmp_path) == {}
    assert collection_alerts.listing(tmp_path)["total"] == 0
    assert list(tmp_path.iterdir()) == []


def test_automatic_monitoring_uses_validated_terminal_when_derived_view_is_older(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY_market"
    initialize(root)
    plan = root / "TEST_ONLY_plan.json"
    identities = [
        {
            "provider_key": "NSE_EQ|TEST_ONLY_" + str(index),
            "symbol": "TEST_ONLY_" + str(index),
            "isin": str(index),
        }
        for index in range(3)
    ]
    engine._checked(plan, {"identities": identities})
    engine._pointer(root, "plan-latest.json", plan)
    old_view = root / "TEST_ONLY_old_view.json"
    engine._checked(
        old_view,
        {
            "dataset_id": "a" * 64,
            "latest_observed_session": "2025-01-02",
            "configured_securities": 3,
            "rows": [{"key": row["provider_key"], "session": "2025-01-02"} for row in identities],
        },
    )
    engine._pointer(root, "market-view-latest.json", old_view)
    captured: list[dict[str, Any]] = []

    def capture(unused: Path, status: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        captured.append(status)
        return {}

    monkeypatch.setattr(collection_alerts, "publish", capture)
    monkeypatch.setattr(
        reliability,
        "expected_session",
        lambda *args, **kwargs: {"expected_trading_session": "2025-01-03"},
    )
    terminal = {
        "run_id": "a" * 32,
        "state": "PARTIAL_OR_PUBLICATION_PENDING",
        "outcome": {
            "session": "2025-01-03",
            "pending_count_basis": "FULL_CONFIGURED_COHORT_AFTER_VALIDATION",
            "configured_securities": 3,
            "accepted_session_securities": 1,
            "pending_securities": 2,
            "accepted_session_keys": [identities[0]["provider_key"]],
            "dataset_id": "b" * 64,
        },
    }
    collection_alerts.from_terminal(root, terminal)
    health = captured[0]
    assert health["accepted_securities"] == 1 and health["missing_securities"] == 2
    assert health["coverage_session"] == "2025-01-03"
    assert health["missing_data_reasons"] == {
        "NOT_QUERIED_FOR_SESSION_NO_ACCEPTED_SOURCE_RECORD": 2
    }
    assert len(health["missing_security_details"]) == 2
    assert health["forecast_freshness"]["fresh_for_expected_session"] is False
