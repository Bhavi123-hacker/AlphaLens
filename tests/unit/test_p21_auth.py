"""TEST_ONLY accounts in isolated stores; no credentials belong to application users."""

import secrets
import sqlite3
from pathlib import Path

import pytest
from argon2 import PasswordHasher

from alphalens_api.auth.store import ABSOLUTE_SECONDS, IDLE_SECONDS, AuthError, AuthStore


@pytest.fixture
def account(tmp_path: Path) -> tuple[AuthStore, str]:
    store = AuthStore(tmp_path / "TEST_ONLY_auth")
    store.initialize()
    secret = secrets.token_urlsafe(24)
    store.bootstrap("test_operator", secret)
    return store, secret


def test_bootstrap_hashes_and_never_overwrites(account: tuple[AuthStore, str]) -> None:
    store, secret = account
    with store.connection() as c:
        original = c.execute("SELECT password_hash FROM accounts").fetchone()[0]
    assert original.startswith("$argon2id$")
    assert PasswordHasher().verify(original, secret)
    with pytest.raises(AuthError, match="ALREADY_EXISTS"):
        store.bootstrap("other_test_user", secrets.token_urlsafe(24))
    store.initialize()
    with store.connection() as c:
        assert c.execute("SELECT password_hash FROM accounts").fetchone()[0] == original


@pytest.mark.parametrize(
    "value", ["short", "a" * 20, "123456789012345", "test_operator" * 2, "abc\x00" * 5]
)
def test_password_policy_rejects_weak_values(account: tuple[AuthStore, str], value: str) -> None:
    store, _ = account
    with pytest.raises(AuthError, match="POLICY"):
        store.change_password(
            store.diagnostics()["account"]["account_id"], None, value, recovery=True
        )


def test_opaque_sessions_are_hashed_and_rotate(account: tuple[AuthStore, str]) -> None:
    store, secret = account
    first, _ = store.login("test_operator", secret, now=1000)
    second, _ = store.login("test_operator", secret, now=1001)
    assert first != second
    with store.connection() as c:
        rows = c.execute("SELECT token_hash FROM sessions").fetchall()
    assert all(len(r[0]) == 64 and r[0] not in {first, second} for r in rows)
    assert store.session(first, now=1002)["role"] == "ADMIN"


@pytest.mark.parametrize("kind", ["idle", "absolute", "malformed", "unknown"])
def test_expiration_and_invalid_sessions(account: tuple[AuthStore, str], kind: str) -> None:
    store, secret = account
    raw, _ = store.login("test_operator", secret, now=1000)
    if kind == "absolute":
        with store.connection(write=True) as c:
            c.execute("UPDATE sessions SET last_seen=?", (1000 + ABSOLUTE_SECONDS - 1,))
        at = 1000 + ABSOLUTE_SECONDS
    else:
        at = 1000 + IDLE_SECONDS if kind == "idle" else 1001
        raw = (
            "invalid"
            if kind == "malformed"
            else secrets.token_urlsafe(32)
            if kind == "unknown"
            else raw
        )
    with pytest.raises(AuthError, match="AUTHENTICATION_REQUIRED"):
        store.session(raw, now=at)


def test_login_rate_limit_survives_restart(account: tuple[AuthStore, str]) -> None:
    store, secret = account
    for offset in range(5):
        with pytest.raises(AuthError, match="INVALID_CREDENTIALS"):
            store.login("unknown_test_user", secrets.token_urlsafe(20), now=1000 + offset)
    restored = AuthStore(store.root)
    with pytest.raises(AuthError, match="RATE_LIMITED"):
        restored.login("test_operator", secret, now=1005)
    assert restored.login("test_operator", secret, now=1400)[1]["role"] == "ADMIN"


@pytest.mark.parametrize("status", ["DISABLED", "LOCKED"])
def test_account_status_revokes_access(account: tuple[AuthStore, str], status: str) -> None:
    store, secret = account
    raw, _ = store.login("test_operator", secret)
    store.status(status)
    with pytest.raises(AuthError, match="AUTHENTICATION_REQUIRED"):
        store.session(raw)
    with pytest.raises(AuthError, match="INVALID_CREDENTIALS"):
        store.login("test_operator", secret)


