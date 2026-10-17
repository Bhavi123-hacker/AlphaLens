"""TEST_ONLY retained-mark eligibility and isolation from provider quote acceptance."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from workers.experimental_nse_v2 import data
from workers.personal import retained_marks
from workers.personal.analytics import mark


@pytest.mark.parametrize("case", ["valid", "future", "stale", "identity", "excluded"])
def test_dated_retained_mark_is_bounded_exact_and_never_a_quote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    day = today + timedelta(days=1 if case == "future" else -8 if case == "stale" else -1)
    key = "NSE_EQ|INE000A01001"
    sample: dict[str, Any] = {
        "identities": [{"provider_key": key, "symbol": "TEST_ONLY", "isin": "INE000A01001"}],
        "sessions": [str(day)],
        "dataset_id": "TEST_ONLY",
        "quality": {"excluded_sessions": {key: [str(day)] if case == "excluded" else []}},
        "rows": [
            {
                "key": key,
                "symbol": "WRONG" if case == "identity" else "TEST_ONLY",
                "isin": "INE000A01001",
                "session": str(day),
                "close": "123.45",
                "received_at": datetime.now(UTC).isoformat(),
                "raw_sha256": "a" * 64,
            }
        ],
    }
    monkeypatch.setattr(data, "load_current", lambda root: sample)
    result = retained_marks.read(tmp_path, (key,))
    if case != "valid":
        assert result == {}
        return
    assert result[key]["quote"]["state"] == "NO_INTRADAY_QUOTE_USED"
    assert result[key]["rows"] == []
    indicative = mark(result[key])
    assert indicative["price"] == "123.45"
    assert indicative["session"] == str(day)
    assert indicative["basis"] == "RETAINED_ADJUSTED_EOD_INDICATIVE_UNRECONCILED_ACTIONS"
    assert indicative["financial_accepted_valuation"] is False


def test_absent_root_or_no_requested_positions_makes_no_dataset_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any) -> Any:
        pytest.fail("Empty portfolio must not load market observations")

    monkeypatch.setattr(data, "load_current", forbidden)
    assert retained_marks.read(None, ("TEST_ONLY",)) == {}
    assert retained_marks.read(Path("TEST_ONLY"), ()) == {}
