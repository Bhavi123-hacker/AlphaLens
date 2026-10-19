"""Isolated TEST_ONLY monitoring/recovery evidence, never fake market observations."""

import json
import logging
import secrets
from datetime import UTC, datetime
from pathlib import Path

import pytest
from workers.alerts.store import AlertStore

from alphalens_api.auth.store import AuthError, AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.core.logging import SafeJsonFormatter
from alphalens_api.operations.health import inspect
from alphalens_api.operations.metrics import Metrics
from alphalens_api.operations.recovery import backup, restore
from alphalens_api.operations.store import OperationsStore


def report(status: str = "UNAVAILABLE") -> dict[str, object]:
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "components": {"postgresql": {"status": status, "reason": "DATABASE_UNAVAILABLE"}},
    }


def test_real_unconfigured_probes_do_not_invent_readiness(tmp_path: Path) -> None:
    value = inspect(Settings(environment="test", auth_root=tmp_path / "missing"))
    assert value["components"]["authentication"]["status"] == "UNAVAILABLE"
    assert value["components"]["postgresql"]["status"] == "NOT_CONFIGURED"
    assert value["components"]["live_source"]["status"] == "BLOCKED_BY_POLICY"
    assert value["production_ready"] is False
    assert not (tmp_path / "missing").exists()


def test_repeated_failure_outbox_and_episode_replay(tmp_path: Path) -> None:
    ops = OperationsStore(tmp_path / "ops")
    alerts = AlertStore(tmp_path / "alerts")
    ops.initialize()
    alerts.initialize()
    ops.record(report(), test_only=True)
    assert ops.process(alerts)["published"] == 0
    ops.record(report(), test_only=True)
    assert ops.process(alerts)["published"] == 1
    for _ in range(3):
        ops.record(report(), test_only=True)
        assert ops.process(alerts)["published"] == 0
    assert ops.history()["pending_alert_events"] == 0
    # Simulate crash between P20 commit and outbox acknowledgment.
    with ops.connection(True) as c:
        c.execute("UPDATE outbox SET delivered=0")
    assert ops.process(alerts)["published"] == 0
    ops.record(report("HEALTHY"), test_only=True)
    ops.record(report(), test_only=True)
    ops.record(report(), test_only=True)
    assert ops.process(alerts)["published"] == 1


def test_online_backup_restores_password_and_revokes_sessions(tmp_path: Path) -> None:
    auth = AuthStore(tmp_path / "auth")
    auth.initialize()
    password = secrets.token_urlsafe(24)
    auth.bootstrap("test_operator", password)
    raw, _ = auth.login("test_operator", password)
    alerts = AlertStore(tmp_path / "alerts")
    alerts.initialize()
    settings = Settings(environment="test", auth_root=auth.root, alerts_root=alerts.root)
    target = tmp_path / "backup"
    # An open reader / committed WAL does not produce a blind file copy.
    with auth.connection():
        assert backup(settings, target)["complete"]
    output = tmp_path / "restored"
    assert restore(target, output)["original_state_modified"] is False
    restored = AuthStore(output / "auth")
    with pytest.raises(AuthError):
        restored.session(raw)
    assert restored.login("test_operator", password)[1]["role"] == "ADMIN"
    assert auth.session(raw)["role"] == "ADMIN"
    with pytest.raises(FileExistsError):
        restore(target, output)


def test_corrupt_backup_refused_before_destination_created(tmp_path: Path) -> None:
    auth = AuthStore(tmp_path / "auth")
    auth.initialize()
    folder = tmp_path / "backup"
    backup(Settings(environment="test", auth_root=auth.root), folder)
    with (folder / "auth.sqlite3").open("ab") as stream:
        stream.write(b"TEST_ONLY_corruption")
    with pytest.raises(ValueError, match="CHECKSUM"):
        restore(folder, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_metrics_bounded_and_no_arbitrary_labels() -> None:
    metrics = Metrics()
    for _ in range(1100):
        metrics.observe("/api/v1/stocks/PRIVATE_ID", 200, 0.01)
    metrics.observe("/PRIVATE_USERNAME", 401, 0.02)
    value = metrics.snapshot()
    assert value["requests"]["stocks"]["retained_samples"] == 1000
    assert value["requests"]["stocks"]["count"] == 1100
    assert value["denied"] == 1
    assert "PRIVATE" not in json.dumps(value)


def test_structured_logging_never_serializes_sensitive_extras() -> None:
    record = logging.LogRecord("test", logging.INFO, "", 0, "request.completed", (), None)
    record.password = "TEST_ONLY_SECRET"
    record.component = "auth"
    record.duration_ms = 5.2
    record.request_id = "attacker_text"
    data = json.loads(SafeJsonFormatter().format(record))
    assert data["duration_ms"] == 5.2
    assert data["component"] == "auth"
    assert "SECRET" not in json.dumps(data)
    assert data["request_id"] is None


@pytest.mark.parametrize("_iteration", range(10))
def test_concurrent_probe_and_alert_publication(tmp_path: Path, _iteration: int) -> None:
    from concurrent.futures import ThreadPoolExecutor

    ops = OperationsStore(tmp_path / "ops")
    alerts = AlertStore(tmp_path / "alerts")
    ops.initialize()
    alerts.initialize()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: ops.record(report(), test_only=True), range(8)))
        results = list(pool.map(lambda _: ops.process(alerts), range(4)))
    assert sum(r["published"] for r in results) == 1
    assert ops.history()["total"] == 8
    assert ops.history()["pending_alert_events"] == 0


