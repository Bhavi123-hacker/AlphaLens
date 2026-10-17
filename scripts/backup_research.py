"""Private research bundle and isolated restore; never replaces operational stores."""

import argparse
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import digest, encoded, initialize, private_path, write_new
from workers.experimental_nse_v2 import data, models, pipeline
from workers.experimental_nse_v2.forward import summary

from alphalens_api.auth.permissions import restrict, verify

REPO = Path(__file__).resolve().parents[1]
OMIT = {"workflow-control", "capture-control", "__pycache__"}


def destination(path: Path) -> Path:
    path = path.absolute()
    if not path.is_relative_to(REPO / ".local-data") or path.exists():
        raise ValueError("NEW_PRIVATE_ISOLATED_DESTINATION_REQUIRED")
    # private_path checks all existing ancestors for symlinks/reparse points.
    private_path(REPO / ".local-data", *path.relative_to(REPO / ".local-data").parts)
    initialize(path)
    return path


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    restrict(target.parent)
    if source.suffix == ".sqlite3":
        with (
            sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as original,
            sqlite3.connect(target) as saved,
        ):
            original.backup(saved)
            if saved.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("RESEARCH_BACKUP_INTEGRITY_FAILED")
    else:
        shutil.copyfile(source, target)
    if os.name != "nt":
        target.chmod(0o600)


def validate(root: Path) -> dict[str, Any]:
    manifest_path = private_path(root, "manifest.json")
    body = manifest_path.read_bytes()
    if digest(body) != private_path(root, "manifest.sha256").read_text(encoding="ascii"):
        raise ValueError("RESEARCH_BUNDLE_HASH_REJECTED")
    manifest = json.loads(body)
    for relative, checksum in manifest["files"].items():
        path = private_path(root, *Path(relative).parts)
        verify(path, directory=False)
        if digest(path.read_bytes()) != checksum:
            raise ValueError("RESEARCH_BUNDLE_FILE_HASH_REJECTED")
    restored_v2 = root / "v2"
    dataset = data.load_current(restored_v2)
    output = restored_v2 / "price-only"
    evaluation = pipeline.verified(output / "evaluation.json")
    models.load_model(output / "model.json", evaluation["model_sha256"])
    forward = summary(output)
    if forward["forecasts"] != manifest["v2_forecasts"]:
        raise ValueError("RESEARCH_BUNDLE_FORECAST_COUNT_MISMATCH")
    return {
        "state": "PASS",
        "files": len(manifest["files"]),
        "v2_observations": len(dataset["rows"]),
        "v2_forecasts": forward["forecasts"],
        "v2_outcomes": forward["outcomes"],
        "model_reload_verified": True,
        "original_state_modified": False,
        "provider_requests": 0,
        "includes_credential_manager": False,
        "includes_postgresql": False,
    }


def backup(target: Path) -> dict[str, Any]:
    config = json.loads((REPO / ".local-data/p33-runtime/operator-config.json").read_bytes())
    roots = {
        "v1": Path(config["experimental_nse_root"]),
        "v2": Path(config["experimental_nse_v2_root"]),
    }
    target = destination(target)
    for label, source_root in roots.items():
        verify(source_root)
        for source in source_root.rglob("*"):
            relative = source.relative_to(source_root)
            if source.is_symlink():
                raise ValueError("RESEARCH_BACKUP_SYMLINK_REJECTED")
            if (
                set(relative.parts) & OMIT
                or source.name.endswith(("-wal", "-shm", ".lock", ".tmp"))
                or not source.is_file()
            ):
                continue
            copy_file(source, private_path(target, label, *relative.parts))
    for source in (REPO / "docs/development").glob("*registered-protocol.md"):
        copy_file(source, private_path(target, "protocols", source.name))
    v2_forward = summary(target / "v2/price-only")
    files = {
        str(path.relative_to(target)): digest(path.read_bytes())
        for path in target.rglob("*")
        if path.is_file()
    }
    body = encoded(
        {
            "version": "private.research.backup.1",
            "created_at": datetime.now(UTC).isoformat(),
            "v2_forecasts": v2_forward["forecasts"],
            "files": files,
            "scope": "V1_V2_RESEARCH_ONLY_NO_CREDENTIALS_OR_PERSONAL_OR_POSTGRESQL",
        }
    )
    write_new(target / "manifest.json", body)
    write_new(target / "manifest.sha256", digest(body).encode("ascii"))
    return validate(target)


def restore(source: Path, target: Path) -> dict[str, Any]:
    validate(source)
    target = destination(target)
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise ValueError("RESEARCH_RESTORE_SYMLINK_REJECTED")
        if path.is_file() and not path.name.endswith(("-wal", "-shm")):
            copy_file(path, private_path(target, *relative.parts))
    return validate(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "restore", "verify"))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.operation == "verify" and args.source:
        result = validate(args.source)
    elif args.operation == "backup" and args.destination:
        result = backup(args.destination)
    elif args.operation == "restore" and args.source and args.destination:
        result = restore(args.source, args.destination)
    else:
        parser.error("Provide the required source and/or new private destination")
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"FAIL","code":"RESEARCH_BACKUP_OR_RESTORE_NOT_VERIFIED"}')
        raise SystemExit(1) from None
