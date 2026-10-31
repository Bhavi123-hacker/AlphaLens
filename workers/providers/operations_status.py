"""Read-only private collection status; prices and local paths never leave this projection."""

import json
import stat
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


def _reject_reparse(path: Path) -> None:
    for item in (path, *path.parents):
        try:
            metadata = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 1024:
            raise ValueError("PRIVATE_EOD_STATUS_REPARSE_REJECTED")


def status(config_path: Path | None, *, owner_root: Path | None = None) -> dict[str, Any]:
    """Read existing evidence; optional owner comes only from trusted local settings.

    A release's code checkout need not own its configured private data. Explicit
    owners still require the protected direct .local-data configuration layout,
    original operational namespace checks and non-reparse paths.
    """
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
    _reject_reparse(config_path)
    repo = Path(__file__).resolve().parents[2]
    if owner_root is not None:
        repo = owner_root.absolute()
        _reject_reparse(repo)
        if config_path.absolute().parent.parent != repo / ".local-data":
            raise ValueError("PRIVATE_EOD_STATUS_CONFIG_OWNER_MISMATCH")
        # The existing private configuration directory is the ACL boundary;
        # its shared .local-data parent also contains nonsensitive build output.
        verify(config_path, directory=False)
    verify(config_path.parent)
    if config_path.stat().st_size > 100000:
        raise ValueError("PRIVATE_EOD_CONFIG_SIZE_LIMIT")
    config = json.loads(config_path.read_bytes())
    declared_root = config.get("pipeline_root")
    if isinstance(declared_root, str):
        _reject_reparse(Path(declared_root).absolute())
    root = configured_pipeline(config, repo)
    _reject_reparse(root)
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
