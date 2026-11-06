"""Read-only frozen research verification, independent of evolving application code.

This verifies the recorded artifact inventory and original alert evidence. It does
not load estimators, open a writable database, or make provider requests. Receipts
are private local files and must not contain market observations or credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALERT_SHA256 = "dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def artifact_path(root: Path, relative: str) -> Path:
    """Reject escapes and links before reading protected file contents."""
    name = Path(relative)
    if name.is_absolute() or not name.parts or any(p in {"..", "."} for p in name.parts):
        raise ValueError("ARTIFACT_PATH_REJECTED")
    base = root.resolve(strict=True)
    path = base
    for part in name.parts:
        path = path / part
        if path.is_symlink() or path.is_junction():
            raise ValueError("ARTIFACT_LINK_REJECTED")
    if not path.resolve(strict=True).is_relative_to(base) or not path.is_file():
        raise ValueError("ARTIFACT_FILE_REQUIRED")
    return path


def verify_artifacts(root: Path, inventory: list[dict[str, Any]]) -> dict[str, int]:
    seen: set[str] = set()
    total = 0
    for entry in inventory:
        relative = str(entry["path"])
        if relative in seen:
            raise ValueError("ARTIFACT_DUPLICATE_REJECTED")
        seen.add(relative)
        path = artifact_path(root, relative)
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
        total += entry["bytes"]
    if not seen:
        raise ValueError("ARTIFACT_INVENTORY_REQUIRED")
    return {"verified_files": len(seen), "verified_bytes": total}


def verify_alerts(database: Path, expected_count: int, expected_digest: str) -> int:
    # strict resolution + mode=ro prevents sqlite3 from creating a missing store.
    path = database.resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT id,event_key,evidence,evidence_hash FROM alerts ORDER BY id"
        ).fetchall()
    actual = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    if len(rows) != expected_count or actual != expected_digest:
        raise ValueError("ORIGINAL_ALERT_EVIDENCE_CHANGED")
    if any(hashlib.sha256(row[2].encode()).hexdigest() != row[3] for row in rows):
        raise ValueError("ALERT_BODY_HASH_REJECTED")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--alerts-database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    manifest = repo / "docs/backtesting/real-research-economic-audit.json"
    audit = json.loads(manifest.read_bytes())
    result: dict[str, Any] = verify_artifacts(args.run_root, audit["artifact_inventory"])
    result.update(
        state="PASS",
        verified_at=datetime.now(UTC).isoformat(),
        manifest_sha256=digest(manifest),
        original_alerts=verify_alerts(args.alerts_database, 47, ALERT_SHA256),
        method="READ_ONLY_SHA256_AND_SQLITE_QUERY_ONLY",
        provider_requests=0,
        estimator_operations=0,
        database_writes=0,
    )
    # Exclusive creation preserves earlier verification evidence.
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
