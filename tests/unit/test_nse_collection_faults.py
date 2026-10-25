"""TEST_ONLY per-security failure isolation, bounded resume and accurate saved reasons."""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_nse_market import AT, Transport, fixture, identity
from workers.experimental_nse.acquire import PERMISSION, digest
from workers.nse_market import daily, engine, reliability
from workers.providers.upstox import Reply


def freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        daily,
        "datetime",
        SimpleNamespace(now=lambda *args: AT, fromisoformat=datetime.fromisoformat),
    )
    monkeypatch.setattr(engine, "_score", lambda *args: {"state": "TEST_ONLY", "new_forecasts": 0})


@pytest.mark.parametrize("bad_status", [200, 500])
def test_one_bad_candle_reply_does_not_abort_other_securities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_status: int
) -> None:
    root = fixture(tmp_path, monkeypatch)
    freeze(monkeypatch)

    class Mixed(Transport):
        def get(self, operation: str, **kwargs: Any) -> Reply:
            if operation == "candles" and kwargs["key"] == identity(1).provider_key:
                self.calls += 1
                return Reply(
                    bad_status,
                    b'{"TEST_ONLY_malformed":true}',
                    AT,
                    "ACCEPTED" if bad_status == 200 else "HTTP_ERROR",
                )
            return super().get(operation, **kwargs)

    meter = Mixed()
    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        max_stocks=3,
        permission_reference=PERMISSION,
        meter=meter,
    )
    assert result["accepted_session_securities"] == 2 and result["pending_securities"] == 1
    assert result["state"] == "PARTIAL_OR_PUBLICATION_PENDING"
    assert meter.calls <= result["max_requests"]
    expected = "CANDLE_SCHEMA_OR_QUALITY_REJECTED" if bad_status == 200 else "HTTP_ERROR"
    assert result["failures"] == [{"key": identity(1).provider_key, "reason": expected}]
    detail = reliability._missing_reason(root, "2025-01-03", identity(1).model_dump(mode="json"))
    assert detail["reason"] == expected and detail["saved_failed_request_attempts"] == 1
    assert not (root / "daily/2025-01-03" / str(identity(1).isin) / "response.json").exists()
    # A later bounded run retries only the missing stock, not the accepted ones.
    recovery = Transport()
    completed = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        permission_reference=PERMISSION,
        meter=recovery,
    )
    assert completed["accepted_session_securities"] == 3 and completed["pending_securities"] == 0
    assert recovery.operations == ["candles", "actions"]


def test_interrupted_orphan_raw_is_preserved_without_redownload_or_batch_abort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    freeze(monkeypatch)
    orphan = root / "daily/2025-01-03" / str(identity(1).isin)
    orphan.mkdir(parents=True)
    raw = orphan / "candles.json"
    raw.write_bytes(b"TEST_ONLY_ORPHAN_UNQUALIFIED_ORIGINAL_BYTES")
    before = digest(raw.read_bytes())
    meter = Transport()
    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        permission_reference=PERMISSION,
        meter=meter,
    )
    assert result["accepted_session_securities"] == 2 and result["pending_securities"] == 1
    assert result["failures"][0]["reason"] == "ORPHAN_RAW_RESPONSE_RECEIPT_MISSING"
    assert meter.operations.count("candles") == 2
    assert digest(raw.read_bytes()) == before
    detail = reliability._missing_reason(root, "2025-01-03", identity(1).model_dump(mode="json"))
    assert detail["reason"] == "ORPHAN_RAW_RESPONSE_RECEIPT_MISSING"
    replay_meter = Transport()
    replay = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        permission_reference=PERMISSION,
        meter=replay_meter,
    )
    assert replay["pending_securities"] == 1 and replay_meter.calls == 0
    assert digest(raw.read_bytes()) == before


def test_failed_action_resumes_from_saved_candle_and_preserves_original_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    freeze(monkeypatch)

    class ActionFailure(Transport):
        def get(self, operation: str, **kwargs: Any) -> Reply:
            if operation == "actions" and kwargs["key"] == identity(1).provider_key:
                self.calls += 1
                return Reply(503, b"TEST_ONLY_UNAVAILABLE", AT, "HTTP_ERROR")
            return super().get(operation, **kwargs)

    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        permission_reference=PERMISSION,
        meter=ActionFailure(),
    )
    assert result["accepted_session_securities"] == 2 and result["pending_securities"] == 1
    folder = root / "daily/2025-01-03" / str(identity(1).isin)
    before = {
        name: digest((folder / name).read_bytes()) for name in ("candles.json", "response.json")
    }
    detail = reliability._missing_reason(root, "2025-01-03", identity(1).model_dump(mode="json"))
    assert detail["reason"] == "ACTION_EVIDENCE_PENDING"
    assert detail["latest_action_attempt_state"] == "HTTP_ERROR"
    assert detail["latest_action_attempt_status"] == 503
    retry = Transport()
    recovered = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        collect=True,
        permission_reference=PERMISSION,
        meter=retry,
    )
    assert recovered["accepted_session_securities"] == 3 and recovered["pending_securities"] == 0
    assert retry.operations == ["actions"]
    assert {name: digest((folder / name).read_bytes()) for name in before} == before
