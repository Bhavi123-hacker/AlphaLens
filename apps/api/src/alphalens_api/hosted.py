"""Explicit private hosting preflight; never imports credentials or starts collectors.

The hosting edge must enforce HTTPS. Forwarded headers are deliberately not a
source of identity, origin, host or transport trust inside this application.
"""

import os

from alphalens_api.auth.permissions import verify
from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings


def validate_state(settings: Settings) -> None:
    if settings.access_mode != "hosted_private":
        return
    root = settings.hosted_data_root
    if root is None:
        raise ValueError("HOSTED_PERSISTENT_STATE_REQUIRED")
    if not root.is_absolute() or any(item.is_symlink() for item in (root, *root.parents)):
        raise ValueError("HOSTED_REAL_PERSISTENT_STATE_REQUIRED")
    if not root.is_dir():
        raise ValueError("HOSTED_PERSISTENT_STATE_NOT_IMPORTED")
    verify(root)
    for name in (
        "auth_root",
        "operations_root",
        "research_data_root",
        "research_run_root",
        "research_report_root",
        "catalog_path",
        "daily_root",
        "alerts_root",
        "providers_root",
        "upstox_validation_root",
        "experimental_nse_root",
        "experimental_nse_v2_root",
        "personal_root",
    ):
        value = getattr(settings, name)
        if value is None:
            continue
        if (
            not value.is_absolute()
            or not value.resolve().is_relative_to(root.resolve())
            or any(item.is_symlink() for item in (value, *value.parents))
            or not value.exists()
        ):
            raise ValueError("HOSTED_CONFIGURED_STATE_NOT_IMPORTED_OR_OUTSIDE_PERSISTENT_ROOT")
    frontend = settings.frontend_root
    if (
        frontend is None
        or not (frontend / "index.html").is_file()
        or any(item.is_symlink() for item in (frontend, *frontend.parents))
    ):
        raise ValueError("HOSTED_COMPILED_FRONTEND_REQUIRED")
    if settings.auth_root is None:
        raise ValueError("HOSTED_OPERATOR_REQUIRED")
    # Read-only connection: never bootstrap, reset passwords, initialize or repair.
    with AuthStore(settings.auth_root).connection() as connection:
        rows = connection.execute("SELECT role,status,password_hash FROM accounts").fetchall()
    if (
        len(rows) != 1
        or rows[0]["role"] != "ADMIN"
        or rows[0]["status"] != "ACTIVE"
        or not rows[0]["password_hash"].startswith("$argon2id$")
    ):
        raise ValueError("HOSTED_EXISTING_ACTIVE_OPERATOR_REQUIRED")


def serving_address(settings: Settings) -> tuple[str, int]:
    if settings.access_mode == "loopback":
        return "127.0.0.1", settings.port
    raw_port = os.environ.get("PORT", str(settings.port))
    if not raw_port.isascii() or not raw_port.isdecimal() or not 1024 <= int(raw_port) <= 65535:
        raise ValueError("HOSTED_VALID_PORT_REQUIRED")
    if settings.hosted_bind_host is None:
        raise ValueError("HOSTED_EXPLICIT_BIND_ADDRESS_REQUIRED")
    return settings.hosted_bind_host, int(raw_port)