def test_password_change_recovery_and_revocation(account: tuple[AuthStore, str]) -> None:
    store, secret = account
    raw, identity = store.login("test_operator", secret)
    replacement = secrets.token_urlsafe(24)
    with pytest.raises(AuthError, match="INVALID_CREDENTIALS"):
        store.change_password(identity["account_id"], secrets.token_urlsafe(24), replacement)
    store.change_password(identity["account_id"], secret, replacement)
    with pytest.raises(AuthError):
        store.session(raw)
    with pytest.raises(AuthError):
        store.login("test_operator", secret)
    raw, identity = store.login("test_operator", replacement)
    store.revoke(identity["account_id"], identity["session_id"])
    with pytest.raises(AuthError):
        store.session(raw)
    store.change_password(identity["account_id"], None, secrets.token_urlsafe(24), recovery=True)
    events = {x["event_type"] for x in store.diagnostics()["audit"]}
    assert {"PASSWORD_CHANGED", "LOCAL_PASSWORD_RECOVERY", "SESSION_REVOKED"} <= events


def test_no_second_owner_or_unknown_schema(account: tuple[AuthStore, str]) -> None:
    store, _ = account
    with pytest.raises(AuthError, match="NOT_FOUND"):
        store.revoke("not_an_owner", "unknown_session")
    with store.connection(write=True) as c:
        c.execute("PRAGMA user_version=900")
    with pytest.raises(AuthError, match="SCHEMA_UNSUPPORTED"):
        store.initialize()


def test_uninitialized_store_never_creates_database(tmp_path: Path) -> None:
    store = AuthStore(tmp_path / "absent")
    with pytest.raises(AuthError, match="NOT_INITIALIZED"):
        store.login("test_operator", secrets.token_urlsafe(24))
    assert not store.root.exists()


def test_concurrent_account_bootstrap_is_unique(account: tuple[AuthStore, str]) -> None:
    from concurrent.futures import ThreadPoolExecutor

    store, _ = account

    def attempt(_: int) -> str:
        try:
            store.bootstrap("other_test_user", secrets.token_urlsafe(24))
        except AuthError:
            return "REFUSED"
        return "UNEXPECTED"

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert set(pool.map(attempt, range(4))) == {"REFUSED"}
    with store.connection() as c:
        assert c.execute("SELECT count(*) FROM accounts").fetchone()[0] == 1


def test_cli_hidden_prompt_recovery_and_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from alphalens_api.auth.cli import main

    root = tmp_path / "TEST_ONLY_cli"
    secret = secrets.token_urlsafe(24)
    monkeypatch.setattr("getpass.getpass", lambda _: secret)
    assert main(["--root", str(root), "bootstrap", "--username", "test_operator"]) == 0
    assert secret not in capsys.readouterr().out
    monkeypatch.setattr(
        "getpass.getpass", lambda _: pytest.fail("Existing account must not prompt")
    )
    assert main(["--root", str(root), "bootstrap", "--username", "test_operator"]) == 2
    assert main(["--root", str(root), "diagnostics"]) == 0
    assert "password_hash" not in capsys.readouterr().out
    assert main(["--root", str(root), "sessions"]) == 0
    assert main(["--root", str(root), "revoke"]) == 0
    assert main(["--root", str(root), "cleanup"]) == 0


def test_transaction_rollback_retains_account(account: tuple[AuthStore, str]) -> None:
    store, secret = account
    with pytest.raises(sqlite3.IntegrityError), store.connection(write=True) as c:
        c.execute("UPDATE accounts SET role='VIEWER'")
    assert store.login("test_operator", secret)[1]["role"] == "ADMIN"


