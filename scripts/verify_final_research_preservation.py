"""Read-only research/account/credential preservation, with a private pinned baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import restrict, verify
from alphalens_api.credentials import credential_module

REPO = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = REPO / ".local-data/final-operational-runtime/preservation-baseline.json"
EXCLUDED_PARTS = {"workflow", "workflow-control", "capture-control", "__pycache__"}
MUTABLE_POINTERS = {"latest-inference.txt", "latest-capture.json", "latest-capture.sha256"}


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("PRESERVATION_REGULAR_FILE_REQUIRED")
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def logical_database(path: Path, query: str) -> list[Any]:
    verify(path, directory=False)
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        return connection.execute(query).fetchall()


def credential_inventory() -> dict[str, Any]:
    module = credential_module()
    records = module.CredEnumerate("AlphaLens/*", 0)
    result = {}
    for record in records:
        blob = record["CredentialBlob"]
        raw = blob if isinstance(blob, bytes) else str(blob).encode("utf-16-le")
        result[record["TargetName"]] = {
            "blob_sha256": hashlib.sha256(raw).hexdigest(),
            "type": record["Type"],
            "persist": record["Persist"],
            "username_sha256": hashlib.sha256(str(record.get("UserName", "")).encode()).hexdigest(),
        }
    if "AlphaLens/UpstoxReadOnlyAnalytics" not in result:
        raise ValueError("ORIGINAL_PROVIDER_CREDENTIAL_REQUIRED")
    return result


def ledger_snapshot(path: Path) -> dict[str, Any]:
    rows = logical_database(path, "SELECT id,body FROM experimental_forecasts ORDER BY id")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        schema = connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()
    return {
        "path": str(path),
        "schema_sha256": hashlib.sha256(encoded(schema)).hexdigest(),
        "forecast_bodies": {
            identity: hashlib.sha256(body.encode()).hexdigest() for identity, body in rows
        },
    }


def config_inventory(paths: list[Path]) -> list[dict[str, Any]]:
    result = []
    for path in paths:
        verify(path, directory=False)
        value = json.loads(path.read_bytes())
        projection = {key: item for key, item in value.items() if key != "frontend_root"}
        result.append(
            {
                "path": str(path),
                "file_sha256": digest(path),
                "protected_projection_sha256": hashlib.sha256(encoded(projection)).hexdigest(),
                "permitted_changed_field": "frontend_root",
            }
        )
    return result


def create_snapshot() -> dict[str, Any]:
    native_config = REPO / ".local-data/p33-runtime/operator-config.json"
    configs = [native_config, REPO / ".local-data/p33-browser-runtime/operator-config.json"]
    native = json.loads(native_config.read_bytes())
    v1 = Path(native["experimental_nse_root"])
    v2 = Path(native["experimental_nse_v2_root"])
    files: dict[str, str] = {}
    for root in (v1, v2):
        verify(root)
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if (
                set(relative.parts) & EXCLUDED_PARTS
                or path.name in MUTABLE_POINTERS
                or path.suffix in {".sqlite3", ".lock", ".tmp"}
                or path.name.endswith(("-wal", "-shm"))
            ):
                continue
            if path.is_symlink():
                raise ValueError("PRESERVATION_SYMLINK_FORBIDDEN")
            if path.is_file():
                files[str(path)] = digest(path)
    for name in (
        "ml-v2-registered-protocol.md",
        "ml-v2-price-only-registered-protocol.md",
        "experimental-nse-v1-predeclared-study.md",
    ):
        path = REPO / "docs/development" / name
        files[str(path)] = digest(path)
    auth = Path(native["auth_root"]) / "auth.sqlite3"
    personal = Path(native["personal_root"]) / "personal.sqlite3"
    accounts = logical_database(auth, "SELECT * FROM accounts ORDER BY account_id")
    records = logical_database(
        personal,
        "SELECT owner,kind,id,body,revision,updated_at FROM records ORDER BY owner,kind,id",
    )
    ledgers = [
        ledger_snapshot(v1 / "experimental-prospective.sqlite3"),
        ledger_snapshot(v2 / "price-only/experimental-v2-prospective.sqlite3"),
    ]
    return {
        "version": "final.research.preservation.1",
        "created_at": datetime.now(UTC).isoformat(),
        "research_roots": {"v1": str(v1), "v2": str(v2)},
        "immutable_files": files,
        "configurations": config_inventory(configs),
        "accounts": {
            "path": str(auth),
            "count": len(accounts),
            "sha256": hashlib.sha256(encoded(accounts)).hexdigest(),
        },
        "personal": {
            "path": str(personal),
            "count": len(records),
            "sha256": hashlib.sha256(encoded(records)).hexdigest(),
        },
        "credentials": credential_inventory(),
        "ledgers": ledgers,
        "excluded": {
            "workflow_metadata": True,
            "sqlite_container_bytes": True,
            "auth_sessions": True,
            "future_pointer_moves": sorted(MUTABLE_POINTERS),
        },
    }


def verify_snapshot(baseline: dict[str, Any]) -> dict[str, Any]:
    checked = 0
    for name, checksum in baseline["immutable_files"].items():
        if digest(Path(name)) != checksum:
            raise ValueError("ORIGINAL_RESEARCH_FILE_CHANGED")
        checked += 1
    config_changes = 0
    for before, after in zip(
        baseline["configurations"],
        config_inventory([Path(item["path"]) for item in baseline["configurations"]]),
        strict=True,
    ):
        if before["protected_projection_sha256"] != after["protected_projection_sha256"]:
            raise ValueError("PROTECTED_NATIVE_CONFIGURATION_CHANGED")
        config_changes += int(before["file_sha256"] != after["file_sha256"])
    for label, query in (
        ("accounts", "SELECT * FROM accounts ORDER BY account_id"),
        (
            "personal",
            "SELECT owner,kind,id,body,revision,updated_at FROM records ORDER BY owner,kind,id",
        ),
    ):
        rows = logical_database(Path(baseline[label]["path"]), query)
        if hashlib.sha256(encoded(rows)).hexdigest() != baseline[label]["sha256"]:
            raise ValueError("ORIGINAL_ACCOUNT_OR_PERSONAL_RECORD_CHANGED")
    if credential_inventory() != baseline["credentials"]:
        raise ValueError("PROTECTED_CREDENTIAL_INVENTORY_CHANGED")
    forecasts = 0
    for ledger in baseline["ledgers"]:
        current = ledger_snapshot(Path(ledger["path"]))
        if current["schema_sha256"] != ledger["schema_sha256"]:
            raise ValueError("ORIGINAL_LEDGER_SCHEMA_CHANGED")
        for identity, checksum in ledger["forecast_bodies"].items():
            if current["forecast_bodies"].get(identity) != checksum:
                raise ValueError("ORIGINAL_FORECAST_BODY_CHANGED")
            forecasts += 1
    return {
        "state": "PASS",
        "immutable_file_count": checked,
        "original_forecast_bodies": forecasts,
        "v2_original_forecast_bodies": len(baseline["ledgers"][1]["forecast_bodies"]),
        "credential_count": len(baseline["credentials"]),
        "credential_hashes_match": True,
        "accounts_match": True,
        "personal_records_match": True,
        "protected_configuration_fields_match": True,
        "configuration_files_with_permitted_frontend_change": config_changes,
        "workflow_metadata_excluded": True,
        "provider_requests": 0,
        "original_state_modified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--create-baseline", action="store_true")
    args = parser.parse_args()
    if args.create_baseline:
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        restrict(args.baseline.parent)
        baseline = create_snapshot()
        if len(baseline["ledgers"][1]["forecast_bodies"]) != 31:
            raise ValueError("EXPECTED_ORIGINAL_31_V2_FORECASTS_REQUIRED")
        body = encoded(baseline)
        with args.baseline.open("xb") as stream:
            stream.write(body)
        with args.baseline.with_suffix(".sha256").open("xb") as stream:
            stream.write(hashlib.sha256(body).hexdigest().encode())
    verify(args.baseline, directory=False)
    if digest(args.baseline) != args.baseline.with_suffix(".sha256").read_text(encoding="ascii"):
        raise ValueError("PRESERVATION_BASELINE_CHECKSUM_REJECTED")
    print(json.dumps(verify_snapshot(json.loads(args.baseline.read_bytes()))))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"FAIL","code":"PRESERVATION_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
