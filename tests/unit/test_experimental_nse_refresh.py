"""TEST_ONLY transport and retained bodies verify independent incremental capture."""

import copy
import gzip
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse import refresh as module
from workers.experimental_nse.acquire import PERMISSION, encoded
from workers.providers.upstox import KEY, Reply, instrument_master

from alphalens_data.errors import DataContractError

RECEIVED = datetime(2026, 10, 17, tzinfo=UTC)


@pytest.fixture
def setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict[str, Any], list[str]]:
    """No actual source data or provider is used by these constructed tests."""
    root = tmp_path / "test-only-study"
    root.mkdir()
    master = gzip.compress(
        json.dumps(
            [
                {
                    "segment": "NSE_EQ",
                    "exchange": "NSE",
                    "instrument_type": "EQ",
                    "instrument_key": KEY,
                    "isin": "INE002A01018",
                    "trading_symbol": "RELIANCE",
                }
            ]
        ).encode()
    )
    original_identities, _ = instrument_master(
        Reply(200, master, datetime(2026, 10, 16, tzinfo=UTC), "ACCEPTED"), require_reliance=False
    )
    original = original_identities[0]
    base: dict[str, Any] = {
        "dataset_id": "TEST_ONLY_ORIGINAL_DATASET",
        "sessions": ["2026-10-15"],
        "rows": [
            {
                "key": KEY,
                "symbol": "RELIANCE",
                "isin": "INE002A01018",
                "name": None,
                "session": "2026-10-15",
                "open": "100",
                "high": "110",
                "low": "90",
                "close": "105",
                "volume": 1000,
                "received_at": "2026-10-16T00:00:00+00:00",
                "raw_sha256": "TEST_ONLY",
                "provider_candle_at": "2026-10-15T00:00:00+05:30",
            }
        ],
        "source_observed_at": "2026-10-16T00:00:00+00:00",
        "manifest": {
            "api_calls": 2,
            "exclusions": [],
            "instruments": [
                {
                    "identity": original.model_dump(mode="json"),
                    "observations": 1,
                    "start": "2026-10-15",
                    "end": "2026-10-15",
                }
            ],
        },
        "replay_api_calls": 0,
    }
    calls: list[str] = []

    class Client:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            assert kwargs == {"budget": 31, "retries": 0}
            self.calls = 0

        def get(self, operation: str, **kwargs: Any) -> Reply:
            self.calls += 1
            calls.append(operation)
            if operation == "instruments":
                return Reply(200, master, RECEIVED, "ACCEPTED")
            assert kwargs["key"] == KEY
            assert str(kwargs["start"]) == str(kwargs["end"]) == "2026-10-16"
            body = json.dumps(
                {
                    "status": "success",
                    "data": {"candles": [["2026-10-16T00:00:00+05:30", 100, 110, 90, 106, 1200]]},
                }
            ).encode()
            return Reply(200, body, RECEIVED, "ACCEPTED")

    monkeypatch.setattr(module, "initialize", lambda root: None)
    monkeypatch.setattr(module, "replay", lambda root: copy.deepcopy(base))
    monkeypatch.setattr(
        module, "guard", lambda: {"session_date": "2026-10-17", "state": "TEST_ONLY"}
    )
    monkeypatch.setattr(module, "ProviderStore", lambda root: None)
    monkeypatch.setattr(module, "UpstoxClient", Client)
    return root, base, calls


def test_refresh_preserves_original_and_replays_zero_get(setup: tuple[Any, ...]) -> None:
    root, base, calls = setup
    original_bytes = encoded(base["rows"])
    updated = module.refresh(root, root, permission_reference=PERMISSION)
    assert calls == ["instruments", "candles"]
    assert updated["sessions"] == ["2026-10-15", "2026-10-16"]
    assert encoded(updated["rows"][:1]) == original_bytes
    assert updated["parent_dataset_id"] == base["dataset_id"]
    assert updated["dataset_id"] != base["dataset_id"]
    replayed = module.current_dataset(root)
    assert replayed["dataset_id"] == updated["dataset_id"]
    assert replayed["rows"] == updated["rows"]
    again = module.refresh(root, root, permission_reference=PERMISSION)
    assert "ZERO_REQUEST_REPLAY" in again["refresh_state"]
    assert calls == ["instruments", "candles"]


