"""TEST_ONLY entry completeness, holding thresholds and immutable P15 what-if results."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from workers.personal.analytics import candidate, portfolio_review, simulate
from workers.personal.contracts import ManualEntry, Profile, Scenario
from workers.personal.decision import exit_impact, holding_thresholds
from workers.personal.store import PersonalStore

KEY = "NSE_EQ|INE000000001"


def test_hypothetical_reduction_reuses_fifo_costs_without_mutation(tmp_path: Path) -> None:
    store = PersonalStore(tmp_path / "TEST_ONLY", "TEST_ONLY_owner")
    store.initialize()
    id_ = store.create_portfolio("TEST_ONLY FIFO")["id"]
    instrument = {"provider_key": KEY, "symbol": "TEST_ONLY", "isin": KEY.split("|")[1]}
    for quantity, price in (("10", "100"), ("5", "200")):
        store.record(
            id_,
            ManualEntry(
                request_id=uuid4().hex,
                kind="OPENING_POSITION",
                instrument_key=KEY,
                session=date(2024, 1, 2),
                quantity=quantity,
                price=price,
                fees_known=True,
            ),
            instrument,
        )
    before = store.get("portfolios", id_)
    item: dict[str, Any] = {
        "quote": {
            "state": "VALIDATED_SNAPSHOT",
            "ltp": "250",
            "last_trade_at": "2024-01-03T10:00:00+05:30",
            "snapshot_at": "2024-01-03T10:01:00+05:30",
            "freshness": "OLDER_TRADE",
        },
        "rows": [],
        "source": "TEST_ONLY_PROVIDER",
    }
    result = exit_impact(
        before["value"],
        Scenario(instrument_key=KEY, quantity_delta="-12", transaction_cost_inr="5"),
        item,
    )
    assert result["fifo_realized_change_exact"] == "1595"
    assert result["remaining_basis_exact"] == "600" and result["remaining_quantity"] == "3"
    assert not result["writes_performed"] and store.get("portfolios", id_) == before
    review = portfolio_review(before["value"], Profile(), {KEY: item})
    scenario = simulate(
        review,
        Scenario(instrument_key=KEY, quantity_delta="-12", transaction_cost_inr="5"),
        {KEY: item},
    )
    assert scenario["hypothetical_trade_cash_flow"] == "2995.00"
    assert scenario["remaining_holdings_plus_trade_flow_and_declared_cash"] == "3745.00"
    rules: list[dict[str, Any]] = [
        {
            "id": "TEST_ONLY_rule",
            "value": {
                "name": "TEST_ONLY target",
                "enabled": True,
                "instrument_key": KEY,
                "portfolio_id": id_,
                "kind": "PRICE_ABOVE",
                "threshold": "240",
            },
        }
    ]
    review = holding_thresholds(review, rules)
    assert "PRICE_TARGET_REACHED" in review["holdings"][0]["diagnostics"]
    item.update(latest_close="200", latest_session="2024-01-02")
    rules[0]["value"].update(threshold="225", evidence_source="DAILY_CANDLES")
    dated = holding_thresholds(
        portfolio_review(before["value"], Profile(), {KEY: item}), rules, {KEY: item}
    )
    assert dated["holdings"][0]["threshold_reviews"][0]["state"] == "NOT_REACHED"
    assert dated["holdings"][0]["threshold_reviews"][0]["evidence"]["session"] == "2024-01-02"


def test_short_series_cannot_match_longer_horizon() -> None:
    rows = [
        {"session": str(date(2024, 1, 1) + timedelta(days=i)), "close": str(100 + i), "volume": 100}
        for i in range(5)
    ]
    item = {
        "instrument_key": KEY,
        "symbol": "TEST_ONLY",
        "source": "TEST_ONLY",
        "rows": rows,
        "quote": {"state": "UNAVAILABLE"},
        "latest_close": "104",
        "latest_session": rows[-1]["session"],
    }
    result = candidate(item, Profile(horizon="Medium"))
    assert result["preferences"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "SUFFICIENT_HORIZON_OBSERVATIONS" in result["preferences"]["missing"]
