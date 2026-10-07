"""P16 immutable simulation intents/events. There is no real execution interface."""

from datetime import date
from fractions import Fraction
from typing import Literal, Self

from pydantic import AwareDatetime, Field, field_validator, model_validator

from alphalens_backtesting.contracts import CalendarDay, CostScenario, scenarios
from alphalens_data.canonical.models import reject_float
from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_decision.explanation_contracts import ExplainabilitySnapshot
from alphalens_decision.models import Horizon
from alphalens_decision.signal_contracts import SignalSnapshot
from alphalens_evaluation.contracts import digest

from .contracts import Ledger
from .valuation import PortfolioSnapshot


class PaperPolicy(Contract):
    version: Literal["p16.paper_policy.v1"] = "p16.paper_policy.v1"
    revision: NonEmpty = "initial"
    status: Literal["DEVELOPMENT_ASSUMPTION"] = "DEVELOPMENT_ASSUMPTION"
    signal_orders_enabled: bool = False
    controlling_horizon: Horizon = 5
    sizing: Literal["FIXED_CASH_PER_POSITION", "EQUAL_WEIGHT_AVAILABLE_CAPITAL"] = (
        "FIXED_CASH_PER_POSITION"
    )
    fixed_cash_per_position: Fraction = Fraction(1000)
    maximum_positions: int = Field(default=3, ge=1, le=1000)
    maximum_entry_rank: int = Field(default=5, ge=1)
    maximum_risk: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    exit_signal_enabled: bool = True
    take_profit_review_auto_exit: bool = False
    order_type: Literal["MARKET_ON_NEXT_OPEN"] = "MARKET_ON_NEXT_OPEN"
    quantity_policy: Literal["WHOLE_SHARES_FLOOR_NO_LEVERAGE"] = "WHOLE_SHARES_FLOOR_NO_LEVERAGE"
    pyramiding: Literal[False] = False
    short_selling: Literal[False] = False
    costs: CostScenario = scenarios()[0]

    @field_validator("fixed_cash_per_position", mode="before")
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def sizing_valid(self) -> Self:
        if self.fixed_cash_per_position <= 0:
            raise ValueError("Positive cash budget required")
        return self

    @property
    def policy_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class ManualPaperOrder(Contract):
    request_id: NonEmpty
    security_id: NonEmpty
    symbol: NonEmpty
    side: Literal["BUY", "SELL"]
    quantity: int | None = Field(default=None, gt=0, strict=True)
    maximum_cash: Fraction | None = None
    reason: NonEmpty

    @field_validator("maximum_cash", mode="before")
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def budget(self) -> Self:
        if self.side == "BUY" and (self.maximum_cash is None or self.maximum_cash <= 0):
            raise ValueError("Manual entry requires explicit maximum reserved cash")
        if self.side == "SELL" and (self.quantity is None or self.maximum_cash is not None):
            raise ValueError("Manual exit requires quantity and no cash reservation")
        return self


class PaperOrder(Contract):
    order_id: Hash
    account_id: str
    request_id: str
    security_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    decision_session: date
    decision_at: AwareDatetime
    target: CalendarDay
    calendar_id: Hash
    canonical_input_id: Hash
    policy: PaperPolicy
    intent_source: Literal["MANUAL_PAPER_ORDER", "SIGNAL_POLICY_PAPER_ORDER"]
    quantity: int | None = Field(gt=0)
    reserved_cash: Fraction
    signal: SignalSnapshot | None = None
    explanation: ExplainabilitySnapshot | None = None
    reason: str
    classification: Literal["PAPER", "TEST_ONLY_PAPER"]

    @model_validator(mode="after")
    def identity(self) -> Self:
        if self.order_id != digest(self.model_dump(mode="json", exclude={"order_id"})):
            raise ValueError("Paper intent identity mismatch")
        if (
            self.target.session_date <= self.decision_session
            or self.target.available_at > self.decision_at
            or not self.target.open_at
            or self.target.open_at <= self.decision_at
            or self.reserved_cash < 0
            or self.side == "BUY"
            and self.reserved_cash <= 0
        ):
            raise ValueError(
                "Paper intent requires future evidenced open and positive entry reservation"
            )
        if self.intent_source == "SIGNAL_POLICY_PAPER_ORDER" and (
            not self.signal or not self.explanation
        ):
            raise ValueError("Signal order requires explanation lineage")
        if self.side == "SELL" and (self.quantity is None or self.reserved_cash):
            raise ValueError("Exit requires owned quantity and no cash reservation")
        if (
            self.signal
            and self.explanation
            and (
                self.signal.horizon != self.policy.controlling_horizon
                or self.signal.knowledge_cutoff > self.decision_at
                or self.signal.security_id != self.security_id
                or self.explanation.signal_snapshot_id != self.signal.signal_snapshot_id
                or self.explanation.security_id != self.security_id
                or self.explanation.horizon != self.signal.horizon
                or self.explanation.state != self.signal.state
                or self.explanation.classification != self.signal.classification
                or self.explanation.knowledge_cutoff > self.decision_at
            )
        ):
            raise ValueError("Signal/explanation/horizon lineage mismatch")
        return self


