"""Explicitly TEST_ONLY declared portfolio records; never market executions."""

from datetime import UTC, date, datetime

from alphalens_portfolio.accounting import append
from alphalens_portfolio.contracts import Ledger, Portfolio, Transaction


def clock(day: int, hour: int = 12) -> datetime:
    return datetime(2024, 1, day, hour, tzinfo=UTC)


def account(classification: str = "TEST_ONLY") -> Ledger:
    return Ledger(
        portfolio=Portfolio.model_validate(
            dict(
                portfolio_id="TEST_ONLY_MANUAL",
                portfolio_name="TEST_ONLY portfolio",
                portfolio_type="USER_RECORDED",
                created_at=clock(1, 0),
                classification=classification,
            )
        )
    )


def event(kind: str, day: int, identity: str, **kwargs: object) -> Transaction:
    data: dict[str, object] = dict(
        transaction_id=identity,
        portfolio_id="TEST_ONLY_MANUAL",
        kind=kind,
        session=date(2024, 1, day),
        effective_at=clock(day, 1),
        recorded_at=clock(day, 2),
        source="USER_RECORDED_DECLARATION",
        classification="USER_RECORDED",
    )
    if kind in {"BUY", "SELL", "OPENING_POSITION"}:
        data.update(security_id="TEST:ALPHA", symbol="TEST_ALPHA", quantity="10", price="100")
    else:
        data.update(cash_amount="10000")
    data.update(kwargs)
    return Transaction.model_validate(data)


def funded() -> Ledger:
    return append(account(), event("CASH_DEPOSIT", 1, "deposit"))


def bought() -> Ledger:
    return append(funded(), event("BUY", 2, "buy", fees="10"))
