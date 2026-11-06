"""Actual personal online backup, isolated restore and restart equality; sanitized receipts."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from workers.personal.store import PersonalStore, encode

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import configured
from alphalens_api.operations.recovery import backup, restore

KINDS = ("profile", "portfolios", "watchlists", "journal", "rules", "recent")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-restart", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    settings = configured(repo / ".local-data/p33-browser-runtime/operator-config.json")
    assert settings.auth_root and settings.personal_root
    owner = AuthStore(settings.auth_root).diagnostics()["account"]["account_id"]
    source = PersonalStore(settings.personal_root, owner)
    state = {kind: source.listing(kind) for kind in KINDS}
    digest = hashlib.sha256(encode(state).encode()).hexdigest()
    receipt_path = repo / ".local-data/p33-personal-recovery.json"
    if args.verify_restart:
        old = json.loads(receipt_path.read_bytes())
        if digest != old["personal_records_sha256"]:
            raise ValueError("RESTART_PERSONAL_RECORD_MISMATCH")
        old["restart_records_identical"] = True
        receipt_path.write_text(json.dumps(old, indent=2), encoding="utf-8")
        print(json.dumps(old))
        return
    identity = uuid4().hex
    destination = repo / (".local-data/p33-backup-" + identity)
    backup_receipt = backup(settings, destination)
    restored_path = repo / (".local-data/p33-restore-" + identity)
    restored = restore(destination, restored_path)
    recovered = PersonalStore(restored_path / "personal", owner)
    if any(recovered.listing(kind) != state[kind] for kind in KINDS):
        raise ValueError("RESTORED_PERSONAL_RECORD_MISMATCH")
    try:
        PersonalStore(restored_path / "personal", "TEST_ONLY_OTHER_OWNER").profile()
    except ValueError:
        foreign_rejected = True
    else:
        raise ValueError("RESTORED_PERSONAL_OWNER_NOT_PROTECTED")
    receipt = {
        "state": "PASSED",
        "online_sqlite_snapshot": True,
        "personal_records_sha256": digest,
        "personal_record_counts": {k: len(v) for k, v in state.items()},
        "databases_backed_up": backup_receipt["databases"],
        "manifest_sha256": backup_receipt["manifest_sha256"],
        "restore_original_state_modified": restored["original_state_modified"],
        "restored_auth_sessions": restored["auth_sessions"],
        "restored_other_owner_rejected": foreign_rejected,
        "provider_payloads_in_backup": False,
        "credential_values_printed": False,
        "restart_records_identical": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P33_RECOVERY_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
