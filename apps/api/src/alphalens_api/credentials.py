"""Explicit operator-only Alpha Vantage credential import and bounded metadata probe."""

import argparse
import hashlib
import hmac
import importlib
import json
import os
import re
import sqlite3
import sys
import time
from contextlib import closing
from datetime import UTC, datetime
from http.client import HTTPSConnection
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .auth.permissions import restrict, verify

TARGET = "AlphaLens/AlphaVantage"


def credential_module() -> Any:
    if sys.platform != "win32":
        raise ValueError("WINDOWS_OPERATOR_CREDENTIAL_STORE_REQUIRED")
    return importlib.import_module("win32cred")


def credential_present() -> bool:
    if sys.platform != "win32":
        return False
    try:
        module = credential_module()
        module.CredRead(TARGET, module.CRED_TYPE_GENERIC)
        return True
    except Exception:
        return False


def load_key() -> str:
    module = credential_module()
    try:
        record = module.CredRead(TARGET, module.CRED_TYPE_GENERIC)
        blob = record["CredentialBlob"]
        value = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        if not re.fullmatch(r"[A-Za-z0-9]{12,64}", value):
            raise ValueError
        return value
    except Exception:
        raise ValueError("PROVIDER_CREDENTIAL_UNAVAILABLE") from None


def import_key(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > 4096:
        raise ValueError("CREDENTIAL_INPUT_INVALID")
    value = path.read_text(encoding="utf-8-sig").strip()
    if not re.fullmatch(r"[A-Za-z0-9]{12,64}", value):
        raise ValueError("CREDENTIAL_INPUT_INVALID")
    module = credential_module()
    try:
        existing = module.CredRead(TARGET, module.CRED_TYPE_GENERIC)
    except Exception as exc:
        # Only ERROR_NOT_FOUND authorizes creation; do not overwrite on other failures.
        if getattr(exc, "winerror", None) != 1168:
            raise ValueError("CREDENTIAL_STORE_UNAVAILABLE") from None
        existing = None
    if existing is not None:
        if not hmac.compare_digest(load_key(), value):
            raise ValueError("EXISTING_PROVIDER_CREDENTIAL_PRESERVED")
    else:
        module.CredWrite(
            {
                "Type": module.CRED_TYPE_GENERIC,
                "TargetName": TARGET,
                "CredentialBlob": value,
                "Persist": module.CRED_PERSIST_LOCAL_MACHINE,
                "Comment": "Operator-private AlphaLens provider credential; acquisition disabled",
            },
            0,
        )
    if not hmac.compare_digest(load_key(), value):
        raise ValueError("CREDENTIAL_READBACK_FAILED")
    return {
        "credential_storage": "WINDOWS_CURRENT_USER_CREDENTIAL_MANAGER",
        "readback_verified": True,
        "plaintext_file_deleted": False,
    }


def state_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if sys.platform != "win32" or not base:
        raise ValueError("WINDOWS_OPERATOR_STATE_REQUIRED")
    root = Path(base) / "AlphaLens" / "provider-state"
    if not root.exists():
        root.mkdir(parents=True, exist_ok=False)
        restrict(root)
    verify(root)
    return root


def reserve_request(root: Path, now: float) -> None:
    """Count failures too; 25 per rolling 24h, no automatic retries or reset assumptions."""
    with closing(sqlite3.connect(root / "alpha-vantage-requests.sqlite3", timeout=5)) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS attempts(at REAL NOT NULL)")
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute("SELECT COUNT(*) FROM attempts WHERE at>?", (now - 86400,)).fetchone()[
            0
        ]
        if count >= 25:
            raise ValueError("PROVIDER_LOCAL_REQUEST_LIMIT")
        conn.execute("INSERT INTO attempts VALUES (?)", (now,))
        conn.commit()


def classify_search(payload: bytes, secret: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError
    except (ValueError, TypeError):
        return {"result": "SCHEMA_REJECTED", "matches": []}
    matches = value.get("bestMatches")
    if not isinstance(matches, list):
        # Never reproduce provider messages that could echo query credentials.
        return {
            "result": "RATE_OR_TIER_LIMIT"
            if "Information" in value or "Note" in value
            else "PROVIDER_REJECTED_REQUEST",
            "matches": [],
        }
    safe = []
    for row in matches[:50]:
        if not isinstance(row, dict):
            continue
        symbol = row.get("1. symbol", "")
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9. :_-]{1,80}", symbol):
            continue
        selected = {
            "symbol": symbol,
            "type": row.get("3. type"),
            "region": row.get("4. region"),
            "currency": row.get("8. currency"),
        }
        if secret in json.dumps(selected):
            continue
        selected["exchange_evidence"] = (
            "BSE_SYMBOL_NOT_NSE"
            if symbol.endswith(".BSE")
            else (
                "NSE_CANDIDATE_REQUIRES_EXPLICIT_EXCHANGE_VERIFICATION"
                if "NSE" in symbol.upper()
                else "EXCHANGE_NOT_VERIFIED"
            )
        )
        safe.append(selected)
    return {
        "result": "SYMBOL_SEARCH_ACCEPTED",
        "matches": safe,
        "nse_coverage": "NOT_ESTABLISHED",
        "accessible_nse_sessions": [],
        "price_download_attempted": False,
    }


def probe_search() -> dict[str, Any]:
    secret = load_key()
    root = state_root()
    reserve_request(root, time.time())
    connection = HTTPSConnection("www.alphavantage.co", timeout=15)
    try:
        query = urlencode({"function": "SYMBOL_SEARCH", "keywords": "RELIANCE", "apikey": secret})
        connection.request("GET", "/query?" + query, headers={"Accept": "application/json"})
        response = connection.getresponse()
        payload = response.read(1_000_001)
        result = (
            classify_search(payload, secret)
            if len(payload) <= 1_000_000
            else {"result": "RESPONSE_LIMIT", "matches": []}
        )
        receipt = {
            **result,
            "http_status": response.status,
            "received_at": datetime.now(UTC).isoformat(),
            "response_sha256": hashlib.sha256(payload).hexdigest(),
            "request_count_this_probe": 1,
            "retries": 0,
            "live_activation": "BLOCKED",
            "scheduling": "DISABLED",
        }
        output = root / (
            "alpha-vantage-probe-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json"
        )
        with output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
        return receipt
    except Exception:
        raise ValueError("PROVIDER_PROBE_FAILED_NO_AUTOMATIC_RETRY") from None
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bootstrap = sub.add_parser("import-alpha-vantage")
    bootstrap.add_argument("--file", type=Path, required=True)
    sub.add_parser("probe-alpha-vantage")
    args = parser.parse_args()
    try:
        result = import_key(args.file) if args.command == "import-alpha-vantage" else probe_search()
        print(json.dumps(result, indent=2))
    except Exception:
        # Deliberately do not print exception representations or request URLs.
        print(
            json.dumps({"status": "FAILED", "reason": "LOCAL_CREDENTIAL_OR_PROVIDER_CHECK_FAILED"})
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
