"""Saved Windows task facts. Reading the dashboard never invokes Task Scheduler."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

NAME = "AlphaLens-Private-NSE-Market-Research"


def validate(value: dict[str, Any], policy_sha256: str) -> None:
    if (
        value.get("task_name") != NAME
        or value.get("policy_sha256") != policy_sha256
        or value.get("provider_requests") != 0
        or value.get("tasks_modified") is not False
        or type(value.get("last_result")) is not int
        or type(value.get("enabled")) is not bool
        or type(value.get("action_matches")) is not bool
    ):
        raise ValueError("SAVED_TASK_OBSERVATION_CONTRACT_REJECTED")
    for field in ("observed_at", "last_run_at", "next_run_at"):
        if field != "observed_at" and value.get(field) is None:
            continue
        at = datetime.fromisoformat(value[field])
        if at.utcoffset() is None or (field == "observed_at" and at > datetime.now(UTC)):
            raise ValueError("SAVED_TASK_OBSERVATION_TIME_REJECTED")
