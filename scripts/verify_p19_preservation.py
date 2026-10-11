"""Streaming read-only frozen-artifact verification. No estimators or evaluations."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only P19 artifact preservation")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    expected = json.loads((repo / "docs/development/p18-artifact-preservation.json").read_bytes())
    audit = json.loads((repo / "docs/backtesting/real-research-economic-audit.json").read_bytes())
    protected = []
    start = time.perf_counter()
    for entry in expected["protected_files"]:
        actual = digest(repo / entry["file"])
        if actual != entry["sha256"]:
            if entry["file"] == ".github/workflows/ci.yml":
                original = subprocess.check_output(
                    [
                        "git",
                        "show",
                        "5e02e5cd1b120e200def460b3ab037fb27df9ec7:.github/workflows/ci.yml",
                    ],
                    cwd=repo,
                ).decode()
                expected_text = original.replace("portfolio/src\n", "portfolio/src workers/daily\n")
                if (repo / entry["file"]).read_text(encoding="utf-8") != expected_text:
                    raise ValueError("STRICT_WORKFLOW_CHANGED_BEYOND_WORKER_BANDIT_SCOPE")
                protected.append(
                    dict(
                        file=entry["file"],
                        original_sha256=entry["sha256"],
                        sha256=actual,
                        unchanged_from_p18=False,
                        authorized_change="EXTEND_BANDIT_TO_NEW_WORKER_ONLY",
                    )
                )
                continue
            raise ValueError("FROZEN_PROTECTED_FILE_CHANGED")
        protected.append(entry | {"unchanged_from_p18": True})
    total = 0
    for entry in audit["artifact_inventory"]:
        path = (args.run_root / entry["path"]).resolve()
        if not path.is_relative_to(args.run_root.resolve()) or digest(path) != entry["sha256"]:
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError("FROZEN_ARTIFACT_SIZE_CHANGED")
        total += entry["bytes"]
    main_commit = subprocess.check_output(["git", "rev-parse", "main"], cwd=repo, text=True).strip()
    if main_commit != expected["main_commit"]:
        raise ValueError("MAIN_CHANGED")
    result = dict(
        baseline="5e02e5cd1b120e200def460b3ab037fb27df9ec7",
        main_commit=main_commit,
        protected_files=protected,
        verified_files=len(audit["artifact_inventory"]),
        verified_bytes=total,
        artifact_inventory_sha256=audit["artifact_inventory_sha256"],
        frozen_artifact_full_hash_gate="PASSED",
        verification_seconds=round(time.perf_counter() - start, 3),
        method="READ_ONLY_STREAMING_SHA256_NO_FIT_OR_HOLDOUT_EVALUATION",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "protected_files"}))


if __name__ == "__main__":
    main()
