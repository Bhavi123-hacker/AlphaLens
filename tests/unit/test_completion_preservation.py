"""TEST_ONLY preservation failure injection; no historical market data."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from scripts.verify_completion_preservation import verify_alerts, verify_artifacts


def inventory(root: Path) -> list[dict[str, object]]:
    body = b"TEST_ONLY immutable research artifact"
    (root / "artifact.bin").write_bytes(body)
    return [
        {"path": "artifact.bin", "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    ]


def test_protected_artifact_mutation_is_detected(tmp_path: Path) -> None:
    entries = inventory(tmp_path)
    assert verify_artifacts(tmp_path, entries)["verified_files"] == 1
    (tmp_path / "artifact.bin").write_bytes(b"TEST_ONLY changed")
    with pytest.raises(ValueError, match="FROZEN_ARTIFACT_CHANGED"):
        verify_artifacts(tmp_path, entries)


@pytest.mark.parametrize("relative", ["../outside.bin", "C:/outside.bin"])
def test_inventory_escape_is_rejected(tmp_path: Path, relative: str) -> None:
    entries = inventory(tmp_path)
    entries[0]["path"] = relative
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_artifacts(tmp_path, entries)


def test_duplicate_inventory_is_rejected(tmp_path: Path) -> None:
    entries = inventory(tmp_path)
    with pytest.raises(ValueError, match="ARTIFACT_DUPLICATE_REJECTED"):
        verify_artifacts(tmp_path, entries * 2)


def test_missing_database_is_never_created(tmp_path: Path) -> None:
    path = tmp_path / "absent.sqlite3"
    with pytest.raises(FileNotFoundError):
        verify_alerts(path, 0, "TEST_ONLY")
    assert not path.exists()


def test_alert_read_is_byte_preserving_and_detects_mutation(tmp_path: Path) -> None:
    path = tmp_path / "alerts.sqlite3"
    body = "TEST_ONLY evidence"
    row = ("TEST_ONLY", "TEST_ONLY", body, hashlib.sha256(body.encode()).hexdigest())
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE alerts(id TEXT,event_key TEXT,evidence TEXT,evidence_hash TEXT)"
        )
        connection.execute("INSERT INTO alerts VALUES(?,?,?,?)", row)
    expected = hashlib.sha256(json.dumps([row]).encode()).hexdigest()
    before = path.read_bytes()
    assert verify_alerts(path, 1, expected) == 1
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE alerts SET evidence='TEST_ONLY corrupted'")
    with pytest.raises(ValueError, match="ORIGINAL_ALERT_EVIDENCE_CHANGED"):
        verify_alerts(path, 1, expected)
