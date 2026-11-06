"""One pinned local release launcher; never changes accounts, tasks or market sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from scripts.private_v1_status import fingerprint, report, safe_path, smoke

PACKAGES = (
    "apps/api/src",
    "ml/data/src",
    "ml/features/src",
    "ml/labels/src",
    "ml/training/src",
    "ml/evaluation/src",
    "backtesting/src",
    "decision/src",
    "portfolio/src",
)


def pinned_environment(source: Path) -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(str(source / part) for part in (".", *PACKAGES)),
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }


def validate(path: Path, *, source_required: bool) -> dict[str, Any]:
    safe_path(path)
    value: dict[str, Any] = json.loads(path.read_bytes())
    if value.get("schema") != "alphalens.private_v1.local_deployment.v1":
        raise ValueError("LOCAL_RELEASE_MANIFEST_REQUIRED")
    for key in ("workspace", "source_root", "python", "config", "database_source_root"):
        target = Path(value[key])
        if not target.is_absolute() or not target.exists():
            raise ValueError("LOCAL_RELEASE_ABSOLUTE_EXISTING_PATH_REQUIRED")
        safe_path(target)
    config_path = Path(value["config"])
    if hashlib.sha256(config_path.read_bytes()).hexdigest() != value["config_sha256"]:
        raise ValueError("LOCAL_RELEASE_CONFIG_CHANGED")
    config = json.loads(config_path.read_bytes())
    if (
        config.get("port") != 8041
        or config.get("upstox_private_view") is not False
        or config.get("personal_mutations") is not False
        or config.get("alert_mutations") is not False
        or config.get("cors_origins") != ["http://127.0.0.1:8041"]
        or "database_url" in config
    ):
        raise ValueError("LOCAL_RELEASE_LOOPBACK_SECURITY_POLICY_REQUIRED")
    frontend = Path(config["frontend_root"])
    if not frontend.is_absolute():
        raise ValueError("LOCAL_RELEASE_ABSOLUTE_EXISTING_PATH_REQUIRED")
    index = frontend / "index.html"
    safe_path(index)
    if (
        not index.is_file()
        or hashlib.sha256(index.read_bytes()).hexdigest() != value["frontend_index_sha256"]
    ):
        raise ValueError("LOCAL_RELEASE_COMPILED_FRONTEND_CHANGED")
    if source_required:
        actual = fingerprint(Path(value["source_root"]))
        if actual["actual_source_sha256"] != value["source_fingerprint"]:
            raise ValueError("LOCAL_RELEASE_SOURCE_CHANGED_REVIEW_DEPLOYMENT_AGAIN")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "stop", "status", "smoke", "check"))
    parser.add_argument(
        "--deployment",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHALENS_PRIVATE_V1_DEPLOYMENT", ".local-data/private-v1-release/deployment.json"
            )
        ),
    )
    parser.add_argument("--credential-file", type=Path)
    args = parser.parse_args()
    release = validate(args.deployment, source_required=args.command in {"start", "check", "smoke"})
    source, python = Path(release["source_root"]), release["python"]
    config, workspace = Path(release["config"]), Path(release["workspace"])
    if args.command in {"status", "smoke"}:
        result = report(config, workspace=workspace)
        if args.command == "smoke":
            if not args.credential_file:
                parser.error("smoke requires --credential-file for an existing operator")
            result["smoke"] = smoke("http://127.0.0.1:8041", args.credential_file)
        print(json.dumps(result, indent=2))
        return
    if args.command == "start":
        # The existing owned-cluster implementation resolves its paths against
        # its source checkout. Pin that original source separately from the app.
        database_source = Path(release["database_source_root"])
        database_process = subprocess.run(
            [python, "-m", "scripts.p30_local_database", "start"],
            cwd=database_source,
            env=pinned_environment(database_source),
            check=False,
        )
        if database_process.returncode:
            raise SystemExit(database_process.returncode)
    app_process = subprocess.run(
        [python, "-m", "alphalens_api.local.cli", "--config", str(config), args.command],
        cwd=source,
        env=pinned_environment(source),
        check=False,
    )
    raise SystemExit(app_process.returncode)


if __name__ == "__main__":
    main()