def test_password_reauthentication_is_audited_and_rate_limited(
    account: tuple[AuthStore, str],
) -> None:
    store, secret = account
    _, identity = store.login("test_operator", secret)
    for _ in range(5):
        with pytest.raises(AuthError, match="INVALID_CREDENTIALS"):
            store.change_password(
                identity["account_id"], secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            )
    with pytest.raises(AuthError, match="RATE_LIMITED"):
        store.change_password(identity["account_id"], secret, secrets.token_urlsafe(24))
    assert {"PASSWORD_VERIFICATION_FAILED", "PASSWORD_RATE_LIMITED"} <= {
        x["event_type"] for x in store.diagnostics()["audit"]
    }
    store.change_password(identity["account_id"], None, secrets.token_urlsafe(24), recovery=True)


def test_local_permissions_fail_closed(account: tuple[AuthStore, str]) -> None:
    import os

    store, secret = account
    if os.name == "nt":
        import importlib

        security = importlib.import_module("win32security")
        descriptor = security.GetNamedSecurityInfo(
            str(store.path), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION
        )
        acl = descriptor.GetSecurityDescriptorDacl()
        acl.AddAccessAllowedAce(
            security.ACL_REVISION, 0x1F01FF, security.CreateWellKnownSid(security.WinWorldSid, None)
        )
        security.SetNamedSecurityInfo(
            str(store.path),
            security.SE_FILE_OBJECT,
            security.DACL_SECURITY_INFORMATION,
            None,
            None,
            acl,
            None,
        )
    else:
        store.path.chmod(0o644)
    with pytest.raises(AuthError, match="FILESYSTEM_PERMISSION_FAILED"):
        store.login("test_operator", secret)


def test_concurrent_sessions_and_monotonic_activity(account: tuple[AuthStore, str]) -> None:
    from concurrent.futures import ThreadPoolExecutor

    store, secret = account
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(
            pool.map(lambda _: store.login("test_operator", secret, now=1000)[0], range(4))
        )
    assert len(set(values)) == 4
    store.session(values[0], now=1050)
    store.session(values[0], now=1020)
    with store.connection() as c:
        assert c.execute("SELECT max(last_seen) FROM sessions").fetchone()[0] == 1050


def test_unicode_password_change_and_salted_hashes(account: tuple[AuthStore, str]) -> None:
    store, secret = account
    original = store.diagnostics()["account"]["account_id"]
    replacement = secrets.token_urlsafe(24) + chr(945)
    store.change_password(original, secret, replacement)
    assert store.login("test_operator", replacement)[1]["account_id"] == original
    assert PasswordHasher().hash(replacement) != PasswordHasher().hash(replacement)


def test_cli_password_change_and_explicit_recovery(
    account: tuple[AuthStore, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphalens_api.auth.cli import main

    store, secret = account
    replacement = secrets.token_urlsafe(24)
    answers = iter([secret, replacement, replacement])
    monkeypatch.setattr("getpass.getpass", lambda _: next(answers))
    assert main(["--root", str(store.root), "change-password"]) == 0
    assert store.login("test_operator", replacement)[1]["role"] == "ADMIN"
    monkeypatch.setattr("builtins.input", lambda _: "CANCEL")
    assert main(["--root", str(store.root), "reset-password"]) == 2
    monkeypatch.setattr("builtins.input", lambda _: "RESET")
    answers = iter([secret, secret])
    assert main(["--root", str(store.root), "reset-password"]) == 0
    assert store.login("test_operator", secret)[1]["role"] == "ADMIN"


def test_cli_refuses_echoed_password_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import getpass
    import warnings

    from alphalens_api.auth.cli import main

    def echoed(_: str) -> str:
        warnings.warn("TEST_ONLY terminal absent", getpass.GetPassWarning, stacklevel=2)
        return secrets.token_urlsafe(24)

    monkeypatch.setattr("getpass.getpass", echoed)
    root = tmp_path / "TEST_ONLY_no_terminal"
    assert main(["--root", str(root), "bootstrap", "--username", "test_operator"]) == 2
    assert AuthStore(root).diagnostics()["account"] is None
