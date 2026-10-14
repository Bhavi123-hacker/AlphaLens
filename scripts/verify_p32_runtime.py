"""Verify served compiled UI and original operator isolation without a password reset."""

import hashlib
import json
from pathlib import Path

import httpx
from workers.personal.store import PersonalStore

from alphalens_api.auth.store import AuthStore


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    config = json.loads((repo / ".local-data/p32-runtime/operator-config.json").read_bytes())
    original = json.loads((repo / ".local-data/p31-runtime/operator-config.json").read_bytes())
    if any(
        config[k] != original[k]
        for k in ("auth_root", "alerts_root", "operations_root", "catalog_path")
    ):
        raise ValueError("ORIGINAL_OPERATOR_ROOTS_REQUIRED")
    expected = hashlib.sha256(
        (Path(config["frontend_root"]) / "index.html").read_bytes()
    ).hexdigest()
    with httpx.Client(base_url="http://127.0.0.1:8017", timeout=10) as client:
        login = client.get("/login")
        login.raise_for_status()
        if hashlib.sha256(login.content).hexdigest() != expected:
            raise ValueError("LATEST_COMPILED_UI_REQUIRED")
        protected = {}
        for path in ("/personal/workspace", "/providers/upstox-private/instruments"):
            reply = client.get("/api/v1" + path)
            protected[path] = reply.status_code
            if reply.status_code != 401:
                raise ValueError("ORIGINAL_AUTHENTICATION_REQUIRED")
        for page in ("preferences", "my-portfolio", "opportunities", "journal", "watchlists"):
            reply = client.get("/" + page)
            if reply.status_code != 200 or hashlib.sha256(reply.content).hexdigest() != expected:
                raise ValueError("COMPILED_PERSONAL_ROUTES_REQUIRED")
    account = AuthStore(Path(config["auth_root"])).diagnostics()["account"]
    if not account or account["role"] != "ADMIN" or account["status"] != "ACTIVE":
        raise ValueError("ORIGINAL_ACTIVE_OPERATOR_REQUIRED")
    personal = PersonalStore(Path(config["personal_root"]), account["account_id"])
    counts = {
        kind: len(personal.list(kind)) for kind in ("portfolios", "watchlists", "journal", "rules")
    }
    if any(counts.values()) or personal.profile()["value"]["budget_inr"] is not None:
        raise ValueError("TEST_ONLY_RECORDS_MUST_REMAIN_ISOLATED")
    receipt = {
        "state": "PASSED",
        "url": "http://127.0.0.1:8017/login",
        "compiled_index_sha256": expected,
        "original_authentication_and_operational_roots": "PRESERVED",
        "anonymous_private_endpoint_status": protected,
        "original_personal_record_counts": counts,
        "test_only_records_in_original_workspace": False,
        "password_reset": False,
        "credentials_printed": False,
    }
    (repo / ".local-data/p32-runtime-verification.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P32_RUNTIME_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
