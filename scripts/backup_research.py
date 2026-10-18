"""Private research bundle and isolated restore; never replaces operational stores."""

import argparse
import json
import os
import shutil
import sqlite3
from contextlib import ExitStack, closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import digest, encoded, initialize, private_path, write_new
from workers.experimental_nse_v2 import data, models, pipeline
from workers.experimental_nse_v2.forward import summary
from workers.nse_market import engine
from workers.providers import universe

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.daily.storage import Store

REPO = Path(__file__).resolve().parents[1]
OMIT = {"workflow-control", "capture-control", "__pycache__"}
EXPANDED_LABELS = ("nse-universe", "nse-market-expansion", "sequence-benchmark-v1")


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
            closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original,
            closing(sqlite3.connect(target)) as saved,
        ):
            original.backup(saved)
            if saved.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("RESEARCH_BACKUP_INTEGRITY_FAILED")
    else:
        shutil.copyfile(source, target)
    if os.name != "nt":
        target.chmod(0o600)


def _files(source_root: Path) -> list[Path]:
    result = []
    for source in source_root.rglob("*"):
        relative = source.relative_to(source_root)
        if source.is_symlink() or source.is_junction():
            raise ValueError("RESEARCH_BACKUP_SYMLINK_REJECTED")
        if (
            set(relative.parts) & OMIT
            or relative.parts[0] == "control"
            or source.name.endswith(("-wal", "-shm", ".lock", ".tmp"))
            or not source.is_file()
        ):
            continue
        result.append(source)
    return sorted(result)


def _immutable_inventory(roots: dict[str, Path]) -> dict[str, str]:
    return {
        label + "/" + path.relative_to(root).as_posix(): digest(path.read_bytes())
        for label, root in roots.items()
        for path in _files(root)
        if path.suffix != ".sqlite3"
    }


