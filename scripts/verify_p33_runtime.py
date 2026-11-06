"""Back up original state, then verify the compiled deployment without a password reset."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
from workers.personal.store import PersonalStore, encode

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import configured
from alphalens_api.operations.recovery import backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    path = repo / ".local-data/p33-runtime/operator-config.json"
    config = json.loads(path.read_bytes())
    baseline = json.loads((repo / ".local-data/p32-runtime/operator-config.json").read_bytes())
    if {k: v for k, v in config.items() if k != "frontend_root"} != {
        k: v for k, v in baseline.items() if k != "frontend_root"
    }:
        raise ValueError("ORIGINAL_OPERATOR_CONFIGURATION_REQUIRED")
    settings = configured(path)
    assert settings.auth_root and settings.personal_root
    auth = AuthStore(settings.auth_root)
    account = auth.diagnostics()["account"]
    if not account or account["role"] != "ADMIN" or account["status"] != "ACTIVE":
        raise ValueError("ORIGINAL_ACTIVE_OPERATOR_REQUIRED")
    personal = PersonalStore(settings.personal_root, account["account_id"])
    records = {
        kind: personal.listing(kind)
        for kind in ("profile", "portfolios", "watchlists", "journal", "rules", "recent")
    }
    with auth.connection() as connection:
        credentials = connection.execute(
            "SELECT account_id,password_hash,password_changed_at FROM accounts ORDER BY account_id"
        ).fetchall()
    unchanged = {
        "personal_sha256": hashlib.sha256(encode(records).encode()).hexdigest(),
        "authentication_sha256": hashlib.sha256(
            encode([tuple(r) for r in credentials]).encode()
        ).hexdigest(),
    }
    preservation_path = repo / ".local-data/p33-original-preservation.json"
    if args.prepare:
        if preservation_path.exists():
            raise ValueError("ORIGINAL_PRESERVATION_RECEIPT_ALREADY_EXISTS")
        destination = repo / (".local-data/p33-original-backup-" + uuid4().hex)
        receipt = backup(settings, destination)
        preservation_path.write_text(
            json.dumps(
                {**unchanged, "backup": receipt, "backup_directory": str(destination)}, indent=2
            ),
            encoding="utf-8",
        )
        print(json.dumps({"state": "ORIGINAL_ONLINE_BACKUP_PASSED", **receipt}))
        return
    before = json.loads(preservation_path.read_bytes())
    if any(before[k] != v for k, v in unchanged.items()):
        raise ValueError("ORIGINAL_PERSONAL_OR_AUTHENTICATION_RECORD_CHANGED")
    expected = hashlib.sha256((settings.frontend_root / "index.html").read_bytes()).hexdigest()
    protected = {}
    with httpx.Client(base_url="http://127.0.0.1:8017", timeout=15) as client:
        for page in (
            "login",
            "preferences",
            "my-portfolio",
            "decision-desk",
            "opportunities",
            "journal",
            "watchlists",
            "research-alerts",
        ):
            response = client.get("/" + page)
            if (
                response.status_code != 200
                or hashlib.sha256(response.content).hexdigest() != expected
            ):
                raise ValueError("LATEST_COMPILED_UI_REQUIRED")
        for endpoint in (
            "/personal/workspace",
            "/personal/decision-desk",
            "/personal/model-readiness",
            "/providers/upstox-private/instruments",
            "/providers/upstox-private/reference",
        ):
            protected[endpoint] = client.get("/api/v1" + endpoint).status_code
            if protected[endpoint] != 401:
                raise ValueError("ORIGINAL_AUTHENTICATION_REQUIRED")
    receipt = {
        "state": "PASSED",
        "url": "http://127.0.0.1:8017/login",
        "compiled_index_sha256": expected,
        "original_configuration_except_frontend_root": "PRESERVED",
        "original_personal_records_identical": True,
        "original_password_and_account_identical": True,
        "original_record_counts": {k: len(v) for k, v in records.items()},
        "anonymous_private_endpoint_status": protected,
        "password_reset": False,
        "credentials_printed": False,
    }
    (repo / ".local-data/p33-runtime-verification.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P33_RUNTIME_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
