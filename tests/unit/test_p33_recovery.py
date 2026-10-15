"""TEST_ONLY real online SQLite snapshots, isolated restoration, corruption and ownership."""

import json
import secrets
from pathlib import Path

import pytest
from workers.personal.contracts import Profile
from workers.personal.store import PersonalStore

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.operations.recovery import backup, restore


def configured(tmp_path: Path) -> tuple[Settings, PersonalStore]:
    auth = AuthStore(tmp_path / "auth")
    auth.initialize()
    auth.bootstrap("TEST_ONLY_operator", secrets.token_urlsafe(24))
    owner = auth.diagnostics()["account"]["account_id"]
    personal = PersonalStore(tmp_path / "personal", owner)
    personal.initialize()
    personal.save("profile", "default", Profile(budget_inr="10000").model_dump(), 0)
    personal.create_portfolio("TEST_ONLY_owned")
    for kind in ("watchlists", "journal", "rules", "recent"):
        personal.save(kind, "TEST_ONLY_" + kind, {"TEST_ONLY": True}, 0)
    return Settings(auth_root=auth.root, personal_root=personal.root), personal


def test_personal_online_snapshot_all_records_restore_and_tamper(tmp_path: Path) -> None:
    settings, store = configured(tmp_path)
    before = store.profile()
    target = tmp_path / "backup"
    with store.connection():
        result = backup(settings, target)
    assert set(result["databases"]) == {"auth", "personal"}
    manifest = json.loads((target / "manifest.json").read_bytes())
    assert manifest["version"] == "p33.backup.v2"
    assert manifest["databases"]["personal"]["owner"] == store.owner
    store.save("profile", "default", Profile(budget_inr="20000").model_dump(), 1)
    destination = tmp_path / "isolated_restore"
    assert restore(target, destination)["original_state_modified"] is False
    restored = PersonalStore(destination / "personal", store.owner)
    assert restored.profile() == before
    for kind in ("portfolios", "watchlists", "journal", "rules", "recent"):
        assert len(restored.listing(kind)) == 1
    assert store.profile()["value"]["budget_inr"] == "20000"
    with pytest.raises(FileExistsError):
        restore(target, destination)
    with pytest.raises(ValueError, match="OWNER_MISMATCH"):
        PersonalStore(destination / "personal", "TEST_ONLY_foreign").profile()
    with (target / "personal.sqlite3").open("ab") as stream:
        stream.write(b"TEST_ONLY_corruption")
    with pytest.raises(ValueError, match="CHECKSUM"):
        restore(target, tmp_path / "corrupt_restore")
    assert not (tmp_path / "corrupt_restore").exists()


def test_backup_refuses_foreign_personal_owner_and_nested_destination(tmp_path: Path) -> None:
    settings, store = configured(tmp_path)
    with pytest.raises(ValueError, match="SEPARATE"):
        backup(settings, store.root / "backup")
    with store.connection(write=True) as conn:
        conn.execute("UPDATE metadata SET value='TEST_ONLY_foreign' WHERE key='owner'")
    with pytest.raises(ValueError, match="OWNER_MISMATCH"):
        backup(settings, tmp_path / "foreign_backup")
    assert not (tmp_path / "foreign_backup").exists()
