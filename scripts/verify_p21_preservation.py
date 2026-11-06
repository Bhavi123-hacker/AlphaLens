"""Read-only P21 research, dependency and retained alert integrity verification."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import time
import tomllib
from pathlib import Path

from scripts.verify_p19_preservation import digest

BASELINE = "eaeb01dcfa77cea4d1325de693373ae7e2020a58"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--alerts-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    start = time.perf_counter()
    previous = json.loads((repo / "docs/development/p20-artifact-preservation.json").read_bytes())
    for entry in previous["protected_files"]:
        if (
            entry["file"] not in {"uv.lock", ".github/workflows/ci.yml"}
            and digest(repo / entry["file"]) != entry["sha256"]
        ):
            raise ValueError("PROTECTED_RESEARCH_FILE_CHANGED")
    original = subprocess.check_output(["git", "show", f"{BASELINE}:uv.lock"], cwd=repo)
    old = {p["name"]: p["version"] for p in tomllib.loads(original.decode())["package"]}
    new = {
        p["name"]: p["version"] for p in tomllib.loads((repo / "uv.lock").read_text())["package"]
    }
    additions = {k: v for k, v in new.items() if k not in old}
    if any(new.get(k) != v for k, v in old.items()) or set(additions) != {
        "argon2-cffi",
        "argon2-cffi-bindings",
        "cffi",
        "pycparser",
        "pywin32",
    }:
        raise ValueError("RESEARCH_RUNTIME_VERSIONS_CHANGED")
    roots = [
        "ml",
        "decision",
        "portfolio",
        "backtesting",
        "workers/daily",
        "workers/alerts",
        "db/migrations",
        "db/alerts",
    ]
    if subprocess.check_output(["git", "diff", BASELINE, "--", *roots], cwd=repo):
        raise ValueError("FROZEN_DOMAIN_CHANGED")
    inventory = json.loads(
        (repo / "docs/backtesting/real-research-economic-audit.json").read_bytes()
    )
    root = args.run_root.resolve()
    total = 0
    for entry in inventory["artifact_inventory"]:
        path = (root / entry["path"]).resolve()
        if (
            not path.is_relative_to(root)
            or digest(path) != entry["sha256"]
            or path.stat().st_size != entry["bytes"]
        ):
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
        total += entry["bytes"]
    path = (args.alerts_root / "alerts.sqlite3").resolve()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as c:
        rows = c.execute(
            "SELECT id,event_key,evidence,evidence_hash FROM alerts ORDER BY id"
        ).fetchall()
        if len(rows) != 47 or any(hashlib.sha256(r[2].encode()).hexdigest() != r[3] for r in rows):
            raise ValueError("P20_ALERT_EVIDENCE_CHANGED")
    alert_inventory_hash = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    if alert_inventory_hash != "dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41":
        raise ValueError("P20_ALERT_INVENTORY_CHANGED")
    main_commit = subprocess.check_output(["git", "rev-parse", "main"], cwd=repo, text=True).strip()
    if main_commit != previous["main_commit"]:
        raise ValueError("MAIN_CHANGED")
    result = dict(
        baseline=BASELINE,
        main_commit=main_commit,
        verified_files=len(inventory["artifact_inventory"]),
        verified_bytes=total,
        artifact_inventory_sha256=inventory["artifact_inventory_sha256"],
        protected_file_hashes="UNCHANGED_EXCEPT_AUTH_ADDITIONS_TO_LOCK_AND_CI_SMOKE",
        existing_package_versions="ALL_UNCHANGED",
        new_auth_dependencies=additions,
        unchanged_domain_roots=roots,
        retained_alerts=47,
        alert_inventory_sha256=alert_inventory_hash,
        verification_seconds=round(time.perf_counter() - start, 3),
        status="PASSED",
        method="READ_ONLY_SHA256_NO_FIT_NO_EVALUATION_NO_BACKTEST",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
