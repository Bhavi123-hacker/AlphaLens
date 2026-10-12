"""Isolated TEST_ONLY prospective evidence; never investment-performance claims."""

import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.build_p19_test_evidence import AT, DAY, calendar, parquet, request
from workers.daily.engine import Worker
from workers.daily.forward import Forecast, ForwardStore, FuturePrice, outcome
from workers.daily.inference import input_compatibility

from alphalens_data.errors import DataContractError


@pytest.fixture
def evidence(tmp_path: Path) -> tuple[ForwardStore, Forecast, list[datetime]]:
    root = tmp_path / "TEST_ONLY" / "daily"
    root.mkdir(parents=True)
    path = parquet(root / "TEST_ONLY.parquet")
    req = request(path)
    worker = Worker(root)
    receipt = worker.run(req, path)
    row = worker.store.product(req.run_id, "canonical")["rows"][0]
    clock = [AT]
    store = ForwardStore(root, test_only=True, clock=lambda: clock[0])
    store.initialize()
    forecast = Forecast(
        classification="TEST_ONLY",
        source_run_id=req.run_id,
        source_receipt_sha256=receipt["receipt_sha256"],
        source_revision="TEST_ONLY",
        feature_registry_id=req.feature_registry_id,
        feature_product_sha256=receipt["products"]["features"]["sha256"],
        model_sha256="b" * 64,
        model_run_id="c" * 64,
        model_family="hist_gradient_boosting",
        security_id=row["security_id"],
        symbol="TEST_ONLY",
        session=DAY,
        horizon=1,
        predicted_direction=1,
        model_probability=0.6,
        decision_at=AT,
        received_at=AT,
        training_cutoff=AT - timedelta(days=300),
    )
    return store, forecast, clock


def prices(day: date, *, close: str = "110", action: str = "VERIFIED_NO_ACTION") -> FuturePrice:
    return FuturePrice.model_validate(
        dict(
            session=day,
            source_run_id="d" * 64,
            source_revision="TEST_ONLY",
            open="100",
            close=close,
            received_at=datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=18),
            eligible=True,
            action_status=action,
        )
    )


def test_atomic_replay_and_concurrent_records(evidence: Any) -> None:
    store, forecast, _ = evidence
    with ThreadPoolExecutor(max_workers=4) as pool:
        keys = list(pool.map(store.record, [forecast] * 8))
    assert len(set(keys)) == 1 and store.forecasts()["total"] == 1
    with pytest.raises(DataContractError, match="REWRITE"):
        store.record(forecast.model_copy(update={"model_probability": 0.9}))
    with sqlite3.connect(store.path) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM forecasts")
    reopened = ForwardStore(store.daily.root, test_only=True)
    assert reopened.forecasts()["rows"][0]["model_probability"] == 0.6


@pytest.mark.parametrize("change", [dict(source_revision="other"), dict(security_id="other")])
def test_provenance_rejects_unrelated_source(evidence: Any, change: Any) -> None:
    store, forecast, _ = evidence
    with pytest.raises(DataContractError, match="LINEAGE|SECURITY"):
        store.record(forecast.model_copy(update=change))


def test_normal_mode_cannot_promote_test_forecasts(evidence: Any) -> None:
    store, forecast, _ = evidence
    store.record(forecast)
    normal = ForwardStore(store.daily.root)
    commands: list[Callable[[], Any]] = [
        lambda: normal.record(forecast),
        normal.forecasts,
        normal.summary,
    ]
    for command in commands:
        with pytest.raises(DataContractError, match="ACCEPTANCE|TEST_ONLY"):
            command()
    with pytest.raises(DataContractError, match="ADAPTER"):
        normal.evaluate("a" * 64, calendar([DAY]), [])


def test_future_outcome_reuses_exact_p7_semantics(evidence: Any) -> None:
    store, forecast, clock = evidence
    key = store.record(forecast)
    next_day = date(2026, 10, 12)
    cal = calendar([DAY, next_day]).model_copy(
        update={"completeness": "VERIFIED_TRADING_SESSION_SEQUENCE"}
    )
    clock[0] = datetime(2026, 10, 13, tzinfo=UTC)
    first = store.evaluate(key, cal, [prices(next_day)])
    assert store.evaluate(key, cal, [prices(next_day)]) == first
    result = store.summary()
    assert result["resolved"] == 1 and result["pending"] == 0
    assert result["horizons"][0]["directional_accuracy"] == 1
    assert result["horizons"][0]["roc_auc"] is None
    assert result["economic_validation"].startswith("UNAVAILABLE")
    with store.connection() as conn:
        row = conn.execute("SELECT payload FROM outcomes").fetchone()[0]
    assert '"exact_numerator":"10"' in row and '"exact_denominator":"100"' in row


