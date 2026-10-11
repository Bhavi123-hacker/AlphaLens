"""Read-only P20 freeze gate, including the original complete research inventory."""

import argparse
import json
import subprocess
import time
from pathlib import Path

from scripts.verify_p19_preservation import digest

BASELINE = "487a68552c79b1db1b09dfb3d03205854f26aae4"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    expected = json.loads((repo / "docs/development/p18-artifact-preservation.json").read_bytes())
    start = time.perf_counter()
    protected = []
    for entry in expected["protected_files"]:
        if entry["file"] == ".github/workflows/ci.yml":
            original = subprocess.check_output(
                ["git", "show", f"{BASELINE}:.github/workflows/ci.yml"], cwd=repo
            ).decode()
            allowed = original.replace(
                "portfolio/src workers/daily\n", "portfolio/src workers/daily workers/alerts\n"
            ).replace(
                '"alphalens_api", "alphalens_data", "alphalens_features", "alphalens_labels",',
                '"alphalens_api", "alphalens_api.main", "workers.alerts.store", "alphalens_data",\n'
                '              "alphalens_features", "alphalens_labels",',
            )
            if (repo / entry["file"]).read_text(encoding="utf-8") != allowed:
                raise ValueError("STRICT_WORKFLOW_CHANGED_BEYOND_ALERT_SCOPE")
            protected.append(
                {
                    "file": entry["file"],
                    "authorized_change": "EXTEND_BANDIT_AND_RUNTIME_IMPORT_CHECKS_ONLY",
                }
            )
        else:
            if digest(repo / entry["file"]) != entry["sha256"]:
                raise ValueError("PROTECTED_RESEARCH_FILE_CHANGED")
            protected.append(entry | {"unchanged": True})
    unchanged_roots = [
        "ml",
        "decision",
        "portfolio",
        "backtesting",
        "workers/daily",
        "db/migrations",
    ]
    changes = subprocess.check_output(["git", "diff", BASELINE, "--", *unchanged_roots], cwd=repo)
    if changes:
        raise ValueError("FROZEN_DOMAIN_OR_PROTOCOL_CODE_CHANGED")
    audit = json.loads((repo / "docs/backtesting/real-research-economic-audit.json").read_bytes())
    root = args.run_root.resolve()
    total = 0
    for entry in audit["artifact_inventory"]:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root) or digest(path) != entry["sha256"]:
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError("FROZEN_ARTIFACT_SIZE_CHANGED")
        total += entry["bytes"]
    main_commit = subprocess.check_output(["git", "rev-parse", "main"], cwd=repo, text=True).strip()
    if main_commit != expected["main_commit"]:
        raise ValueError("MAIN_CHANGED")
    result = dict(
        baseline=BASELINE,
        main_commit=main_commit,
        protected_files=protected,
        verified_files=len(audit["artifact_inventory"]),
        verified_bytes=total,
        artifact_inventory_sha256=audit["artifact_inventory_sha256"],
        frozen_artifact_full_hash_gate="PASSED",
        unchanged_domain_roots=unchanged_roots,
        verification_seconds=round(time.perf_counter() - start, 3),
        method="READ_ONLY_SHA256_NO_FIT_NO_HOLDOUT_EVALUATION_NO_BACKTEST",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError("PRESERVATION_RECEIPT_ALREADY_EXISTS_USE_NEW_VERSION")
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "protected_files"}))


if __name__ == "__main__":
    main()
