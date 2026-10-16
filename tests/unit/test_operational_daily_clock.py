"""TEST_ONLY independent date bounds and selected-watchlist safety."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.providers import daily, daily_clock
from workers.providers.calendar import past_session_fact
from workers.providers.upstox import Reply

from alphalens_data.errors import DataContractError


@pytest.mark.parametrize(
    "missing,discontinuous,midnight",
    [(True, False, False), (False, True, False), (False, False, True), (False, False, False)],
)
def test_clock_requires_independent_consistent_date(
    monkeypatch: pytest.MonkeyPatch, missing: bool, discontinuous: bool, midnight: bool
) -> None:
    local = (
        datetime(2026, 10, 16, 18, 30, tzinfo=UTC)
        if midnight
        else datetime(2026, 10, 16, 5, tzinfo=UTC)
    )

    class Calibration:
        def receipt(self, at: datetime, mono: float) -> dict[str, Any]:
            assert at == local
            if discontinuous:
                raise ValueError("TEST_ONLY_DISCONTINUITY")
            return {
                "receipt_lower_at": (local - timedelta(milliseconds=20)).isoformat(),
                "receipt_upper_at": (local + timedelta(milliseconds=20)).isoformat(),
                "authentication": "UNAUTHENTICATED_NTP_NOT_PRODUCTION_TIME_ATTESTATION",
            }

    monkeypatch.setattr(daily_clock, "recent", lambda: None if missing else Calibration())
    monkeypatch.setattr(daily_clock, "precise_utc", lambda: local)
    if missing or discontinuous or midnight:
        with pytest.raises(DataContractError):
            daily_clock.guard()
    else:
        result = daily_clock.guard()
        assert result["state"] == "INDEPENDENT_DATE_BOUNDS_AGREE"
        assert result["quote_classification_required"] is False


@pytest.mark.parametrize(
    "keys", [[], ["A"] * 2, list(map(str, range(7))), "NSE_EQ|INE002A01018", [1]]
)
def test_daily_batch_rejects_bad_scope_before_network(keys: Any, tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        daily.run_watchlist({"instrument_keys": keys}, tmp_path)


def test_all_daily_keys_are_validated_before_any_acquisition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    def acquire(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {"api_calls": 0, "state": "TEST_ONLY"}

    monkeypatch.setattr(daily, "run", acquire)
    with pytest.raises(DataContractError):
        daily.run_watchlist({"instrument_keys": ["NSE_EQ|INE002A01018", "bad"]}, tmp_path)
    assert calls == []


@pytest.mark.parametrize(
    "body", [b'{"status":"success","data":[]}', b'{"status":"success","data":[{"exchange":"MCX"}]}']
)
def test_dated_absence_of_open_nse_session_is_non_trading(body: bytes) -> None:
    local = datetime(2026, 10, 16, 5, tzinfo=UTC)
    result = past_session_fact(
        Reply(200, body, local, "ACCEPTED"), (local - timedelta(days=1)).date(), local
    )
    assert result.status == "NON_TRADING"
    assert result.evidence_type == "OFFICIAL_VERIFIED_SESSION"


@pytest.mark.parametrize(
    "body",
    [
        b'{"status":"success","data":[{}]}',
        b'{"status":"success","data":null}',
        b'{"status":"error","data":[]}',
    ],
)
def test_malformed_or_failed_timing_is_never_a_holiday(body: bytes) -> None:
    local = datetime(2026, 10, 16, 5, tzinfo=UTC)
    with pytest.raises(DataContractError):
        past_session_fact(
            Reply(200, body, local, "ACCEPTED"), (local - timedelta(days=1)).date(), local
        )
