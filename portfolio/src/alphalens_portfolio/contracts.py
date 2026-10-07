"""P15 immutable, exact financial contracts; manual execution is never verified."""

from datetime import date
from fractions import Fraction
from typing import Literal, Self

from pydantic import AwareDatetime, field_validator, model_validator

from alphalens_data.canonical.models import reject_float
from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.ingestion.contracts import Hash
from alphalens_evaluation.contracts import digest

PortfolioClass = Literal["USER_RECORDED", "TEST_ONLY", "RESEARCH_FIXTURE"]
ExecutionClass = Literal["USER_RECORDED", "PAPER", "TEST_ONLY_PAPER"]


class AccountingPolicy(Contract):
    version: Literal["p15.accounting.v1"] = "p15.accounting.v1"
    revision: NonEmpty = "initial"
    method: Literal["FIFO"] = "FIFO"
    buy_fees: Literal["CAPITALIZED_IN_LOT_BASIS"] = "CAPITALIZED_IN_LOT_BASIS"
    sell_fees: Literal["DEDUCTED_FROM_PROCEEDS"] = "DEDUCTED_FROM_PROCEEDS"
    short_selling: Literal[False] = False
    overdraft: Literal[False] = False
    valuation: Literal["LATEST_VALID_RAW_EOD_AT_OR_BEFORE_SESSION"] = (
        "LATEST_VALID_RAW_EOD_AT_OR_BEFORE_SESSION"
    )
    corporate_actions: Literal["UNRESOLVED_NO_AUTOMATIC_ADJUSTMENTS"] = (
        "UNRESOLVED_NO_AUTOMATIC_ADJUSTMENTS"
    )
    return_basis: Literal["TOTAL_PNL_OVER_GROSS_ACQUISITION_BASIS_NOT_TWR"] = (
        "TOTAL_PNL_OVER_GROSS_ACQUISITION_BASIS_NOT_TWR"
    )


class Portfolio(Contract):
    portfolio_id: NonEmpty
    portfolio_name: NonEmpty
    portfolio_type: Literal["USER_RECORDED", "PAPER"]
    base_currency: Literal["INR"] = "INR"
    accounting_policy: AccountingPolicy = AccountingPolicy()
    created_at: AwareDatetime
    classification: PortfolioClass

    @model_validator(mode="after")
    def boundary(self) -> Self:
        if self.portfolio_type == "PAPER" and self.classification == "USER_RECORDED":
            raise ValueError("Paper portfolios require an explicit market classification")
        return self


class Transaction(Contract):
    transaction_id: NonEmpty
    portfolio_id: NonEmpty
    kind: Literal["BUY", "SELL", "CASH_DEPOSIT", "CASH_WITHDRAWAL", "OPENING_POSITION"]
    security_id: NonEmpty | None = None
    symbol: NonEmpty | None = None
    session: date
    effective_at: AwareDatetime
    recorded_at: AwareDatetime
    quantity: Fraction = Fraction(0)
    price: Fraction = Fraction(0)
    fees: Fraction = Fraction(0)
    cash_amount: Fraction = Fraction(0)
    declared_cost_basis: Fraction | None = None
    currency: Literal["INR"] = "INR"
    source: NonEmpty
    classification: ExecutionClass
    notes: str = ""
    evidence_reference: str | None = None

    @field_validator(
        "quantity", "price", "fees", "cash_amount", "declared_cost_basis", mode="before"
    )
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def semantics(self) -> Self:
        from zoneinfo import ZoneInfo

        if (
            self.effective_at > self.recorded_at
            or self.effective_at.astimezone(ZoneInfo("Asia/Kolkata")).date() != self.session
            or min(self.quantity, self.price, self.fees, self.cash_amount) < 0
            or "://" in self.source
        ):
            raise ValueError("Invalid transaction clock, numeric or source")
        if self.kind in {"BUY", "SELL", "OPENING_POSITION"}:
            if not self.security_id or not self.symbol or self.quantity <= 0 or self.cash_amount:
                raise ValueError("Position events require security, symbol and positive quantity")
            if self.kind == "OPENING_POSITION":
                if self.declared_cost_basis is None or self.declared_cost_basis < 0:
                    raise ValueError("Opening lot requires declared basis; never inferred history")
                if self.price or self.fees or self.classification != "USER_RECORDED":
                    raise ValueError(
                        "Opening basis includes costs and is exclusively user recorded"
                    )
            elif self.price <= 0 or self.declared_cost_basis is not None:
                raise ValueError("Buy/sell requires price and no opening basis")
        elif (
            self.cash_amount <= 0
            or self.security_id
            or self.symbol
            or self.quantity
            or self.price
            or self.fees
            or self.declared_cost_basis is not None
        ):
            raise ValueError("Cash events require only positive cash amount")
        if self.classification != "USER_RECORDED" and not self.evidence_reference:
            raise ValueError("Simulated executions require fill/deposit lineage")
        return self

    @property
    def content_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class Ledger(Contract):
    portfolio: Portfolio
    transactions: tuple[Transaction, ...] = ()

    @model_validator(mode="after")
    def identity(self) -> Self:
        if len({t.transaction_id for t in self.transactions}) != len(self.transactions):
            raise ValueError("Duplicate transaction identity")
        for t in self.transactions:
            if (
                t.portfolio_id != self.portfolio.portfolio_id
                or t.recorded_at < self.portfolio.created_at
            ):
                raise ValueError("Transaction portfolio/creation mismatch")
            if (self.portfolio.portfolio_type == "USER_RECORDED") != (
                t.classification == "USER_RECORDED"
            ):
                raise ValueError("Manual and simulated executions cannot mix")
            if self.portfolio.portfolio_type == "PAPER" and (
                (self.portfolio.classification == "TEST_ONLY")
                != (t.classification == "TEST_ONLY_PAPER")
            ):
                raise ValueError("Paper execution classification mismatch")
        return self


class Lot(Contract):
    transaction_id: str
    session: date
    quantity: Fraction
    cost_basis: Fraction
    provenance: ExecutionClass


class Position(Contract):
    security_id: str
    transaction_symbol: str
    first_session: date
    quantity: Fraction
    cost_basis: Fraction
    gross_acquisition_basis: Fraction
    realized_pnl: Fraction
    fees: Fraction
    lots: tuple[Lot, ...]


class AccountingState(Contract):
    ledger_state_id: Hash
    cash: Fraction
    net_external_capital: Fraction
    positions: tuple[Position, ...]
    transaction_ids: tuple[str, ...]
