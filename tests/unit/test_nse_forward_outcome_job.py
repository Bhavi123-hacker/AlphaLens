"""TEST_ONLY raw calendars and saved ledgers; no provider requests or market claims."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from test_experimental_nse_v2_forward import KEY, NOW, RECEIVED, SESSIONS, rows, score
from workers.experimental_nse.acquire import digest, initialize
from workers.experimental_nse_v2 import data, forward
from workers.nse_market import daily, engine, outcomes
from workers.providers.upstox import Reply

from alphalens_api import nse_evaluation
from alphalens_data.daily.storage import Store


def fixture(root: Path, monkeypatch: pytest.MonkeyPatch, count: int = 1) -> dict[str, Any]:
    initialize(root)
    (root / "calendar").mkdir()
    (root / "session-links").mkdir()
    facts: dict[str, Any] = {}
    for index in range(8):
        day = date(2025, 1, 2) + timedelta(days=index)
        body = json.dumps(
            {
                "status": "success",
                "data": [
                    {
                        "exchange": "NSE",
                        "start_time": datetime.combine(day, datetime.min.time(), UTC).timestamp()
                        * 1000
                        + 3.75 * 3600000,
                        "end_time": datetime.combine(day, datetime.min.time(), UTC).timestamp()
                        * 1000
                        + 10 * 3600000,
                    }
                ]
                if str(day) in SESSIONS
                else [],
            }
        ).encode()
        fact = data.timing_fact(Reply(200, body, RECEIVED, "ACCEPTED"), day)
        facts[str(day)] = fact
        engine._checked(
            root / "calendar" / (str(day) + ".json"),
            {
                "received_at": RECEIVED.isoformat(),
                "raw_hex": body.hex(),
                "raw_sha256": digest(body),
                "fact": fact,
            },
        )
    for previous, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        elapsed = (date.fromisoformat(following) - date.fromisoformat(previous)).days
        engine._checked(
            root / "session-links" / (previous + ".json"),
            {
                "session_timing": facts[previous],
                "next_session_timing": {
                    **facts[following],
                    "previous_session": previous,
                    "intervening_dates_verified_closed": True,
                    "closed_dates": [
                        str(date.fromisoformat(previous) + timedelta(days=i))
                        for i in range(1, elapsed)
                    ],
                },
            },
        )
    saved_rows = []
    for index in range(count):
        key = KEY if index == 0 else "NSE_EQ|INE000000001"
        frozen_following = {
            **facts[SESSIONS[1]],
            "previous_session": SESSIONS[0],
            "intervening_dates_verified_closed": True,
        }
        monkeypatch.setattr(forward, "_utc_now", lambda: NOW)
        forward.append_forecasts(
            root / "expanded-forecasts" / f"TEST_ONLY_{index}",
            "TEST_MODEL",
            "TEST_DATA",
            "TEST_PROTOCOL",
            [
                score(
                    key=key, session_timing=facts[SESSIONS[0]], next_session_timing=frozen_following
                )
            ],
            RECEIVED,
        )
        saved_rows += [
            {**row, "key": key, "received_at": "2025-01-10T11:00:00+00:00"} for row in rows()
        ]
        saved_rows.append({**saved_rows[-1], "session": SESSIONS[0]})
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 10, 12, tzinfo=UTC))
    frame = {
        "rows": saved_rows,
        "sessions": list(SESSIONS),
        "source_observed_at": "2025-01-10T11:00:00+00:00",
        "quality": {"excluded_sessions": {row["key"]: [] for row in saved_rows}},
    }
    monkeypatch.setattr(engine, "snapshot", lambda unused_root: frame)
    return frame


def ledger_bytes(root: Path) -> dict[str, bytes]:
    return {str(path): path.read_bytes() for path in root.rglob("*.sqlite3")}


def contradict_closed_day(root: Path) -> None:
    """Change disposable TEST_ONLY raw evidence into a genuinely parsed open day."""
    record = engine._read(root / "calendar/2025-01-03.json")
    raw = json.loads(bytes.fromhex(record["raw_hex"]))
    raw["data"][0]["start_time"] += 86_400_000
    raw["data"][0]["end_time"] += 86_400_000
    body = json.dumps(raw).encode()
    record.update(raw_hex=body.hex(), raw_sha256=digest(body))
    path = root / "calendar/2025-01-04.json"
    payload = json.dumps(record).encode()
    path.write_bytes(payload)
    path.with_suffix(".json.sha256").write_text(digest(payload), encoding="utf-8")


def test_preview_is_readonly_and_supported_retry_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY"
    fixture(root, monkeypatch)
    before, files = ledger_bytes(root), set(root.rglob("*"))
    result = outcomes.run(root)
    assert result["mode"] == "READ_ONLY_PREVIEW"
    assert result["eligible_price_references"] == 1
    assert result["provider_requests"] == result["outcome_writes"] == 0
    assert before == ledger_bytes(root) and files == set(root.rglob("*"))
    first = outcomes.run(root, append=True)
    assert first["result"]["inserted"] == 1
    second = outcomes.run(root, append=True)
    assert second["result"]["inserted"] == 0 and second["result"]["replayed"] == 1
    assert len(list((root / "outcome-jobs").glob("*.json"))) == 2


def test_unassessed_forecast_in_shared_shard_cannot_bypass_prequalification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY"
    frame = fixture(root, monkeypatch)
    other_key = "NSE_EQ|INE000000001"
    monkeypatch.setattr(forward, "_utc_now", lambda: NOW)
    forward.append_forecasts(
        root / "expanded-forecasts/TEST_ONLY_0",
        "TEST_MODEL",
        "TEST_DATA",
        "TEST_PROTOCOL",
        [score(key=other_key)],
        RECEIVED,
    )
    # Both securities have prices. Only the first has an action-quality assessment.
    frame["rows"] += [{**row, "key": other_key} for row in list(frame["rows"])]
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 10, 12, tzinfo=UTC))
    result = daily.reconcile(root, frame)
    assert result["inserted"] == 1
    with forward._connection(root / "expanded-forecasts/TEST_ONLY_0") as conn:
        assert conn.execute("SELECT COUNT(*) FROM experimental_forecasts").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM experimental_outcomes").fetchone()[0] == 1


def test_claimed_closed_weekend_is_not_accepted_when_raw_response_is_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY"
    frame = fixture(root, monkeypatch)
    # Fully checksummed TEST_ONLY raw data contradicts the closure summary.
    contradict_closed_day(root)
    before = ledger_bytes(root)
    with pytest.raises(ValueError, match="CLAIMED_CLOSURE_IS_OPEN_SESSION"):
        daily.reconcile(root, frame)
    assert before == ledger_bytes(root)


def test_api_requires_same_raw_calendar_proof_as_outcome_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY"
    frame = fixture(root, monkeypatch)
    assert daily.reconcile(root, frame)["inserted"] == 1
    result = nse_evaluation.read(
        root, tmp_path / "TEST_ONLY_missing_v2", at=datetime(2025, 1, 11, tzinfo=UTC)
    )
    assert result["matured_outcomes"] == 1
    before = ledger_bytes(root)
    contradict_closed_day(root)
    with pytest.raises(ValueError, match="CLAIMED_CLOSURE_IS_OPEN_SESSION"):
        nse_evaluation.read(
            root, tmp_path / "TEST_ONLY_missing_v2", at=datetime(2025, 1, 11, tzinfo=UTC)
        )
    assert before == ledger_bytes(root)


@pytest.mark.parametrize(
    "missing",
    ["calendar/2025-01-04.json", "calendar/2025-01-07.json", "session-links/2025-01-06.json"],
)
def test_missing_saved_calendar_or_chain_cannot_mature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    root = tmp_path / "TEST_ONLY"
    frame = fixture(root, monkeypatch)
    (root / missing).unlink()  # Explicit disposable TEST_ONLY evidence fixture.
    before = ledger_bytes(root)
    result = daily.reconcile(root, frame)
    assert result["inserted"] == 0 and result["pending"] == 1
    assert before == ledger_bytes(root)


@pytest.mark.parametrize(
    "defect", ["missing_price", "identity", "publication", "action", "chronology"]
)
def test_ineligible_target_conditions_keep_outcomes_unwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    root = tmp_path / "TEST_ONLY"
    frame = fixture(root, monkeypatch)
    if defect == "missing_price":
        frame["rows"].pop(1)
    elif defect == "identity":
        frame["rows"][0]["symbol"] = "TEST_ONLY_DIFFERENT"
    elif defect == "publication":
        frame["rows"][0]["received_at"] = "2025-01-03T09:00:00+00:00"
    elif defect == "action":
        frame["quality"]["excluded_sessions"] = {KEY: [SESSIONS[2]]}
    else:
        frame["source_observed_at"] = "2025-01-02T11:00:00+00:00"
    before = ledger_bytes(root)
    assert daily.reconcile(root, frame)["inserted"] == 0
    assert before == ledger_bytes(root)


def test_kernel_lock_prevents_overlap_before_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY"
    fixture(root, monkeypatch)
    before = ledger_bytes(root)
    with Store(root / "control").lock(), pytest.raises(ValueError, match="DAILY_WORKER_BUSY"):
        outcomes.run(root, append=True)
    assert before == ledger_bytes(root)


def test_fault_after_one_shard_commit_recovers_without_duplicate_outcomes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY"
    fixture(root, monkeypatch, count=2)
    original, calls = forward.reconcile, 0

    def fail_second(*args: Any, **kwargs: Any) -> dict[str, int]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("TEST_ONLY_PRIVATE_DETAILS_NOT_FOR_RECEIPT")
        return original(*args, **kwargs)

    monkeypatch.setattr(forward, "reconcile", fail_second)
    with pytest.raises(OSError):
        outcomes.run(root, append=True)
    failed = engine._read(next((root / "outcome-jobs").glob("*.json")))
    assert failed["state"] == "FAILED"
    assert failed["error_code"] == "OFFLINE_OUTCOME_RECONCILIATION_FAILED"
    monkeypatch.setattr(forward, "reconcile", original)
    retried = outcomes.run(root, append=True)
    assert retried["result"]["inserted"] == retried["result"]["replayed"] == 1


def test_cli_defaults_to_preview(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts import nse_forward_outcomes

    monkeypatch.setattr("sys.argv", ["TEST_ONLY", "--root", "TEST_ONLY_ROOT"])
    monkeypatch.setattr(
        outcomes, "run", lambda root, append: {"append": append, "provider_requests": 0}
    )
    nse_forward_outcomes.main()
    assert json.loads(capsys.readouterr().out) == {"append": False, "provider_requests": 0}
