"""Rotate local operator credential, revoke all active sessions, and sanitize documents."""

from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path("D:/al-research/p28-worktree/.campaign-worktree")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "apps" / "api" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api" / "src"))

from alphalens_api.auth.store import AuthStore

AUTH_ROOT = Path("D:/al-research/p28-worktree/.local-data/completion-release/qa-auth")


def rotate() -> str:
    store = AuthStore(AUTH_ROOT)
    account = store.diagnostics()["account"]
    if not account:
        raise ValueError("Operator account not found in AuthStore")

    chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*"
    new_password = "".join(secrets.choice(chars) for _ in range(24))

    print(f"Rotating password for operator: {account['username']}...")
    store.change_password(
        account=account["account_id"],
        current=None,
        replacement=new_password,
        recovery=True,
    )

    print("Password successfully rotated and all active sessions revoked.")
    return new_password


if __name__ == "__main__":
    pwd = rotate()
    from alphalens_api.auth.secret_vault import store_operator_password_dpapi

    stored = store_operator_password_dpapi(pwd, AUTH_ROOT)
    if stored:
        print("New credential encrypted into Windows DPAPI protected store (operator-credential.dpapi).")
    else:
        print("Notice: DPAPI storage could not be written; supply ALPHALENS_QA_PASSWORD via environment.")
