"""Protected single-operator sidecar. Atomic, exact, immutable P15 ledger events."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, time
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from alphalens_api.auth.permissions import restrict, verify
from alphalens_portfolio.accounting import append, reconstruct
from alphalens_portfolio.contracts import Ledger, Portfolio, Transaction

from .contracts import ManualEntry, Profile, amount

IST = ZoneInfo("Asia/Kolkata")


def encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class PersonalStore:
    def __init__(self, root: Path, owner: str) -> None:
        self.root, self.owner = root, owner
        self.path = root / "personal.sqlite3"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        restrict(self.root)
        if self.path.exists():
            with self.connection():
                return
        schema = Path(__file__).resolve().parents[2] / "db/personal-workspace.sql"
        with sqlite3.connect(self.path) as conn:
            conn.executescript(schema.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO metadata VALUES ('owner',?)", (self.owner,))
            conn.execute("INSERT INTO metadata VALUES ('schema','p32.personal.v1')")
        if self.path.stat().st_size == 0:
            raise ValueError("PERSONAL_INITIALIZATION_FAILED")
        if os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        verify(self.root)
        verify(self.path, directory=False)
        conn = sqlite3.connect(
            self.path.resolve().as_uri() + ("?mode=rw" if write else "?mode=ro"),
            uri=True,
            timeout=5,
        )
        conn.row_factory = sqlite3.Row
        try:
            owner = conn.execute("SELECT value FROM metadata WHERE key='owner'").fetchone()
            if not owner or owner[0] != self.owner:
                raise ValueError("PERSONAL_OWNER_MISMATCH")
            conn.execute("PRAGMA foreign_keys=ON")
            if write:
                conn.execute("BEGIN IMMEDIATE")
            else:
                conn.execute("PRAGMA query_only=ON")
            yield conn
            if write:
                conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def listing(self, kind: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return [
                self.public(row)
                for row in conn.execute(
                    "SELECT * FROM records WHERE owner=? AND kind=? "
                    "ORDER BY updated_at DESC,id LIMIT 201",
                    (self.owner, kind),
                )
            ]

    @staticmethod
    def public(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "revision": row["revision"],
            "updated_at": row["updated_at"],
            "value": json.loads(row["body"]),
        }

    def get(self, kind: str, identity: str) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM records WHERE owner=? AND kind=? AND id=?",
                (self.owner, kind, identity),
            ).fetchone()
            if not row:
                raise ValueError("PERSONAL_RECORD_NOT_FOUND")
            return self.public(row)

    def save(
        self, kind: str, identity: str, value: dict[str, Any], revision: int
    ) -> dict[str, Any]:
        with self.connection(write=True) as conn:
            self.write(conn, kind, identity, value, revision)
        return self.get(kind, identity)

    def write(
        self,
        conn: sqlite3.Connection,
        kind: str,
        identity: str,
        value: dict[str, Any],
        revision: int,
    ) -> None:
        existing = conn.execute(
            "SELECT revision FROM records WHERE owner=? AND kind=? AND id=?",
            (self.owner, kind, identity),
        ).fetchone()
        if (existing[0] if existing else 0) != revision:
            raise ValueError("PERSONAL_REVISION_CONFLICT")
        if (
            not existing
            and conn.execute(
                "SELECT count(*) FROM records WHERE owner=? AND kind=?", (self.owner, kind)
            ).fetchone()[0]
            >= 200
        ):
            raise ValueError("PERSONAL_RECORD_LIMIT")
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO records VALUES(?,?,?,?,?,?) ON CONFLICT(owner,kind,id) "
            "DO UPDATE SET body=excluded.body,revision=excluded.revision,"
            "updated_at=excluded.updated_at",
            (self.owner, kind, identity, encode(value), revision + 1, now),
        )
        conn.execute(
            "INSERT INTO audit(owner,operation,record_id,at) VALUES(?,?,?,?)",
            (self.owner, kind.upper() + "_SAVED", identity, now),
        )
        if kind == "recent":
            conn.execute(
                "DELETE FROM records WHERE owner=? AND kind='recent' AND id NOT IN "
                "(SELECT id FROM records WHERE owner=? AND kind='recent' "
                "ORDER BY updated_at DESC,id LIMIT 30)",
                (self.owner, self.owner),
            )

    def remove(self, kind: str, identity: str, revision: int) -> None:
        if kind not in {"watchlists", "rules", "journal"}:
            raise ValueError("IMMUTABLE_PORTFOLIO_RECORD")
        with self.connection(write=True) as conn:
            result = conn.execute(
                "DELETE FROM records WHERE owner=? AND kind=? AND id=? AND revision=?",
                (self.owner, kind, identity, revision),
            )
            if result.rowcount != 1:
                raise ValueError("PERSONAL_REVISION_CONFLICT")

    def profile(self) -> dict[str, Any]:
        records = self.listing("profile")
        return (
            records[0]
            if records
            else {
                "id": "default",
                "revision": 0,
                "updated_at": None,
                "value": Profile().model_dump(),
            }
        )

    def create_portfolio(self, name: str) -> dict[str, Any]:
        identity = uuid4().hex
        ledger = Ledger(
            portfolio=Portfolio(
                portfolio_id=identity,
                portfolio_name=name,
                portfolio_type="USER_RECORDED",
                classification="USER_RECORDED",
                created_at=datetime.now(UTC),
            )
        )
        return self.save(
            "portfolios",
            identity,
            {
                "ledger": ledger.model_dump(mode="json"),
                "manual_details": {},
                "cash_history_complete": False,
            },
            0,
        )

    def record(
        self, identity: str, entry: ManualEntry, verified: dict[str, Any] | None
    ) -> dict[str, Any]:
        return self.record_many(identity, [(entry, verified)])

    def record_many(
        self,
        identity: str,
        entries: list[tuple[ManualEntry, dict[str, Any] | None]],
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        if not 1 <= len(entries) <= 100:
            raise ValueError("MANUAL_IMPORT_ROW_LIMIT")
        with self.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM records WHERE owner=? AND kind='portfolios' AND id=?",
                (self.owner, identity),
            ).fetchone()
            if not row:
                raise ValueError("PERSONAL_RECORD_NOT_FOUND")
            if expected_revision is not None and row["revision"] != expected_revision:
                raise ValueError("PERSONAL_REVISION_CONFLICT")
            original = json.loads(row["body"])
            value = original
            at = datetime.now(UTC)
            for entry, metadata in entries:
                value = apply_entry(value, identity, entry, metadata, at)
            if value != original:
                self.write(conn, "portfolios", identity, value, row["revision"])
        return self.get("portfolios", identity)


def apply_entry(
    value: dict[str, Any],
    identity: str,
    entry: ManualEntry,
    verified: dict[str, Any] | None,
    at: datetime | None = None,
) -> dict[str, Any]:
    """Pure validation/reconstruction used identically for preview and committed records."""
    value = json.loads(encode(value))
    request_hash = sha256(encode(entry.model_dump(mode="json")).encode()).hexdigest()
    details = value["manual_details"]
    if entry.request_id in details:
        if details[entry.request_id]["request_hash"] != request_hash:
            raise ValueError("IMMUTABLE_MANUAL_EVENT_CONFLICT")
        return value
    ledger = Ledger.model_validate(value["ledger"])
    if len(ledger.transactions) >= 500:
        raise ValueError("MANUAL_LEDGER_EVENT_LIMIT")
    now = at or datetime.now(UTC)
    if ledger.transactions and now < max(t.recorded_at for t in ledger.transactions):
        raise ValueError("MANUAL_CLOCK_BEHIND_LAST_RECORD")
    if entry.session > now.astimezone(IST).date():
        raise ValueError("FUTURE_MANUAL_EVENT_REJECTED")
    position_event = entry.kind in {"OPENING_POSITION", "BUY", "SELL"}
    if position_event:
        if not verified or verified["provider_key"] != entry.instrument_key:
            raise ValueError("VERIFIED_MANUAL_IDENTITY_REQUIRED")
        if amount(entry.quantity, zero=False) != int(amount(entry.quantity)):
            raise ValueError("NSE_WHOLE_SHARE_QUANTITY_REQUIRED")
        amount(entry.price, zero=False)
    elif entry.instrument_key or any(amount(v) for v in (entry.quantity, entry.price, entry.fees)):
        raise ValueError("CASH_EVENT_FIELDS_INVALID")
    if not entry.fees_known and amount(entry.fees):
        raise ValueError("KNOWN_FEES_CONFIRMATION_REQUIRED")
    opening = entry.kind == "OPENING_POSITION"
    transaction = Transaction(
        # Native Windows clocks can repeat an instant. P15 sorts ties by
        # transaction_id, so sequence IDs preserve recorded event order.
        transaction_id=f"p32:{identity}:{len(ledger.transactions) + 1:06d}",
        portfolio_id=identity,
        kind=entry.kind,
        security_id="upstox:" + entry.instrument_key
        if position_event and entry.instrument_key
        else None,
        symbol=verified["symbol"] if position_event and verified else None,
        session=entry.session,
        effective_at=datetime.combine(entry.session, time.min, IST),
        recorded_at=now,
        quantity=Fraction(entry.quantity),
        price=Fraction(0) if opening else Fraction(entry.price),
        fees=Fraction(0) if opening else Fraction(entry.fees),
        cash_amount=Fraction(entry.cash_amount),
        declared_cost_basis=Fraction(entry.quantity) * Fraction(entry.price) + Fraction(entry.fees)
        if opening
        else None,
        source="LOCAL_OPERATOR_MANUAL_RECORD",
        classification="USER_RECORDED",
        notes=entry.notes,
    )
    candidate = append(ledger, transaction)
    reconstruct(candidate, now.astimezone(IST).date(), now)
    details[entry.request_id] = {
        "transaction_id": transaction.transaction_id,
        "effective_time_basis": "USER_DATE_ONLY_MIDNIGHT_SORTING_NOT_VERIFIED_EXECUTION_TIME",
        "request_hash": request_hash,
        "entered": entry.model_dump(mode="json"),
        "identity": verified,
        "cash_effect": "UNKNOWN_ACQUISITION_FUNDING" if opening else "RECORDED_FLOW",
    }
    value["ledger"] = candidate.model_dump(mode="json")
    return value