def _ledger(path: Path) -> dict[str, Any]:
    """Online logical evidence; no source pragma, checkpoint or schema mutation."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        forecasts = connection.execute(
            "SELECT id,body FROM experimental_forecasts ORDER BY id"
        ).fetchall()
        outcomes = connection.execute(
            "SELECT id,body FROM experimental_outcomes ORDER BY id"
        ).fetchall()
    return {
        "forecasts": len(forecasts),
        "outcome_revisions": len(outcomes),
        "logical_sha256": digest(encoded({"forecasts": forecasts, "outcomes": outcomes})),
    }


def _extended_evidence(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if (root / "nse-universe").exists():
        snapshot = universe.load(root / "nse-universe")
        result["universe_snapshot_id"] = snapshot.snapshot_id
        result["verified_current_common_equities"] = len(snapshot.eligible)
    expanded = root / "nse-market-expansion"
    if expanded.exists():
        # Saved workspace validates source/model-score hashes without inference.
        workspace = engine.workspace(expanded, root / "v2")
        result["expanded_coverage"] = workspace.get("coverage", {})
        result["expanded_scored_securities"] = len(workspace.get("candidates", []))
        ledgers = {}
        for path in sorted(expanded.rglob("experimental-v2-prospective.sqlite3")):
            evidence = _ledger(path)
            checked = summary(path.parent)
            if checked["forecasts"] != evidence["forecasts"]:
                raise ValueError("RESEARCH_BUNDLE_EXPANDED_FORECAST_MISMATCH")
            ledgers[path.relative_to(expanded).as_posix()] = evidence
        result["expanded_ledgers"] = ledgers
        result["expanded_forecasts"] = sum(value["forecasts"] for value in ledgers.values())
    sequence = root / "sequence-benchmark-v1"
    if sequence.exists():
        if not (sequence / "report.json").exists():
            result["sequence_state"] = "INCOMPLETE_UNPUBLISHED_FILES_PRESERVED_ONLY"
            return result
        model = engine._read(sequence / "model.json")
        report = engine._read(sequence / "report.json")
        historical = engine._read(sequence / "historical-predictions.json")
        model_sha = digest((sequence / "model.json").read_bytes())
        if (
            report["model_sha256"] != model_sha
            or historical["model_sha256"] != model_sha
            or report["protocol_sha256"] != model["protocol_sha256"]
            or report["accepted_rankings"] != 0
        ):
            raise ValueError("RESEARCH_BUNDLE_SEQUENCE_MODEL_HASH_MISMATCH")
        result["sequence_model_sha256"] = model_sha
        result["sequence_current_scores"] = len(report["current_scores"])
        result["sequence_historical_predictions"] = len(historical["rows"])
    return result


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
    extended = _extended_evidence(root)
    if extended != manifest.get("expanded_evidence", {}):
        raise ValueError("RESEARCH_BUNDLE_EXPANDED_EVIDENCE_MISMATCH")
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
        "expanded_evidence": extended,
    }


def backup(target: Path, *, include_expanded: bool = True) -> dict[str, Any]:
    config = json.loads((REPO / ".local-data/p33-runtime/operator-config.json").read_bytes())
    roots = {
        "v1": Path(config["experimental_nse_root"]),
        "v2": Path(config["experimental_nse_v2_root"]),
    }
    if include_expanded:
        for label in EXPANDED_LABELS:
            root = roots["v2"].parent / label
            if root.exists():
                roots[label] = root
    if any(
        target.absolute().resolve().is_relative_to(source.resolve()) for source in roots.values()
    ):
        raise ValueError("RESEARCH_BACKUP_DESTINATION_MUST_BE_OUTSIDE_ACTIVE_ROOTS")
    target = destination(target)
    with ExitStack() as locks:
        for label, source_root in roots.items():
            verify(source_root)
            private_path(source_root)
            candidates = (
                ("workflow-control", "capture-control")
                if label == "v2"
                else ("control",)
                if label == "nse-market-expansion"
                else ()
            )
            for child in candidates:
                if (source_root / child).is_dir():
                    locks.enter_context(Store(private_path(source_root, child)).lock())
        before = _immutable_inventory(roots)
        source_ledgers = {
            label + "/" + path.relative_to(root).as_posix(): _ledger(path)
            for label, root in roots.items()
            for path in _files(root)
            if label == "nse-market-expansion"
            and path.name == "experimental-v2-prospective.sqlite3"
        }
        for label, source_root in roots.items():
            for source in _files(source_root):
                relative = source.relative_to(source_root)
                copy_file(source, private_path(target, label, *relative.parts))
        if _immutable_inventory(roots) != before:
            raise ValueError("RESEARCH_SOURCE_CHANGED_DURING_BACKUP_RETRY_WHEN_IDLE")
        for relative_ledger, evidence in source_ledgers.items():
            if _ledger(private_path(target, *Path(relative_ledger).parts)) != evidence:
                raise ValueError("RESEARCH_ONLINE_FORECAST_SNAPSHOT_MISMATCH")
    for source in (REPO / "docs/development").glob("*registered-protocol.md"):
        copy_file(source, private_path(target, "protocols", source.name))
    v2_forward = summary(target / "v2/price-only")
    expanded_evidence = _extended_evidence(target)
    files = {
        str(path.relative_to(target)): digest(path.read_bytes())
        for path in target.rglob("*")
        if path.is_file()
    }
    body = encoded(
        {
            "version": "private.research.backup.2"
            if expanded_evidence
            else "private.research.backup.1",
            "created_at": datetime.now(UTC).isoformat(),
            "v2_forecasts": v2_forward["forecasts"],
            "files": files,
            "scope": (
                "V1_V2_EXPANDED_NSE_SEQUENCE_RESEARCH_NO_CREDENTIALS_OR_PERSONAL_OR_POSTGRESQL"
                if expanded_evidence
                else "V1_V2_RESEARCH_ONLY_NO_CREDENTIALS_OR_PERSONAL_OR_POSTGRESQL"
            ),
            "root_labels": list(roots),
            "expanded_evidence": expanded_evidence,
        }
    )
    write_new(target / "manifest.json", body)
    write_new(target / "manifest.sha256", digest(body).encode("ascii"))
    return validate(target)


def restore(source: Path, target: Path) -> dict[str, Any]:
    validate(source)
    if target.absolute().resolve().is_relative_to(source.resolve()):
        raise ValueError("RESEARCH_RESTORE_DESTINATION_MUST_BE_OUTSIDE_SOURCE_BUNDLE")
    target = destination(target)
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if path.is_symlink() or path.is_junction():
            raise ValueError("RESEARCH_RESTORE_SYMLINK_REJECTED")
        if path.is_file() and not path.name.endswith(("-wal", "-shm")):
            copy_file(path, private_path(target, *relative.parts))
    return validate(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "restore", "verify"))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--legacy-only", action="store_true", help="Only original V1/V2 roots")
    args = parser.parse_args()
    if args.operation == "verify" and args.source:
        result = validate(args.source)
    elif args.operation == "backup" and args.destination:
        result = backup(args.destination, include_expanded=not args.legacy_only)
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
