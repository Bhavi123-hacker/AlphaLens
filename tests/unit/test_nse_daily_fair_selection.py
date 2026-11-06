"""TEST_ONLY: bounded pending selection cannot starve an unqueried security."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from test_nse_collection_faults import freeze
from test_nse_market import Transport, fixture, identity
from workers.experimental_nse.acquire import PERMISSION
from workers.nse_market import daily
from workers.providers.upstox import Reply


def test_empty_retry_does_not_take_slot_ahead_of_unqueried_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    freeze(monkeypatch)

    class Recorded(Transport):
        def __init__(self, *, empty: bool = False) -> None:
            super().__init__(empty=empty)
            self.keys: list[str] = []

        def get(self, operation: str, **kwargs: Any) -> Reply:
            if operation == "candles":
                self.keys.append(kwargs["key"])
            return super().get(operation, **kwargs)

    def run(meter: Recorded) -> dict[str, Any]:
        return daily.run(
            root,
            root / "TEST_ONLY_provider",
            root / "TEST_ONLY_v2",
            session=date(2025, 1, 3),
            max_stocks=1,
            max_requests=20,
            collect=True,
            permission_reference=PERMISSION,
            meter=meter,
        )

    empty = Recorded(empty=True)
    assert run(empty)["accepted_session_securities"] == 0
    assert empty.keys == [identity(1).provider_key]
    second = Recorded()
    assert run(second)["accepted_session_securities"] == 1
    assert second.keys == [identity(2).provider_key]
    third = Recorded()
    assert run(third)["accepted_session_securities"] == 2
    assert third.keys == [identity(3).provider_key]
    retry = Recorded()
    recovered = run(retry)
    assert recovered["accepted_session_securities"] == 3
    assert recovered["pending_securities"] == 0
    assert retry.keys == [identity(1).provider_key]
    replay = Recorded()
    assert run(replay)["state"] == "REPLAY"
    assert replay.calls == 0


def test_created_but_unrequested_directory_does_not_count_as_attempt(tmp_path: Path) -> None:
    folder = tmp_path / "daily/2025-01-03" / str(identity(1).isin)
    folder.mkdir(parents=True)
    assert not daily._attempted_target(tmp_path, date(2025, 1, 3), identity(1))
