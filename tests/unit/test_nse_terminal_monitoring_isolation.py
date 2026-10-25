"""TEST_ONLY disk failures after commit do not replace durable collection results."""

from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import encoded
from workers.nse_market import collection_alerts, diagnostics, operational, operational_health


@pytest.mark.parametrize("failed_stage", ["alerts", "health", "both"])
def test_failed_diagnostics_cannot_change_durable_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_stage: str
) -> None:
    terminal = {
        "collection_requested": True,
        "launch_id": "a" * 32,
        "run_id": "b" * 32,
        "state": "PARTIAL_OR_PUBLICATION_PENDING",
    }
    original = encoded(terminal)
    reached: list[str] = []

    def alerts(*args: Any) -> None:
        reached.append("alerts")
        if failed_stage in {"alerts", "both"}:
            raise OSError("TEST_ONLY_FULL_DISK")

    def health(*args: Any) -> None:
        reached.append("health")
        if failed_stage in {"health", "both"}:
            raise ValueError("TEST_ONLY_INVALID_REPORT")

    def unavailable_log(*args: Any, **kwargs: Any) -> None:
        raise OSError("TEST_ONLY_FULL_DISK")

    monkeypatch.setattr(collection_alerts, "from_terminal", alerts)
    monkeypatch.setattr(operational_health, "after_terminal", health)
    monkeypatch.setattr(diagnostics, "emit", unavailable_log)
    operational._publish_monitoring(tmp_path, terminal)
    assert reached == ["alerts", "health"]
    assert encoded(terminal) == original
    assert list(tmp_path.iterdir()) == []
