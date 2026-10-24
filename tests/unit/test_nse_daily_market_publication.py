"""TEST_ONLY derived publication integration; no provider or scheduler calls."""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_nse_market import AT, Transport, fixture
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
        target = root / ("TEST_ONLY_view_" + str(len(published)) + ".json")
        engine._checked(target, {"dataset_id": frame["dataset_id"]})
        engine._pointer(root, "market-view-latest.json", target)
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
    assert result["pending_before_run"] == 3
    assert result["accepted_session_securities"] == 3 and result["pending_securities"] == 0
    assert result["pending_count_basis"] == "FULL_CONFIGURED_COHORT_AFTER_VALIDATION"
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
    assert replay["pending_before_run"] == 0 and replay["pending_securities"] == 0
    assert replay["accepted_session_securities"] == 3
    assert transport.calls == calls and len(published) == (2 if publication_fails else 1)
    assert replay["market_view"]["state"] == (
        "FAILED" if publication_fails else "UNCHANGED_VERIFIED_DATASET"
    )


@pytest.mark.parametrize("stale_view", [False, True])
def test_completed_collection_recovers_publication_without_gets_or_new_forecasts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stale_view: bool
) -> None:
    root = fixture(tmp_path, monkeypatch)
    if stale_view:
        old = root / "TEST_ONLY_stale_market_view.json"
        engine._checked(old, {"dataset_id": "0" * 64})
        engine._pointer(root, "market-view-latest.json", old)
    transport = Transport()
    monkeypatch.setattr(engine, "Meter", lambda *args: transport)
    scored: list[bool] = []

    def score(*args: Any) -> dict[str, Any]:
        scored.append(True)
        return {"state": "TEST_ONLY"}

    monkeypatch.setattr(engine, "_score", score)
    original = saved_market.publish
    monkeypatch.setattr(
        saved_market, "publish", lambda *args, **kw: (_ for _ in ()).throw(OSError())
    )
    kwargs: dict[str, Any] = {
        "session": date(2025, 1, 3),
        "max_stocks": 3,
        "collect": True,
        "permission_reference": PERMISSION,
    }
    captured = daily.run(root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", **kwargs)
    assert captured["market_view"]["state"] == "FAILED"
    assert captured["pending_before_run"] == 3
    assert captured["accepted_session_securities"] == 3 and captured["pending_securities"] == 0
    calls, score_calls = transport.calls, len(scored)
    monkeypatch.setattr(saved_market, "publish", original)
    replay = daily.run(root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", **kwargs)
    assert replay["state"] == "REPLAY" and replay["market_view"]["provider_requests"] == 0
    assert replay["market_view"]["state"] == "SAVED_MARKET_VIEW_PUBLISHED"
    assert saved_market.workspace(root) is None  # No mocked research score pointer.
    assert transport.calls == calls and len(scored) == score_calls
    again = daily.run(root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", **kwargs)
    assert again["market_view"]["state"] == "UNCHANGED_VERIFIED_DATASET"
    assert transport.calls == calls and len(scored) == score_calls


def test_partial_collection_recovers_failed_view_despite_new_empty_replies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        daily,
        "datetime",
        SimpleNamespace(now=lambda *args: AT, fromisoformat=datetime.fromisoformat),
    )
    transport = Transport()
    monkeypatch.setattr(engine, "_score", lambda *args: {"state": "TEST_ONLY"})
    original = saved_market.publish
    monkeypatch.setattr(
        saved_market, "publish", lambda *args, **kw: (_ for _ in ()).throw(OSError())
    )
    kwargs: dict[str, Any] = {
        "session": date(2025, 1, 3),
        "max_stocks": 1,
        "collect": True,
        "permission_reference": PERMISSION,
    }
    captured = daily.run(
        root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", meter=transport, **kwargs
    )
    assert captured["market_view"]["state"] == "FAILED"
    assert captured["pending_before_run"] == 3
    assert captured["accepted_session_securities"] == 1 and captured["pending_securities"] == 2
    monkeypatch.setattr(saved_market, "publish", original)
    empty = Transport(empty=True)
    recovery = daily.run(
        root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", meter=empty, **kwargs
    )
    assert recovery["state"] == "PARTIAL_OR_PUBLICATION_PENDING"
    assert recovery["new_daily_observations"] == 0
    assert recovery["pending_before_run"] == 2
    assert recovery["accepted_session_securities"] == 1 and recovery["pending_securities"] == 2
    assert recovery["api_calls"] == 1  # Only the pending security's candle request.
    assert recovery["market_view"]["state"] == "SAVED_MARKET_VIEW_PUBLISHED"


def test_terminal_pending_counts_include_current_identity_exclusions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    from test_nse_market import identity

    monkeypatch.setattr(engine, "_score", lambda *args: {"state": "TEST_ONLY"})
    kwargs: dict[str, Any] = {
        "session": date(2025, 1, 3),
        "collect": True,
        "permission_reference": PERMISSION,
        "identity_overrides": {identity(1).provider_key: identity(1)},
    }
    captured = daily.run(
        root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", meter=Transport(), **kwargs
    )
    assert captured["pending_before_run"] == 3
    assert captured["eligible_pending_before_run"] == 1
    assert captured["accepted_session_securities"] == 1
    assert captured["pending_securities"] == 2
    assert captured["identity_excluded_missing_securities"] == 2
    assert captured["identity_excluded_missing_keys"] == [
        identity(2).provider_key,
        identity(3).provider_key,
    ]
    replay = daily.run(root, root / "TEST_ONLY_provider", root / "TEST_ONLY_v2", **kwargs)
    assert replay["state"] == "REPLAY" and replay["api_calls"] == 0
    assert replay["pending_securities"] == 2 and replay["accepted_session_securities"] == 1


@pytest.mark.parametrize("scores_changed", [False, True])
def test_replay_publication_checks_score_lineage_even_when_candles_are_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scores_changed: bool
) -> None:
    root = fixture(tmp_path, monkeypatch)
    old_scores = {"TEST_ONLY_score_version": 1}
    view = root / "TEST_ONLY_market_view.json"
    engine._checked(view, {"dataset_id": "a" * 64, "research_workspace": {"scores": old_scores}})
    engine._pointer(root, "market-view-latest.json", view)
    score_path = root / "TEST_ONLY_score.json"
    engine._checked(score_path, {"TEST_ONLY_score_version": 2} if scores_changed else old_scores)
    engine._pointer(root, "scores-latest.json", score_path)
    calls: list[bool] = []

    def publish(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(True)
        return {"state": "SAVED_MARKET_VIEW_PUBLISHED", "provider_requests": 0}

    monkeypatch.setattr(saved_market, "publish", publish)
    result = daily._publish_market(root, {"dataset_id": "a" * 64}, only_if_changed=True)
    assert calls == ([True] if scores_changed else [])
    assert result["state"] == (
        "SAVED_MARKET_VIEW_PUBLISHED" if scores_changed else "UNCHANGED_VERIFIED_DATASET"
    )
    assert result["provider_requests"] == 0
