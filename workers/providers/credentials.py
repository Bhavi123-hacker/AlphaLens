"""Operator-only future Analytics Token import. No authentication or network activation."""

import getpass
import hmac
from typing import Any

from alphalens_api.credentials import credential_module

TARGET = "AlphaLens/UpstoxReadOnlyAnalytics"


def import_analytics() -> dict[str, Any]:
    # getpass prompts on the local console; no token argument, environment or URL.
    value = getpass.getpass("Read-only Upstox Analytics Token (hidden): ").strip()
    if not 20 <= len(value) <= 2048 or not value.isascii() or any(c.isspace() for c in value):
        raise ValueError("ANALYTICS_CREDENTIAL_INPUT_INVALID")
    module = credential_module()
    try:
        existing = module.CredRead(TARGET, module.CRED_TYPE_GENERIC)
    except Exception as exc:
        if getattr(exc, "winerror", None) != 1168:
            raise ValueError("ANALYTICS_CREDENTIAL_STORE_UNAVAILABLE") from None
        existing = None
    if existing:
        blob = existing["CredentialBlob"]
        previous = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        if not hmac.compare_digest(previous, value):
            raise ValueError("EXISTING_ANALYTICS_CREDENTIAL_PRESERVED")
    else:
        module.CredWrite(
            {
                "Type": module.CRED_TYPE_GENERIC,
                "TargetName": TARGET,
                "CredentialBlob": value,
                "Persist": module.CRED_PERSIST_LOCAL_MACHINE,
                "Comment": (
                    "AlphaLens operator-designated read-only Analytics; scope and "
                    "expiry unverified; acquisition disabled"
                ),
            },
            0,
        )
    blob = module.CredRead(TARGET, module.CRED_TYPE_GENERIC)["CredentialBlob"]
    readback = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
    if not hmac.compare_digest(readback, value):
        raise ValueError("ANALYTICS_CREDENTIAL_READBACK_FAILED")
    return {
        "storage": "WINDOWS_CURRENT_USER_CREDENTIAL_MANAGER",
        "readback_verified": True,
        "scope_evidence": "OPERATOR_DESIGNATED_NOT_SERVER_VERIFIED",
        "expiry": "NOT_VERIFIED",
        "account_status": "NOT_VERIFIED",
        "collection_enabled": False,
    }
