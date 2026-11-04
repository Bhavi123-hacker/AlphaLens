"""Read-only local AlphaLens evidence check. No provider GETs or database writes.

Usage (Windows):
    python scripts/check_local_release.py --root D:\\al-research\\p28-worktree\\.campaign-worktree
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.audit_existing_exchange_horizons import audit_existing_horizons  # noqa: E402


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _safe_market_path(pointer: Path, target: str) -> Path | None:
    if not target or not isinstance(target, str):
        return None
    candidate = (pointer.parent / target).resolve()
    if not candidate.is_relative_to(pointer.parent.resolve()):
        return None
    return candidate


def market_view_status(pointer: Path) -> dict[str, Any]:
    doc = read_json(pointer)
    if doc is None:
        return {"status": "MISSING_OR_INVALID_POINTER", "path": str(pointer)}
    view = _safe_market_path(pointer, doc.get("path", ""))
    if view is None:
        return {"status": "POINTER_OUTSIDE_APPROVED_DIRECTORY"}
    market = read_json(view)
    if market is None:
        return {"status": "MISSING_OR_INVALID_MARKET_VIEW", "path": str(view)}
    histories = market.get("histories")
    if not isinstance(histories, dict):
        return {"status": "MARKET_VIEW_HISTORIES_UNAVAILABLE"}

    observations: Counter[str] = Counter()
    total = 0
    for key, candles in histories.items():
        if not (isinstance(key, str) and key.startswith("NSE_EQ|")):
            continue
        if not isinstance(candles, list):
            continue
        unique_sessions: set[str] = set()
        for bar in candles:
            if not isinstance(bar, dict):
                continue
            raw = bar.get("session") or bar.get("date") or bar.get("timestamp")
            session = str(raw)[:10] if raw is not None else ""
            try:
                date.fromisoformat(session)
            except ValueError:
                continue
            unique_sessions.add(session)
            total += 1
        for session in unique_sessions:
            observations[session] += 1

    latest = max(observations, default=None)
    return {
        "status": "SAVED_MARKET_VIEW_INSPECTED",
        "latest_observation_session": latest,
        "equities_with_latest_session": observations[latest] if latest else 0,
        "equities_with_any_history": sum(
            isinstance(h, list) and len(h) > 0
            for k, h in histories.items()
            if isinstance(k, str) and k.startswith("NSE_EQ|")
        ),
        "parsed_candles": total,
        "data_verified_as_authorized": False,
        "qualification_note": (
            "Session presence is not proof of source rights, complete OHLCV quality, "
            "or prospective model acceptance."
        ),
    }


def _find_path(root: Path, relative: str) -> Path:
    for base in (root, root.parent):
        candidate = base / relative
        if candidate.is_file():
            return candidate
    return root / relative


def daily_receipt_status(pointer: Path) -> dict[str, Any]:
    document = read_json(pointer)
    if document is None:
        return {"status": "UNAVAILABLE", "path": str(pointer)}
    receipt = document
    checked = False
    if "path" in document:
        target = _safe_market_path(pointer, document["path"])
        if target is None:
            return {"status": "POINTER_OUTSIDE_APPROVED_DIRECTORY"}
        pointed = read_json(target)
        if pointed is None:
            return {"status": "POINTED_RECEIPT_UNAVAILABLE"}
        receipt = pointed
        checksum = target.with_suffix(target.suffix + ".sha256")
        if checksum.is_file():
            checked = (
                hashlib.sha256(target.read_bytes()).hexdigest()
                == checksum.read_text(encoding="utf-8").strip()
            )
            if not checked:
                return {"status": "RECEIPT_SHA256_MISMATCH"}
    return {
        "status": "AVAILABLE",
        "session": receipt.get("session"),
        "state": receipt.get("state"),
        "completed_at": receipt.get("completed_at"),
        "checksum_verified": checked,
    }


def ledger_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "LOCAL_LEDGER_NOT_FOUND", "path": str(path)}
    sha = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    audit = audit_existing_horizons(path)
    result: dict[str, Any] = {
        "status": audit.get("status", "UNKNOWN"),
        "sha256": sha,
        "total_legacy_outcomes": audit.get("total"),
        "aligned": audit.get("aligned"),
        "misaligned": audit.get("misaligned"),
        "unverifiable": audit.get("unverifiable"),
        "independent_acceptance_unlocked": False,
        "database_mutated": False,
    }
    if audit.get("status") == "EXCHANGE_SESSION_WINDOWS_ALIGNED":
        result["note"] = "Chronology aligned; provenance and acceptance require separate checks."
    else:
        result["note"] = "Fail closed; do not use legacy outcomes for independent acceptance."
    return result


def dashboard_status(url: str) -> dict[str, Any]:
    if url != "http://127.0.0.1:8041/api/v1/health/live":
        return {"status": "UNAPPROVED_HEALTH_URL"}
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            payload = response.read(8192)
            return {
                "status": "HTTP_HEALTH_REACHABLE" if response.status == 200 else "HEALTH_ERROR",
                "http_status": response.status,
                "response": json.loads(payload.decode("utf-8")),
                "full_data_pipeline_verified": False,
            }
    except (OSError, ValueError, UnicodeError, urllib.error.URLError):
        return {"status": "LOCAL_HEALTH_UNREACHABLE"}


def task_status(name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"status": "WINDOWS_TASK_CHECK_NOT_SUPPORTED_ON_THIS_HOST"}
    try:
        run = subprocess.run(
            ["schtasks", "/query", "/tn", name, "/fo", "LIST", "/v"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "TASK_QUERY_FAILED"}
    if run.returncode != 0:
        return {"status": "TASK_NOT_REGISTERED_OR_UNREADABLE", "exit_code": run.returncode}
    fields = {}
    for line in run.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip().lower() in {
                "status",
                "last result",
                "last run time",
                "next run time",
                "scheduled task state",
            }:
                fields[key.strip()] = value.strip()
    return {"status": "TASK_REGISTERED", "observed_fields": fields}


def full_universe_status(root: Path) -> str:
    rankings_path = root / "docs" / "ml" / "full_universe_rankings_20261102.json"
    retraining_path = root / "docs" / "ml" / "automated_retraining_receipt.json"
    if rankings_path.exists() and retraining_path.exists():
        try:
            rankings = json.loads(rankings_path.read_text(encoding="utf-8"))
            retraining = json.loads(retraining_path.read_text(encoding="utf-8"))
            if (
                rankings.get("universe_summary", {}).get("total_searchable_listings") == 8169
                and retraining.get("lifecycle_state", {}).get("training_state")
                == "TRAINING_SUCCESS"
            ):
                return "FULL_UNIVERSE_V2_COMPLETE"
        except Exception:
            pass
    return "FULL_UNIVERSE_V2_GATED"


def git_status(root: Path) -> dict[str, Any]:
    try:
        cmd = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if cmd.returncode != 0:
            return {"status": "GIT_METADATA_UNAVAILABLE"}
        return {"status": "GIT_HEAD_OBSERVED", "head": cmd.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "GIT_METADATA_UNAVAILABLE"}


def inspect(root: Path, *, check_tasks: bool) -> dict[str, Any]:
    root = root.resolve()
    pointer = _find_path(root, ".local-data/nse-market-expansion/market-view-latest.json")
    ledger = _find_path(root, "data/forecasts/matured_outcomes_ledger.db")
    daily = _find_path(root, ".local-data/nse-market-expansion/daily-latest.json")
    result: dict[str, Any] = {
        "schema": "alphalens.local_read_only_verification.v1",
        "workspace": str(root),
        "provider_requests_made": 0,
        "file_writes_performed": 0,
        "git": git_status(root),
        "dashboard": dashboard_status("http://127.0.0.1:8041/api/v1/health/live"),
        "market_view": market_view_status(pointer),
        "last_daily_receipt": daily_receipt_status(daily),
        "legacy_maturation_ledger": ledger_status(ledger),
        "full_universe": full_universe_status(root),
    }
    if check_tasks:
        result["tasks"] = {
            "private_nse_collection": task_status("AlphaLens-Private-NSE-Market-Research"),
            "v2_settlement": task_status("AlphaLens-Daily-Settlement-V2"),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--check-windows-tasks", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect(args.root, check_tasks=args.check_windows_tasks), indent=2))


if __name__ == "__main__":
    main()
