"""TEST_ONLY local deployment boundary and append-only ledger verification fixtures."""

import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import private_v1_local
from scripts.private_v1_local import pinned_environment, validate
from scripts.private_v1_status import (
    _collection,
    _current_predictions,
    _ledgers,
    fingerprint,
    smoke,
)
from workers.experimental_nse_v2 import forward
from workers.nse_market import engine


def deployment(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    index = frontend / "index.html"
    index.write_text("TEST_ONLY compiled frontend")
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "port": 8041,
                "upstox_private_view": False,
                "personal_mutations": False,
                "alert_mutations": False,
                "cors_origins": ["http://127.0.0.1:8041"],
                "frontend_root": str(frontend),
            }
        )
    )
    executable = tmp_path / "TEST_ONLY_python.exe"
    executable.write_bytes(b"TEST_ONLY")
    value: dict[str, object] = {
        "schema": "alphalens.private_v1.local_deployment.v1",
        "workspace": str(tmp_path),
        "source_root": str(tmp_path),
        "python": str(executable),
        "config": str(config),
        "database_source_root": str(tmp_path),
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "frontend_index_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
    }
    path = tmp_path / "release.json"
    path.write_text(json.dumps(value))
    return path, value


def test_source_fingerprint_covers_new_source_and_ignores_private_state(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    (tmp_path / "workers").mkdir()
    (tmp_path / "workers/original.py").write_text("# TEST_ONLY original\n")
    (tmp_path / ".gitignore").write_text(".local-data/\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=TEST_ONLY",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "TEST_ONLY baseline",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    before = fingerprint(tmp_path)
    (tmp_path / "workers/new.py").write_text("# TEST_ONLY new source\n")
    added = fingerprint(tmp_path)
    assert added["actual_source_sha256"] != before["actual_source_sha256"]
    assert added["tracked_source_files"] == before["tracked_source_files"] + 1
    (tmp_path / ".local-data").mkdir()
    (tmp_path / ".local-data/TEST_ONLY_private.txt").write_text("TEST_ONLY private state")
    assert fingerprint(tmp_path) == added


def test_local_deployment_rejects_changed_config_or_build(tmp_path: Path) -> None:
    path, value = deployment(tmp_path)
    assert validate(path, source_required=False) == value
    index = tmp_path / "frontend/index.html"
    index.write_text("TEST_ONLY changed build")
    with pytest.raises(ValueError, match="COMPILED_FRONTEND_CHANGED"):
        validate(path, source_required=False)
    config = Path(str(value["config"]))
    config.write_text("{}")
    with pytest.raises(ValueError, match="CONFIG_CHANGED"):
        validate(path, source_required=False)


@pytest.mark.parametrize(
    "key,value",
    [
        ("port", 8042),
        ("upstox_private_view", True),
        ("personal_mutations", True),
        ("alert_mutations", True),
        ("cors_origins", ["http://0.0.0.0:8041"]),
    ],
)
def test_local_deployment_never_enables_unapproved_mutations(
    tmp_path: Path, key: str, value: object
) -> None:
    path, manifest = deployment(tmp_path)
    config = Path(str(manifest["config"]))
    data = json.loads(config.read_bytes())
    data[key] = value
    config.write_text(json.dumps(data))
    manifest["config_sha256"] = hashlib.sha256(config.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="LOOPBACK_SECURITY_POLICY"):
        validate(path, source_required=False)


def test_status_counts_duplicate_decisions_without_changing_source(tmp_path: Path) -> None:
    roots = [tmp_path / "TEST_ONLY_original", tmp_path / "TEST_ONLY_expanded"]
    original = {
        "model_id": "TEST_ONLY_MODEL",
        "key": "TEST_ONLY_KEY",
        "session": "2025-01-03",
        "target_version": "TEST_ONLY_TARGET",
        "horizon": 5,
    }
    for root in roots:
        root.mkdir()
        with sqlite3.connect(root / "experimental-v2-prospective.sqlite3") as db:
            db.execute("CREATE TABLE experimental_forecasts(body TEXT)")
            db.execute("CREATE TABLE experimental_outcomes(body TEXT)")
            db.execute("INSERT INTO experimental_forecasts VALUES(?)", (json.dumps(original),))
    before = [(root / "experimental-v2-prospective.sqlite3").read_bytes() for root in roots]
    result = _ledgers(roots)
    assert result["forecast_records"] == 2 and result["unique_decisions"] == 1
    assert result["outcome_revisions"] == 0
    assert before == [(root / "experimental-v2-prospective.sqlite3").read_bytes() for root in roots]


def test_launcher_pins_every_workspace_package_and_smoke_refuses_external_url(
    tmp_path: Path,
) -> None:
    env = pinned_environment(tmp_path)
    assert str(tmp_path / "apps/api/src") in env["PYTHONPATH"]
    assert env["OMP_NUM_THREADS"] == "1"
    with pytest.raises(ValueError, match="LOOPBACK_8041"):
        smoke("https://example.invalid", tmp_path / "never_read_credentials.json")


def test_status_includes_original_price_only_ledger_exactly_once(tmp_path: Path) -> None:
    root = tmp_path / "TEST_ONLY_v2"
    ledger = root / "price-only/experimental-v2-prospective.sqlite3"
    ledger.parent.mkdir(parents=True)
    with sqlite3.connect(ledger) as db:
        db.execute("CREATE TABLE experimental_forecasts(body TEXT)")
        db.execute("CREATE TABLE experimental_outcomes(body TEXT)")
        db.execute(
            "INSERT INTO experimental_forecasts VALUES(?)",
            (
                json.dumps(
                    {
                        "model_id": "TEST_ONLY",
                        "key": "TEST_ONLY",
                        "session": "2025-01-03",
                        "target_version": "TEST_ONLY",
                        "horizon": 5,
                    }
                ),
            ),
        )
    result = _ledgers([root, root / "price-only"])
    assert result["forecast_records"] == 1


def test_current_predictions_require_exact_saved_lineage_and_future_entry(tmp_path: Path) -> None:
    observed = {
        "session": "2025-01-03",
        "open_at": "2025-01-03T04:00:00+00:00",
        "close_at": "2025-01-03T10:00:00+00:00",
    }
    following = {
        "session": "2025-01-06",
        "open_at": "2025-01-06T04:00:00+00:00",
        "close_at": "2025-01-06T10:00:00+00:00",
        "previous_session": "2025-01-03",
        "intervening_dates_verified_closed": True,
    }
    for item in (observed, following):
        item.update(
            source="UPSTOX_OFFICIAL_MARKET_TIMINGS",
            source_sha256="a" * 64,
            source_received_at="2025-01-03T12:00:00+00:00",
        )
    score = {
        "key": "NSE_EQ|INE002A01018",
        "session": "2025-01-03",
        "model_id": "TEST_ONLY_MODEL",
        "dataset_id": "TEST_ONLY_DATA",
        "feature_hash": "b" * 64,
        "source_sha256": "c" * 64,
        "score": 0.5,
        "next_session_timing": following,
    }
    forecast = {
        **score,
        "session_timing": observed,
        "prospective_eligible": True,
        "recorded_at": "2025-01-03T13:00:00+00:00",
        "inference_at": "2025-01-03T13:00:00+00:00",
        "source_observed_at": "2025-01-03T12:00:00+00:00",
    }
    root = tmp_path / "TEST_ONLY_market"
    view = {"dataset_id": "TEST_ONLY_DATA", "latest_observed_session": "2025-01-03"}
    scores = {
        "dataset_id": "TEST_ONLY_DATA",
        "model_id": "TEST_ONLY_MODEL",
        "observation_session": "2025-01-03",
        "candidates": [score, score],
    }
    at = datetime(2025, 1, 4, tzinfo=UTC)
    assert _current_predictions(root, view, scores, at) == 0
    shard = hashlib.sha256(str(score["key"]).encode()).hexdigest()[:2]
    ledger = root / "expanded-forecasts" / shard / "experimental-v2-prospective.sqlite3"
    ledger.parent.mkdir(parents=True)
    with sqlite3.connect(ledger) as db:
        db.execute("CREATE TABLE experimental_forecasts(id TEXT,body TEXT,recorded_at TEXT)")
        db.execute(
            "INSERT INTO experimental_forecasts VALUES(?,?,?)",
            (forward._hash(forecast), json.dumps(forecast), forecast["recorded_at"]),
        )
    assert _current_predictions(root, view, scores, at) == 1
    score["feature_hash"] = "d" * 64
    assert _current_predictions(root, view, scores, at) == 0
    score["feature_hash"] = "b" * 64
    assert _current_predictions(root, view, scores, datetime(2025, 1, 6, 5, tzinfo=UTC)) == 0


def test_launcher_rejects_junction_ancestor_and_relative_frontend(tmp_path: Path) -> None:
    path, manifest = deployment(tmp_path)
    alias = tmp_path / "TEST_ONLY_alias"
    target = tmp_path / "TEST_ONLY_other"
    target.mkdir()
    source = Path(str(manifest["config"]))
    (target / "config.json").write_bytes(source.read_bytes())
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(target)], capture_output=True, check=True
        )
    else:
        alias.symlink_to(target, target_is_directory=True)
    try:
        manifest["config"] = str(alias / "config.json")
        path.write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="REPARSE_PATH"):
            validate(path, source_required=False)
    finally:
        if sys.platform == "win32":
            alias.rmdir()
        else:
            alias.unlink()
    manifest["config"] = str(source)
    data = json.loads(source.read_bytes())
    data["frontend_root"] = "frontend"
    source.write_text(json.dumps(data))
    manifest["config_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="ABSOLUTE_EXISTING_PATH"):
        validate(path, source_required=False)


def test_collection_exposes_real_nested_publication_not_only_terminal_exit(tmp_path: Path) -> None:
    runs = tmp_path / "operational/runs"
    runs.mkdir(parents=True)
    for number in range(22):
        engine._checked(
            runs / (str(number) + ".done.json"),
            {
                "run_id": str(number),
                "state": "FAILED" if number == 0 else "CAPTURED",
                "completed_at": f"2025-01-03T12:{number:02}:00+00:00",
                "outcome": {
                    "session": "2025-01-03",
                    "api_calls": 2,
                    "new_daily_observations": 1 if number == 1 else 0,
                    "market_view": {"state": "SAVED_MARKET_VIEW_PUBLISHED"} if number == 1 else {},
                },
            },
        )
    result = _collection(tmp_path)
    assert result["latest_failure"]["run_id"] == "0"
    assert result["last_new_observation_publication"]["run_id"] == "1"
    assert result["latest_terminal_receipt"]["session"] == "2025-01-03"
    assert result["terminal_receipts_examined"] == 22


def test_start_pins_cwd_to_separate_app_and_database_source_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, database_source = (
        tmp_path / "TEST_ONLY_new_source",
        tmp_path / "TEST_ONLY_old_db_source",
    )
    workspace = tmp_path / "TEST_ONLY_runtime_workspace"
    release = {
        "source_root": str(source),
        "database_source_root": str(database_source),
        "workspace": str(workspace),
        "python": "TEST_ONLY_python",
        "config": str(tmp_path / "config.json"),
    }
    calls = []

    def run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(private_v1_local, "validate", lambda *args, **kwargs: release)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["private_v1_local", "start"])
    with pytest.raises(SystemExit) as result:
        private_v1_local.main()
    assert result.value.code == 0
    assert calls[0][0][2:] == ["scripts.p30_local_database", "start"]
    assert calls[0][1]["cwd"] == database_source
    assert calls[1][0][2] == "alphalens_api.local.cli"
    assert calls[1][1]["cwd"] == source
    assert calls[0][1]["cwd"] != workspace and calls[1][1]["cwd"] != workspace