def test_maturity_calendar_action_and_chronology(evidence: Any) -> None:
    _, f, _ = evidence
    at = datetime(2026, 10, 20, tzinfo=UTC)
    cal = calendar([DAY, date(2026, 10, 12)]).model_copy(
        update={"completeness": "VERIFIED_TRADING_SESSION_SEQUENCE"}
    )
    assert outcome(f, calendar([DAY]), [], at, AT)["reasons"] == ["SESSION_SEQUENCE_NOT_VERIFIED"]
    assert outcome(f, cal, [], at, AT)["maturity"] == "NOT_YET_MATURE"
    assert (
        outcome(f, cal, [prices(date(2026, 10, 12), action="UNKNOWN")], at, AT)["maturity"]
        == "UNAVAILABLE"
    )
    late = datetime(2026, 10, 12, tzinfo=UTC)
    assert outcome(f, cal, [], at, late)["reasons"] == ["FORECAST_NOT_RECORDED_BEFORE_ENTRY_DATE"]
    with pytest.raises(DataContractError, match="PRECEDES"):
        outcome(f, cal, [], AT - timedelta(days=1), AT)


def test_corruption_pagination_and_isolation(evidence: Any, tmp_path: Path) -> None:
    store, forecast, _ = evidence
    store.record(forecast)
    with pytest.raises(DataContractError, match="PAGINATION"):
        store.forecasts(101)
    with pytest.raises(DataContractError, match="NAMESPACE"):
        ForwardStore(tmp_path / "normal", test_only=True)
    with sqlite3.connect(store.path) as conn:
        conn.execute("DROP TRIGGER forecast_no_update")
        conn.execute("UPDATE forecasts SET payload='{}'")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        store.forecasts()


def test_forecast_and_future_price_reject_lookahead(evidence: Any) -> None:
    _, f, _ = evidence
    for change in [
        dict(training_cutoff=AT),
        dict(ranking_position=1),
        dict(session=date(2026, 10, 6)),
    ]:
        with pytest.raises(ValidationError):
            Forecast.model_validate(f.model_dump() | change)
    with pytest.raises(ValidationError, match="FUTURE_SESSION"):
        FuturePrice.model_validate(prices(date(2026, 10, 12)).model_dump() | dict(received_at=AT))


def test_input_projection_respects_exact_order_and_missing_evidence() -> None:
    good = dict(a=dict(state="AVAILABLE", value=1), b=dict(state="AVAILABLE", value=2))
    assert input_compatibility(("b", "a"), good)["values"] == [2, 1]
    for invalid in [
        dict(state="UNAVAILABLE", value=None),
        dict(state="DEGRADED", value=1),
        dict(state="AVAILABLE", value=float("nan")),
        dict(state="AVAILABLE", value=True),
    ]:
        result = input_compatibility(("a", "b"), good | dict(b=invalid))
        assert result["values"] is None and not result["inference_authorized"]
    assert not input_compatibility(("target_return",), good)["compatible"]


def test_optional_forecast_store_online_backup_and_isolated_restore(
    evidence: Any, tmp_path: Path
) -> None:
    from alphalens_api.core.config import Settings
    from alphalens_api.operations.recovery import backup, restore

    store, forecast, _ = evidence
    store.record(forecast)
    target = tmp_path / "backup"
    settings = Settings(environment="test", daily_root=store.daily.root)
    assert backup(settings, target)["databases"] == ["prospective"]
    destination = tmp_path / "restored"
    assert restore(target, destination)["original_state_modified"] is False
    with sqlite3.connect(destination / "prospective/prospective.sqlite3") as conn:
        assert conn.execute("SELECT count(*) FROM forecasts").fetchone()[0] == 1
    assert store.forecasts()["total"] == 1


def test_evaluation_alert_cursor_and_interrupted_replay(evidence: Any, tmp_path: Path) -> None:
    from workers.alerts.store import AlertStore

    store, forecast, clock = evidence
    key = store.record(forecast)
    next_day = date(2026, 10, 12)
    cal = calendar([DAY, next_day]).model_copy(
        update={"completeness": "VERIFIED_TRADING_SESSION_SEQUENCE"}
    )
    clock[0] = datetime(2026, 10, 13, tzinfo=UTC)
    store.evaluate(key, cal, [prices(next_day)])
    alerts = AlertStore(tmp_path / "TEST_ONLY_alerts")
    alerts.initialize()
    assert store.process_alerts(alerts)["published"] == 1
    assert store.process_alerts(alerts)["scanned"] == 0
    with store.connection(write=True) as conn:
        conn.execute("UPDATE notification_cursor SET position=0")
    assert store.process_alerts(alerts)["published"] == 0
    with alerts.connection() as conn:
        assert conn.execute("SELECT count(*) FROM alerts").fetchone()[0] == 1
        assert (
            conn.execute("SELECT event_code FROM alerts").fetchone()[0] == "PROSPECTIVE_EVALUATED"
        )
