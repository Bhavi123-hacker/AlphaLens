"""TEST_ONLY derived publication integration; no provider or scheduler calls."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from test_nse_market import Transport, fixture
from workers.experimental_nse.acquire import PERMISSION
from workers.nse_market import daily, engine, saved_market


@pytest.mark.parametrize("publication_fails", [False, True])
def test_daily_publishes_verified_frame_without_breaking_capture_or_zero_get_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, publication_fails: bool
) -> None:
    root = fixture(tmp_path, monkeypatch)
    transport = Transport()
    monkeypatch.setattr(engine, "Meter", lambda *args: transport)
    monkeypatch.setattr(engine, "_score", lambda *args: {"state": "TEST_ONLY", "new_forecasts": 0})
    published: list[str] = []

    def publish(unused_root: Path, frame: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        assert frame["sessions"][-1] == "2025-01-03"
        assert len({row["key"] for row in frame["rows"] if row["session"] == "2025-01-03"}) == 3
        assert kwargs["at"].utcoffset() is not None
        published.append(frame["dataset_id"])
        if publication_fails:
            raise OSError("TEST_ONLY_PRIVATE_EXCEPTION_MUST_NOT_BE_EXPOSED")
        return {"state": "SAVED_MARKET_VIEW_PUBLISHED", "provider_requests": 0}

    monkeypatch.setattr(saved_market, "publish", publish)
    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        max_stocks=3,
        collect=True,
        permission_reference=PERMISSION,
    )
    assert result["state"] == "CAPTURED" and result["new_daily_observations"] == 3
    assert len(published) == 1
    if publication_fails:
        assert result["market_view"] == {
            "state": "FAILED",
            "error_code": "SAVED_MARKET_PUBLICATION_FAILED",
        }
    else:
        assert result["market_view"]["state"] == "SAVED_MARKET_VIEW_PUBLISHED"
    calls = transport.calls
    replay = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        max_stocks=3,
        collect=True,
        permission_reference=PERMISSION,
    )
    assert replay["state"] == "REPLAY" and replay["api_calls"] == 0
    assert transport.calls == calls and len(published) == 1
