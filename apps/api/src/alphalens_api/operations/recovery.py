"""Transactional SQLite online backup, integrity manifests and new-location restore."""

import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import restrict, verify
from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings

NAMES = {
    "auth": "auth.sqlite3",
    "alerts": "alerts.sqlite3",
    "operations": "operations.sqlite3",
    "prospective": "prospective.sqlite3",
    "personal": "personal.sqlite3",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    restrict(path)


def copy_database(source: Path, target: Path, *, personal: bool = False) -> dict[str, Any]:
    if target.exists() or not source.is_file():
        raise ValueError("BACKUP_SOURCE_OR_DESTINATION_INVALID")
    # Open online source read-only; SQLite backup reconciles WAL transactions.
    if os.name != "nt":
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
    with (
        closing(
            sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        ) as src,
        closing(sqlite3.connect(target, timeout=5)) as dst,
    ):
        started = time.monotonic()

        def progress(status: int, remaining: int, total: int) -> None:
            if time.monotonic() - started > 30:
                raise TimeoutError("BACKUP_TIME_BUDGET_EXCEEDED")

        src.backup(dst, pages=128, sleep=0.05, progress=progress)
        if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("BACKUP_INTEGRITY_FAILED")
        version = dst.execute("PRAGMA user_version").fetchone()[0]
        if version != (0 if personal else 1):
            raise ValueError("BACKUP_SCHEMA_UNSUPPORTED")
        owner = None
        if personal:
            metadata = dict(dst.execute("SELECT key,value FROM metadata"))
            owner = metadata.get("owner")
            if not owner or metadata.get("schema") != "p32.personal.v1":
                raise ValueError("BACKUP_PERSONAL_SCHEMA_INVALID")
            if dst.execute("SELECT 1 FROM records WHERE owner<>? LIMIT 1", (owner,)).fetchone():
                raise ValueError("BACKUP_PERSONAL_OWNER_MISMATCH")
    verify(target, directory=False)
    return {
        "file": target.name,
        "sha256": digest(target),
        "bytes": target.stat().st_size,
        "schema_version": version,
        **({"owner": owner} if personal else {}),
    }


def backup(settings: Settings, destination: Path) -> dict[str, Any]:
    roots = {
        "auth": settings.auth_root,
        "alerts": settings.alerts_root,
        "operations": settings.operations_root,
    }
    if settings.daily_root and (settings.daily_root / "prospective/prospective.sqlite3").is_file():
        roots["prospective"] = settings.daily_root / "prospective"
    if settings.personal_root is not None:
        from workers.personal.store import PersonalStore

        if settings.auth_root is None:
            raise ValueError("PERSONAL_BACKUP_AUTH_OWNER_REQUIRED")
        account = AuthStore(settings.auth_root).diagnostics()["account"]
        if not account:
            raise ValueError("PERSONAL_BACKUP_AUTH_OWNER_REQUIRED")
        with PersonalStore(settings.personal_root, account["account_id"]).connection():
            pass
        roots["personal"] = settings.personal_root
    target = destination.resolve()
    for root in roots.values():
        if root and (target == root.resolve() or target.is_relative_to(root.resolve())):
            raise ValueError("BACKUP_MUST_BE_SEPARATE")
    private_directory(target)
    receipt: dict[str, Any] = {
        "version": "p33.backup.v2",
        "complete": False,
        "scope": "MUTABLE_OPERATIONAL_STATE",
        "databases": {},
    }
    for kind, root in roots.items():
        if root is not None:
            if kind == "auth":
                with AuthStore(root).connection():
                    pass
            receipt["databases"][kind] = copy_database(
                root / NAMES[kind], target / NAMES[kind], personal=kind == "personal"
            )
    if not receipt["databases"]:
        raise ValueError("NO_CONFIGURED_BACKUP_SOURCE")
    receipt["complete"] = True
    # A failed backup has no complete manifest, never a falsely complete snapshot.
    with (target / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    return {
        "complete": True,
        "databases": list(receipt["databases"]),
        "manifest_sha256": hashlib.sha256((target / "manifest.json").read_bytes()).hexdigest(),
    }


def restore(source: Path, destination: Path) -> dict[str, Any]:
    root = source.resolve()
    verify(root)
    manifest = root / "manifest.json"
    if manifest.stat().st_size > 65536:
        raise ValueError("BACKUP_MANIFEST_INVALID")
    value = json.loads(manifest.read_bytes())
    if (
        value.get("version") not in {"p22.backup.v1", "p33.backup.v2"}
        or value.get("complete") is not True
    ):
        raise ValueError("BACKUP_MANIFEST_INVALID")
    rows = value["databases"]
    if not rows or set(rows) - NAMES.keys():
        raise ValueError("BACKUP_MANIFEST_INVALID")
    for kind, entry in rows.items():
        path = root / NAMES[kind]
        if (
            entry["file"] != NAMES[kind]
            or path.resolve().parent != root
            or path.stat().st_size != entry["bytes"]
            or digest(path) != entry["sha256"]
        ):
            raise ValueError("BACKUP_CHECKSUM_FAILED")
        verify(path, directory=False)
    target = destination.resolve()
    if target == root or target.is_relative_to(root):
        raise ValueError("RESTORE_MUST_BE_SEPARATE")
    private_directory(target)
    for kind in rows:
        folder = target / kind
        private_directory(folder)
        copied = copy_database(
            root / NAMES[kind], folder / NAMES[kind], personal=kind == "personal"
        )
        if kind == "personal" and copied["owner"] != rows[kind].get("owner"):
            raise ValueError("BACKUP_PERSONAL_OWNER_MISMATCH")
    # Restoring old sessions must never resurrect already revoked credentials.
    if "auth" in rows:
        store = AuthStore(target / "auth")
        details = store.diagnostics()["account"]
        if details:
            store.revoke(details["account_id"])
            if "personal" in rows and details["account_id"] != rows["personal"].get("owner"):
                raise ValueError("BACKUP_PERSONAL_OWNER_MISMATCH")
    return {
        "restored": True,
        "databases": list(rows),
        "auth_sessions": "REVOKED",
        "original_state_modified": False,
    }