def test_tampered_probe_cannot_publish_alert(tmp_path: Path) -> None:
    ops = OperationsStore(tmp_path / "ops")
    alerts = AlertStore(tmp_path / "alerts")
    ops.initialize()
    alerts.initialize()
    ops.record(report(), test_only=True)
    probe = ops.record(report(), test_only=True)
    with ops.connection(True) as c:
        c.execute("UPDATE probes SET payload='{}' WHERE id=?", (probe,))
    with pytest.raises(ValueError, match="PROVENANCE"):
        ops.process(alerts)
    assert ops.history(limit=1, offset=1)["pending_alert_events"] == 1
    with pytest.raises(ValueError, match="CORRUPT"):
        ops.history()


def test_authentication_anomaly_is_based_on_actual_audit(tmp_path: Path) -> None:
    auth = AuthStore(tmp_path / "auth")
    auth.initialize()
    auth.bootstrap("test_operator", secrets.token_urlsafe(24))
    for _ in range(5):
        with pytest.raises(AuthError):
            auth.login("test_operator", secrets.token_urlsafe(24))
    value = inspect(Settings(environment="test", auth_root=auth.root))
    assert value["components"]["authentication"]["status"] == "DEGRADED"
    assert value["components"]["authentication"]["failures_last_five_minutes"] == 5


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (1, -1), (1, 5001)])
def test_history_limits(tmp_path: Path, limit: int, offset: int) -> None:
    with pytest.raises(ValueError, match="PAGE_INVALID"):
        OperationsStore(tmp_path).history(limit, offset)


def test_rotating_log_files_remain_bounded_and_redacted(tmp_path: Path) -> None:
    from logging.handlers import RotatingFileHandler

    from alphalens_api.core.logging import configure_logging

    ops = OperationsStore(tmp_path / "ops")
    ops.initialize()
    logger = configure_logging(ops.root)
    handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
    handler.maxBytes = 512
    try:
        for _ in range(30):
            logger.info("request.completed", extra={"password": "TEST_ONLY_SECRET"})
        paths = list(ops.root.glob("api.jsonl*"))
        assert len(paths) <= 4
        assert all("SECRET" not in path.read_text() for path in paths)
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_finite_operator_cli_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alphalens_api.operations.cli import main

    alerts = AlertStore(tmp_path / "alerts")
    alerts.initialize()
    monkeypatch.setenv("ALPHALENS_ENVIRONMENT", "test")
    monkeypatch.setenv("ALPHALENS_TEST_ONLY_EVIDENCE", "true")
    monkeypatch.setenv("ALPHALENS_OPERATIONS_ROOT", str(tmp_path / "ops"))
    monkeypatch.setenv("ALPHALENS_ALERTS_ROOT", str(alerts.root))
    for command in ("init", "check", "history", "process-alerts"):
        assert main([command]) == 0
    destination = tmp_path / "backup"
    assert main(["backup", "--destination", str(destination)]) == 0
    assert (
        main(["restore", "--source", str(destination), "--destination", str(tmp_path / "restore")])
        == 0
    )


def test_invalid_cli_recovery_is_sanitized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from alphalens_api.operations.cli import main

    assert (
        main(
            [
                "restore",
                "--source",
                str(tmp_path / "PRIVATE_MISSING"),
                "--destination",
                str(tmp_path / "PRIVATE_OUTPUT"),
            ]
        )
        == 2
    )
    output = capsys.readouterr().out
    assert "PRIVATE_MISSING" not in output and "PRIVATE_OUTPUT" not in output
