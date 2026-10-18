"""TEST_ONLY saved monitoring metadata; no Task Scheduler or provider operations."""

from datetime import UTC, datetime, timedelta

import pytest
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
