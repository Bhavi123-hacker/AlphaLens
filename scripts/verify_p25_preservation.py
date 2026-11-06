"""Read-only final artifact/alert preservation; never run research estimators."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import time
from contextlib import closing
from pathlib import Path

from scripts.verify_p19_preservation import digest

BASELINE = "de80e3d136287e0834429bd8d93b18ab3846ba98"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--alerts-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    repo = Path(__file__).resolve().parents[1]
    previous = json.loads((repo / "docs/development/p20-artifact-preservation.json").read_bytes())
    protected = []
    for entry in previous["protected_files"]:
        if entry["file"] not in {"uv.lock", ".github/workflows/ci.yml"}:
            if digest(repo / entry["file"]) != entry["sha256"]:
                raise ValueError("FROZEN_RESEARCH_FILE_CHANGED")
            protected.append(entry["file"])
    for path in ("uv.lock", "apps/web/package-lock.json"):
        original = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=repo)
        actual = (repo / path).read_bytes()
        # Git stores LF; the retained Windows checkout uses CRLF. This permits
        # only Git's checkout newline representation, never changed lock content.
        if actual not in {original, original.replace(b"\n", b"\r\n")}:
            raise ValueError("FROZEN_RUNTIME_LOCK_CHANGED")
    roots = ["ml", "decision", "portfolio", "backtesting", "db/migrations", "db/alerts"]
    if subprocess.check_output(["git", "diff", BASELINE, "--", *roots], cwd=repo):
        raise ValueError("FROZEN_DOMAIN_CHANGED")
    audit = json.loads((repo / "docs/backtesting/real-research-economic-audit.json").read_bytes())
    total = 0
    for entry in audit["artifact_inventory"]:
        path = (args.run_root / entry["path"]).resolve()
        if (
            not path.is_relative_to(args.run_root.resolve())
            or digest(path) != entry["sha256"]
            or path.stat().st_size != entry["bytes"]
        ):
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
        total += entry["bytes"]
    database = args.alerts_root / "alerts.sqlite3"
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        rows = conn.execute(
            "SELECT id,event_key,evidence,evidence_hash FROM alerts ORDER BY id"
        ).fetchall()
    alert_hash = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    if (
        len(rows) != 47
        or any(hashlib.sha256(r[2].encode()).hexdigest() != r[3] for r in rows)
        or alert_hash != "dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41"
    ):
        raise ValueError("ORIGINAL_ALERT_EVIDENCE_CHANGED")
    main_sha = subprocess.check_output(["git", "rev-parse", "main"], cwd=repo, text=True).strip()
    if main_sha != previous["main_commit"]:
        raise ValueError("MAIN_CHANGED")
    receipt = {
        "baseline": BASELINE,
        "main_commit": main_sha,
        "verified_files": len(audit["artifact_inventory"]),
        "verified_bytes": total,
        "artifact_inventory_sha256": audit["artifact_inventory_sha256"],
        "protected_files": protected,
        "domain_roots": roots,
        "dependency_locks": "UNCHANGED",
        "retained_original_alerts": 47,
        "alert_inventory_sha256": alert_hash,
        "verification_seconds": round(time.perf_counter() - started, 3),
        "status": "PASSED",
        "method": "READ_ONLY_SHA256_NO_FIT_NO_EVALUATION_NO_BACKTEST",
        "worker_changes": (
            "Reviewed additive safe CLI logging and P22 operational alert vocabulary; "
            "no pipeline/ranking/financial engine changes"
        ),
    }
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
