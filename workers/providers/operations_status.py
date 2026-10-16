"""Read-only private collection status; prices and local paths never leave this projection."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import verify
from alphalens_data.daily.contracts import Calendar
from alphalens_data.daily.storage import Store
from alphalens_data.providers.multi_contracts import Access

from .automation import readiness
from .daily import configured_pipeline
from .upstox import KEY


def status(config_path: Path | None) -> dict[str, Any]:
    if config_path is None:
        return {
            "configured": False,
            "selected_count": 0,
            "observations": 0,
            "latest_session": None,
            "scheduler_enabled": False,
            "task": None,
            "inference": "UNAVAILABLE",
            "cohort": [],
        }
    verify(config_path.parent)
    if config_path.stat().st_size > 100000:
        raise ValueError("PRIVATE_EOD_CONFIG_SIZE_LIMIT")
    config = json.loads(config_path.read_bytes())
    repo = Path(__file__).resolve().parents[2]
    root = configured_pipeline(config, repo)
    keys = config.get("instrument_keys", [config.get("instrument_key", KEY)])
    if not isinstance(keys, list) or not 1 <= len(keys) <= 6:
        raise ValueError("BOUNDED_SELECTED_DAILY_WATCHLIST_REQUIRED")
    cohort = []
    for key in keys:
        selected_root = (
            root if key == KEY else root / ("instrument-" + sha256(key.encode()).hexdigest()[:16])
        )
        receipts = Store(selected_root).receipts() if selected_root.is_dir() else []
        accepted = [
            r
            for r in receipts
            if r["mode"] == "DAILY"
            and r["state"] == "COMPLETED_WITH_WARNINGS"
            and r["counts"].get("observations", 0) > 0
        ]
        cohort.append(
            {
                "instrument_key": key,
                "observations": sum(r["counts"]["observations"] for r in accepted),
                "latest_session": max((r["session"] for r in accepted), default=None),
                "source": "UPSTOX_PRIVATE_OPERATIONAL_EOD",
                "historical_membership": "UNVERIFIED",
                "model_eligible": False,
            }
        )
    task_path = config_path.parent / "daily-task-status.json"
    last_run_path = config_path.parent / "daily-last-run.json"
    last_run = (
        json.loads(last_run_path.read_bytes())
        if last_run_path.is_file() and last_run_path.stat().st_size <= 100000
        else {}
    )
    task = None
    if task_path.is_file() and task_path.stat().st_size <= 8192:
        document = json.loads(task_path.read_bytes())
        task = {
            k: document.get(k)
            for k in (
                "name",
                "enabled",
                "state",
                "next_run",
                "run_level",
                "logon_type",
                "schedule",
                "publication_guarantee",
            )
        }
    return {
        "configured": True,
        "selected_count": len(keys),
        "observations": sum(c["observations"] for c in cohort),
        "latest_session": max(
            (c["latest_session"] for c in cohort if c["latest_session"]), default=None
        ),
        "scheduler_enabled": bool(task and task.get("enabled")),
        "task": task,
        "cohort": cohort,
        "inference": "UNAVAILABLE",
        "last_run_state": last_run.get("state"),
        "last_run_local_at": last_run.get("observed_at"),
        "last_run_reason": last_run.get("reason"),
        "readiness": readiness(
            Access.model_validate(config["access"]),
            Calendar.model_validate(config["calendar"]),
            datetime.now(UTC),
            root,
        ),
        "full_nse_coverage": False,
        "prices_in_status_response": False,
    }
