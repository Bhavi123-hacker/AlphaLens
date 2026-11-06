"""Private Windows credential import; never return or log secret material."""

import base64
import getpass
import hmac
import json
import re
from pathlib import Path
from typing import Any

from alphalens_api.credentials import credential_module

TARGET = "AlphaLens/UpstoxReadOnlyAnalytics"


def select_file_token(path: Path) -> str:
    """Recognize one long token among labels/legacy keys; ambiguity fails closed."""
    if not path.is_file() or path.stat().st_size > 32768:
        raise ValueError("UPSTOX_INPUT_INVALID")
    raw = path.read_bytes()
    try:
        content = raw.decode(
            "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        )
    except UnicodeError:
        raise ValueError("UPSTOX_INPUT_ENCODING_INVALID") from None
    candidates: set[str] = set(
        re.findall(r"(?<![A-Za-z0-9_.-])[A-Za-z0-9_.-]{80,2048}(?![A-Za-z0-9_.-])", content)
    )
    if len(candidates) != 1:
        raise ValueError("LOCAL_TOKEN_SELECTION_REQUIRED")
    return candidates.pop()


def token_metadata(value: str) -> dict[str, Any]:
    """Unverified JWT claims are hints, never server authentication/scope proof."""
    result: dict[str, Any] = {
        "category": "UNDETERMINED",
        "category_evidence": "NOT_SERVER_VERIFIED",
        "jwt_shaped": False,
        "expiry_claim_present": False,
    }
    parts = value.split(".")
    if len(parts) != 3:
        return result
    try:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        if not isinstance(payload, dict):
            return result
        result["jwt_shaped"] = True
        result["expiry_claim_present"] = isinstance(payload.get("exp"), (int, float))
        # Only recognize explicit category hints. Lifetime alone does not prove category.
        hints = [payload.get(k) for k in ("token_type", "type", "scope", "scopes", "purpose")]
        if any(isinstance(h, str) and "analytics" in h.lower() for h in hints):
            result["category"] = "ANALYTICS_CLAIM_UNVERIFIED"
        if isinstance(payload.get("exp"), int) and isinstance(payload.get("iat"), int):
            result["long_lived_claim"] = payload["exp"] - payload["iat"] > 300 * 86400
        return result
    except (ValueError, TypeError, UnicodeError):
        return result


def load_token() -> str:
    module = credential_module()
    try:
        blob = module.CredRead(TARGET, module.CRED_TYPE_GENERIC)["CredentialBlob"]
        value = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        if not re.fullmatch(r"[A-Za-z0-9_.-]{20,2048}", value):
            raise ValueError
        return value
    except Exception:
        raise ValueError("UPSTOX_CREDENTIAL_UNAVAILABLE") from None


def import_file(path: Path) -> dict[str, Any]:
    value = select_file_token(path)
    result = store_token(value)
    return {**result, **token_metadata(value), "plaintext_file_deleted": False}


def import_analytics() -> dict[str, Any]:
    # getpass prompts on the local console; no token argument, environment or URL.
    value = getpass.getpass("Read-only Upstox Analytics Token (hidden): ").strip()
    return store_token(value)


def store_token(value: str) -> dict[str, Any]:
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
