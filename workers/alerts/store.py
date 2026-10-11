"""Operational SQLite evidence, mutable projections and transactional delivery outbox."""

import json
import sqlite3
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum

from .contracts import TEMPLATES, Event, Lifecycle, Preferences


class AlertError(ValueError):
    """Only safe codes cross the operational boundary."""


def timestamp(now: datetime | None = None) -> str:
    value = now or datetime.now(UTC)
    if value.tzinfo is None:
        raise AlertError("AWARE_TIME_REQUIRED")
    return value.astimezone(UTC).isoformat()


class AlertStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / "alerts.sqlite3"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=10) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1}:
                raise AlertError("ALERT_SCHEMA_UNSUPPORTED")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            schema = Path(__file__).resolve().parents[2] / "db" / "alerts" / "schema.sql"
            connection.executescript(schema.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT OR IGNORE INTO preferences VALUES (1, ?)",
                (Preferences().model_dump_json(),),
            )

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise AlertError("ALERT_STORE_NOT_INITIALIZED")
        mode = "rw" if write else "ro"
        connection = sqlite3.connect(f"{self.path.as_uri()}?mode={mode}", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise AlertError("ALERT_SCHEMA_UNSUPPORTED")
            if write:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                connection.commit()
        except BaseException:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def audit(
        connection: sqlite3.Connection,
        action: str,
        at: str,
        payload: Any,
        alert_id: str | None = None,
    ) -> None:
        if connection.execute("SELECT count(*) FROM audit").fetchone()[0] >= 1_000_000:
            raise AlertError("ALERT_AUDIT_CAPACITY_REACHED")
        connection.execute(
            "INSERT INTO audit(alert_id, action, at, payload) VALUES (?, ?, ?, ?)",
            (alert_id, action, at, stable_json(payload).decode()),
        )

    def publish(
        self,
        source_key: str,
        fingerprint: str,
        events: Sequence[Event],
        *,
        now: datetime | None = None,
    ) -> int:
        """Evidence and source cursor commit together. Failed publication advances neither."""
        if len(events) > 500:
            raise AlertError("ALERT_BATCH_LIMIT")
        at = timestamp(now)
        with self.connection(write=True) as connection:
            previous = connection.execute(
                "SELECT fingerprint FROM sources WHERE source_key=?", (source_key,)
            ).fetchone()
            if previous and previous[0] == fingerprint:
                return 0
            if (
                not previous
                and connection.execute("SELECT count(*) FROM sources").fetchone()[0] >= 100_000
            ):
                raise AlertError("ALERT_SOURCE_CAPACITY_REACHED")
            inserted = 0
            for event in events:
                event = Event.model_validate(event.model_dump(mode="json"))
                if connection.execute(
                    "SELECT 1 FROM seen WHERE event_key=?", (event.event_key,)
                ).fetchone():
                    continue
                if connection.execute("SELECT count(*) FROM alerts").fetchone()[0] >= 10_000:
                    raise AlertError("ALERT_RETENTION_REQUIRED")
                if connection.execute("SELECT count(*) FROM seen").fetchone()[0] >= 200_000:
                    raise AlertError("ALERT_IDENTITY_CAPACITY_REACHED")
                payload = event.model_dump_json()
                category, severity, _, _ = TEMPLATES[event.code]
                connection.execute(
                    "INSERT INTO alerts(id,event_key,evidence,evidence_hash,category,severity,"
                    "event_code,event_at,created_at,group_key) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        event.alert_id,
                        event.event_key,
                        payload,
                        checksum(payload.encode()),
                        category,
                        severity,
                        event.code,
                        timestamp(event.event_at),
                        at,
                        event.group,
                    ),
                )
                connection.execute(
                    "INSERT INTO seen VALUES (?,?)", (event.event_key, event.alert_id)
                )
                self.audit(connection, "PUBLISHED", at, {"source": source_key}, event.alert_id)
                inserted += 1
            connection.execute(
                "INSERT INTO sources VALUES (?,?) ON CONFLICT(source_key) "
                "DO UPDATE SET fingerprint=excluded.fingerprint",
                (source_key, fingerprint),
            )
            return inserted

    @staticmethod
    def public(row: sqlite3.Row) -> dict[str, Any]:
        payload = row["evidence"]
        if checksum(payload.encode()) != row["evidence_hash"]:
            raise AlertError("ALERT_EVIDENCE_CHECKSUM_INVALID")
        event = Event.model_validate_json(payload)
        if event.alert_id != row["id"] or event.event_key != row["event_key"]:
            raise AlertError("ALERT_IDENTITY_INVALID")
        category, severity, title, message = TEMPLATES[event.code]
        if (category, severity, event.code) != (
            row["category"],
            row["severity"],
            row["event_code"],
        ):
            raise AlertError("ALERT_PROJECTION_INVALID")
        if row["lifecycle"] not in {"NEW", "READ", "ACKNOWLEDGED", "RESOLVED"} or row[
            "delivery"
        ] not in {"NOT_REQUESTED", "PENDING", "DELIVERED", "FAILED", "RETRY_PENDING", "SUPPRESSED"}:
            raise AlertError("ALERT_PROJECTION_INVALID")
        return dict(
            id=row["id"],
            category=category,
            severity=severity,
            title=title,
            message=message,
            evidence=event.model_dump(mode="json"),
            evidence_status="VERIFIED_PERSISTED_EVENT"
            if event.time_basis == "PERSISTED_EVENT_TIME"
            else "VERIFIED_DETECTOR_OBSERVATION",
            lifecycle=row["lifecycle"],
            delivery=row["delivery"],
            created_at=row["created_at"],
            attempts=row["attempts"],
            next_attempt=row["next_attempt"],
            delivered_at=row["delivered_at"],
            delivery_reason=row["delivery_reason"],
            deduplication_key=row["event_key"],
            channel="IN_APP",
            external_delivery="NOT_REQUESTED",
        )

    def listing(
        self,
        *,
        category: str | None = None,
        severity: str | None = None,
        lifecycle: str | None = None,
        delivery: str | None = None,
        search: str = "",
        limit: int = 20,
        offset: int = 0,
        test_only: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        if not 1 <= limit <= 100 or not 0 <= offset <= 10_000 or len(search) > 100:
            raise AlertError("ALERT_QUERY_LIMIT")
        with self.connection() as connection:
            # At most 10,000 rows. Verify evidence before it can reach a client.
            rows = [
                self.public(row)
                for row in connection.execute(
                    "SELECT * FROM alerts ORDER BY created_at DESC,id DESC"
                )
            ]
        if not test_only and any(
            r["evidence"]["classification"] in {"TEST_ONLY", "TEST_ONLY_PAPER"} for r in rows
        ):
            raise AlertError("TEST_ONLY_ALERT_EVIDENCE_BLOCKED")
        text = search.casefold()
        selected = [
            r
            for r in rows
            if (category is None or r["category"] == category)
            and (severity is None or r["severity"] == severity)
            and (lifecycle is None or r["lifecycle"] == lifecycle)
            and (delivery is None or r["delivery"] == delivery)
            and (
                not text
                or text
                in (r["title"] + " " + r["message"] + " " + json.dumps(r["evidence"])).casefold()
            )
        ]
        return selected[offset : offset + limit], len(selected)

    def get(self, alert_id: str, *, test_only: bool = False) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        if row is None:
            raise AlertError("ALERT_NOT_FOUND")
        result = self.public(row)
        if not test_only and result["evidence"]["classification"] in {
            "TEST_ONLY",
            "TEST_ONLY_PAPER",
        }:
            raise AlertError("TEST_ONLY_ALERT_EVIDENCE_BLOCKED")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT action,at,payload FROM audit WHERE alert_id=? "
                "ORDER BY sequence DESC LIMIT 201",
                (alert_id,),
            ).fetchall()
        result["history"] = [
            {"action": row["action"], "at": row["at"], "details": json.loads(row["payload"])}
            for row in rows[:200]
        ]
        result["history_truncated"] = len(rows) > 200
        return result

    def unread(self, *, test_only: bool = False) -> int:
        # Count uses the same validated, classification-gated projection as history.
        _, count = self.listing(lifecycle="NEW", delivery="DELIVERED", test_only=test_only)
        return count

    def preferences(self) -> Preferences:
        with self.connection() as connection:
            return Preferences.model_validate_json(
                connection.execute("SELECT payload FROM preferences WHERE singleton=1").fetchone()[
                    0
                ]
            )

    def set_preferences(self, value: Preferences, *, now: datetime | None = None) -> None:
        with self.connection(write=True) as connection:
            connection.execute(
                "UPDATE preferences SET payload=? WHERE singleton=1", (value.model_dump_json(),)
            )
            self.audit(connection, "PREFERENCES", timestamp(now), value.model_dump(mode="json"))

    def transition(self, alert_id: str, target: Lifecycle, *, now: datetime | None = None) -> None:
        allowed = {
            "NEW": {"READ", "ACKNOWLEDGED", "RESOLVED"},
            "READ": {"ACKNOWLEDGED", "RESOLVED"},
            "ACKNOWLEDGED": {"RESOLVED"},
            "RESOLVED": set(),
        }
        with self.connection(write=True) as connection:
            row = connection.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
            if row is None:
                raise AlertError("ALERT_NOT_FOUND")
            self.public(row)
            current = row["lifecycle"]
            if target == current:
                return
            if target not in allowed[current]:
                raise AlertError("INVALID_ALERT_TRANSITION")
            connection.execute("UPDATE alerts SET lifecycle=? WHERE id=?", (target, alert_id))
            self.audit(
                connection, "LIFECYCLE", timestamp(now), {"from": current, "to": target}, alert_id
            )

    def deliver(
        self,
        *,
        now: datetime | None = None,
        publisher: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, int]:
        """IN_APP visibility only. No external transport exists or is called."""
        at = timestamp(now)
        clock = datetime.fromisoformat(at)
        result: dict[str, int] = {}
        with self.connection(write=True) as connection:
            prefs = Preferences.model_validate_json(
                connection.execute("SELECT payload FROM preferences WHERE singleton=1").fetchone()[
                    0
                ]
            )
            rows = connection.execute(
                "SELECT * FROM alerts WHERE delivery IN ('PENDING','RETRY_PENDING') "
                "AND (next_attempt IS NULL OR next_attempt<=?) ORDER BY created_at,id LIMIT 100",
                (at,),
            ).fetchall()
            for row in rows:
                item = self.public(row)
                severity = item["severity"]
                status, reason, next_at = "DELIVERED", None, None
                attempts = row["attempts"]
                if item["category"] not in prefs.categories or (
                    severity == "INFO" and not prefs.include_info
                ):
                    status, reason = "SUPPRESSED", "CATEGORY_OR_INFO_PREFERENCE"
                elif (
                    severity not in {"ERROR", "CRITICAL"}
                    and prefs.quiet_enabled
                    and quiet(clock, prefs)
                ):
                    status, reason = "RETRY_PENDING", "QUIET_HOURS"
                    next_at = timestamp(clock + timedelta(minutes=5))
                elif (
                    severity not in {"ERROR", "CRITICAL"}
                    and connection.execute(
                        "SELECT 1 FROM alerts WHERE group_key=? AND severity=? "
                        "AND delivery='DELIVERED' AND delivered_at>? LIMIT 1",
                        (
                            row["group_key"],
                            severity,
                            timestamp(clock - timedelta(seconds=prefs.cooldown_seconds)),
                        ),
                    ).fetchone()
                ):
                    status, reason = "SUPPRESSED", "COOLDOWN"
                else:
                    attempts += 1
                    try:
                        if publisher is not None:
                            publisher(item)
                    except Exception:
                        status = "FAILED" if attempts >= prefs.maximum_attempts else "RETRY_PENDING"
                        reason = "LOCAL_PUBLICATION_FAILED"
                        next_at = (
                            None
                            if status == "FAILED"
                            else timestamp(
                                clock + timedelta(seconds=min(3600, 30 * 2 ** (attempts - 1)))
                            )
                        )
                connection.execute(
                    "UPDATE alerts SET delivery=?,attempts=?,next_attempt=?,delivered_at=?,"
                    "delivery_reason=? WHERE id=?",
                    (
                        status,
                        attempts,
                        next_at,
                        at if status == "DELIVERED" else None,
                        reason,
                        row["id"],
                    ),
                )
                if (status, reason) != (row["delivery"], row["delivery_reason"]):
                    self.audit(
                        connection,
                        "DELIVERY",
                        at,
                        {"state": status, "reason": reason, "attempt": attempts},
                        row["id"],
                    )
                result[status] = result.get(status, 0) + 1
        return result

    def prune(self, *, now: datetime | None = None) -> int:
        cutoff = timestamp(
            (now or datetime.now(UTC)) - timedelta(days=self.preferences().retention_days)
        )
        with self.connection(write=True) as connection:
            rows = connection.execute(
                "SELECT id FROM alerts WHERE lifecycle='RESOLVED' "
                "AND severity IN ('INFO','WARNING') AND created_at<?",
                (cutoff,),
            ).fetchall()
            for row in rows:
                self.audit(connection, "RETAINED_TOMBSTONE", timestamp(now), {}, row[0])
                connection.execute("DELETE FROM alerts WHERE id=?", (row[0],))
            return len(rows)


def quiet(now: datetime, prefs: Preferences) -> bool:
    local = now.astimezone(ZoneInfo(prefs.timezone)).strftime("%H:%M")
    if prefs.quiet_start < prefs.quiet_end:
        return prefs.quiet_start <= local < prefs.quiet_end
    return local >= prefs.quiet_start or local < prefs.quiet_end
