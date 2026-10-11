"""Explicit TEST_ONLY observations; tests are not market-performance evidence."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError
from scripts.build_p19_test_evidence import AT, DAY, calendar, parquet, request
from workers.daily.cli import main
from workers.daily.engine import Worker
from workers.daily.features import definitions, update
from workers.daily.inference import load, predict, verify_model
from workers.daily.schedule import disabled_task

from alphalens_data.daily.contracts import Calendar, Request
from alphalens_data.daily.providers import check_source
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_features.research import numerical


def test_source_offline_clearance_separate() -> None:
    result = check_source()
    assert result["live_data_activation"] == "BLOCKED"
    assert not result["price_download_attempted"]


@pytest.mark.parametrize(
    "flag", ["automation_permitted", "retention_permitted", "research_permitted"]
)
def test_provider_requires_all_permissions(flag: str) -> None:
    provider = request().provider.model_copy(
        update={
            "status": "SOURCE_APPROVED_FOR_RESEARCH",
            "automation_permitted": True,
            "retention_permitted": True,
            "research_permitted": True,
            flag: False,
        }
    )
    assert not provider.allowed("DAILY")


def test_no_weekday_calendar_assumption() -> None:
    cal = calendar([DAY])
    assert cal.status(DAY - timedelta(days=1), AT) == "UNKNOWN_SESSION_STATUS"
    assert cal.expected(AT) == DAY


def test_special_session_and_missing_price() -> None:
    special = date(2023, 11, 12)
    cal = calendar([special, DAY])
    assert special.weekday() == 6 and cal.status(special, AT) == "TRADING"
    assert cal.trailing(DAY, AT, 200) == (special, DAY)


def test_future_calendar_evidence_invisible() -> None:
    cal = calendar([DAY]).model_copy(
        update={
            "sessions": (
                calendar([DAY])
                .sessions[0]
                .model_copy(update={"known_at": AT + timedelta(seconds=1)}),
            )
        }
    )
    assert cal.status(DAY, AT) == "UNKNOWN_SESSION_STATUS"


def test_production_mode_forbidden() -> None:
    with pytest.raises(ValidationError):
        Request.model_validate(request().model_dump() | {"mode": "PRODUCTION"})


def test_daily_never_downloads_uncleared(tmp_path: Path) -> None:
    req = request().model_copy(update={"mode": "DAILY"})
    receipt = Worker(tmp_path).run(req)
    assert receipt["state"] == "BLOCKED_SOURCE"
    assert receipt["products"] == {}
    assert "ONGOING_PROVIDER_NOT_CLEARED" in receipt["reasons"]


def test_late_release_pending(tmp_path: Path) -> None:
    assert Worker(tmp_path).run(request())["reasons"] == ["SOURCE_OBSERVATION_PENDING"]


def test_repeat_run_exact_and_raw_preserved(tmp_path: Path) -> None:
    path = parquet(tmp_path / "fixture.parquet")
    worker = Worker(tmp_path / "daily")
    req = request(path)
    first = worker.run(req, path)
    second = worker.run(
        req.model_copy(update={"source_received_at": AT + timedelta(hours=1)}), path
    )
    assert first == second
    raw = worker.store.read(req.run_id, "normalized.json")["raw_manifest"]
    assert raw["sha256"] == checksum(path.read_bytes())
    assert first["usage_classification"] == "TEST_ONLY"
    assert first["counts"]["missing"] is None
    assert first["signal_status"] == "UNAVAILABLE"
    assert first["counts"]["counts"].get("REJECTED", 0) == 0


def test_corrected_bytes_new_identity(tmp_path: Path) -> None:
    one = request(parquet(tmp_path / "one.parquet", close=100))
    two = request(parquet(tmp_path / "two.parquet", close=101))
    assert one.run_id != two.run_id


def test_corrupted_source_no_published_prices(tmp_path: Path) -> None:
    path = parquet(tmp_path / "bad.parquet")
    worker = Worker(tmp_path / "daily")
    req = request(path).model_copy(update={"payload_sha256": "b" * 64})
    receipt = worker.run(req, path)
    assert receipt["state"] == "FAILED" and not receipt["products"]


def test_invalid_ohlc_quarantined(tmp_path: Path) -> None:
    path = parquet(tmp_path / "bad.parquet", close=110)
    receipt = Worker(tmp_path / "daily").run(request(path), path)
    assert receipt["state"] == "BLOCKED_EVIDENCE"
    assert receipt["products"]["validation"]


def test_etf_remains_excluded(tmp_path: Path) -> None:
    path = parquet(tmp_path / "etf.parquet", isin="INF000A01001", name="TEST_ONLY ETF")
    worker = Worker(tmp_path / "daily")
    req = request(path)
    worker.run(req, path)
    row = worker.store.product(req.run_id, "canonical")["rows"][0]
    assert row["analytical_type"] == "EXCLUDED_NON_EQUITY"
    assert all(
        v["value"] is None
        for v in worker.store.product(req.run_id, "features")["rows"][0]["values"].values()
    )


@pytest.mark.parametrize("stage", ["normalized", "canonical", "features", "before_publish"])
def test_recovery_publishes_once(tmp_path: Path, stage: str) -> None:
    path = parquet(tmp_path / "fixture.parquet")
    req = request(path)

    def crash(value: str) -> None:
        if value == stage:
            raise OSError("TEST_ONLY_IO_FAILURE")

    worker = Worker(tmp_path / "daily", hook=crash)
    with pytest.raises(DataContractError, match="RETRYABLE_FAILURE"):
        worker.run(req, path)
    assert worker.store.receipts() == []
    receipt = Worker(tmp_path / "daily").run(req, path)
    assert receipt["state"] == "COMPLETED_WITH_WARNINGS"
    assert len(worker.store.receipts()) == 1


def test_worker_kernel_lock(tmp_path: Path) -> None:
    store = Store(tmp_path)
    with store.lock(), pytest.raises(DataContractError, match="DAILY_WORKER_BUSY"), store.lock():
        pass
    with store.lock():
        pass


def test_receipt_detects_product_tampering(tmp_path: Path) -> None:
    path = parquet(tmp_path / "fixture.parquet")
    worker = Worker(tmp_path / "daily")
    req = request(path)
    worker.run(req, path)
    worker.store.path(req.run_id, "features.json").write_bytes(b"{}")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        worker.store.receipt(req.run_id)


def test_path_traversal_rejected(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        Store(tmp_path).path("../escape", "receipt.json")


def rows() -> list[dict[str, Any]]:
    return [
        dict(
            security_id="TEST_ONLY",
            session_date=(DAY - timedelta(days=250 - i)).isoformat(),
            close=100 + i / 10,
            high=102 + i / 10,
            low=99 + i / 10,
            volume=1000 + i,
            quality="VALID",
            analytical_type="RESEARCH_EQUITY_CANDIDATE",
        )
        for i in range(251)
    ]


def test_incremental_p6_numerical_parity() -> None:
    history = rows()
    cal = calendar([date.fromisoformat(r["session_date"]) for r in history])
    actual = update(history[-1:], history[:-1], cal, DAY, AT)
    arrays = [np.array([r[n] for r in history]) for n in ("close", "high", "low", "volume")]
    values = actual["rows"][0]["values"]
    for definition in definitions(DAY, AT):
        if definition.feature_family in {"CROSS_SECTIONAL", "RELATIVE_STRENGTH", "MARKET_CONTEXT"}:
            assert values[definition.feature_name]["value"] is None
            continue
        expected = numerical(definition, *arrays)[-1]
        assert values[definition.feature_name]["value"] == pytest.approx(expected, rel=1e-12)
    assert actual["bounded_session_slots"] <= 201


def test_missing_required_session_not_filled() -> None:
    history = rows()
    cal = calendar([date.fromisoformat(r["session_date"]) for r in history])
    history.pop(-2)
    actual = update(history[-1:], history[:-1], cal, DAY, AT)
    assert actual["rows"][0]["values"]["sma_200"]["value"] is None


def test_future_context_and_identity_do_not_backfill() -> None:
    history = rows()
    cal = calendar([date.fromisoformat(r["session_date"]) for r in history])
    earlier = update(history[-1:], history[:-1], cal, DAY, AT)
    future = history[-2] | {
        "security_id": "FUTURE_ISIN",
        "close": 999999,
        "received_at": (AT + timedelta(days=1)).isoformat(),
    }
    assert earlier == update(history[-1:], history[:-1] + [future], cal, DAY, AT)


def test_ambiguous_revisions_fail_closed() -> None:
    history = rows()
    cal = calendar([date.fromisoformat(r["session_date"]) for r in history])
    with pytest.raises(DataContractError, match="AMBIGUOUS"):
        update(history[-1:], history[:-1] + [history[-3]], cal, DAY, AT)


class TestOnlyFitted:
    def predict(self, values: Any) -> Any:
        return np.array([1])

    def predict_proba(self, values: Any) -> Any:
        return np.array([[0.4, 0.6]])


def inference(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = dict(
        session=DAY,
        decision_time=AT,
        receipt_time=AT,
        training_cutoff=AT - timedelta(days=100),
        archive_end=DAY - timedelta(days=1),
        authorized_experimental=True,
    )
    return predict(TestOnlyFitted(), [1.0], ("return_1",), ("return_1",), **(arguments | overrides))


@pytest.mark.parametrize(
    "override",
    [
        dict(authorized_experimental=False),
        dict(archive_end=DAY),
        dict(decision_time=AT - timedelta(days=1)),
        dict(training_cutoff=AT),
        dict(receipt_time=AT + timedelta(seconds=1)),
    ],
)
def test_inference_temporal_and_activation_guards(override: dict[str, Any]) -> None:
    with pytest.raises(DataContractError):
        inference(**override)


def test_fitted_preprocessing_only_no_training() -> None:
    assert inference()["model_probability"] == 0.6


def test_cli_dry_run_no_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "request.json"
    path.write_bytes(stable_json(request().model_dump(mode="json")))
    assert main(["dry-run", "--root", str(tmp_path / "out"), "--request", str(path)]) == 0
    assert not (tmp_path / "out").exists()
    assert json.loads(capsys.readouterr().out)["mutations"] is False


def test_model_loading_disabled_before_deserialization(tmp_path: Path) -> None:
    with pytest.raises(DataContractError, match="NOT_ACTIVATED"):
        load(tmp_path / "missing.skops", "a" * 64, authorized_experimental=False)


def test_model_hash_fails_before_deserialization(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY.skops"
    path.write_bytes(b"TEST_ONLY_NOT_A_MODEL")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        load(path, "a" * 64, authorized_experimental=True)


def test_model_candidate_metadata_checked_before_loading(tmp_path: Path) -> None:
    report = dict(
        model_identity={},
        model_run_id="a" * 64,
        dataset_id="b" * 64,
        horizon=1,
        model_family="hist_gradient_boosting",
        task="classification",
        phase="2026",
        usage_classification="RESEARCH_ONLY",
    )
    with pytest.raises(DataContractError, match="MISMATCH"):
        verify_model(tmp_path, report, "b" * 64)


def test_disabled_scheduler_never_installs_task(tmp_path: Path) -> None:
    from xml.etree.ElementTree import fromstring

    xml = disabled_task(
        tmp_path / "python.exe", tmp_path, tmp_path / "request.json", tmp_path / "daily"
    )
    task = fromstring(xml)
    namespace = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert all(node.text == "false" for node in task.findall(".//t:Enabled", namespace))
    assert "dry-run" in (task.find(".//t:Arguments", namespace).text or "")  # type: ignore[union-attr]


def test_source_outage_bounded_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    from alphalens_data.daily import providers

    attempts = []

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        attempts.append(1)
        raise OSError("TEST_ONLY_OUTAGE")

    monkeypatch.setattr(providers, "HTTPSConnection", unavailable)
    monkeypatch.setattr("alphalens_data.daily.providers.time.sleep", lambda _: None)
    assert providers.check_source(network=True)["availability"] == "SOURCE_UNAVAILABLE_RETRY_LIMIT"
    assert len(attempts) == 3


def test_operational_retry_checkpoint_visible_not_products(tmp_path: Path) -> None:
    path = parquet(tmp_path / "TEST_ONLY.parquet")
    req = request(path)

    def fail(_: str) -> None:
        raise OSError("TEST_ONLY")

    worker = Worker(tmp_path / "daily", hook=fail)
    with pytest.raises(DataContractError):
        worker.run(req, path)
    checkpoints = worker.store.checkpoints()
    assert checkpoints[0]["state"] == "RETRYABLE_FAILURE"
    assert checkpoints[0]["products_visible"] is False


def test_retry_limit_returns_explicit_failure(tmp_path: Path) -> None:
    path = parquet(tmp_path / "TEST_ONLY.parquet")
    req = request(path)

    def fail(_: str) -> None:
        raise OSError("TEST_ONLY")

    worker = Worker(tmp_path / "daily", hook=fail)
    for _ in range(3):
        with pytest.raises(DataContractError):
            worker.run(req, path)
    assert worker.run(req, path)["state"] == "FAILED"


def test_nontrading_holiday_explicit_not_guessed(tmp_path: Path) -> None:
    req = request()
    holiday = req.calendar.sessions[0].model_copy(update={"status": "NON_TRADING"})
    req = req.model_copy(update={"calendar": Calendar(sessions=(holiday,))})
    assert Worker(tmp_path).run(req)["reasons"] == ["NON_TRADING"]


def test_blocked_run_exit_is_not_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "request.json"
    req = request().model_copy(update={"mode": "DAILY"})
    path.write_bytes(stable_json(req.model_dump(mode="json")))
    assert main(["run-once", "--root", str(tmp_path / "out"), "--request", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["state"] == "BLOCKED_SOURCE"


def test_content_identity_independent_of_capture_clock(tmp_path: Path) -> None:
    payload = parquet(tmp_path / "TEST_ONLY.parquet")
    req = request(payload)
    first = Worker(tmp_path / "one")
    second = Worker(tmp_path / "two")
    first.run(req, payload)
    second.run(req, payload)
    assert (
        first.store.product(req.run_id, "canonical")["rows"][0]["canonical_record_id"]
        == second.store.product(req.run_id, "canonical")["rows"][0]["canonical_record_id"]
    )


def test_unchanged_decision_policy_pinned(tmp_path: Path) -> None:
    req = request().model_copy(update={"decision_policy_id": "c" * 64})
    with pytest.raises(DataContractError, match="UNCHANGED_DECISION_POLICY"):
        Worker(tmp_path).run(req)
