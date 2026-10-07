"""Authored TEST_ONLY paper clock/calendar/account, not exchange or broker evidence."""

from datetime import date
from fractions import Fraction

from scripts.build_p15_test_fixture import clock

from alphalens_backtesting.contracts import CalendarDay, ExecutionCalendar
from alphalens_data.canonical.services import CanonicalReader
from alphalens_portfolio.contracts import Portfolio
from alphalens_portfolio.paper import create
from alphalens_portfolio.paper_contracts import ManualPaperOrder, PaperState


def account() -> PaperState:
    return create(
        Portfolio(
            portfolio_id="TEST_ONLY_PAPER_ACCOUNT",
            portfolio_name="TEST_ONLY forward simulation",
            portfolio_type="PAPER",
            classification="TEST_ONLY",
            created_at=clock(1, 0),
        ),
        Fraction(10000),
    )


def calendar(reader: CanonicalReader) -> ExecutionCalendar:
    return ExecutionCalendar(
        canonical_input_id=reader.batch.input_id,
        classification="TEST_ONLY",
        evidence_reference="TEST_ONLY_AUTHORED_CALENDAR_NOT_NSE",
        days=tuple(
            CalendarDay(
                session_date=date(2024, 1, d),
                status="VERIFIED_TRADING_SESSION",
                available_at=clock(1, 0),
                open_at=clock(d, 3),
                open_clock_policy="EXPLICIT_SESSION_OPEN_CONVENTION",
                evidence_reference="TEST_ONLY_AUTHORED_OPEN",
            )
            for d in range(1, 21)
        ),
    )


def request(
    identity: str = "manual",
    security: str = "TEST:ALPHA",
    side: str = "BUY",
    quantity: int | None = None,
    budget: str = "1000",
) -> ManualPaperOrder:
    return ManualPaperOrder.model_validate(
        dict(
            request_id=identity,
            security_id=security,
            symbol=security.replace(":", "_"),
            side=side,
            quantity=quantity,
            maximum_cash=budget if side == "BUY" else None,
            reason="EXPLICIT_MANUAL_TEST_ONLY_PAPER_DECISION",
        )
    )