class PaperFill(Contract):
    fill_id: Hash
    order_id: Hash
    session: date
    simulated_at: AwareDatetime
    evidence_available_at: AwareDatetime
    quantity: int
    observed_open: Fraction
    simulated_price: Fraction
    fees: Fraction
    slippage_amount: Fraction
    price_revision_key: Hash
    canonical_input_id: Hash
    source_lineage: dict[str, object]
    transaction_id: Hash
    classification: Literal["PAPER", "TEST_ONLY_PAPER"]
    execution: Literal["SIMULATED_FILL_NOT_REAL_EXECUTION"] = "SIMULATED_FILL_NOT_REAL_EXECUTION"

    @model_validator(mode="after")
    def identity(self) -> Self:
        if self.fill_id != digest(self.model_dump(mode="json", exclude={"fill_id"})):
            raise ValueError("Paper fill identity mismatch")
        return self


class OrderEvent(Contract):
    event_id: Hash
    order_id: Hash
    recorded_at: AwareDatetime
    state: Literal["PENDING", "FILLED", "CANCELLED", "EXPIRED", "NO_FILL", "REJECTED"]
    reason: str
    fill_id: Hash | None = None

    @model_validator(mode="after")
    def identity(self) -> Self:
        if self.event_id != digest(self.model_dump(mode="json", exclude={"event_id"})):
            raise ValueError("Paper event identity mismatch")
        if (self.state == "FILLED") != (self.fill_id is not None):
            raise ValueError("FILLED requires actual simulated fill evidence")
        return self


class PaperReport(Contract):
    report_id: Hash
    session: date
    knowledge_cutoff: AwareDatetime
    policy_id: Hash
    policy: PaperPolicy
    valuation: PortfolioSnapshot
    starting_cash: Fraction
    ending_cash: Fraction
    available_cash: Fraction
    reserved_cash: Fraction
    orders_created: tuple[Hash, ...]
    fills: tuple[Hash, ...]
    exits: tuple[Hash, ...]
    signals_considered: tuple[Hash, ...]
    skipped: tuple[dict[str, str], ...]
    classification: Literal["PAPER", "TEST_ONLY_PAPER"]
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def identity(self) -> Self:
        if self.report_id != digest(self.model_dump(mode="json", exclude={"report_id"})):
            raise ValueError("Paper report identity mismatch")
        if self.disclaimer != paper_disclaimer(self.classification):
            raise ValueError("Paper simulation disclaimer cannot be upgraded")
        if self.policy_id != self.policy.policy_id:
            raise ValueError("Paper report policy identity mismatch")
        return self