@pytest.mark.parametrize("after_close", [True, False])
def test_same_day_requires_official_elapsed_session_and_independent_lower_bound(
    setup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, after_close: bool
) -> None:
    root, _, calls = setup
    original_client = vars(module)["UpstoxClient"]
    received = datetime(2026, 10, 16, 14, tzinfo=UTC)
    start = datetime(2026, 10, 16, 3, 45, tzinfo=UTC)
    end = datetime(2026, 10, 16, 10, tzinfo=UTC)

    class SameDayClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            assert kwargs == {"budget": 32, "retries": 0}
            self.inner = original_client(*args, budget=31, retries=0)
            self.calls = 0

        def get(self, operation: str, **kwargs: Any) -> Reply:
            self.calls += 1
            if operation == "timings":
                calls.append(operation)
                payload = {
                    "status": "success",
                    "data": [
                        {
                            "exchange": "NSE",
                            "start_time": int(start.timestamp() * 1000),
                            "end_time": int(end.timestamp() * 1000),
                        }
                    ],
                }
                return Reply(200, encoded(payload), received, "ACCEPTED")
            reply = self.inner.get(operation, **kwargs)
            return Reply(reply.status, reply.body, received, reply.state)

    monkeypatch.setattr(module, "UpstoxClient", SameDayClient)
    lower = received if after_close else datetime(2026, 10, 16, 9, tzinfo=UTC)
    monkeypatch.setattr(
        module,
        "guard",
        lambda: {"session_date": "2026-10-16", "lower_at": lower.isoformat(), "state": "TEST_ONLY"},
    )
    if not after_close:
        with pytest.raises(DataContractError, match="SESSION_NOT_COMPLETED"):
            module.refresh(
                root, root, permission_reference=PERMISSION, include_completed_today=True
            )
        assert calls == ["timings"]
        assert not (root / "data-latest.json").exists()
        return
    updated = module.refresh(
        root, root, permission_reference=PERMISSION, include_completed_today=True
    )
    assert calls == ["timings", "instruments", "candles"]
    assert updated["completed_session"]["session"] == "2026-10-16"
    assert updated["completed_session"]["official_final_close_verified"] is False
    assert module.current_dataset(root)["dataset_id"] == updated["dataset_id"]
    again = module.refresh(
        root, root, permission_reference=PERMISSION, include_completed_today=True
    )
    assert again["refresh_state"] == "UP_TO_DATE_ZERO_REQUEST_REPLAY"
    assert calls == ["timings", "instruments", "candles"]


def test_refresh_rejects_tampered_raw_and_path(setup: tuple[Any, ...]) -> None:
    root, _, _ = setup
    module.refresh(root, root, permission_reference=PERMISSION)
    folder = next((root / "refreshes").iterdir())
    (folder / "INE002A01018.json").write_bytes(b"TEST_ONLY_TAMPER")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        module.current_dataset(root)
    (root / "data-latest.json").write_text(
        json.dumps({"refresh_id": "../unsafe", "receipt_sha256": "0" * 64})
    )
    with pytest.raises(DataContractError, match="PATH"):
        module.current_dataset(root)


def test_refresh_source_and_clock_rejection_before_provider(
    setup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, calls = setup
    with pytest.raises(DataContractError, match="PERMISSION"):
        module.refresh(root, root, permission_reference="UNKNOWN")
    monkeypatch.setattr(module, "guard", lambda: {"session_date": "2026-12-01"})
    with pytest.raises(DataContractError, match="CATCHUP"):
        module.refresh(root, root, permission_reference=PERMISSION)
    assert calls == []


def test_missing_publication_retains_no_empty_candle_and_repeats_zero_get(
    setup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, calls = setup
    original_client = vars(module)["UpstoxClient"]

    class EmptyClient(original_client):  # type: ignore[misc, valid-type]
        def get(self, operation: str, **kwargs: Any) -> Reply:
            reply = super().get(operation, **kwargs)
            if operation == "candles":
                return Reply(
                    200, b'{"status":"success","data":{"candles":[]}}', RECEIVED, "ACCEPTED"
                )
            assert isinstance(reply, Reply)
            return reply

    monkeypatch.setattr(module, "UpstoxClient", EmptyClient)
    result = module.refresh(root, root, permission_reference=PERMISSION)
    assert result["refresh_state"] == "PUBLICATION_OR_NONSESSION_PENDING"
    assert len(result["rows"]) == 1
    assert not list((root / "refreshes").glob("*/INE002A01018.json"))
    again = module.refresh(root, root, permission_reference=PERMISSION)
    assert "PENDING_ZERO_REQUEST_REPLAY" in again["refresh_state"]
    assert calls == ["instruments", "candles"]
    module.refresh(root, root, permission_reference=PERMISSION, retry_pending=True)
    assert calls == ["instruments", "candles", "instruments", "candles"]
