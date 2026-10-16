"""Read-only frozen evidence/account verification; write only a new local receipt."""

import hashlib
import io
import json
import sqlite3
import subprocess
import tarfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from workers.personal.store import PersonalStore, encode

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import configured

BASELINE = "8d931ed0fbabce24f0b84c161134ff19b3554626"
RESEARCH_ROOT = Path("D:/al-research/tejhq-research-evaluation-v2-fit-parallel")
ALERTS_PATH = Path("D:/al-research/p20-runtime/alerts/alerts.sqlite3")
ALERTS_SHA = "dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41"


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def check() -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    started = time.perf_counter()
    protected = (
        "ml",
        "decision",
        "portfolio",
        "backtesting",
        "db",
        "uv.lock",
        "apps/web/package-lock.json",
        "docs/ml",
        "docs/backtesting",
        "docs/data/dataset-identity.json",
        "scripts/run_tejhq_research.py",
        "AlphaLens_Complete_Project_Documentation.docx",
        "workers/daily/experimental.py",
        "workers/daily/forward.py",
        "workers/providers/credentials.py",
    )
    # The baseline archive enumerates ORIGINAL files, so an independent added
    # experimental schema is allowed without exempting any original db schema.
    archived = subprocess.check_output(["git", "archive", BASELINE, *protected], cwd=repo)
    tracked_count = 0
    checkout_newline_only = []
    with tarfile.open(fileobj=io.BytesIO(archived), mode="r:") as baseline:
        for entry in baseline:
            if not entry.isfile():
                continue
            path = (repo / entry.name).resolve()
            if not path.is_relative_to(repo.resolve()):
                raise ValueError("ORIGINAL_SOURCE_PATH_ESCAPE")
            original = baseline.extractfile(entry)
            if original is None or not path.is_file():
                raise ValueError("ORIGINAL_SOURCE_FILE_MISSING")
            with original:
                original_bytes = original.read()
            expected = hashlib.sha256(original_bytes).hexdigest()
            if sha(path) != expected:
                actual_bytes = path.read_bytes()
                if (
                    path.suffix
                    not in {".py", ".md", ".json", ".yml", ".toml", ".sql", ".txt", ".lock"}
                    or actual_bytes.replace(b"\r\n", b"\n") != original_bytes
                    or subprocess.run(
                        ["git", "diff", "--quiet", BASELINE, "--", entry.name],
                        cwd=repo,
                        check=False,
                    ).returncode
                    != 0
                ):
                    raise ValueError("ORIGINAL_FROZEN_SOURCE_BYTES_CHANGED:" + entry.name)
                checkout_newline_only.append(entry.name)
            tracked_count += 1
    audit = json.loads((repo / "docs/backtesting/real-research-economic-audit.json").read_bytes())
    total_bytes = 0
    for entry in audit["artifact_inventory"]:
        path = (RESEARCH_ROOT / entry["path"]).resolve()
        if not path.is_relative_to(RESEARCH_ROOT.resolve()):
            raise ValueError("FROZEN_ARTIFACT_PATH_ESCAPE")
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("ORIGINAL_FROZEN_ARTIFACT_BYTES_CHANGED")
        total_bytes += entry["bytes"]
    with closing(sqlite3.connect(ALERTS_PATH.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        alerts = db.execute(
            "SELECT id,event_key,evidence,evidence_hash FROM alerts ORDER BY id"
        ).fetchall()
    alerts_sha = hashlib.sha256(json.dumps(alerts).encode()).hexdigest()
    if len(alerts) != 47 or alerts_sha != ALERTS_SHA:
        raise ValueError("ORIGINAL_47_ALERT_RECORDS_CHANGED")
    settings = configured(repo / ".local-data/p33-runtime/operator-config.json")
    if not settings.auth_root or not settings.personal_root or not settings.frontend_root:
        raise ValueError("ORIGINAL_NATIVE_ROOTS_REQUIRED")
    auth = AuthStore(settings.auth_root)
    owner = auth.diagnostics()["account"]["account_id"]
    personal = PersonalStore(settings.personal_root, owner)
    kinds = ("profile", "portfolios", "watchlists", "journal", "rules", "recent")
    records = {kind: personal.listing(kind) for kind in kinds}
    personal_sha = hashlib.sha256(encode(records).encode()).hexdigest()
    with auth.connection() as connection:
        account_rows = connection.execute(
            "SELECT account_id,password_hash,password_changed_at FROM accounts ORDER BY account_id"
        ).fetchall()
    account_sha = hashlib.sha256(encode([tuple(row) for row in account_rows]).encode()).hexdigest()
    prior = json.loads((repo / ".local-data/p33-original-preservation.json").read_bytes())
    if account_sha != prior["authentication_sha256"] or personal_sha != prior["personal_sha256"]:
        raise ValueError("ORIGINAL_OPERATOR_OR_PERSONAL_RECORDS_CHANGED")
    index_sha = sha(settings.frontend_root / "index.html")
    anonymous = {}
    with httpx.Client(base_url="http://127.0.0.1:8017", timeout=15) as client:
        login = client.get("/login")
        if login.status_code != 200 or hashlib.sha256(login.content).hexdigest() != index_sha:
            raise ValueError("NATIVE_COMPILED_INDEX_MISMATCH")
        for route in (
            "/personal/workspace",
            "/personal/model-readiness",
            "/providers/upstox-private/instruments",
            "/providers/private-eod-status",
        ):
            status = client.get("/api/v1" + route).status_code
            if status != 401:
                raise ValueError("ORIGINAL_PRIVATE_ENDPOINT_NOT_AUTHENTICATED")
            anonymous[route] = status
    return {
        "state": "PASSED",
        "verified_at": datetime.now(UTC).isoformat(),
        "baseline": BASELINE,
        "original_tracked_files_unchanged_git_content": tracked_count,
        "original_tracked_files_byte_exact": tracked_count - len(checkout_newline_only),
        "existing_windows_checkout_crlf_only": checkout_newline_only,
        "frozen_artifact_newline_normalization_performed": False,
        "independent_added_schemas_allowed_original_schemas_unchanged": True,
        "frozen_artifact_files_byte_exact": len(audit["artifact_inventory"]),
        "frozen_artifact_bytes": total_bytes,
        "artifact_inventory_sha256": audit["artifact_inventory_sha256"],
        "original_alerts": len(alerts),
        "original_alerts_sha256": alerts_sha,
        "original_account_password_hash_unchanged": True,
        "original_personal_records_byte_equivalent": True,
        "original_personal_counts": {kind: len(values) for kind, values in records.items()},
        "native_login": 200,
        "native_compiled_index_sha256": index_sha,
        "anonymous_private_status": anonymous,
        "credential_manager_verifier_operations": "NONE_READ_OR_WRITE",
        "database_write_operations": 0,
        "seconds": time.perf_counter() - started,
    }


def main() -> None:
    result = check()
    target = Path(__file__).resolve().parents[1] / ".local-data/experimental-nse-preservation.json"
    # Preserve earlier receipts: an explicit second verification gets its own file.
    if target.exists():
        target = target.with_name("experimental-nse-preservation-" + str(time.time_ns()) + ".json")
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"EXPERIMENTAL_PRESERVATION_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