class PaperState(Contract):
    version: Literal["p16.paper_state.v1"] = "p16.paper_state.v1"
    ledger: Ledger
    starting_cash: Fraction
    orders: tuple[PaperOrder, ...] = ()
    events: tuple[OrderEvent, ...] = ()
    fills: tuple[PaperFill, ...] = ()
    reports: tuple[PaperReport, ...] = ()

    @field_validator("starting_cash", mode="before")
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @property
    def state_id(self) -> str:
        return digest(self.model_dump(mode="json"))

    @property
    def classification(self) -> Literal["PAPER", "TEST_ONLY_PAPER"]:
        return "TEST_ONLY_PAPER" if self.ledger.portfolio.classification == "TEST_ONLY" else "PAPER"

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if self.ledger.portfolio.portfolio_type != "PAPER" or self.starting_cash <= 0:
            raise ValueError("Explicit funded PAPER account required")
        if len({o.order_id for o in self.orders}) != len(self.orders) or len(
            {f.fill_id for f in self.fills}
        ) != len(self.fills):
            raise ValueError("Duplicate paper order/fill")
        orders = {o.order_id: o for o in self.orders}
        latest: dict[str, str] = {}
        for event in self.events:
            if event.order_id not in orders or (
                event.order_id in latest and latest[event.order_id] != "PENDING"
            ):
                raise ValueError("Unknown order or terminal event rewritten")
            if event.order_id not in latest and event.state != "PENDING":
                raise ValueError("Lifecycle must begin PENDING")
            if event.order_id in latest and event.state == "PENDING":
                raise ValueError("Duplicate PENDING lifecycle event")
            if event.recorded_at < orders[event.order_id].decision_at:
                raise ValueError("Event precedes decision")
            latest[event.order_id] = event.state
        if set(latest) != set(orders):
            raise ValueError("Every intent requires lifecycle evidence")
        if len({r.session for r in self.reports}) != len(self.reports) or list(
            self.reports
        ) != sorted(self.reports, key=lambda r: r.session):
            raise ValueError("Unique chronological reports required")
        for fill in self.fills:
            order = orders.get(fill.order_id)
            if (
                not order
                or fill.session != order.target.session_date
                or order.decision_at >= fill.simulated_at
                or fill.evidence_available_at < fill.simulated_at
                or fill.classification != self.classification
                or not any(
                    t.transaction_id == fill.transaction_id and t.evidence_reference == fill.fill_id
                    for t in self.ledger.transactions
                )
            ):
                raise ValueError("Simulated fill/accounting/decision lineage contradiction")
            transaction = next(
                t for t in self.ledger.transactions if t.transaction_id == fill.transaction_id
            )
            if (
                transaction.security_id != order.security_id
                or transaction.kind != order.side
                or transaction.quantity != fill.quantity
                or transaction.price != fill.simulated_price
                or transaction.fees != fill.fees
                or transaction.effective_at != fill.simulated_at
                or transaction.recorded_at < fill.evidence_available_at
                or fill.simulated_at != order.target.open_at
            ):
                raise ValueError("Fill must match exact P15 accounting event")
        if {e.fill_id for e in self.events if e.state == "FILLED"} != {
            f.fill_id for f in self.fills
        }:
            raise ValueError("Fill lifecycle evidence mismatch")
        if any(o.classification != self.classification for o in self.orders) or any(
            r.classification != self.classification for r in self.reports
        ):
            raise ValueError("Paper classification mismatch")
        if any(o.account_id != self.ledger.portfolio.portfolio_id for o in self.orders):
            raise ValueError("Paper order account mismatch")
        if len({e.event_id for e in self.events}) != len(self.events):
            raise ValueError("Duplicate paper event identity")
        if any(
            t.kind in {"BUY", "SELL"}
            and t.transaction_id not in {f.transaction_id for f in self.fills}
            for t in self.ledger.transactions
        ):
            raise ValueError("Paper trade without simulated fill")
        deposits = [t for t in self.ledger.transactions if t.kind == "CASH_DEPOSIT"]
        if (
            len(deposits) != 1
            or deposits[0].cash_amount != self.starting_cash
            or deposits[0].source != "P16_SIMULATED_STARTING_CAPITAL"
            or any(
                t.kind in {"CASH_WITHDRAWAL", "OPENING_POSITION"} for t in self.ledger.transactions
            )
        ):
            raise ValueError("P16 v1 supports one declared starting-capital event only")
        return self


def paper_disclaimer(classification: str) -> str:
    if classification == "TEST_ONLY_PAPER":
        return "TEST_ONLY PAPER SIMULATION — NOT REAL MARKET PERFORMANCE"
    return "PAPER SIMULATION — NOT REAL EXECUTION; RESEARCH_FIXTURE NOT PRODUCTION VALIDATED"


def market_class(state: PaperState) -> Classification:
    return Classification(state.ledger.portfolio.classification)
