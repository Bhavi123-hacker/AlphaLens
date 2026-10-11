"""TEST_ONLY operational evidence, never synthetic market notifications in application mode."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.build_p19_test_evidence import parquet, request
from scripts.build_p20_test_evidence import AT, event
from workers.alerts.contracts import FreshnessEvidence, Preferences
from workers.alerts.producer import check_freshness, process_daily, receipt_events, source_check
from workers.alerts.store import AlertError, AlertStore, quiet
from workers.daily.engine import Worker

from alphalens_data.daily.contracts import Session
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum


@pytest.fixture
def store(tmp_path: Path) -> AlertStore:
    value = AlertStore(tmp_path / "alerts")
    value.initialize()
    return value


def test_dedup_replay_restart_and_changed_failure(store: AlertStore) -> None:
    first = event()
    assert store.publish("TEST_ONLY_SOURCE", "a", [first], now=AT) == 1
    restarted = AlertStore(store.root)
    assert restarted.publish("TEST_ONLY_SOURCE", "a", [first]) == 0
    assert restarted.publish("TEST_ONLY_SOURCE", "b", [first]) == 0
    assert restarted.publish("TEST_ONLY_SOURCE", "c", [event(identity="TEST_ONLY_CHANGED")]) == 1
    assert store.listing(test_only=True)[1] == 2
    with pytest.raises(AlertError, match="TEST_ONLY"):
        store.listing()


def test_concurrent_unique_publication(store: AlertStore) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(
            pool.map(lambda _: store.publish("TEST_ONLY_SHARED", "same", [event()]), range(24))
        )
    assert sum(counts) == 1
    assert store.listing(test_only=True)[1] == 1


def test_atomic_evidence_cursor_recovery(
    store: AlertStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = store.audit

    def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("TEST_ONLY_CRASH")

    monkeypatch.setattr(store, "audit", fail)
    with pytest.raises(RuntimeError):
        store.publish("TEST_ONLY_CURSOR", "same", [event()])
    with store.connection() as connection:
        assert connection.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM seen").fetchone()[0] == 0
    monkeypatch.setattr(store, "audit", original)
    assert store.publish("TEST_ONLY_CURSOR", "same", [event()]) == 1


def test_lifecycle_delivery_and_unread_are_separate(store: AlertStore) -> None:
    item = event()
    store.publish("TEST_ONLY", "one", [item], now=AT)
    assert store.unread(test_only=True) == 0
    assert store.deliver(now=AT) == {"DELIVERED": 1}
    assert store.unread(test_only=True) == 1
    store.transition(item.alert_id, "READ")
    assert store.unread(test_only=True) == 0
    store.transition(item.alert_id, "ACKNOWLEDGED")
    store.transition(item.alert_id, "RESOLVED")
    assert store.get(item.alert_id, test_only=True)["delivery"] == "DELIVERED"
    with pytest.raises(AlertError, match="INVALID_ALERT_TRANSITION"):
        store.transition(item.alert_id, "READ")
    store.transition(item.alert_id, "RESOLVED")  # Idempotent control.


def test_quiet_hours_preserve_warning_and_deliver_critical(store: AlertStore) -> None:
    store.set_preferences(Preferences(quiet_enabled=True, quiet_start="17:00", quiet_end="19:00"))
    assert quiet(AT, store.preferences())  # 17:30 IST.
    warning, critical = event(), event("INTEGRITY_FAILURE", "TEST_ONLY_CRITICAL")
    store.publish("TEST_ONLY", "one", [warning, critical], now=AT)
    assert store.deliver(now=AT) == {"RETRY_PENDING": 1, "DELIVERED": 1}
    retained = store.get(warning.alert_id, test_only=True)
    assert retained["attempts"] == 0 and retained["delivery_reason"] == "QUIET_HOURS"
    assert store.deliver(now=AT + timedelta(hours=2)) == {"DELIVERED": 1}


@pytest.mark.parametrize("hour,expected", [(15, False), (17, True), (22, True), (3, False)])
def test_overnight_quiet_interval(hour: int, expected: bool) -> None:
    assert quiet(AT.replace(hour=hour), Preferences(quiet_enabled=True)) is expected


def test_cooldown_and_preferences_retain_evidence(store: AlertStore) -> None:
    one, two, info = (
        event(),
        event(identity="TEST_ONLY_SECOND"),
        event("PIPELINE_COMPLETED", "TEST_ONLY_INFO"),
    )
    store.publish("TEST_ONLY", "one", [one], now=AT)
    store.deliver(now=AT)
    store.publish("TEST_ONLY", "two", [two, info], now=AT)
    assert store.deliver(now=AT) == {"SUPPRESSED": 2}
    assert store.get(two.alert_id, test_only=True)["delivery_reason"] == "COOLDOWN"
    assert store.listing(test_only=True)[1] == 3
    store.set_preferences(Preferences(categories=(), include_info=True))
    third = event("PIPELINE_FAILED", "TEST_ONLY_THIRD")
    store.publish("TEST_ONLY", "three", [third])
    assert store.deliver(now=AT) == {"SUPPRESSED": 1}


def test_bounded_failure_backoff_redaction_and_restart(store: AlertStore) -> None:
    item = event("INTEGRITY_FAILURE")
    store.publish("TEST_ONLY", "one", [item])

    def fail(_: dict[str, Any]) -> None:
        raise RuntimeError("TEST_ONLY_PRIVATE_CREDENTIAL_MUST_NOT_APPEAR")

    assert store.deliver(now=AT, publisher=fail) == {"RETRY_PENDING": 1}
    assert store.deliver(now=AT + timedelta(seconds=29), publisher=fail) == {}
    assert store.deliver(now=AT + timedelta(seconds=30), publisher=fail) == {"RETRY_PENDING": 1}
    restarted = AlertStore(store.root)
    assert restarted.deliver(now=AT + timedelta(seconds=90), publisher=fail) == {"FAILED": 1}
    assert restarted.deliver(now=AT + timedelta(days=1)) == {}
    row = store.get(item.alert_id, test_only=True)
    assert row["attempts"] == 3 and row["delivery_reason"] == "LOCAL_PUBLICATION_FAILED"
    assert "PRIVATE_CREDENTIAL" not in str(row)


def test_retention_tombstones_protect_replay_and_critical(store: AlertStore) -> None:
    warning, critical = event(), event("INTEGRITY_FAILURE", "TEST_ONLY_CRITICAL")
    store.publish("TEST_ONLY", "one", [warning, critical], now=AT)
    for item in (warning, critical):
        store.transition(item.alert_id, "RESOLVED")
    assert store.prune(now=AT + timedelta(days=91)) == 1
    assert store.publish("TEST_ONLY", "changed_cursor", [warning], now=AT) == 0
    assert store.listing(test_only=True)[1] == 1


def test_pagination_search_and_severity(store: AlertStore) -> None:
    store.publish("TEST_ONLY", "one", [event(identity=f"TEST_ONLY_{i}") for i in range(25)])
    first, count = store.listing(limit=20, test_only=True)
    second, _ = store.listing(limit=20, offset=20, test_only=True)
    assert count == 25 and len(second) == 5
    assert not {r["id"] for r in first} & {r["id"] for r in second}
    assert store.listing(search="daily source", severity="WARNING", test_only=True)[1] == 25
    assert store.listing(severity="CRITICAL", test_only=True)[1] == 0
    with pytest.raises(AlertError, match="QUERY_LIMIT"):
        store.listing(limit=101)


def test_evidence_tamper_rejected(store: AlertStore) -> None:
    item = event()
    store.publish("TEST_ONLY", "one", [item])
    with store.connection(write=True) as connection:
        connection.execute("UPDATE alerts SET evidence='{}'")
    with pytest.raises(AlertError, match="CHECKSUM"):
        store.get(item.alert_id, test_only=True)


@pytest.mark.parametrize(
    "changes",
    [
        {"email": True},
        {"desktop": True},
        {"categories": ["STOCK_SIGNAL"]},
        {"maximum_attempts": 6},
        {"quiet_enabled": True, "quiet_start": "07:00", "quiet_end": "07:00"},
    ],
)
def test_disabled_channels_and_invalid_preferences(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Preferences.model_validate(changes)


@pytest.mark.parametrize("code", ["PREDICTION_AVAILABLE", "BUY", "SELL", "STOCK_SIGNAL"])
def test_unsupported_predictions_and_stock_alerts(code: str) -> None:
    with pytest.raises(ValidationError):
        event(code)


def test_real_p19_event_types_and_replay(store: AlertStore, tmp_path: Path) -> None:
    payload = parquet(tmp_path / "TEST_ONLY.parquet")
    daily_root = tmp_path / "daily"
    Worker(daily_root).run(request(payload), payload)
    assert process_daily(store, daily_root)["published"] > 0
    assert process_daily(store, daily_root)["published"] == 0
    rows, _ = store.listing(test_only=True)
    assert {r["evidence"]["classification"] for r in rows} == {"TEST_ONLY"}
    assert "INFERENCE_BLOCKED" in {r["evidence"]["code"] for r in rows}
    assert "PIPELINE_COMPLETED" in {r["evidence"]["code"] for r in rows}


def test_interrupted_checkpoint_then_recovered_receipt(store: AlertStore, tmp_path: Path) -> None:
    payload = parquet(tmp_path / "TEST_ONLY.parquet")
    req = request(payload)
    worker = Worker(
        tmp_path / "daily",
        hook=lambda stage: (
            (_ for _ in ()).throw(TimeoutError()) if stage == "before_publish" else None
        ),
    )
    with pytest.raises(DataContractError, match="RETRYABLE_FAILURE"):
        worker.run(req, payload)
    process_daily(store, worker.store.root)
    assert "PUBLICATION_INCOMPLETE" in {
        r["evidence"]["code"] for r in store.listing(test_only=True)[0]
    }
    Worker(worker.store.root).run(req, payload)
    process_daily(store, worker.store.root)
    assert "RECOVERED" in {
        r["evidence"]["code"] for r in store.listing(limit=100, test_only=True)[0]
    }


def test_corrupt_p19_product_becomes_durable_integrity_alert(
    store: AlertStore, tmp_path: Path
) -> None:
    payload = parquet(tmp_path / "TEST_ONLY.parquet")
    req = request(payload)
    worker = Worker(tmp_path / "daily")
    worker.run(req, payload)
    worker.store.path(req.run_id, "canonical.json").write_text("{}")
    assert process_daily(store, worker.store.root)["invalid"] == 1
    rows, count = store.listing(test_only=True)
    assert count == 1 and rows[0]["severity"] == "CRITICAL"
    assert process_daily(store, worker.store.root)["published"] == 0


def test_no_source_event_spam_on_repeated_check(store: AlertStore) -> None:
    first = source_check(store, now=AT)
    assert first["live_data_activation"] == "BLOCKED"
    assert not first["price_download_attempted"]
    assert first["alerts_published"] == 1
    assert source_check(store, now=AT + timedelta(hours=1))["alerts_published"] == 0


def test_receipt_mapping_never_uses_positive_research_score(tmp_path: Path) -> None:
    row = Worker(tmp_path / "daily").run(request())
    row["rank_ic"] = 1.0
    assert all(e.code not in {"PREDICTION_AVAILABLE", "BUY", "SELL"} for e in receipt_events(row))


@pytest.mark.parametrize(
    "kind",
    ["SPECIAL_TRADING", "HOLIDAY", "FUTURE_KNOWLEDGE", "PENDING_RELEASE", "UNCLEARED_REAL_SOURCE"],
)
def test_freshness_requires_calendar_release_and_source_evidence(
    store: AlertStore, tmp_path: Path, kind: str
) -> None:
    session = Session(
        session=AT.date(),
        status="NON_TRADING" if kind == "HOLIDAY" else "TRADING",
        known_at=AT + timedelta(hours=1) if kind == "FUTURE_KNOWLEDGE" else AT - timedelta(days=1),
        evidence_reference="TEST_ONLY_SPECIAL_SESSION",
        evidence_type="OFFICIAL_VERIFIED_SESSION"
        if kind == "UNCLEARED_REAL_SOURCE"
        else "TEST_ONLY",
    )
    evidence = FreshnessEvidence(
        provider=request().provider,
        session=session,
        release_window_known_at=AT - timedelta(days=1),
        expected_available_at=AT + timedelta(hours=1)
        if kind == "PENDING_RELEASE"
        else AT - timedelta(hours=1),
        release_evidence_ref="TEST_ONLY_DOCUMENTED_RELEASE_WINDOW",
        classification="RESEARCH_ONLY" if kind == "UNCLEARED_REAL_SOURCE" else "TEST_ONLY",
    )
    payload = stable_json(evidence.model_dump(mode="json"))
    path = tmp_path / f"{checksum(payload)}.json"
    path.write_bytes(payload)
    result = check_freshness(store, path, tmp_path / "empty", test_only=True, now=AT)
    assert result["alerts_published"] == (1 if kind == "SPECIAL_TRADING" else 0)
    if kind == "SPECIAL_TRADING":
        assert AT.weekday() == 6  # Explicit Sunday session; no weekday inference.
        assert (
            check_freshness(
                store, path, tmp_path / "empty", test_only=True, now=AT + timedelta(hours=1)
            )["alerts_published"]
            == 0
        )
        assert store.listing(test_only=True)[0][0]["evidence"]["code"] == "SESSION_DELAYED"
        with pytest.raises(AlertError, match="TEST_ONLY"):
            check_freshness(store, path, tmp_path / "empty", now=AT)


def test_persisted_paper_and_valuation_inputs_are_verified_and_redacted(
    store: AlertStore, tmp_path: Path
) -> None:
    from datetime import date

    from scripts.build_p6_test_fixture import build_history
    from scripts.build_p15_test_fixture import bought, clock
    from scripts.build_p16_test_fixture import account, calendar
    from scripts.build_p16_test_fixture import request as paper_request
    from workers.alerts.producer import process_paper, process_valuation

    from alphalens_data.canonical.services import CanonicalReader
    from alphalens_portfolio.paper import process_session
    from alphalens_portfolio.paper_storage import save
    from alphalens_portfolio.valuation import value

    reader = CanonicalReader(build_history(tmp_path / "TEST_ONLY", length=3)[0])
    state = process_session(
        account(), reader, calendar(reader), date(2024, 1, 1), clock(1), manual=(paper_request(),)
    )
    state = process_session(state, reader, calendar(reader), date(2024, 1, 2), clock(2))
    path = save(tmp_path / "paper", state)
    with pytest.raises(AlertError, match="TEST_ONLY"):
        process_paper(store, path)
    assert process_paper(store, path, test_only=True) > 0
    assert process_paper(store, path, test_only=True) == 0
    rows, _ = store.listing(limit=100, test_only=True)
    assert "PAPER_FILL" in {r["evidence"]["code"] for r in rows}
    assert all(
        "observed_open" not in str(r)
        and "starting_cash" not in str(r)
        and "TEST_ONLY forward simulation" not in str(r)
        for r in rows
    )
    snapshot = value(bought(), reader, date(2024, 1, 10), clock(10))
    snapshot_path = tmp_path / f"{snapshot.snapshot_id}.json"
    snapshot_path.write_bytes(stable_json(snapshot.model_dump(mode="json")))
    assert process_valuation(store, snapshot_path, test_only=True) > 0
    assert process_valuation(store, snapshot_path, test_only=True) == 0
    assert "VALUATION_UNRESOLVED" in {
        r["evidence"]["code"] for r in store.listing(limit=100, test_only=True)[0]
    }
    path.write_text("{}")
    with pytest.raises(ValueError):
        process_paper(store, path, test_only=True)


def test_lock_conflict_is_observed_without_interrupting_owner(
    store: AlertStore, tmp_path: Path
) -> None:
    from workers.alerts.producer import inspect_lock

    from alphalens_data.daily.storage import Store

    daily = Store(tmp_path / "daily")
    with daily.lock():
        assert inspect_lock(store, daily.root)["status"] == "DAILY_WORKER_BUSY"
        assert inspect_lock(store, daily.root)["alerts_published"] == 0
    assert inspect_lock(store, daily.root)["status"] == "AVAILABLE_AT_PROBE_TIME"
    assert store.listing()[0][0]["evidence"]["code"] == "WORKER_LOCK"


def test_invalid_request_creates_integrity_evidence_without_invented_classification(
    store: AlertStore, tmp_path: Path
) -> None:
    from alphalens_data.daily.storage import Store

    daily = Store(tmp_path / "daily")
    daily.write("b" * 64, "request.json", {"untrusted": "TEST_ONLY_UNKNOWN_PAYLOAD"})
    result = process_daily(store, daily.root)
    assert result["invalid"] == 1
    item = store.listing()[0][0]
    assert item["severity"] == "CRITICAL"
    assert item["evidence"]["classification"] == "UNVERIFIED_OPERATIONAL_EVIDENCE"
    assert "UNKNOWN_PAYLOAD" not in str(item)


def test_cli_preferences_controls_retries_and_safe_errors(
    store: AlertStore, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from workers.alerts.cli import main

    prefix = ["--root", str(store.root)]
    store.publish("TEST_ONLY_CLI", "one", [event()])
    assert main([*prefix, "deliver"]) == 0
    assert main([*prefix, "state", event().alert_id, "READ"]) == 0
    assert store.get(event().alert_id, test_only=True)["lifecycle"] == "READ"
    path = tmp_path / "prefs.json"
    path.write_text(Preferences(categories=(), include_info=True).model_dump_json())
    assert main([*prefix, "preferences", "--file", str(path)]) == 0
    assert store.preferences().categories == ()
    assert main([*prefix, "retry"]) == 0
    assert main([*prefix, "list", "--test-only", "--limit", "1"]) == 0
    capsys.readouterr()
    path.write_text('{"secret":"TEST_ONLY_DO_NOT_PRINT"}')
    assert main([*prefix, "preferences", "--file", str(path)]) == 2
    assert "DO_NOT_PRINT" not in capsys.readouterr().out
