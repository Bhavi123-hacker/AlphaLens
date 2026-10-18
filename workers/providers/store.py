"""Crash-safe operator selection and bounded rate reservations, never credential storage."""

import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import RATES
from alphalens_data.providers.multi_contracts import ProviderName


class ProviderStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "providers.sqlite3"

    def initialize(self) -> None:
        if self.root.exists():
            raise DataContractError("NEW_PROVIDER_STATE_LOCATION_REQUIRED")
        self.root.mkdir(parents=True)
        restrict(self.root)
        schema = Path(__file__).resolve().parents[2] / "db/providers/schema.sql"
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript("BEGIN IMMEDIATE;" + schema.read_text() + "COMMIT;")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
        if __import__("os").name != "nt":
            self.path.chmod(0o600)

    def connection(self, *, readonly: bool = False) -> sqlite3.Connection:
        verify(self.root)
        if not self.path.is_file():
            raise DataContractError("PROVIDER_STATE_NOT_INITIALIZED")
        conn = sqlite3.connect(
            self.path.resolve().as_uri() + ("?mode=ro" if readonly else "?mode=rw"),
            uri=True,
            timeout=5,
        )
        if conn.execute("SELECT version FROM schema_version").fetchall() != [(1,)]:
            conn.close()
            raise DataContractError("PROVIDER_SCHEMA_UNSUPPORTED")
        if readonly:
            conn.execute("PRAGMA query_only=ON")
        else:
            conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _quota_store(self, provider: ProviderName) -> "ProviderStore":
        """Optional protected same-account budget link; never relocate source data.

        Operator migration must preserve previous attempts before publishing a
        link. Single-hop only: invalid links fail closed instead of falling back.
        """
        pointer = self.root / "upstox-shared-quota.json"
        if provider != "upstox" or not pointer.exists():
            return self
        verify(pointer, directory=False)
        if pointer.is_symlink() or pointer.stat().st_size > 4096:
            raise DataContractError("SHARED_PROVIDER_QUOTA_LINK_INVALID")
        value = json.loads(pointer.read_bytes())
        if set(value) != {"version", "root"} or value["version"] != "provider.shared_quota.v1":
            raise DataContractError("SHARED_PROVIDER_QUOTA_LINK_INVALID")
        if not isinstance(value["root"], str):
            raise DataContractError("SHARED_PROVIDER_QUOTA_LINK_INVALID")
        target = Path(value["root"])
        if (
            not target.is_absolute()
            or target.is_symlink()
            or target.resolve() == self.root.resolve()
            or (target / pointer.name).exists()
        ):
            raise DataContractError("SHARED_PROVIDER_QUOTA_SINGLE_PROTECTED_TARGET_REQUIRED")
        verify(target)
        return ProviderStore(target)

    def select(self, provider: ProviderName, at: float) -> None:
        if not math.isfinite(at) or at <= 0:
            raise DataContractError("PROVIDER_CLOCK_INVALID")
        if provider not in RATES:
            raise DataContractError("PROVIDER_NOT_SUPPORTED")
        with closing(self.connection()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT provider FROM selection").fetchone() == (provider,):
                return
            if conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0] >= 100000:
                raise DataContractError("PROVIDER_AUDIT_RETENTION_LIMIT_ARCHIVE_REQUIRED")
            conn.execute(
                "INSERT INTO selection VALUES(1,?,0) ON CONFLICT(singleton) "
                "DO UPDATE SET provider=excluded.provider,enabled=0",
                (provider,),
            )
            conn.execute(
                "INSERT INTO audit(at,event,provider) VALUES(?,?,?)",
                (at, "PROVIDER_SELECTED_ACQUISITION_DISABLED", provider),
            )

    def status(self, at: float) -> dict[str, Any]:
        with closing(self.connection(readonly=True)) as conn:
            selected = conn.execute("SELECT provider FROM selection").fetchone()
            pending = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE outcome='PENDING'"
            ).fetchone()[0]
            counts = dict(
                conn.execute(
                    "SELECT provider,COUNT(*) FROM attempts WHERE reserved_at>? GROUP BY provider",
                    (at - 86400,),
                ).fetchall()
            )
        shared = self._quota_store("upstox")
        if shared is not self:
            with closing(shared.connection(readonly=True)) as conn:
                counts["upstox"] = conn.execute(
                    "SELECT COUNT(*) FROM attempts WHERE provider='upstox' AND reserved_at>?",
                    (at - 86400,),
                ).fetchone()[0]
                pending = conn.execute(
                    "SELECT COUNT(*) FROM attempts WHERE provider='upstox' AND outcome='PENDING'"
                ).fetchone()[0]
            with closing(self.connection(readonly=True)) as conn:
                pending += conn.execute(
                    "SELECT COUNT(*) FROM attempts WHERE provider!='upstox' AND outcome='PENDING'"
                ).fetchone()[0]
        return {
            "selected_provider": selected[0] if selected else None,
            "collection_enabled": False,
            "pending_attempts": pending,
            "local_rolling_24h_attempts": counts,
            "provider_remaining_allowance": None,
            "schema_version": 1,
            "upstox_budget_shared": shared is not self,
        }

    def reserve(self, provider: ProviderName, request_id: str, attempt: int, at: float) -> bool:
        shared = self._quota_store(provider)
        if shared is not self:
            return shared.reserve(provider, request_id, attempt, at)
        if not math.isfinite(at) or at <= 0:
            raise DataContractError("PROVIDER_CLOCK_INVALID")
        if (
            provider not in RATES
            or len(request_id) != 64
            or any(c not in "0123456789abcdef" for c in request_id)
        ):
            raise DataContractError("PROVIDER_REQUEST_ID_INVALID")
        if not 1 <= attempt <= 3:
            raise DataContractError("BOUNDED_PROVIDER_RETRY_EXCEEDED")
        with closing(self.connection()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM attempts WHERE provider=? AND request_id=? AND attempt=?",
                (provider, request_id, attempt),
            ).fetchone():
                return False
            count = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            if count >= 100000:
                raise DataContractError("PROVIDER_STATE_RETENTION_LIMIT_ARCHIVE_REQUIRED")
            latest = conn.execute(
                "SELECT MAX(reserved_at),MAX(retry_at) FROM attempts WHERE provider=?", (provider,)
            ).fetchone()
            if (latest[0] is not None and at < latest[0]) or (
                latest[1] is not None and at < latest[1]
            ):
                raise DataContractError("PROVIDER_CLOCK_OR_BACKOFF_GUARD")
            for name, seconds in {
                "second": 1,
                "minute": 60,
                "half_hour": 1800,
                "hour": 3600,
                "day": 86400,
            }.items():
                limit = RATES[provider].get(name)
                if (
                    limit is not None
                    and conn.execute(
                        "SELECT COUNT(*) FROM attempts WHERE provider=? AND reserved_at>?",
                        (provider, at - seconds),
                    ).fetchone()[0]
                    >= limit
                ):
                    raise DataContractError("PROVIDER_QUOTA_EXHAUSTED")
            # Failure retries also consume quota and must follow a previous finished attempt.
            if attempt > 1:
                prior = conn.execute(
                    "SELECT outcome FROM attempts WHERE provider=? AND request_id=? AND attempt=?",
                    (provider, request_id, attempt - 1),
                ).fetchone()
                if not prior or prior[0] not in {"FAILED", "RATE_LIMITED"}:
                    raise DataContractError("PROVIDER_RETRY_NOT_ELIGIBLE")
            conn.execute(
                "INSERT INTO attempts VALUES(?,?,?,?, 'PENDING',NULL)",
                (provider, request_id, attempt, at),
            )
        return True

    def finish(
        self,
        provider: ProviderName,
        request_id: str,
        attempt: int,
        at: float,
        status: int,
        retry_after_seconds: int | None = None,
    ) -> None:
        shared = self._quota_store(provider)
        if shared is not self:
            shared.finish(provider, request_id, attempt, at, status, retry_after_seconds)
            return
        if not math.isfinite(at) or at <= 0 or not 1 <= attempt <= 3:
            raise DataContractError("PROVIDER_ATTEMPT_CLOCK_INVALID")
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise DataContractError("PROVIDER_RETRY_AFTER_INVALID")
        outcome = (
            "SUCCEEDED"
            if status == 200
            else "RATE_LIMITED"
            if status == 429
            else ("AUTH_REJECTED" if status in {401, 403} else "FAILED")
        )
        delay = max(2**attempt, retry_after_seconds or 0)
        retry_at = at + delay if outcome in {"FAILED", "RATE_LIMITED"} else None
        with closing(self.connection()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            reserved = conn.execute(
                "SELECT reserved_at FROM attempts WHERE provider=? AND request_id=? AND attempt=?",
                (provider, request_id, attempt),
            ).fetchone()
            if not reserved or at < reserved[0]:
                raise DataContractError("PROVIDER_ATTEMPT_CLOCK_INVALID")
            changed = conn.execute(
                "UPDATE attempts SET outcome=?,retry_at=? WHERE provider=? "
                "AND request_id=? AND attempt=? AND outcome='PENDING'",
                (outcome, retry_at, provider, request_id, attempt),
            ).rowcount
            if changed != 1:
                raise DataContractError("PROVIDER_ATTEMPT_STATE_INVALID")
