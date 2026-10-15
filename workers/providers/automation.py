"""Windows scheduler preparation, with source/retention gates before any network I/O."""

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.daily.contracts import Calendar
from alphalens_data.daily.storage import Store
from alphalens_data.providers.multi_contracts import Access

from .daily import configured_pipeline
from .session_plan import Release, plan


def readiness(
    access: Access, calendar: Calendar, at: datetime, pipeline_root: Path | None = None
) -> dict[str, Any]:
    blockers = list(access.blockers(at))
    if not calendar.sessions or any(
        s.evidence_type != "OFFICIAL_VERIFIED_SESSION" for s in calendar.sessions
    ):
        blockers.append("AUTHORITATIVE_EXCHANGE_CALENDAR_REQUIRED")
    # Collection and model evidence are distinct. The P19 operational staging path
    # preserves UNKNOWN basis and never silently promotes it into model features.
    if not access.retention_permitted:
        blockers.append("LOCAL_RETENTION_PERMISSION_NOT_ESTABLISHED")
    if not access.research_permitted:
        blockers.append("PRIVATE_ML_RESEARCH_PERMISSION_NOT_ESTABLISHED")
    verified_release = False
    if pipeline_root is not None and pipeline_root.is_dir():
        store = Store(pipeline_root)
        verified_release = any(
            r["mode"] == "DAILY"
            and r["identity"]["provider"]["source"] == "upstox"
            and r["state"] == "COMPLETED_WITH_WARNINGS"
            and r["counts"].get("observations", 0) > 0
            and "provider_observations" in r["products"]
            for r in store.receipts()
        )
    if not verified_release:
        blockers.append("RETAINED_P19_OPERATIONAL_RELEASE_NOT_LIVE_VERIFIED")
    return {
        "state": "BLOCKED_EVIDENCE" if blockers else "READY_FOR_OPERATOR_TASK_ACTIVATION",
        "scheduler_enabled": False,
        "network_calls": 0,
        "blockers": sorted(set(blockers)),
        "model_eligibility": "INDEPENDENT_FROM_DATA_COLLECTION",
        "worker_adapter": "UPSTOX_OPERATIONAL_STAGING_SUPPORTED_SOURCE_GATED",
        "model_blockers": [
            "PRICE_BASIS_SERIES_PUBLICATION_AND_ACTION_EVIDENCE_REQUIRED",
            "COMPLETE_DATED_PEER_UNIVERSE_REQUIRED",
            "INDEPENDENT_MODEL_ACCEPTANCE_NOT_PASSED",
        ],
    }


def catch_up(calendar: Calendar, at: datetime, pipeline_root: Path) -> dict[str, Any]:
    """Use checksum-verified completed receipts instead of reporting captured days pending."""
    selected: dict[date, dict[str, Any]] = {}
    if pipeline_root.is_dir():
        for receipt in Store(pipeline_root).receipts():
            if (
                receipt["mode"] != "DAILY"
                or receipt["identity"]["provider"]["source"] != "upstox"
                or receipt["state"] != "COMPLETED_WITH_WARNINGS"
                or receipt["counts"].get("observations", 0) <= 0
                or receipt["counts"].get("missing", 0) != 0
                or datetime.fromisoformat(receipt["source_received_at"]) > at
                or datetime.fromisoformat(receipt["completed_at"]) > at
            ):
                continue
            day = date.fromisoformat(receipt["session"])
            if calendar.sessions[0].session <= day <= calendar.sessions[-1].session:
                previous = selected.get(day)
                if previous is None or receipt["completed_at"] > previous["completed_at"]:
                    selected[day] = receipt
    releases = tuple(
        Release(
            provider="upstox",
            session=day,
            revision_sha256=receipt["identity"]["payload_sha256"],
            observed_at=datetime.fromisoformat(receipt["source_received_at"]),
            complete=True,
        )
        for day, receipt in sorted(selected.items())
    )
    return plan(
        calendar,
        calendar.sessions[0].session,
        calendar.sessions[-1].session,
        at,
        "upstox",
        releases=releases,
        accepted={r.session: r.revision_sha256 for r in releases},
    )


def task_xml(config: Path, *, update_hour: int = 19, update_minute: int = 30) -> bytes:
    if not config.is_absolute() or not 0 <= update_hour <= 23 or not 0 <= update_minute <= 59:
        raise ValueError("LOCAL_TASK_PARAMETERS_INVALID")
    repo = Path(__file__).resolve().parents[2]
    command = escape(str(repo / "scripts/windows/p30-daily-update.cmd"))
    arguments = escape('"' + str(config) + '"')
    directory = escape(str(repo))
    start = datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=1)
    boundary = f"{start}T{update_hour:02}:{update_minute:02}:00+05:30"
    return f"""<?xml version="1.0"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
<RegistrationInfo>
<Description>AlphaLens daily readiness; mandatory source retention gates</Description>
</RegistrationInfo>
<Triggers>
<CalendarTrigger>
<StartBoundary>{boundary}</StartBoundary>
<Enabled>false</Enabled>
<ScheduleByDay>
<DaysInterval>1</DaysInterval>
</ScheduleByDay>
</CalendarTrigger>
</Triggers>
<Principals>
<Principal id="LocalOperator">
<LogonType>InteractiveToken</LogonType>
<RunLevel>LeastPrivilege</RunLevel>
</Principal>
</Principals>
<Settings>
<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
<StartWhenAvailable>true</StartWhenAvailable>
<ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
<Enabled>false</Enabled>
</Settings>
<Actions Context="LocalOperator">
<Exec>
<Command>{command}</Command>
<Arguments>{arguments}</Arguments>
<WorkingDirectory>{directory}</WorkingDirectory>
</Exec>
</Actions>
</Task>""".encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--export-task", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.config.read_bytes())
        if len(args.config.read_bytes()) > 100000:
            raise ValueError("AUTOMATION_CONFIG_LIMIT")
        access = Access.model_validate(value["access"])
        calendar = Calendar.model_validate(value["calendar"])
        at = datetime.now(UTC)
        result = readiness(
            access,
            calendar,
            at,
            configured_pipeline(value, Path(__file__).resolve().parents[2]),
        )
        result["catch_up"] = catch_up(
            calendar, at, configured_pipeline(value, Path(__file__).resolve().parents[2])
        )
        if args.export_task:
            with args.export_task.open("xb") as stream:
                stream.write(task_xml(args.config.resolve()))
            result["task_exported_disabled"] = True
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError):
        print(
            json.dumps(
                {"state": "DAILY_SETUP_REJECTED", "scheduler_enabled": False, "network_calls": 0}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
