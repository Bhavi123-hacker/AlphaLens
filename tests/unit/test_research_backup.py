"""TEST_ONLY backup boundaries and integrity, never real research evidence."""

import sqlite3
from pathlib import Path

import pytest
from scripts import backup_research as bundle
from workers.experimental_nse.acquire import digest, encoded, initialize

from alphalens_api.auth.permissions import restrict


def test_destination_refuses_existing_or_external_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bundle, "REPO", tmp_path)
    initialize(tmp_path / ".local-data")
    existing = tmp_path / ".local-data/existing"
    initialize(existing)
    for path in (existing, tmp_path / "outside"):
        with pytest.raises(ValueError, match="NEW_PRIVATE_ISOLATED_DESTINATION_REQUIRED"):
            bundle.destination(path)
    assert not (tmp_path / "outside").exists()


def test_online_sqlite_copy_preserves_source_and_private_permissions(tmp_path: Path) -> None:
    restrict(tmp_path)
    source = tmp_path / "TEST_ONLY.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence(value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('TEST_ONLY')")
    before = digest(source.read_bytes())
    target = tmp_path / "private/saved.sqlite3"
    bundle.copy_file(source, target)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT * FROM evidence").fetchall() == [("TEST_ONLY",)]
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert digest(source.read_bytes()) == before


def test_tampered_manifest_file_is_rejected_before_model_loading(tmp_path: Path) -> None:
    restrict(tmp_path)
    body = encoded({"files": {"payload.json": "0" * 64}, "v2_forecasts": 0})
    (tmp_path / "manifest.json").write_bytes(body)
    (tmp_path / "manifest.sha256").write_text(digest(body), encoding="ascii")
    (tmp_path / "payload.json").write_bytes(b"TEST_ONLY")
    (tmp_path / "payload.json").chmod(0o600)
    with pytest.raises(ValueError, match="RESEARCH_BUNDLE_FILE_HASH_REJECTED"):
        bundle.validate(tmp_path)
