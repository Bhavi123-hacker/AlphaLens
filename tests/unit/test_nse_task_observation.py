"""TEST_ONLY saved monitoring metadata; no Task Scheduler or provider operations."""

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest
from scripts.observe_nse_task import query_command
from workers.nse_market.task_observation import NAME, validate


@pytest.mark.parametrize("bad", ["policy", "future", "mutated", "requests", "result"])
def test_rejects_unqualified_saved_windows_observations(bad: str) -> None:
    value = {
        "task_name": NAME,
        "policy_sha256": "a" * 64,
        "observed_at": datetime.now(UTC).isoformat(),
        "last_run_at": None,
        "next_run_at": None,
        "last_result": 267014,
        "enabled": True,
        "action_matches": True,
        "provider_requests": 0,
        "tasks_modified": False,
    }
    validate(value, "a" * 64)
    if bad == "policy":
        value["policy_sha256"] = "b" * 64
    elif bad == "future":
        value["observed_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    elif bad == "mutated":
        value["tasks_modified"] = True
    elif bad == "requests":
        value["provider_requests"] = 1
    else:
        value["last_result"] = "0"
    with pytest.raises(ValueError):
        validate(value, "a" * 64)


@pytest.mark.skipif(sys.platform != "win32", reason="Executes isolated Windows PowerShell")
@pytest.mark.parametrize("code", [0, 267014, 3221225786, 4294967295])
def test_windows_query_retains_unsigned_task_results(code: int) -> None:
    # TEST_ONLY functions shadow both cmdlets: no real task/provider is inspected
    # or changed. Exercise the actual observer projection and JSON serialization.
    fixture = (
        "function Get-ScheduledTask { param($TaskName) "
        "[pscustomobject]@{Settings=@{Enabled=$true};State='Ready';Actions=@();"
        "Principal=@{RunLevel='Limited';LogonType='Interactive'}} };"
        "function Get-ScheduledTaskInfo { param($TaskName) "
        f"[pscustomobject]@{{LastTaskResult=[uint32]{code};"
        "LastRunTime=[datetime]'2026-10-19T21:30:00';"
        "NextRunTime=[datetime]'2026-10-19T22:30:00'} };"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", fixture + query_command()],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
        creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
    )
    value = json.loads(result.stdout)
    assert type(value["last_result"]) is int
    assert value["last_result"] == code
    assert value["state"] == "Ready"
    assert value["actions"] == []
