"""TEST_ONLY endpoint replay: no market, NTP, scheduler or real-model requests."""

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from test_nse_market import Transport, fixture, identity
from workers.experimental_nse.acquire import PERMISSION, digest, encoded
from workers.experimental_nse_v2 import data as v2_data
from workers.nse_market import daily, engine
from workers.providers.upstox import Reply

TARGET = date(2025, 1, 6)
AT = datetime(2025, 1, 6, 12, tzinfo=UTC)
EMPTY_SAVED_RESPONSE_SHAPE = (
    Path(__file__).resolve().parents[1] / "fixtures/upstox_20261026_empty_daily.json"
).read_bytes()


def setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, at: datetime = AT
) -> tuple[Path, list[str]]:
    root = fixture(tmp_path, monkeypatch)
    clock = {
        "session_date": str(at.astimezone(ZoneInfo("Asia/Kolkata")).date()),
        "lower_at": at.isoformat(),
        "upper_at": at.isoformat(),
    }
    monkeypatch.setattr(daily, "guard", lambda: clock)
    monkeypatch.setattr(engine, "guard", lambda: clock)
    monkeypatch.setattr(
        daily,
        "datetime",
        SimpleNamespace(now=lambda *args: at, fromisoformat=datetime.fromisoformat),
    )
    scoring: list[str] = []

    def no_fixture_model(*args: Any) -> dict[str, Any]:
        # The three-slot fixture deliberately lacks real ML features/models.
        scoring.append("TEST_ONLY_INSUFFICIENT_FEATURES")
        return {"state": "TEST_ONLY_INSUFFICIENT_FEATURES", "new_forecasts": 0}

    monkeypatch.setattr(engine, "_score", no_fixture_model)
    return root, scoring


class RoutingTransport(Transport):
    """Historical current-day responses replay the retained empty envelope only."""

    def __init__(self, *, mode: str = "valid", at: datetime = AT) -> None:
        super().__init__()
        self.mode = mode
        self.at = at
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def get(self, operation: str, **kwargs: Any) -> Reply:
        self.requests.append((operation, kwargs))
        if operation in {"timings", "actions"}:
            reply = super().get(operation, **kwargs)
            return Reply(reply.status, reply.body, self.at, reply.state)
        self.calls += 1
        self.operations.append(operation)
        if operation == "candles":
            body = (
                EMPTY_SAVED_RESPONSE_SHAPE
                if kwargs["end"] == TARGET
                else encoded(
                    {
                        "status": "success",
                        "data": {"candles": [self.candle(str(kwargs["end"]))]},
                    }
                )
            )
        else:
            assert operation == "intraday_candles"
            assert set(kwargs) == {"key"}, "Current-day route must have no date arguments"
            if self.mode == "mixed" and kwargs["key"] == identity(1).provider_key:
                return Reply(500, b'{"TEST_ONLY_unavailable":true}', self.at, "HTTP_ERROR")
            days = {
                "valid": [str(TARGET)],
                "mixed": [str(TARGET)],
                "empty": [],
                "wrong_day": ["2025-01-03"],
                "multiple_days": ["2025-01-03", str(TARGET)],
                "duplicate_target": [str(TARGET), str(TARGET)],
            }[self.mode]
            body = encoded(
                {"status": "success", "data": {"candles": [self.candle(day) for day in days]}}
            )
        return Reply(200, body, self.at, "ACCEPTED")

    @staticmethod
    def candle(day: str) -> list[Any]:
        return [day + "T00:00:00+05:30", 110, 120, 109, 115, 1234, 0]


def run(
    root: Path,
    meter: RoutingTransport,
    *,
    target: date = TARGET,
    max_stocks: int = 3,
    max_requests: int = 20,
) -> dict[str, Any]:
    return daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=target,
        max_stocks=max_stocks,
        max_requests=max_requests,
        collect=True,
        permission_reference=PERMISSION,
        meter=meter,
    )


