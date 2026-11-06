"""TEST_ONLY transport fixtures; never evidence of real NSE model performance."""

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse import acquire
from workers.providers.upstox import Reply


@pytest.fixture
def captured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    now = datetime(2026, 10, 16, 5, tzinfo=UTC)
    master = gzip.compress(
        json.dumps(
            [
                {
                    "segment": "NSE_EQ",
                    "exchange": "NSE",
                    "instrument_type": "EQ",
                    "instrument_key": "NSE_EQ|INE002A01018",
                    "isin": "INE002A01018",
                    "trading_symbol": "RELIANCE",
                    "name": "TEST_ONLY source fixture",
                }
            ]
        ).encode()
    )
    body = json.dumps(
        {
            "status": "success",
            "data": {"candles": [["2026-10-15T00:00:00+05:30", 100, 110, 90, 105, 1000, 0]]},
        }
    ).encode()

    class Client:
        calls = 0

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            assert kwargs == {"budget": 31, "retries": 0}

        def get(self, operation: str, **kwargs: Any) -> Reply:
            self.calls += 1
            if operation == "candles":
                assert kwargs["key"] == "NSE_EQ|INE002A01018"
            return Reply(200, master if operation == "instruments" else body, now, "ACCEPTED")

    monkeypatch.setattr(acquire, "UpstoxClient", Client)
    monkeypatch.setattr(acquire, "guard", lambda: {"session_date": "2026-10-16"})
    root = tmp_path / "private"
    result = acquire.capture(root, tmp_path / "unused", permission_reference=acquire.PERMISSION)
    assert len(result["rows"]) == 1
    assert result["manifest"]["api_calls"] == 2
    assert len(result["manifest"]["exclusions"]) == 29
    return root


def test_replay_makes_zero_transport_calls(captured: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Replay must not initialize a network client")

    monkeypatch.setattr(acquire, "UpstoxClient", forbidden)
    first = acquire.replay(captured)
    second = acquire.capture(captured, Path("unused"), permission_reference=acquire.PERMISSION)
    assert first == second
    assert second["replay_api_calls"] == 0
    assert second["rows"][0]["received_at"] == "2026-10-16T05:00:00+00:00"


@pytest.mark.parametrize("filename", ["master.json.gz", "INE002A01018.json"])
def test_capture_tamper_rejected(captured: Path, filename: str) -> None:
    path = captured / "snapshot-v1" / filename
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="CHECKSUM_REJECTED"):
        acquire.replay(captured)


def test_capture_explicit_permission_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PERMISSION_REQUIRED"):
        acquire.capture(tmp_path / "new", tmp_path / "unused", permission_reference="UNKNOWN")
    assert not (tmp_path / "new").exists()


def test_manifest_path_cannot_escape_private_root(captured: Path) -> None:
    path = captured / "snapshot-v1/manifest.json"
    value = json.loads(path.read_bytes())
    value["instruments"][0]["filename"] = "../outside.json"
    path.write_bytes(acquire.encoded(value))
    with pytest.raises(ValueError, match="PAYLOAD_PATH_REJECTED"):
        acquire.replay(captured)


def test_incomplete_capture_never_restarts_network_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY_partial_capture"
    acquire.initialize(root)
    (root / "snapshot-v1").mkdir()

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Incomplete capture must require review without more network requests")

    monkeypatch.setattr(acquire, "UpstoxClient", forbidden)
    monkeypatch.setattr(acquire, "guard", forbidden)
    with pytest.raises(ValueError, match="INCOMPLETE_CAPTURE_REQUIRES_REVIEW_NO_REQUESTS"):
        acquire.capture(root, tmp_path / "unused", permission_reference=acquire.PERMISSION)


def test_symlink_or_escape_path_rejected(captured: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="SYMLINK_PATH_REJECTED"):
        acquire.private_path(captured, "..", "outside")
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path.name == "snapshot-v1" or original(path),
    )
    with pytest.raises(ValueError, match="SYMLINK_PATH_REJECTED"):
        acquire.replay(captured)


def test_workspace_receipt_must_match_directory_identity(tmp_path: Path) -> None:
    from workers.experimental_nse.workspace import read_workspace

    root = tmp_path / "TEST_ONLY_workspace"
    acquire.initialize(root)
    run_id = "1" * 32
    run = root / "runs" / run_id
    run.mkdir(parents=True)
    receipt = acquire.encoded({"family": acquire.FAMILY, "run_id": "2" * 32})
    (run / "receipt.json").write_bytes(receipt)
    (root / "latest.json").write_bytes(
        acquire.encoded({"run_id": run_id, "receipt_sha256": acquire.digest(receipt)})
    )
    with pytest.raises(ValueError, match="FAMILY_REJECTED"):
        read_workspace(root)
