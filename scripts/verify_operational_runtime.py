"""Original operator preservation, online backup/isolated restore and compiled native reads."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
from workers.personal.store import PersonalStore, encode

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import configured
from alphalens_api.operations.recovery import backup, restore


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    settings = configured(repo / ".local-data/p33-runtime/operator-config.json")
    if not settings.auth_root or not settings.personal_root or not settings.frontend_root:
        raise ValueError("ORIGINAL_NATIVE_CONFIGURATION_REQUIRED")
    auth = AuthStore(settings.auth_root)
    owner = auth.diagnostics()["account"]["account_id"]
    personal = PersonalStore(settings.personal_root, owner)
    kinds = ("profile", "portfolios", "watchlists", "journal", "rules", "recent")
    records = {k: personal.listing(k) for k in kinds}
    digest = hashlib.sha256(encode(records).encode()).hexdigest()
    with auth.connection() as db:
        credentials = db.execute(
            "SELECT account_id,password_hash,password_changed_at FROM accounts ORDER BY account_id"
        ).fetchall()
    auth_digest = hashlib.sha256(encode([tuple(r) for r in credentials]).encode()).hexdigest()
    baseline = json.loads((repo / ".local-data/p33-original-preservation.json").read_bytes())
    if digest != baseline["personal_sha256"] or auth_digest != baseline["authentication_sha256"]:
        raise ValueError("ORIGINAL_ACCOUNT_OR_PERSONAL_RECORDS_CHANGED")
    identity = uuid4().hex
    target = repo / (".local-data/operational-original-backup-" + identity)
    saved = backup(settings, target)
    recovered_root = repo / (".local-data/operational-original-restore-" + identity)
    recovered = restore(target, recovered_root)
    if any(
        PersonalStore(recovered_root / "personal", owner).listing(k) != records[k] for k in kinds
    ):
        raise ValueError("ORIGINAL_ONLINE_BACKUP_RESTORE_MISMATCH")
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
            reply = client.get("/" + page)
            if reply.status_code != 200 or hashlib.sha256(reply.content).hexdigest() != expected:
                raise ValueError("LATEST_COMPILED_NATIVE_INDEX_REQUIRED")
        for route in (
            "/personal/workspace",
            "/personal/model-readiness",
            "/providers/upstox-private/instruments",
            "/providers/private-eod-status",
        ):
            protected[route] = client.get("/api/v1" + route).status_code
            if protected[route] != 401:
                raise ValueError("PRIVATE_ENDPOINT_AUTHENTICATION_REQUIRED")
    result = {
        "state": "PASSED",
        "url": "http://127.0.0.1:8017/login",
        "original_personal_records_byte_equivalent": True,
        "original_account_password_hash_unchanged": True,
        "original_counts": {k: len(v) for k, v in records.items()},
        "original_personal_sha256": digest,
        "compiled_index_sha256": expected,
        "anonymous_status": protected,
        "backup_databases": saved["databases"],
        "restore_original_state_modified": recovered["original_state_modified"],
        "restored_auth_sessions": recovered["auth_sessions"],
        "backup_restored_personal_records_identical": True,
        "credential_manager_writes_performed": False,
        "operator_password_reset": False,
    }
    (repo / ".local-data/operational-native-verification.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"OPERATIONAL_RUNTIME_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
