"""Protected local accounts and hashed opaque sessions, independent of research evidence."""

import os
import re
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from .permissions import restrict, verify

IDLE_SECONDS = 1800
ABSOLUTE_SECONDS = 28800
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


class AuthError(ValueError):
    """Safe fixed codes only; no exception from a hash/database crosses the API."""


def username(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{2,31}", value):
        raise AuthError("USERNAME_POLICY_REJECTED")
    return value.casefold()


def password(value: str, name: str) -> None:
    if (
        not 15 <= len(value) <= 128
        or len(value.encode("utf-8")) > 1024
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
        or len(set(value)) < 5
        or name.casefold() in value.casefold()
        or value.casefold() in {"passwordpassword", "123456789012345", "qwertyqwertyqwerty"}
    ):
        raise AuthError("PASSWORD_POLICY_REJECTED")


def token_hash(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode("ascii")).hexdigest()


class AuthStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / "auth.sqlite3"

    def initialize(self) -> None:
        """Explicit CLI only. Never alter an existing account or unknown schema."""
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        restrict(self.root)
        with sqlite3.connect(self.path, timeout=5) as c:
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version == 1:
                return
            if (
                version != 0
                or c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()
            ):
                raise AuthError("AUTH_SCHEMA_UNSUPPORTED")
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=FULL")
            schema = next(
                (
                    p / "db/auth/schema.sql"
                    for p in Path(__file__).resolve().parents
                    if (p / "db/auth/schema.sql").is_file()
                ),
                None,
            )
            if schema is None:
                raise AuthError("AUTH_SCHEMA_MISSING")
            c.executescript("BEGIN IMMEDIATE;\n" + schema.read_text(encoding="utf-8") + "\nCOMMIT;")
        if os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise AuthError("AUTH_NOT_INITIALIZED")
        try:
            verify(self.root)
            for path in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
                if path.exists():
                    verify(path, directory=False)
        except ValueError:
            raise AuthError("AUTH_FILESYSTEM_PERMISSION_FAILED") from None
        c = sqlite3.connect(
            f"{self.path.as_uri()}?mode={'rw' if write else 'ro'}", uri=True, timeout=5
        )
        c.row_factory = sqlite3.Row
        try:
            if c.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise AuthError("AUTH_SCHEMA_UNSUPPORTED")
            c.execute("PRAGMA foreign_keys=ON")
            if write:
                c.execute("PRAGMA synchronous=FULL")
                c.execute("BEGIN IMMEDIATE")
            yield c
            if write:
                c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    @staticmethod
    def audit(
        c: sqlite3.Connection,
        event: str,
        now: float,
        account: str | None = None,
        session: str | None = None,
    ) -> None:
        c.execute(
            "INSERT INTO audit(event_type,event_at,account_id,session_id) VALUES(?,?,?,?)",
            (event, now, account, session),
        )
        # Bounded local diagnostics; this never touches immutable research/alert evidence.
        c.execute("DELETE FROM audit WHERE sequence <= (SELECT max(sequence) FROM audit) - 100000")

    def denied(self) -> None:
        with self.connection(write=True) as c:
            self.audit(c, "UNAUTHORIZED_ACCESS", time.time())

    def bootstrap(self, name: str, secret: str) -> None:
        name = username(name)
        password(secret, name)
        with self.connection(write=True) as c:
            if c.execute("SELECT 1 FROM accounts").fetchone():
                raise AuthError("OPERATOR_ALREADY_EXISTS")
            now, account = time.time(), str(uuid4())
            c.execute(
                "INSERT INTO accounts VALUES(1,?,?,?,'ADMIN','ACTIVE',?,?)",
                (account, name, HASHER.hash(secret), now, now),
            )
            self.audit(c, "ACCOUNT_BOOTSTRAPPED", now, account)

    def login(
        self, name: str, secret: str, *, now: float | None = None
    ) -> tuple[str, dict[str, Any]]:
        at = time.time() if now is None else now
        failure = None
        result: tuple[str, dict[str, Any]] | None = None
        with self.connection(write=True) as c:
            rate = c.execute("SELECT * FROM attempts WHERE singleton=1").fetchone()
            if rate and rate["blocked_until"] > at:
                self.audit(c, "LOGIN_RATE_LIMITED", at)
                failure = "LOGIN_RATE_LIMITED"
            else:
                if rate is None or at - rate["window_start"] >= 300:
                    c.execute("INSERT OR REPLACE INTO attempts VALUES(1,?,0,0)", (at,))
                account = c.execute("SELECT * FROM accounts WHERE singleton=1").fetchone()
                matched = False
                with suppress(VerificationError):
                    matched = HASHER.verify(
                        account["password_hash"] if account else DUMMY_HASH, secret
                    )
                if (
                    not account
                    or account["username"] != name.casefold()
                    or not matched
                    or account["status"] != "ACTIVE"
                ):
                    count = c.execute("SELECT failures FROM attempts").fetchone()[0] + 1
                    c.execute(
                        "UPDATE attempts SET failures=?,blocked_until=?",
                        (count, at + 300 if count >= 5 else 0),
                    )
                    self.audit(c, "LOGIN_FAILED", at)
                    failure = "INVALID_CREDENTIALS"
                else:
                    if HASHER.check_needs_rehash(account["password_hash"]):
                        c.execute("UPDATE accounts SET password_hash=?", (HASHER.hash(secret),))
                    c.execute("UPDATE attempts SET failures=0,blocked_until=0")
                    c.execute(
                        "DELETE FROM sessions WHERE absolute_expires<? OR revoked_at IS NOT NULL",
                        (at - 86400,),
                    )
                    if (
                        c.execute(
                            "SELECT count(*) FROM sessions WHERE revoked_at IS NULL"
                        ).fetchone()[0]
                        >= 10
                    ):
                        c.execute(
                            "UPDATE sessions SET revoked_at=? WHERE session_id=(SELECT session_id "
                            "FROM sessions WHERE revoked_at IS NULL ORDER BY created_at LIMIT 1)",
                            (at,),
                        )
                    raw, session, csrf = (
                        secrets.token_urlsafe(32),
                        str(uuid4()),
                        secrets.token_urlsafe(32),
                    )
                    c.execute(
                        "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,NULL)",
                        (
                            session,
                            token_hash(raw),
                            account["account_id"],
                            csrf,
                            at,
                            at,
                            at + ABSOLUTE_SECONDS,
                        ),
                    )
                    self.audit(c, "LOGIN_SUCCEEDED", at, account["account_id"], session)
                    result = (
                        raw,
                        dict(
                            account_id=account["account_id"],
                            username=account["username"],
                            role="ADMIN",
                            session_id=session,
                            csrf_token=csrf,
                            absolute_expires=at + ABSOLUTE_SECONDS,
                            idle_seconds=IDLE_SECONDS,
                        ),
                    )
        if failure:
            raise AuthError(failure)
        if result is None:
            raise AuthError("AUTHENTICATION_REQUIRED")
        return result

    def session(self, raw: str | None, *, now: float | None = None) -> dict[str, Any]:
        if raw is None or not re.fullmatch(r"[A-Za-z0-9_-]{43}", raw):
            raise AuthError("AUTHENTICATION_REQUIRED")
        at = time.time() if now is None else now
        with self.connection(write=True) as c:
            r = c.execute(
                "SELECT s.*,a.username,a.status,a.role FROM sessions s JOIN accounts "
                "a USING(account_id) WHERE token_hash=?",
                (token_hash(raw),),
            ).fetchone()
            if (
                r is None
                or r["revoked_at"] is not None
                or r["absolute_expires"] <= at
                or r["last_seen"] + IDLE_SECONDS <= at
                or r["status"] != "ACTIVE"
                or r["role"] != "ADMIN"
            ):
                self.audit(c, "UNAUTHORIZED_ACCESS", at)
                result = None
            else:
                c.execute(
                    "UPDATE sessions SET last_seen=? WHERE session_id=?",
                    (max(at, r["last_seen"]), r["session_id"]),
                )
                result = dict(
                    account_id=r["account_id"],
                    username=r["username"],
                    role=r["role"],
                    session_id=r["session_id"],
                    csrf_token=r["csrf_secret"],
                    absolute_expires=r["absolute_expires"],
                    idle_seconds=IDLE_SECONDS,
                )
        if result is None:
            raise AuthError("AUTHENTICATION_REQUIRED")
        return result

    def revoke(
        self, account: str, session: str | None = None, *, event: str = "SESSION_REVOKED"
    ) -> None:
        with self.connection(write=True) as c:
            now = time.time()
            if session:
                row = c.execute(
                    "SELECT account_id FROM sessions WHERE session_id=?", (session,)
                ).fetchone()
                if row is None or row[0] != account:
                    raise AuthError("SESSION_NOT_FOUND")
                c.execute("UPDATE sessions SET revoked_at=? WHERE session_id=?", (now, session))
            else:
                c.execute("UPDATE sessions SET revoked_at=? WHERE account_id=?", (now, account))
            self.audit(c, event, now, account, session)

    def change_password(
        self, account: str, current: str | None, replacement: str, *, recovery: bool = False
    ) -> None:
        failure = None
        with self.connection(write=True) as c:
            row = c.execute("SELECT * FROM accounts WHERE account_id=?", (account,)).fetchone()
            if row is None:
                raise AuthError("ACCOUNT_NOT_FOUND")
            at = time.time()
            rate = c.execute("SELECT * FROM attempts WHERE singleton=1").fetchone()
            if not recovery and rate and rate["blocked_until"] > at:
                self.audit(c, "PASSWORD_RATE_LIMITED", at, account)
                failure = "LOGIN_RATE_LIMITED"
            else:
                matched = recovery
                if not recovery:
                    with suppress(VerificationError):
                        matched = HASHER.verify(row["password_hash"], current or "")
                if not matched:
                    if rate is None or at - rate["window_start"] >= 300:
                        c.execute("INSERT OR REPLACE INTO attempts VALUES(1,?,0,0)", (at,))
                    count = c.execute("SELECT failures FROM attempts").fetchone()[0] + 1
                    c.execute(
                        "UPDATE attempts SET failures=?,blocked_until=?",
                        (count, at + 300 if count >= 5 else 0),
                    )
                    self.audit(c, "PASSWORD_VERIFICATION_FAILED", at, account)
                    failure = "INVALID_CREDENTIALS"
                else:
                    password(replacement, row["username"])
                    if current is not None and current == replacement:
                        raise AuthError("PASSWORD_MUST_CHANGE")
                    c.execute(
                        "UPDATE accounts SET password_hash=?,password_changed_at=?,status='ACTIVE' "
                        "WHERE account_id=?",
                        (HASHER.hash(replacement), at, account),
                    )
                    c.execute("UPDATE sessions SET revoked_at=? WHERE account_id=?", (at, account))
                    c.execute("DELETE FROM attempts")
                    self.audit(
                        c,
                        "LOCAL_PASSWORD_RECOVERY" if recovery else "PASSWORD_CHANGED",
                        at,
                        account,
                    )
        if failure:
            raise AuthError(failure)

    def sessions(self, account: str) -> list[dict[str, Any]]:
        with self.connection() as c:
            return [
                dict(r)
                | {
                    "active": r["revoked_at"] is None
                    and r["absolute_expires"] > time.time()
                    and r["last_seen"] + IDLE_SECONDS > time.time()
                }
                for r in c.execute(
                    "SELECT session_id,created_at,last_seen,absolute_expires,revoked_at "
                    "FROM sessions WHERE account_id=? ORDER BY created_at DESC LIMIT 100",
                    (account,),
                )
            ]

    def status(self, value: str) -> None:
        if value not in {"ACTIVE", "DISABLED", "LOCKED"}:
            raise AuthError("ACCOUNT_STATUS_INVALID")
        with self.connection(write=True) as c:
            now = time.time()
            c.execute("UPDATE accounts SET status=?", (value,))
            c.execute("UPDATE sessions SET revoked_at=?", (now,))
            self.audit(c, "ACCOUNT_STATUS_CHANGED", now)

    def diagnostics(self) -> dict[str, Any]:
        with self.connection() as c:
            a = c.execute(
                "SELECT account_id,username,role,status,created_at,password_changed_at "
                "FROM accounts"
            ).fetchone()
            events = [
                dict(r)
                for r in c.execute(
                    "SELECT event_type,event_at FROM audit ORDER BY sequence DESC LIMIT 50"
                )
            ]
        return dict(account=dict(a) if a else None, audit=events, scope="SINGLE_OPERATOR_WORKSPACE")
