"""Crash-safe probe evidence and P20 outbox. Source evidence never comes from a browser."""

import hashlib
import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from workers.alerts.contracts import Event
from workers.alerts.store import AlertStore

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.ingestion.storage import stable_json


class OperationsStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / "operations.sqlite3"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        restrict(self.root)
        if os.name != "nt":
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            except FileExistsError:
                verify(self.path, directory=False)
            else:
                os.close(fd)
        with closing(sqlite3.connect(self.path, timeout=5)) as c, c:
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version == 1:
                return
            if version or c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                raise ValueError("OPERATIONS_SCHEMA_UNSUPPORTED")
            c.execute("PRAGMA journal_mode=WAL")
            schema = next(
                p / "db/operations/schema.sql"
                for p in Path(__file__).resolve().parents
                if (p / "db/operations/schema.sql").is_file()
            )
            c.executescript("BEGIN IMMEDIATE;\n" + schema.read_text() + "\nCOMMIT;")

    @contextmanager
    def connection(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        verify(self.root)
        if not self.path.is_file():
            raise ValueError("OPERATIONS_NOT_INITIALIZED")
        for path in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
            if path.exists():
                verify(path, directory=False)
        with (
            closing(
                sqlite3.connect(
                    self.path.as_uri() + "?mode=" + ("rw" if write else "ro"), uri=True, timeout=5
                )
            ) as c,
            c,
        ):
            c.row_factory = sqlite3.Row
            if c.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("OPERATIONS_SCHEMA_UNSUPPORTED")
            if write:
                c.execute("PRAGMA synchronous=FULL")
                c.execute("BEGIN IMMEDIATE")
            yield c

    def record(self, report: dict[str, Any], *, test_only: bool = False) -> str:
        probe_id = uuid4().hex
        payload = stable_json(
            report | {"classification": "TEST_ONLY" if test_only else "OPERATIONAL_OBSERVATIONS"}
        ).decode()
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.connection(True) as c:
            if c.execute("SELECT count(*) FROM probes").fetchone()[0] >= 5000:
                raise ValueError("OPERATIONS_RETENTION_REQUIRED")
            c.execute(
                "INSERT INTO probes VALUES(?,?,?,?)",
                (probe_id, report["observed_at"], payload, digest),
            )
            for name, component in report["components"].items():
                status = component["status"]
                signature = status + ":" + component["reason"]
                old = c.execute("SELECT * FROM components WHERE name=?", (name,)).fetchone()
                failing = status in {"UNAVAILABLE", "DEGRADED"}
                failures = (old["failures"] if old and old["status"] == signature else 0) + int(
                    failing
                )
                episode = old["episode"] if old and old["status"] == signature else probe_id
                c.execute(
                    "INSERT INTO components VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET "
                    "status=excluded.status,failures=excluded.failures,episode=excluded.episode",
                    (name, signature, failures, episode),
                )
                if failing and failures >= 2:
                    event = Event(
                        code="OPERATION_FAILURE",
                        component="P22",
                        evidence_ref=f"probe:{probe_id}",
                        evidence_sha256=digest,
                        event_at=report["observed_at"],
                        time_basis="DETECTOR_OBSERVATION_TIME",
                        classification="TEST_ONLY"
                        if test_only
                        else "UNVERIFIED_OPERATIONAL_EVIDENCE",
                        mode="TEST_ONLY" if test_only else "RECORDED",
                        reasons=(component["reason"],),
                        group=f"P22:{name}",
                        identity=f"{name}:{status}:{episode}",
                    )
                    c.execute(
                        "INSERT OR IGNORE INTO outbox(id,payload) VALUES(?,?)",
                        (event.event_key, event.model_dump_json()),
                    )
        return probe_id

    def history(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        if not 1 <= limit <= 100 or not 0 <= offset <= 5000:
            raise ValueError("OPERATIONS_PAGE_INVALID")
        with self.connection() as c:
            rows = c.execute(
                "SELECT * FROM probes ORDER BY observed_at DESC,id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            pending = c.execute("SELECT count(*) FROM outbox WHERE delivered=0").fetchone()[0]
            total = c.execute("SELECT count(*) FROM probes").fetchone()[0]
        for row in rows:
            if hashlib.sha256(row["payload"].encode()).hexdigest() != row["sha256"]:
                raise ValueError("OPERATIONS_EVIDENCE_CORRUPT")
        return {
            "total": total,
            "pending_alert_events": pending,
            "probes": [
                {"id": r["id"], "sha256": r["sha256"], "evidence": json.loads(r["payload"])}
                for r in rows
            ],
        }

    def process(self, alerts: AlertStore) -> dict[str, int]:
        with self.connection() as c:
            rows = c.execute(
                "SELECT * FROM outbox WHERE delivered=0 ORDER BY id LIMIT 100"
            ).fetchall()
        published = 0
        for row in rows:
            event = Event.model_validate_json(row["payload"])
            if event.event_key != row["id"]:
                raise ValueError("OPERATIONS_OUTBOX_CORRUPT")
            with self.connection() as c:
                probe = c.execute(
                    "SELECT payload,sha256 FROM probes WHERE id=?",
                    (event.evidence_ref.removeprefix("probe:"),),
                ).fetchone()
            if (
                probe is None
                or probe["sha256"] != event.evidence_sha256
                or hashlib.sha256(probe["payload"].encode()).hexdigest() != probe["sha256"]
            ):
                raise ValueError("OPERATIONS_PROVENANCE_FAILED")
            published += alerts.publish(f"P22:{row['id']}", event.evidence_sha256, [event])
            # A crash here replays the same P20 deduplication identity safely.
            with self.connection(True) as c:
                c.execute("UPDATE outbox SET delivered=1 WHERE id=?", (row["id"],))
        return {"processed": len(rows), "published": published}
