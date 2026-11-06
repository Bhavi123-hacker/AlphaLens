"""Construct TEST_ONLY example records through the original P15 accounting engine."""

import json
from datetime import UTC, datetime
from pathlib import Path

from workers.personal.analytics import portfolio_review
from workers.personal.contracts import ManualEntry, Profile
from workers.personal.store import apply_entry

from alphalens_portfolio.contracts import Ledger, Portfolio


def main() -> None:
    at = datetime(2024, 1, 5, tzinfo=UTC)
    ledger = Ledger(
        portfolio=Portfolio(
            portfolio_id="TEST_ONLY_DEMO",
            portfolio_name="Synthetic FIFO example",
            portfolio_type="USER_RECORDED",
            classification="USER_RECORDED",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    value = {"ledger": ledger.model_dump(mode="json"), "manual_details": {}}
    identity = {"provider_key": "NSE_EQ|INE000000001", "symbol": "DEMO001", "isin": "INE000000001"}
    stages = []
    for index, (kind, quantity, price, fees) in enumerate(
        (
            ("OPENING_POSITION", "10", "100", "10"),
            ("OPENING_POSITION", "5", "200", "0"),
            ("SELL", "12", "250", "5"),
        )
    ):
        entry = ManualEntry(
            request_id=f"{index + 1:032x}",
            kind=kind,
            session="2024-01-02",
            instrument_key=identity["provider_key"],
            quantity=quantity,
            price=price,
            fees=fees,
            fees_known=True,
        )
        value = apply_entry(value, "TEST_ONLY_DEMO", entry, identity, at)
        review = portfolio_review(value, Profile(), {}, now=at)
        stages.append(
            {
                "event": kind,
                "quantity": quantity,
                "declared_price": price,
                "fees": fees,
                "remaining_quantity": review["holdings"][0]["quantity"],
                "remaining_basis": review["holdings"][0]["cost_basis"],
                "realized_fifo": review["realized_pnl"],
                "engine": "ORIGINAL_P15_FIFO",
                "classification": "TEST_ONLY",
            }
        )
    # Do not export ISIN-shaped internal test identities or any private/user/source records.
    document = {
        "classification": "TEST_ONLY_SYNTHETIC_NOT_MARKET_ACTIVITY",
        "example_symbol": "DEMO001",
        "stages": stages,
        "current_predictions": 0,
        "brokerage": False,
    }
    Path("apps/web/demo/personal-example.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    print("SYNTHETIC_P15_FIFO_EXAMPLE_GENERATED_NO_REAL_PRICE_OR_USER_INPUT")


if __name__ == "__main__":
    main()
