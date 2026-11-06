"""TEST_ONLY saved monitoring cannot turn unknown tradability or stale audits green."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_nse_market import identity
from workers.experimental_nse.acquire import digest, encoded, initialize
from workers.nse_market import engine, reliability
from workers.nse_market import operational_health as health

AT = datetime(2025, 1, 4, 12, tzinfo=UTC)


def checked(root: Path, name: str, value: dict[str, Any]) -> None:
    target = root / (name + ".record.json")
    engine._checked(target, value)
    engine._pointer(root, name + ".json", target)


def test_later_master_does_not_prove_historical_tradability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = tmp_path / "TEST_ONLY_market"
    initialize(tmp_path)
    item = identity(1).model_dump(mode="json")
    checked(tmp_path, "plan-latest", {"identities": [item]})
    master = SimpleNamespace(
        records=[
            {
                "instrument_key": item["provider_key"],
                "eligible_common_equity": True,
            }
        ],
        observed_at=AT,
    )
    monkeypatch.setattr(
        health,
        "_raw_identities",
        lambda *_: {
            item["provider_key"]: {"exchange_token": "TEST_ONLY_token"},
        },
    )
    folder = tmp_path / "daily/2025-01-03" / str(item["isin"]) / "publication-attempts"
    folder.mkdir(parents=True)
    body = encoded({"data": {"candles": []}})
    engine._checked(
        folder / "1.json",
        {
            "key": item["provider_key"],
            "received_at": AT.isoformat(),
            "raw_hex": body.hex(),
            "raw_sha256": digest(body),
            "state": "PUBLICATION_PENDING",
        },
    )
    view = {
        "rows": [],
        "histories": {
            item["provider_key"]: [
                {"session": "2025-01-02", "close": 1},
                {"session": "2025-01-06", "close": 2},
            ]
        },
    }
    report = health.gaps(tmp_path, tmp_path, master, view, session="2025-01-03")  # type: ignore[arg-type]
    assert report["raw_configured_coverage"] == {
        "numerator": 0,
        "denominator": 1,
        "measurement_status": "MEASURED_CONFIGURED_COHORT",
    }
    assert report["historical_session_eligible_securities"] is None
    assert report["eligible_universe_coverage"] is None
    missing = report["missing_security_details"][0]
    assert missing["listed_on_expected_session"] is None
    assert missing["tradable_on_expected_session"] is None
    assert missing["valid_candle_expected"] is None
    assert missing["last_accepted_candle"]["session"] == "2025-01-02"
    attempt = missing["provider_response_history"][0]
    assert attempt["returned_candles"] == 0
    assert attempt["http_status"] is None  # Never invent 200 from a valid empty body.
    assert attempt["http_status_basis"] == "NOT_RETAINED_IN_ORIGINAL_ATTEMPT_RECEIPT"


def test_current_day_reservations_do_not_reuse_yesterdays_quota(tmp_path: Path) -> None:
    tmp_path = tmp_path / "TEST_ONLY_market"
    initialize(tmp_path)
    folder = tmp_path / "operational/runs"
    folder.mkdir(parents=True)
    engine._checked(
        folder / "old.started.json",
        {
            "quota_day": "2025-01-03",
            "reserved_requests": 600,
        },
    )
    policy = {"max_requests_per_day": 1800, "max_requests_per_run": 600, "max_runs_per_day": 3}
    report = health._quota(tmp_path, policy, at=AT)
    assert report["reserved_requests_remaining"] == 1800
    assert report["run_slots_remaining"] == 3
    assert report["unused_capacity_authorizes_new_run"] is False
    assert health._quota(tmp_path, {}, at=AT)["reserved_requests_remaining"] is None


def test_unified_snapshot_detects_new_ledger_without_replaying_market_archive(
    tmp_path: Path,
) -> None:
    root = tmp_path / "market"
    initialize(root)
    checked(root, "market-view-latest", {"dataset_id": "TEST_ONLY_source"})
    scores: dict[str, Any] = {"candidates": []}
    checked(root, "scores-latest", scores)
    v2 = root.parent / "experimental-nse-v2"
    report = {
        "observed_at": AT.isoformat(),
        "source_dataset_id": "TEST_ONLY_source",
        "score_snapshot_sha256": digest(encoded(scores)),
        "ledger_signature": health.ledger_signature(root, v2),
        "qualification_observed_at": None,
        "source_bindings": health.source_bindings(root, v2, root.parent / "nse-universe"),
    }
    health.publish(root, report)
    first = health.load(root, at=AT)
    assert not first["snapshot_stale"]
    assert first["qualification_stale"]
    folder = root / "expanded-forecasts/TEST_ONLY_ledger"
    folder.mkdir(parents=True)
    # No SQLite access is performed for signature freshness detection.
    (folder / "experimental-v2-prospective.sqlite3").write_bytes(b"TEST_ONLY_marker")
    assert health.load(root, at=AT)["source_changed_since_report"]
    assert health.load(root, at=AT + timedelta(days=2))["snapshot_stale"]
    with pytest.raises(ValueError, match="SNAPSHOT_CLOCK_REJECTED"):
        health.load(root, at=AT - timedelta(seconds=1))


def test_unconfigured_health_is_unavailable_without_writes(tmp_path: Path) -> None:
    assert health.load(tmp_path, at=AT)["status"] == "UNAVAILABLE"
    health.after_terminal(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_unknown_expected_session_never_becomes_zero_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = tmp_path / "TEST_ONLY_market"
    initialize(tmp_path)
    item = identity(1).model_dump(mode="json")
    checked(tmp_path, "plan-latest", {"identities": [item]})
    master = SimpleNamespace(records=[], observed_at=AT)
    monkeypatch.setattr(health, "_raw_identities", lambda *_: {})
    result = health.gaps(tmp_path, tmp_path, master, {"rows": [], "histories": {}}, session=None)  # type: ignore[arg-type]
    assert result["updated_securities"] is result["missing_securities"] is None
    assert result["raw_configured_coverage"] == {
        "numerator": None,
        "denominator": 1,
        "measurement_status": "NOT_YET_MEASURABLE",
    }
    assert (
        result["missing_security_details"][0]["reason"] == "EXPECTED_SESSION_CALENDAR_UNAVAILABLE"
    )


def saved_report(
    root: Path, *, observed: datetime = AT, qualification: dict[str, Any] | None = None
) -> tuple[Path, Path]:
    initialize(root)
    view: dict[str, Any] = {"dataset_id": "TEST_ONLY_source"}
    scores: dict[str, Any] = {"candidates": []}
    checked(root, "market-view-latest", view)
    checked(root, "scores-latest", scores)
    v2, master = root.parent / "TEST_ONLY_custom_v2", root.parent / "TEST_ONLY_custom_master"
    report = {
        "observed_at": observed.isoformat(),
        "source_dataset_id": view["dataset_id"],
        "score_snapshot_sha256": digest(encoded(scores)),
        "ledger_signature": health.ledger_signature(root, v2),
        "source_roots": {"v2_root": str(v2), "master_root": str(master)},
        "source_bindings": health.source_bindings(root, v2, master),
        "latest_trading_session": None,
        "provider_quota": {"ist_day": observed.astimezone(reliability.IST).date().isoformat()},
        "qualification_observed_at": qualification["observed_at"] if qualification else None,
        "qualification_sha256": digest(encoded(qualification)) if qualification else None,
    }
    health.publish(root, report, qualification=qualification)
    return v2, master


@pytest.mark.parametrize("source", ["calendar", "master", "policy", "terminal", "reservation"])
def test_small_source_changes_invalidate_snapshot_before_24_hours(
    tmp_path: Path, source: str
) -> None:
    root = tmp_path / "market"
    _, master = saved_report(root)
    assert not health.load(root, at=AT)["snapshot_stale"]
    selected = {
        "calendar": root / "calendar/TEST_ONLY.json",
        "master": master / "latest.json",
        "policy": root / "operational/TEST_ONLY_config.json",
        "terminal": root / "operational-latest.json",
        "reservation": root / "operational/runs/TEST_ONLY.started.json",
    }[source]
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_text("TEST_ONLY_changed_source", encoding="utf-8")
    # Calendar contents are independently validated by expected_session; choose a
    # non-date filename so this test isolates the small-source binding.
    changed = health.load(root, at=AT + timedelta(seconds=1))
    assert changed["source_changed_since_report"] and changed["snapshot_stale"]


def test_midnight_and_newly_completed_session_invalidate_even_without_file_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "market"
    observed = datetime(2025, 1, 4, 18, 29, tzinfo=UTC)  # 23:59 IST
    saved_report(root, observed=observed)
    changed = health.load(root, at=observed + timedelta(minutes=2))
    assert changed["snapshot_age_seconds"] < 86400
    assert changed["ist_day_changed_since_report"] and changed["quota_stale"]
    monkeypatch.setattr(
        reliability,
        "expected_session",
        lambda root, at: {"expected_trading_session": "2025-01-06"},
    )
    completed = health.load(root, at=observed + timedelta(minutes=3))
    assert completed["expected_session_changed_since_report"] and completed["snapshot_stale"]


def test_explicit_qualification_is_bound_without_initial_staleness_then_change_invalidates(
    tmp_path: Path,
) -> None:
    root = tmp_path / "market"
    qualification = {
        "observed_at": AT.isoformat(),
        "collector_runtime": {},
        "security": {"container_high": 0},
    }
    saved_report(root, qualification=qualification)
    initial = health.load(root, at=AT)
    assert not initial["snapshot_stale"] and not initial["qualification_stale"]
    folder = root / health.DIRECTORY
    replacement = folder / "TEST_ONLY_qualification.json"
    engine._checked(replacement, {**qualification, "security": {"container_high": 1}})
    engine._pointer(folder, "qualification-latest.json", replacement)
    changed = health.load(root, at=AT)
    assert changed["qualification_stale"] and changed["source_changed_since_report"]


def test_report_failure_keeps_terminal_and_completed_alert_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workers.nse_market import collection_alerts, diagnostics, operational

    terminal = {"collection_requested": True, "run_id": "TEST_ONLY", "launch_id": "TEST_ONLY"}
    original = encoded(terminal)
    stages: list[str] = []
    codes: list[str] = []
    monkeypatch.setattr(collection_alerts, "from_terminal", lambda *_: stages.append("ALERTS"))

    def rejected(_: Path) -> None:
        raise ValueError("TEST_ONLY_CORRUPT_REPORT")

    def capture(*args: Any, **kwargs: Any) -> None:
        codes.append(kwargs["code"])

    monkeypatch.setattr(health, "after_terminal", rejected)
    monkeypatch.setattr(diagnostics, "emit", capture)
    operational._publish_monitoring(tmp_path, terminal)
    assert stages == ["ALERTS"]
    assert codes == ["DERIVED_OPERATIONAL_REPORT_FAILED"]
    assert encoded(terminal) == original


@pytest.mark.parametrize(
    "bad",
    [
        {
            "observed_at": AT.isoformat(),
            "collector_runtime": {},
            "security": {"api_token": "TEST_ONLY"},
        },
        {
            "observed_at": AT.isoformat(),
            "collector_runtime": {},
            "security": {"container_high": True},
        },
        {
            "observed_at": AT.replace(tzinfo=None).isoformat(),
            "collector_runtime": {},
            "security": {},
        },
    ],
)
def test_unreviewed_or_ill_typed_qualification_is_rejected(bad: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="OPERATIONAL_QUALIFICATION"):
        health.validate_qualification(bad)
