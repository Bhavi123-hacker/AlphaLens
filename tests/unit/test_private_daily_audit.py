"""TEST_ONLY audit counts use verified bodies, with zero source mutation."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from scripts.audit_private_daily_delivery import audit, main, risk_ranked


def fixture(root: Path) -> None:
    for folder in (
        "operational/runs",
        "operational/diagnostics",
        "daily",
        "scores",
        "market-views",
        "expanded-forecasts/00",
    ):
        (root / folder).mkdir(parents=True)

    def write(name: str, body: Any) -> None:
        data = json.dumps(body).encode()
        path = root / name
        path.write_bytes(data)
        path.with_suffix(path.suffix + ".sha256").write_text(hashlib.sha256(data).hexdigest())

    write(
        "scores/TEST_ONLY.json",
        {"candidates": [{"session": "2026-10-28", "key": "TEST_ONLY_KEY", "score": 0.5}]},
    )
    write("market-views/TEST_ONLY.json", {"rows": [], "histories": {}})
    (root / "scores-latest.json").write_text(json.dumps({"path": "scores/TEST_ONLY.json"}))
    (root / "market-view-latest.json").write_text(
        json.dumps({"path": "market-views/TEST_ONLY.json"})
    )
    body = {"model_id": "TEST_ONLY", "key": "TEST_ONLY_KEY", "session": "2026-10-28"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"))
    path = root / "expanded-forecasts/00/experimental-v2-prospective.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE experimental_forecasts(id TEXT, body TEXT)")
        db.execute(
            "INSERT INTO experimental_forecasts VALUES (?,?)",
            (hashlib.sha256(encoded.encode()).hexdigest(), encoded),
        )
    db.close()


def test_read_only_audit_counts_verified_decisions_and_candidate_sessions(tmp_path: Path) -> None:
    fixture(tmp_path)
    before = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    result = audit(tmp_path)
    assert result["ledger_totals"]["forecast_records"] == 1
    assert result["unique_decisions"] == 1
    assert result["forecast_sessions"] == {"2026-10-28": 1}
    assert result["latest_scores"]["score_count"] == 1
    assert result["latest_scores"]["score_sessions"] == {"2026-10-28": 1}
    after = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after


def test_read_only_audit_rejects_forecast_body_hash_mismatch(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "expanded-forecasts/00/experimental-v2-prospective.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("UPDATE experimental_forecasts SET id='TEST_ONLY_CORRUPT'")
    db.close()
    with pytest.raises(ValueError, match="FORECAST_CHECKSUM_REJECTED"):
        audit(tmp_path)


def test_audit_risk_ordering_matches_weight_one_and_rejects_unknown_risk() -> None:
    rows = [
        {"key": "TEST_ONLY_A", "score": 0.8, "risk": {"return_daily_sd_20": 0.3}},
        {"key": "TEST_ONLY_B", "score": 0.7, "risk": {"return_daily_sd_20": 0.1}},
        {"key": "TEST_ONLY_C", "score": 0.9, "risk": {}},
        {"key": "TEST_ONLY_D", "score": 0.9, "risk": {"return_daily_sd_20": -1}},
    ]
    assert [row["key"] for row in risk_ranked(rows)] == ["TEST_ONLY_B", "TEST_ONLY_A"]


def test_audit_cli_cannot_overwrite_source_or_an_existing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "TEST_ONLY_SOURCE"
    source.mkdir()
    for output in (source / "NEW_FILE.json", tmp_path / "EXISTING.json"):
        if output.parent == tmp_path:
            output.write_text("TEST_ONLY_ORIGINAL")
        monkeypatch.setattr("sys.argv", ["audit", "--root", str(source), "--output", str(output)])
        with pytest.raises(ValueError, match="FRESH_AUDIT_OUTPUT"):
            main()
        if output.parent == tmp_path:
            assert output.read_text() == "TEST_ONLY_ORIGINAL"
        else:
            assert not output.exists()
