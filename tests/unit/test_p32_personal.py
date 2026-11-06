"""TEST_ONLY exact manual bookkeeping and descriptive research; no real holdings."""

from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from workers.personal.analytics import observed, portfolio_review, preference_match, simulate
from workers.personal.contracts import ManualEntry, Profile, Scenario
from workers.personal.store import PersonalStore

KEY = "NSE_EQ|INE000000001"
IDENTITY = {"provider_key": KEY, "symbol": "TEST_ONLY_ALPHA", "isin": "INE000000001"}


@pytest.fixture
def owned(tmp_path: Path) -> PersonalStore:
    store = PersonalStore(tmp_path / "TEST_ONLY_personal", "TEST_ONLY_owner")
    store.initialize()
    return store


def entry(
    kind: str, quantity: str = "0", price: str = "0", fees: str = "0", **extra: object
) -> ManualEntry:
    return ManualEntry.model_validate(
        {
            "request_id": uuid4().hex,
            "kind": kind,
            "instrument_key": KEY if kind in {"OPENING_POSITION", "BUY", "SELL"} else None,
            "session": "2024-01-02",
            "quantity": quantity,
            "price": price,
            "fees": fees,
            "fees_known": True,
            **extra,
        }
    )


def test_original_fifo_multiple_lots_partial_sale_and_unknown_cash(owned: PersonalStore) -> None:
    identity = owned.create_portfolio("TEST_ONLY multi-lot")["id"]
    owned.record(identity, entry("OPENING_POSITION", "10", "100", "10"), IDENTITY)
    owned.record(identity, entry("OPENING_POSITION", "5", "200"), IDENTITY)
    record = owned.record(identity, entry("SELL", "12", "250", "5"), IDENTITY)
    review = portfolio_review(record["value"], Profile(), {})
    holding = review["holdings"][0]
    assert (holding["quantity"], holding["cost_basis_exact"], holding["realized_pnl_exact"]) == (
        "3",
        "600",
        "1585",
    )
    assert len(holding["lots"]) == 1
    assert review["cash_balance"] is None and review["ledger_cash"] == "2995.00"
    assert review["portfolio_value"] is None and review["indicative_holdings_value"] is None
    assert review["current_ml"] == "UNAVAILABLE"


def test_cash_funding_is_explicit_no_invented_deposit(owned: PersonalStore) -> None:
    identity = owned.create_portfolio("TEST_ONLY funding")["id"]
    with pytest.raises(ValueError, match="NO_OVERDRAFT"):
        owned.record(identity, entry("BUY", "10", "100"), IDENTITY)
    assert not owned.get("portfolios", identity)["value"]["ledger"]["transactions"]
    owned.record(identity, entry("CASH_DEPOSIT", cash_amount="2000"), None)
    record = owned.record(identity, entry("BUY", "10", "100", "5"), IDENTITY)
    review = portfolio_review(record["value"], Profile(), {})
    assert review["ledger_cash"] == "995.00" and review["remaining_cost_basis_exact"] == "1005"


def test_no_short_selling_atomicity_and_idempotency(owned: PersonalStore) -> None:
    identity = owned.create_portfolio("TEST_ONLY idempotency")["id"]
    purchase = entry("OPENING_POSITION", "2", "10")
    before = owned.record(identity, purchase, IDENTITY)
    assert owned.record(identity, purchase, IDENTITY) == before
    with pytest.raises(ValueError, match="IMMUTABLE"):
        owned.record(identity, purchase.model_copy(update={"quantity": "3"}), IDENTITY)
    with pytest.raises(ValueError, match="NO_SHORT_SELLING"):
        owned.record(identity, entry("SELL", "3", "11"), IDENTITY)
    assert owned.get("portfolios", identity) == before


def test_ownership_and_optimistic_revision(owned: PersonalStore) -> None:
    saved = owned.save("profile", "default", Profile().model_dump(), 0)
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        owned.save("profile", "default", Profile().model_dump(), 0)
    assert owned.profile() == saved
    with pytest.raises(ValueError, match="OWNER_MISMATCH"):
        PersonalStore(owned.root, "TEST_ONLY_other").listing("profile")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1e100", "0.000000001", "bogus", 1.2])
def test_exact_numeric_boundaries(value: object) -> None:
    with pytest.raises(ValueError):
        Profile.model_validate({"budget_inr": value})


def test_future_fractional_identity_and_unknown_fees_rejected(owned: PersonalStore) -> None:
    identity = owned.create_portfolio("TEST_ONLY boundaries")["id"]
    for candidate, metadata, reason in (
        (
            entry("OPENING_POSITION", "1", "10", session=date.today() + timedelta(days=2)),
            IDENTITY,
            "FUTURE",
        ),
        (entry("OPENING_POSITION", "1.5", "10"), IDENTITY, "WHOLE_SHARE"),
        (
            entry("OPENING_POSITION", "1", "10"),
            {**IDENTITY, "provider_key": "NSE_EQ|INE000000002"},
            "IDENTITY",
        ),
        (entry("OPENING_POSITION", "1", "10", "1", fees_known=False), IDENTITY, "FEES"),
    ):
        with pytest.raises(ValueError, match=reason):
            owned.record(identity, candidate, metadata)
    assert not owned.get("portfolios", identity)["value"]["ledger"]["transactions"]


