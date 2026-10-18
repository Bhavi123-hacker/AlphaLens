"""Explicit read-only Windows inspection; append private facts, never change a task."""

import argparse
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from workers.nse_market import engine, operational
from workers.nse_market.task_observation import NAME, validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise ValueError("WINDOWS_TASK_OBSERVATION_REQUIRED")
    config = operational.configured(args.config.resolve())
    policy = operational.policy(config)
    # All commands and the single task name are fixed; no shell interpolation.
    command = (
        "$ErrorActionPreference='Stop';"
        f"$t=Get-ScheduledTask -TaskName '{NAME}';"
        f"$i=Get-ScheduledTaskInfo -TaskName '{NAME}';"
        "@{enabled=[bool]$t.Settings.Enabled;state=[string]$t.State;"
        "last_result=[int]$i.LastTaskResult;last_run_at=$i.LastRunTime.ToString('o');"
        "next_run_at=$i.NextRunTime.ToString('o');actions=@($t.Actions|ForEach-Object{"
        "@{execute=$_.Execute;arguments=$_.Arguments;working_directory=$_.WorkingDirectory}});"
        "limited=([string]$t.Principal.RunLevel -eq 'Limited');"
        "interactive=([string]$t.Principal.LogonType -eq 'Interactive')}"
        "|ConvertTo-Json -Depth 4 -Compress"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        check=True,
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    raw = json.loads(result.stdout)
    repo = Path(__file__).resolve().parents[1]
    expected = (
        f'/d /c ""{repo / "scripts/windows/run-nse-market.cmd"}" '
        f'"{args.config.resolve()}" auto --scheduled"'
    )
    actions = raw.pop("actions")
    raw["action_matches"] = (
        len(actions) == 1
        and str(actions[0]["execute"]).lower().endswith("\\system32\\cmd.exe")
        and actions[0]["arguments"] == expected
        and Path(actions[0]["working_directory"]).resolve() == repo.resolve()
    )
    value = dict(
        raw,
        task_name=NAME,
        observed_at=datetime.now(UTC).isoformat(),
        policy_sha256=policy["policy_sha256"],
        provider_requests=0,
        tasks_modified=False,
    )
    validate(value, policy["policy_sha256"])
    folder = config.root / "operational/task-events"
    folder.mkdir(exist_ok=True)
    target = folder / (uuid.uuid4().hex + ".observed.json")
    engine._checked(target, value)
    engine._pointer(config.root, "task-observation-latest.json", target)
    print(json.dumps(value))


if __name__ == "__main__":
    main()
