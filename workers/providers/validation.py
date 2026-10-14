"""Read-only, strict public projection of private sanitized live-validation evidence."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import verify

STATES = {
    "ACCEPTED",
    "AUTH_REJECTED",
    "PERMISSION_OR_SEGMENT_REJECTED",
    "RATE_LIMITED",
    "NETWORK_UNAVAILABLE",
    "NETWORK_TIMEOUT",
    "DNS_UNAVAILABLE",
    "TLS_REJECTED",
    "PROVIDER_OUTAGE",
    "REQUEST_REJECTED",
    "REDIRECT_REJECTED",
    "RESPONSE_LIMIT",
    "UNSAFE_PROVIDER_ECHO_REJECTED",
    "QUOTE_TIME_REJECTED",
    "VALIDATED_SNAPSHOT",
    "QUOTE_IDENTITY_OR_SCHEMA_REJECTED",
    "IDENTITY_REJECTED",
}


def status(root: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "state": "NOT_VERIFIED",
        "authentication": "NOT_VERIFIED",
        "credential_readback": False,
        "credential_kind": "UNVERIFIED",
        "nse_identity_verified": False,
        "latest_provider_daily_session": None,
        "valid_candles": 0,
        "current_master_candidates": None,
        "verified_at": None,
        "requests": [],
        "data_retained": False,
        "ongoing_collection": "DISABLED",
        "current_forecasts": "UNAVAILABLE",
        "blockers": [
            "RETENTION_AUTOMATION_PRIVATE_ANALYSIS_TERMS_NOT_VERIFIED",
            "SOURCE_ADJUSTMENT_ACTIONS_AND_PUBLICATION_NOT_VERIFIED",
            "INDEPENDENT_MODEL_AND_POLICY_ACCEPTANCE_NOT_PASSED",
        ],
    }
    if root is None:
        return result
    try:
        verify(root)
        files = sorted(root.glob("validation-*.json"))
        if not files or len(files) > 1000 or files[-1].stat().st_size > 16384:
            return result
        data = json.loads(files[-1].read_bytes())
        if data.get("schema") != "p30.upstox.validation.v1":
            return result
        at = datetime.fromisoformat(data["verified_at"])
        if at.tzinfo is None:
            return result
        auth = data.get("authentication")
        if auth not in STATES:
            return result
        result.update(
            {
                "state": "VALIDATION_RECEIPT_AVAILABLE",
                "authentication": auth,
                "credential_readback": data.get("credential_readback") is True,
                "nse_identity_verified": data.get("reliance_identity_verified") is True,
                "verified_at": at.isoformat(),
            }
        )
        if data.get("category") == "ANALYTICS_OPERATOR_CONFIRMED":
            result["credential_kind"] = "ANALYTICS_OPERATOR_CONFIRMED_NOT_SERVER_SCOPE_PROOF"
        for source, target in (
            ("valid_candles", "valid_candles"),
            ("nse_eq_type_eq_candidates", "current_master_candidates"),
        ):
            value = data.get(source)
            if type(value) is int and 0 <= value <= 20000:
                result[target] = value
        latest = data.get("latest_provider_daily_session")
        if latest:
            result["latest_provider_daily_session"] = date.fromisoformat(latest).isoformat()
        for entry in data.get("requests", [])[:10]:
            op, state, code = entry.get("operation"), entry.get("state"), entry.get("http_status")
            if op in {"instruments", "candles", "quote"} and state in STATES and type(code) is int:
                result["requests"].append({"operation": op, "state": state, "http_status": code})
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        result["state"] = "VALIDATION_RECEIPT_UNAVAILABLE"
        return result