def test_same_day_replays_empty_historical_shape_but_routes_one_intraday_get_per_stock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = setup(tmp_path, monkeypatch)
    old_route = RoutingTransport().get(
        "candles", key=identity(1).provider_key, start=TARGET, end=TARGET
    )
    assert digest(EMPTY_SAVED_RESPONSE_SHAPE) == (
        "83d511d64ffda7e4c950b5f2c8f95130e5fa0c872af9b85a70e1a6bf3616428f"
    )
    assert old_route.status == 200 and old_route.body == EMPTY_SAVED_RESPONSE_SHAPE
    assert v2_data.normalized(old_route.body, identity(1), old_route.received_at) == []
    meter = RoutingTransport()
    result = run(root, meter)
    assert result["accepted_session_securities"] == 3
    assert result["new_daily_observations"] == 3
    assert meter.operations.count("intraday_candles") == 3
    assert not any(operation == "candles" for operation, _ in meter.requests)
    assert meter.calls == 8  # Two official timing receipts + one candle/action per stock.
    for path in (root / "daily" / str(TARGET)).glob("*/response.json"):
        receipt = engine._read(path)
        assert receipt["start"] == receipt["end"] == str(TARGET)
        assert receipt["request"]["operation"] == "intraday_candles"
        assert receipt["request"]["from_date"] is None
        assert receipt["request"]["to_date"] is None


def test_historical_weekend_catchup_preserves_exact_previous_observation_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = setup(tmp_path, monkeypatch)
    meter = RoutingTransport()
    result = run(root, meter, target=date(2025, 1, 3))
    assert result["accepted_session_securities"] == 3
    candles = [kwargs for operation, kwargs in meter.requests if operation == "candles"]
    assert len(candles) == 3
    assert next(row for row in candles if row["key"] == identity(1).provider_key) == {
        "key": identity(1).provider_key,
        "start": date(2025, 1, 3),
        "end": date(2025, 1, 3),
    }
    assert "intraday_candles" not in meter.operations
    assert all(
        (root / "calendar" / (day + ".json")).is_file()
        for day in ("2025-01-04", "2025-01-05", "2025-01-06")
    )


@pytest.mark.parametrize("mode", ["empty", "wrong_day", "multiple_days", "duplicate_target"])
def test_current_day_empty_wrong_or_multiple_candles_remain_missing_without_forecasts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    root, scoring = setup(tmp_path, monkeypatch)
    meter = RoutingTransport(mode=mode)
    result = run(root, meter)
    assert result["new_daily_observations"] == result["accepted_session_securities"] == 0
    assert result["pending_securities"] == 3
    assert len(result["failures"]) == 3
    assert meter.operations.count("intraday_candles") == 3
    assert not any(operation in {"candles", "actions"} for operation in meter.operations)
    assert not list((root / "daily" / str(TARGET)).glob("*/response.json"))
    assert not (root / "expanded-forecasts").exists() and scoring == []


def test_same_day_preclose_does_not_request_or_accept_a_candle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    at = datetime(2025, 1, 6, 9, tzinfo=UTC)
    root, scoring = setup(tmp_path, monkeypatch, at=at)
    meter = RoutingTransport(at=at)
    result = run(root, meter)
    assert result["state"] == "SESSION_NOT_COMPLETED"
    assert meter.operations == ["timings"] and scoring == []
    assert not (root / "daily" / str(TARGET)).exists()


def test_current_day_reply_received_before_official_close_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, scoring = setup(tmp_path, monkeypatch)
    meter = RoutingTransport(at=datetime(2025, 1, 6, 9, tzinfo=UTC))
    with pytest.raises(ValueError, match="CANDLE_RETRIEVED_BEFORE_OFFICIAL_CLOSE"):
        run(root, meter)
    assert meter.operations.count("intraday_candles") == 1
    assert not list((root / "daily" / str(TARGET)).glob("*/response.json"))
    assert scoring == []


def test_saved_same_day_replay_has_zero_gets_and_preserves_original_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = setup(tmp_path, monkeypatch)
    run(root, RoutingTransport())
    receipts = {
        str(path): digest(path.read_bytes())
        for path in (root / "daily" / str(TARGET)).glob("*/*")
        if path.is_file()
    }
    replay_meter = RoutingTransport(mode="empty")
    replay = run(root, replay_meter)
    assert replay["state"] == "REPLAY" and replay["api_calls"] == replay_meter.calls == 0
    assert all(digest(Path(name).read_bytes()) == sha for name, sha in receipts.items())
    assert not (root / "expanded-forecasts").exists()


