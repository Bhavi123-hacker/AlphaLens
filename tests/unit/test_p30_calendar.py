"""TEST_ONLY explicit holiday/timing facts; no inferred weekdays or final-close promotion."""

import json
from datetime import UTC, date, datetime

import pytest
from workers.providers.calendar import calendar, nse_holidays, nse_timing
from workers.providers.upstox import Reply

from alphalens_data.errors import DataContractError

AT = datetime(2026, 10, 14, 14, tzinfo=UTC)


def reply(value: object) -> Reply:
    return Reply(200, json.dumps({"status": "success", "data": value}).encode(), AT, "ACCEPTED")


def test_settlement_holiday_is_not_a_trading_holiday_and_special_session_is_kept() -> None:
    rows = nse_holidays(
        reply(
            [
                {
                    "date": "2026-10-02",
                    "holiday_type": "TRADING_HOLIDAY",
                    "closed_exchanges": ["NSE"],
                },
                {
                    "date": "2026-10-03",
                    "holiday_type": "SETTLEMENT_HOLIDAY",
                    "closed_exchanges": ["NSE"],
                },
                {
                    "date": "2026-10-04",
                    "holiday_type": "TRADING_HOLIDAY",
                    "open_exchanges": [{"exchange": "NSE"}],
                },
            ]
        )
    )
    assert [(str(s.session), s.status) for s in rows] == [
        ("2026-10-02", "NON_TRADING"),
        ("2026-10-04", "TRADING"),
    ]
    assert all(s.known_at == AT for s in rows)
    assert len(calendar(rows).sessions) == 2


def test_ambiguous_special_session_is_rejected() -> None:
    with pytest.raises(DataContractError, match="AMBIGUOUS"):
        nse_holidays(
            reply(
                [
                    {
                        "date": "2026-10-02",
                        "holiday_type": "TRADING_HOLIDAY",
                        "closed_exchanges": ["NSE"],
                        "open_exchanges": [{"exchange": "NSE"}],
                    }
                ]
            )
        )


def test_session_elapsed_never_establishes_eod_release_or_price_finality() -> None:
    start = datetime(2026, 10, 13, 3, 45, tzinfo=UTC)
    end = datetime(2026, 10, 13, 10, tzinfo=UTC)
    data = reply(
        [
            {
                "exchange": "NSE",
                "start_time": start.timestamp() * 1000,
                "end_time": end.timestamp() * 1000,
            }
        ]
    )
    result = nse_timing(data, date(2026, 10, 13))
    assert result["session_elapsed"] is True
    assert result["eod_release_published"] is None
    assert result["official_final_close_verified"] is False
    with pytest.raises(DataContractError, match="DATE_REJECTED"):
        nse_timing(data, date(2026, 10, 12))
