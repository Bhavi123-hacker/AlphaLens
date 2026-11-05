"""Secure runtime credential management using Windows DPAPI and environment isolation.

Invariants:
1. Never writes or reads plaintext credential files.
2. Uses Windows DPAPI (CryptProtectData/CryptUnprotectData) locked to the operator Windows account.
3. Supports runtime injection via environment variable ALPHALENS_QA_PASSWORD.
4. Fails safely without leaking secret content in logs or exceptions.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_AUTH_ROOT = Path("D:/al-research/p28-worktree/.local-data/completion-release/qa-auth")


def get_operator_password(auth_root: Path | None = None) -> str | None:
    """Retrieve operator password from environment or DPAPI-protected store."""
    # 1. Environment variable
    env_pass = os.environ.get("ALPHALENS_QA_PASSWORD")
    if env_pass:
        return env_pass.strip()

    # 2. Windows DPAPI encrypted store
    root = auth_root or DEFAULT_AUTH_ROOT
    dpapi_path = root / "operator-credential.dpapi"
    if dpapi_path.exists():
        try:
            import win32crypt

            encrypted = dpapi_path.read_bytes()
            decrypted = win32crypt.CryptUnprotectData(
                encrypted, None, None, None, 0
            )[1]
            return decrypted.decode("utf-8")
        except Exception:
            # Fail closed without leaking error internals
            return None

    return None


def store_operator_password_dpapi(password: str, auth_root: Path | None = None) -> bool:
    """Encrypt and store operator password using Windows DPAPI."""
    try:
        import win32crypt

        root = auth_root or DEFAULT_AUTH_ROOT
        root.mkdir(parents=True, exist_ok=True)
        dpapi_path = root / "operator-credential.dpapi"

        encrypted = win32crypt.CryptProtectData(
            password.encode("utf-8"),
            "AlphaLens Operator Secret",
            None,
            None,
            None,
            0,
        )
        dpapi_path.write_bytes(encrypted)
        return True
    except Exception:
        return False