@pytest.mark.parametrize("maximum", [2, 3, 4, 5])
def test_current_day_requests_stop_at_existing_budget_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, maximum: int
) -> None:
    root, _ = setup(tmp_path, monkeypatch)
    meter = RoutingTransport()
    result = run(root, meter, max_requests=maximum)
    assert meter.calls <= maximum
    assert result["api_calls"] <= maximum
    assert "candles" not in meter.operations
    assert result["accepted_session_securities"] < 3


def test_current_day_maximum_stock_scope_and_one_failure_are_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = setup(tmp_path, monkeypatch)
    meter = RoutingTransport(mode="mixed")
    result = run(root, meter, max_stocks=2)
    assert meter.operations.count("intraday_candles") == 2
    assert result["accepted_session_securities"] == 1 and result["pending_securities"] == 2
    assert result["failures"] == [{"key": identity(1).provider_key, "reason": "HTTP_ERROR"}]
    assert "candles" not in meter.operations


def test_current_day_missing_lookback_is_preserved_rather_than_downloaded_or_filled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = setup(tmp_path, monkeypatch)
    meter = RoutingTransport()
    run(root, meter)
    frame = engine.snapshot(root)
    for key in (identity(1).provider_key, identity(2).provider_key):
        dates = {row["session"] for row in frame["rows"] if row["key"] == key}
        assert dates == {"2025-01-02", "2025-01-06"}
        assert "2025-01-03" not in dates
    _, _, features = engine._latest_features(frame)
    assert not any(sample.session == str(TARGET) for sample in features.samples)
    assert not (root / "expanded-forecasts").exists()
    assert "candles" not in meter.operations


def test_utc_ist_rollover_does_not_misroute_previous_completed_day_as_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 20:00UTC Jan6 is 01:30IST Jan7: Jan6 is historical, not today's daily route.
    at = datetime(2025, 1, 6, 20, tzinfo=UTC)
    root, _ = setup(tmp_path, monkeypatch, at=at)
    meter = RoutingTransport(at=at)
    # Keep the saved-response envelope empty: selecting historical must not fallback.
    result = run(root, meter)
    assert result["accepted_session_securities"] == 0
    assert meter.operations.count("candles") == 3
    assert "intraday_candles" not in meter.operations


def test_utc_ist_rollover_current_india_day_is_uncompleted_and_not_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    at = datetime(2025, 1, 6, 20, tzinfo=UTC)
    root, scoring = setup(tmp_path, monkeypatch, at=at)
    meter = RoutingTransport(at=at)
    result = run(root, meter, target=date(2025, 1, 7))
    assert result["state"] == "SESSION_NOT_COMPLETED"
    assert meter.operations == ["timings"] and scoring == []


def test_next_day_reply_after_initial_guard_fails_closed_without_historical_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, scoring = setup(tmp_path, monkeypatch)  # Initial independent date remains Jan6.
    next_day = datetime(2025, 1, 7, 12, tzinfo=UTC)

    class NextDayTransport(RoutingTransport):
        def get(self, operation: str, **kwargs: Any) -> Reply:
            if operation != "intraday_candles":
                return super().get(operation, **kwargs)
            assert set(kwargs) == {"key"}
            self.requests.append((operation, kwargs))
            self.calls += 1
            self.operations.append(operation)
            return Reply(
                200,
                encoded(
                    {
                        "status": "success",
                        "data": {"candles": [self.candle("2025-01-07")]},
                    }
                ),
                next_day,
                "ACCEPTED",
            )

    meter = NextDayTransport(at=next_day)
    result = run(root, meter, max_requests=5)
    assert result["clock"]["session_date"] == "2025-01-06"
    assert result["accepted_session_securities"] == result["new_daily_observations"] == 0
    assert result["pending_securities"] == 3
    assert meter.calls == 5 and meter.operations.count("intraday_candles") == 3
    assert not any(operation in {"candles", "actions"} for operation in meter.operations)
    assert not list((root / "daily" / str(TARGET)).glob("*/response.json"))
    attempts = list((root / "daily" / str(TARGET)).glob("*/publication-attempts/*.json"))
    assert len(attempts) == 3
    assert all(
        engine._read(path)["state"] == "PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE"
        for path in attempts
    )
    assert scoring == [] and not (root / "expanded-forecasts").exists()
