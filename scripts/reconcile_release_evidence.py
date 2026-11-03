"""Read-only release-evidence reconciliation for AlphaLens.

This utility never creates databases, settles forecasts, or changes scheduled
tasks. Committed attestation counts are historical claims, not live evidence.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED: {path}")
    return document


def reconcile_attestation(path: Path) -> dict[str, Any]:
    """Reconcile snapshot counts without treating them as current disk state."""
    if not path.is_file():
        return {"status": "COMMITTED_ATTESTATION_MISSING", "path": str(path)}
    doc = _read_json(path)
    counts = doc.get("equity_counts", {})
    exchanges = doc.get("ordinary_equities_by_exchange", {})
    sources = doc.get("sources", {})
    nse = int(exchanges.get("NSE", 0))
    bse = int(exchanges.get("BSE", 0))
    catalog = int(counts.get("E_searchable_unique_instrument_keys", 0))
    candles = int(sources.get("accepted_candles", 0))
    errors: list[str] = []
    if nse + bse != catalog:
        errors.append("EXCHANGE_SUM_NOT_EQUAL_TO_SEARCHABLE_CATALOG")
    if int(counts.get("G_securities_with_history", 0)) > nse:
        errors.append("NSE_HISTORY_COUNT_EXCEEDS_NSE_CATALOG")
    return {
        "status": "RECONCILED_COMMITTED_SNAPSHOT" if not errors else "SNAPSHOT_INCONSISTENT",
        "evidence_level": "COMMITTED_ATTESTATION_ONLY_NOT_LIVE_DISK_VERIFIED",
        "attested_at": doc.get("attested_at"),
        "catalog_total": catalog,
        "nse_catalog": nse,
        "bse_catalog": bse,
        "unique_company_isins": counts.get("F_unique_company_isins"),
        "nse_cohort_with_history": counts.get("G_securities_with_history"),
        "latest_observed_session": counts.get("H_observation_session"),
        "latest_session_stocks": counts.get("H_securities_with_latest_completed_retained_session"),
        "verified_retained_candles_in_attestation": candles,
        "model_vectors": counts.get("I_complete_model_vectors"),
        "prospective_latest_forecasts": counts.get("J_current_future_entry_eligible_predictions"),
        "accepted_model_forecasts": counts.get("K_independently_accepted_predictions"),
        "errors": errors,
    }


def inspect_ledger_readonly(path: Path) -> dict[str, Any]:
    """Use SQLite mode=ro: a missing or inaccessible DB is never created."""
    if not path.is_file():
        return {"status": "LOCAL_LEDGER_NOT_AVAILABLE", "path": str(path)}
    try:
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            conn.execute("PRAGMA query_only = ON")
            check = conn.execute("PRAGMA integrity_check").fetchone()
            if check is None or check[0] != "ok":
                return {"status": "LEDGER_SQLITE_INTEGRITY_FAILED", "path": str(path)}
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(matured_forecasts)")
            }
            required = {
                "forecast_id",
                "model_id",
                "instrument_key",
                "forecast_session",
                "benchmark_source",
                "record_hash",
            }
            missing = sorted(required - columns)
            if missing:
                return {
                    "status": "LEGACY_LEDGER_SCHEMA_REQUIRES_REVIEW",
                    "path": str(path),
                    "missing_columns": missing,
                    "no_mutations_performed": True,
                }
            total, dates, instruments, models = conn.execute(
                "SELECT COUNT(*), COUNT(DISTINCT forecast_session), "
                "COUNT(DISTINCT instrument_key), COUNT(DISTINCT model_id) "
                "FROM matured_forecasts"
            ).fetchone()
            missing_hashes = conn.execute(
                "SELECT COUNT(*) FROM matured_forecasts "
                "WHERE record_hash IS NULL OR LENGTH(record_hash) = 0"
            ).fetchone()[0]
            bad_benchmarks = conn.execute(
                "SELECT COUNT(*) FROM matured_forecasts "
                "WHERE benchmark_source IN ('ZERO_BASELINE', 'BENCHMARK_UNAVAILABLE') "
                "OR benchmark_source IS NULL"
            ).fetchone()[0]
            by_model = [
                {
                    "model_id": model,
                    "outcomes": count,
                    "decision_dates": n_dates,
                    "securities": n_securities,
                }
                for model, count, n_dates, n_securities in conn.execute(
                    "SELECT model_id, COUNT(*), COUNT(DISTINCT forecast_session), "
                    "COUNT(DISTINCT instrument_key) "
                    "FROM matured_forecasts GROUP BY model_id ORDER BY model_id"
                )
            ]
            return {
                "status": "LOCAL_LEDGER_READ_ONLY_VERIFIED",
                "path": str(path),
                "sqlite_integrity": "ok",
                "total_matured": total,
                "distinct_decision_dates": dates,
                "distinct_securities": instruments,
                "distinct_models": models,
                "missing_record_hashes": missing_hashes,
                "unqualified_benchmark_rows": bad_benchmarks,
                "by_model": by_model,
                "no_mutations_performed": True,
                "note": (
                    "Hash field presence is checked; original source-body hash replay "
                    "needs local provenance"
                ),
            }
    except sqlite3.Error as exc:
        return {"status": "LOCAL_LEDGER_READ_FAILED", "error": str(exc), "path": str(path)}


def inspect_market_view_readonly(pointer: Path, target_session: str) -> dict[str, Any]:
    """Inspect local market-view dates; do not equate a view to full durable storage."""
    if not pointer.is_file():
        return {"status": "LOCAL_MARKET_VIEW_NOT_AVAILABLE", "path": str(pointer)}
    try:
        meta = _read_json(pointer)
        relative = meta.get("path")
        if not isinstance(relative, str) or not relative:
            return {"status": "MARKET_VIEW_POINTER_INVALID", "path": str(pointer)}
        document_path = (pointer.parent / relative).resolve()
        if not document_path.is_relative_to(pointer.parent.resolve()):
            return {"status": "MARKET_VIEW_PATH_OUTSIDE_DIRECTORY"}
        document = _read_json(document_path)
        histories = document.get("histories", {})
        if not isinstance(histories, dict):
            return {"status": "MARKET_VIEW_HISTORIES_INVALID"}
        nse = 0
        bse = 0
        session_stocks = 0
        for key, bars in histories.items():
            if not isinstance(bars, list):
                continue
            if str(key).startswith("NSE_EQ|"):
                nse += 1
            elif str(key).startswith("BSE_EQ|"):
                bse += 1
            if any(
                isinstance(bar, dict) and bar.get("session") == target_session
                for bar in bars
            ):
                session_stocks += 1
        return {
            "status": "LOCAL_MARKET_VIEW_READ_ONLY_INSPECTED",
            "snapshot_scope": "MARKET_VIEW_ONLY_NOT_COMPLETE_DURABLE_DATABASE",
            "path": str(document_path),
            "latest_session_checked": target_session,
            "instruments_in_view": len(histories),
            "nse_in_view": nse,
            "bse_in_view": bse,
            "session_stocks_in_view": session_stocks,
        }
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        return {"status": "LOCAL_MARKET_VIEW_READ_FAILED", "error": str(exc)}


def inspect_task_readonly() -> dict[str, Any]:
    """Query Windows Task Scheduler only; never register or change any task."""
    if sys.platform != "win32":
        return {"status": "WINDOWS_TASK_STATUS_NOT_VERIFIABLE_ON_THIS_RUNNER"}
    task = "AlphaLens-Daily-Settlement-V2"
    try:
        completed = subprocess.run(
            ["schtasks", "/query", "/tn", task, "/fo", "LIST", "/v"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return {
            "status": (
                "WINDOWS_TASK_QUERY_SUCCEEDED"
                if completed.returncode == 0
                else "WINDOWS_TASK_NOT_REGISTERED_OR_QUERY_FAILED"
            ),
            "task_name": task,
            "return_code": completed.returncode,
            "task_details": completed.stdout[-3000:] if completed.returncode == 0 else "",
            "read_only": True,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "WINDOWS_TASK_QUERY_FAILED", "error": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only AlphaLens release reconciliation")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--market-view-pointer", type=Path)
    parser.add_argument("--check-windows-task", action="store_true")
    parser.add_argument(
        "--out", type=Path, help="Optional JSON output; do not point to protected data"
    )
    args = parser.parse_args()
    root = args.root.resolve()
    ledger = args.ledger or root / "data" / "forecasts" / "matured_outcomes_ledger.db"
    pointer = args.market_view_pointer
    if pointer is None:
        candidates = [
            root.parent / ".local-data" / "nse-market-expansion" / "market-view-latest.json",
            root / ".local-data" / "nse-market-expansion" / "market-view-latest.json",
        ]
        pointer = next((p for p in candidates if p.exists()), candidates[-1])

    attestation = reconcile_attestation(
        root / "docs" / "release" / "ALPHALENS_PRIVATE_V1_RELEASE_ATTESTATION.json"
    )
    result: dict[str, Any] = {
        "schema": "alphalens.readonly_release_reconciliation.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "READ_ONLY_NO_COLLECTION_NO_SETTLEMENT",
        "attestation": attestation,
        "ledger": inspect_ledger_readonly(ledger),
        "market_view": inspect_market_view_readonly(
            pointer, str(attestation.get("latest_observed_session") or "2026-11-02")
        ),
        "daily_settlement_task": (
            inspect_task_readonly()
            if args.check_windows_task
            else {"status": "NOT_QUERIED", "note": "Pass --check-windows-task on Windows"}
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
