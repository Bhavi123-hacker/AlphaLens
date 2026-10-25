"""Prepare a fresh isolated collector environment, never change a scheduled task.

The frozen lock is reused with copy-mode package installation. The old shared
environment, private app runtime, credentials, data and task definitions are not
modified. Package downloads require an explicit flag; offline is the default.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fresh_destination(repo: Path, requested: Path) -> Path:
    """Refuse links, existing environments and anything outside private storage."""
    repo = repo.resolve(strict=True)
    base = repo / ".local-data"
    absolute = requested.absolute()
    if not absolute.is_relative_to(base) or absolute == base:
        raise ValueError("FRESH_PRIVATE_RUNTIME_REQUIRED")
    for parent in (absolute, *absolute.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("RUNTIME_REPARSE_PATH_REJECTED")
        if parent == repo:
            break
    if absolute.exists() or not absolute.resolve().is_relative_to(base.resolve(strict=True)):
        raise ValueError("FRESH_PRIVATE_RUNTIME_REQUIRED")
    return absolute


def package_versions(site: Path) -> dict[str, str]:
    """Read distribution metadata; never import old installed package code."""
    return {
        str(item.metadata["Name"]).lower(): item.version
        for item in importlib.metadata.distributions(path=[str(site)])
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-package-download", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = fresh_destination(repo, args.output)
    uv, python = args.uv.resolve(strict=True), args.python.resolve(strict=True)
    cache = args.cache.resolve(strict=True)
    lock = repo / "uv.lock"
    before_lock = digest(lock)
    shared = repo / ".venv" / "Lib" / "site-packages"
    before_shared = package_versions(shared)
    version = subprocess.run([str(uv), "--version"], capture_output=True, check=True)
    if not version.stdout.decode().startswith("uv 0.11.25 "):
        raise ValueError("PINNED_UV_REQUIRED")
    from alphalens_api.auth.permissions import restrict

    output.mkdir(parents=True, mode=0o700)
    restrict(output)
    environment = dict(os.environ)
    environment.update(
        UV_PROJECT_ENVIRONMENT=str(output / "venv"),
        UV_CACHE_DIR=str(cache),
        UV_LINK_MODE="copy",
        UV_PYTHON_DOWNLOADS="never",
        PYTHONUTF8="1",
        TEMP=str(output),
        TMP=str(output),
    )
    command = [str(uv), "sync", "--frozen", "--python", str(python)]
    if not args.allow_package_download:
        command.append("--offline")
    with (output / "install.private.log").open("xb") as log:
        result = subprocess.run(
            command,
            cwd=repo,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    unchanged = digest(lock) == before_lock and package_versions(shared) == before_shared
    if not unchanged:
        raise ValueError("FROZEN_LOCK_OR_SHARED_PACKAGE_METADATA_CHANGED")
    target = output / "venv" / "Scripts" / "python.exe"
    receipt: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "state": "VERIFIED_COMPLETE" if result.returncode == 0 else "BLOCKED_EXTERNAL_DATA",
        "scope": "ENVIRONMENT_INSTALLATION_ONLY_SECURITY_AND_TEST_GATES_SEPARATE",
        "install_exit": result.returncode,
        "runtime": str(target),
        "uv_binary_sha256": digest(uv),
        "base_python_sha256": digest(python),
        "lock_sha256": before_lock,
        "package_link_mode": "copy",
        "package_downloads_allowed": args.allow_package_download,
        "shared_metadata_unchanged": unchanged,
        "scheduled_tasks_modified": False,
        "provider_requests": 0,
        "production_model_operations": 0,
    }
    if result.returncode == 0:
        receipt["packages"] = package_versions(target.parent.parent / "Lib" / "site-packages")
    with (output / "installation-receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps({key: value for key, value in receipt.items() if key != "packages"}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
