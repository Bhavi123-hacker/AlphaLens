"""Explicit local operator setup/recovery; passwords are prompted without echo."""

import argparse
import getpass
import json
import sqlite3
import warnings
from pathlib import Path

from .store import AuthError, AuthStore


def prompt() -> str:
    # Reject getpass's echoed fallback on redirected/noninteractive input.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        value = getpass.getpass("Password (15-128 characters): ")
        repeat = getpass.getpass("Confirm password: ")
    if value != repeat:
        raise AuthError("PASSWORD_CONFIRMATION_FAILED")
    return value


def current_password() -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass("Current password: ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("--username", required=True)
    commands.add_parser("diagnostics")
    commands.add_parser("sessions")
    commands.add_parser("cleanup")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--session-id")
    status = commands.add_parser("status")
    status.add_argument("value", choices=["ACTIVE", "DISABLED", "LOCKED"])
    commands.add_parser("reset-password")
    commands.add_parser("change-password")
    args = parser.parse_args(argv)
    store = AuthStore(args.root)
    try:
        if args.command == "bootstrap":
            store.initialize()
            if store.diagnostics()["account"] is not None:
                raise AuthError("OPERATOR_ALREADY_EXISTS")
            store.bootstrap(args.username, prompt())
            result: object = {"status": "OPERATOR_INITIALIZED"}
        else:
            account = store.diagnostics()["account"]
            if account is None:
                raise AuthError("ACCOUNT_NOT_FOUND")
            if args.command == "diagnostics":
                result = store.diagnostics()
            elif args.command == "sessions":
                result = store.sessions(account["account_id"])
            elif args.command == "revoke":
                store.revoke(account["account_id"], args.session_id)
                result = {"status": "SESSIONS_REVOKED"}
            elif args.command == "status":
                store.status(args.value)
                result = {"status": args.value}
            elif args.command in {"reset-password", "change-password"}:
                recovery = args.command == "reset-password"
                if recovery and (
                    input("Local recovery revokes ALL sessions. Type RESET to continue: ")
                    != "RESET"
                ):
                    raise AuthError("RECOVERY_CANCELLED")
                current = None if recovery else current_password()
                store.change_password(account["account_id"], current, prompt(), recovery=recovery)
                result = {"status": "PASSWORD_UPDATED_ALL_SESSIONS_REVOKED"}
            else:
                import time

                with store.connection(write=True) as c:
                    deleted = c.execute(
                        "DELETE FROM sessions WHERE revoked_at IS NOT NULL "
                        "OR absolute_expires<=? OR last_seen<=?",
                        (time.time(), time.time() - 1800),
                    ).rowcount
                result = {"expired_or_revoked_sessions_removed": deleted}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (AuthError, sqlite3.Error, OSError, ValueError, EOFError, getpass.GetPassWarning):
        print(
            json.dumps(
                {
                    "error_code": "LOCAL_SECURITY_OPERATION_REJECTED",
                    "message": "Check local setup, account status and password policy.",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