def test_partial_marks_and_cost_concentration_are_explicit(owned: PersonalStore) -> None:
    identity = owned.create_portfolio("TEST_ONLY marks")["id"]
    record = owned.record(identity, entry("OPENING_POSITION", "2", "10"), IDENTITY)
    item = {
        "quote": {
            "state": "VALIDATED_SNAPSHOT",
            "ltp": "15",
            "last_trade_at": "2024-01-03T10:00:00+05:30",
            "snapshot_at": "2024-01-03T10:01:00+05:30",
            "freshness": "OLDER_TRADE",
        },
        "rows": [],
        "source": "TEST_ONLY_PROVIDER",
    }
    review = portfolio_review(record["value"], Profile(), {KEY: item})
    assert review["indicative_holdings_value"] == "30.00"
    assert review["indicative_unrealized_pnl"] == "10.00"
    assert review["portfolio_value"] is None
    assert "CONCENTRATION_RISK" in review["holdings"][0]["diagnostics"]
    assert "DATA_TOO_STALE" in review["holdings"][0]["diagnostics"]
    before = owned.get("portfolios", identity)
    scenario = simulate(
        review, Scenario(shock_percent="-10", instrument_key=KEY, quantity_delta="-1"), {KEY: item}
    )
    assert scenario["shocked_holdings_value"] == "13.50" and scenario["writes_performed"] is False
    assert owned.get("portfolios", identity) == before
    allocated = simulate(
        review,
        Scenario(shock_percent="-10", cash_delta="5", target_weights={KEY: "60"}),
        {KEY: item},
    )
    assert allocated["target_allocations"][KEY] == "16.20"
    assert allocated["target_cash_weight_percent"] == "40"
    assert allocated["shocked_holdings_plus_cash_delta"] == "32.00"
    assert scenario["target_cash_weight_percent"] is None
    with pytest.raises(ValueError, match="NO_SHORT"):
        simulate(review, Scenario(instrument_key=KEY, quantity_delta="-3"), {KEY: item})


def test_descriptive_metrics_and_missing_path_not_filled() -> None:
    rows = [
        {"session": "2024-01-02", "close": "100", "volume": 10},
        {"session": "2024-01-03", "close": "120", "volume": 20},
        {"session": "2024-01-04", "close": "90", "volume": 15},
    ]
    metrics = observed(rows)
    assert metrics["price_return_percent"] == -10 and metrics["maximum_drawdown_percent"] == -25
    assert metrics["daily_volatility_percent"] is not None
    match = preference_match(Profile(), metrics)
    assert "maximum_drawdown_percent" in match["excluded"]
    rows[1]["close"] = None
    incomplete = observed(rows)
    assert (
        incomplete["price_return_percent"] is None
        and incomplete["daily_volatility_percent"] is None
    )


def test_missing_or_clock_rejected_prices_do_not_claim_provider_outage() -> None:
    from workers.personal.analytics import provider_request_failed

    assert provider_request_failed(None) is None
    assert provider_request_failed({"quote": {"state": "QUOTE_TIME_REJECTED"}}) is None
    assert provider_request_failed({"quote": {"state": "VALIDATED_SNAPSHOT"}}) is False
    assert provider_request_failed({"quote": {"state": "PROVIDER_OUTAGE"}}) is True


def test_bulk_import_atomicity_and_unchanged_preview(owned: PersonalStore) -> None:
    from workers.personal.store import apply_entry

    record = owned.create_portfolio("TEST_ONLY import")
    original = owned.get("portfolios", record["id"])
    preview = apply_entry(
        original["value"], record["id"], entry("OPENING_POSITION", "2", "10"), IDENTITY
    )
    assert (
        len(preview["ledger"]["transactions"]) == 1
        and owned.get("portfolios", record["id"]) == original
    )
    with pytest.raises(ValueError, match="NO_SHORT"):
        owned.record_many(
            record["id"],
            [
                (entry("OPENING_POSITION", "2", "10"), IDENTITY),
                (entry("SELL", "3", "20"), IDENTITY),
            ],
            original["revision"],
        )
    assert owned.get("portfolios", record["id"]) == original
    result = owned.record_many(
        record["id"],
        [(entry("OPENING_POSITION", "2", "10"), IDENTITY), (entry("SELL", "1", "20"), IDENTITY)],
        original["revision"],
    )
    review = portfolio_review(result["value"], Profile(), {})
    assert review["realized_pnl_exact"] == "10" and review["holdings"][0]["quantity"] == "1"
