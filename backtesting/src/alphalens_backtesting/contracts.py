"""Explicit hypothetical execution/capital/scenario contracts; no production permission."""

from datetime import date
from decimal import Decimal
from fractions import Fraction
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, field_validator, model_validator

from alphalens_data.canonical.models import reject_float
from alphalens_data.contracts import Contract
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_evaluation.contracts import Family, digest

VERSION: Literal["p10.backtest.v1"] = "p10.backtest.v1"


class CostScenario(Contract):
    version: Literal["p10.cost_assumption.v1"] = "p10.cost_assumption.v1"
    name: str = Field(min_length=1)
    status: Literal["ASSUMPTION_NOT_VERIFIED_BROKER_OR_REGULATORY_SCHEDULE"] = (
        "ASSUMPTION_NOT_VERIFIED_BROKER_OR_REGULATORY_SCHEDULE"
    )
    brokerage_bps: Decimal = Field(ge=0, le=1000)
    exchange_bps: Decimal = Field(ge=0, le=1000)
    taxes_fees_bps: Decimal = Field(ge=0, le=1000)
    slippage_bps: Decimal = Field(ge=0, le=1000)

    @field_validator(
        "brokerage_bps", "exchange_bps", "taxes_fees_bps", "slippage_bps", mode="before"
    )
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @property
    def fee_rate(self) -> Fraction:
        return (
            sum(
                (Fraction(v) for v in (self.brokerage_bps, self.exchange_bps, self.taxes_fees_bps)),
                Fraction(0),
            )
            / 10000
        )

    @property
    def slip_rate(self) -> Fraction:
        return Fraction(self.slippage_bps) / 10000


def scenarios() -> tuple[CostScenario, ...]:
    return tuple(
        CostScenario(
            name=name,
            brokerage_bps=str(brokerage),
            exchange_bps=str(exchange),
            taxes_fees_bps=str(taxes),
            slippage_bps=str(slip),
        )
        for name, brokerage, exchange, taxes, slip in (
            ("ZERO_COST_DIAGNOSTIC", 0, 0, 0, 0),
            ("LOW_COST_ASSUMPTION", 2, 1, 2, 2),
            ("HIGHER_COST_STRESS", 10, 5, 10, 10),
        )
    )


class BenchmarkEvidence(Contract):
    security_id: str
    name: str
    classification: Classification
    canonical_input_id: Hash
    rights_evidence_reference: str = Field(min_length=1)
    return_basis: Literal["OBSERVED_PRICE_ONLY_NOT_TOTAL_RETURN"] = (
        "OBSERVED_PRICE_ONLY_NOT_TOTAL_RETURN"
    )

    @model_validator(mode="after")
    def safe(self) -> Self:
        if self.classification == Classification.PRODUCTION or (
            self.classification == Classification.TEST_ONLY and self.name != "TEST_ONLY_BENCHMARK"
        ):
            raise ValueError("No real benchmark name for constructed data; production not cleared")
        return self


class BacktestDefinition(Contract):
    version: Literal["p10.backtest.v1"] = VERSION
    code_version: Literal["p10.engine.v1"] = "p10.engine.v1"
    evaluation_id: Hash
    oos_prediction_dataset_id: Hash
    canonical_input_id: Hash
    feature_set_id: Hash
    comparison_context_id: Hash | None = None
    execution_calendar_id: Hash
    universe_definition_id: str
    model_family: Family
    horizon: Literal[1, 5, 10, 20]
    start_session: date
    end_session: date
    selection_rule: Literal["TOP_K", "TOP_PERCENTILE", "PREDICTION_THRESHOLD"] = "TOP_K"
    top_k: int = Field(default=2, ge=1, le=10000)
    top_percentile: Decimal = Field(default=Decimal("0.2"), gt=0, le=1)
    prediction_threshold: Decimal = Decimal("0.5")
    policy_role: Literal["MECHANICAL_EXPERIMENT_NOT_PRODUCT_SIGNAL"] = (
        "MECHANICAL_EXPERIMENT_NOT_PRODUCT_SIGNAL"
    )
    position_sizing: Literal["EQUAL_WEIGHT"] = "EQUAL_WEIGHT"
    allocation_rule: Literal["AVAILABLE_CASH_DIVIDED_BY_FREE_SLOTS"] = (
        "AVAILABLE_CASH_DIVIDED_BY_FREE_SLOTS"
    )
    execution_convention: Literal["NEXT_VERIFIED_SESSION_OPEN_PRIOR_LOCAL_DATE_DECISION"] = (
        "NEXT_VERIFIED_SESSION_OPEN_PRIOR_LOCAL_DATE_DECISION"
    )
    knowledge_cutoff_policy: Literal["DECISION_PIT_ENTRY_BOUNDARY_EOD_DATE_END_VINTAGE"] = (
        "DECISION_PIT_ENTRY_BOUNDARY_EOD_DATE_END_VINTAGE"
    )
    initial_capital: Decimal = Field(default=Decimal("100000"), gt=0)
    currency: Literal["INR"] = "INR"
    fractional_quantity_policy: Literal["HYPOTHETICAL_EXACT_RATIONAL_NOT_EXCHANGE_ORDER"] = (
        "HYPOTHETICAL_EXACT_RATIONAL_NOT_EXCHANGE_ORDER"
    )
    maximum_positions: int = Field(default=3, ge=1, le=10000)
    rebalance_policy: Literal["NEW_PREDICTIONS_FREE_SLOTS_HORIZON_EXITS_NO_REPLACEMENT"] = (
        "NEW_PREDICTIONS_FREE_SLOTS_HORIZON_EXITS_NO_REPLACEMENT"
    )
    price_basis: Literal["RAW_UNADJUSTED"] = "RAW_UNADJUSTED"
    price_quality_policy: Literal["VALID_OR_DEGRADED_EXPLICITLY_RETAIN_QUALITY"] = (
        "VALID_OR_DEGRADED_EXPLICITLY_RETAIN_QUALITY"
    )
    corporate_action_policy: Literal["KNOWN_ECONOMIC_ACTION_UNRESOLVED_NO_INVENTED_ADJUSTMENT"] = (
        "KNOWN_ECONOMIC_ACTION_UNRESOLVED_NO_INVENTED_ADJUSTMENT"
    )
    missing_exit_policy: Literal["RETAIN_UNRESOLVED_NO_ZERO_OR_CLOSE_SUBSTITUTION"] = (
        "RETAIN_UNRESOLVED_NO_ZERO_OR_CLOSE_SUBSTITUTION"
    )
    costs: CostScenario
    benchmark: BenchmarkEvidence | None = None
    baseline: Literal["MODEL", "EQUAL_WEIGHT_ELIGIBLE_COHORT", "SEEDED_RANDOM_CONTROL"] = "MODEL"
    random_seed: int = Field(default=1729, ge=0, le=2**32 - 1)
    annual_sessions_assumption: int = Field(default=252, ge=1)
    annualization_minimum_sessions: int = Field(default=252, ge=252)
    risk_free_annual_assumption: Decimal = Field(default=Decimal("0"), ge=0)
    data_classification: Classification
    production_claims_permitted: Literal[False] = False

    @field_validator(
        "initial_capital",
        "top_percentile",
        "prediction_threshold",
        "risk_free_annual_assumption",
        mode="before",
    )
    @classmethod
    def exact(cls, value: object) -> object:
        return reject_float(value)

    @model_validator(mode="after")
    def safe(self) -> Self:
        if (
            self.end_session < self.start_session
            or self.data_classification == Classification.PRODUCTION
        ):
            raise ValueError("Invalid period or production clearance not granted")
        if self.benchmark and (
            self.benchmark.classification != self.data_classification
            or self.benchmark.canonical_input_id != self.canonical_input_id
        ):
            raise ValueError("Benchmark classification/input mismatch")
        return self


class CalendarDay(Contract):
    session_date: date
    status: Literal[
        "VERIFIED_TRADING_SESSION", "VERIFIED_NON_TRADING_SESSION", "UNKNOWN_SESSION_STATUS"
    ]
    available_at: AwareDatetime
    open_at: AwareDatetime | None = None
    open_clock_policy: Literal["EXPLICIT_SESSION_OPEN_CONVENTION", "UNKNOWN"] = "UNKNOWN"
    evidence_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def clock(self) -> Self:
        if self.open_at is not None and (
            self.status != "VERIFIED_TRADING_SESSION"
            or self.open_clock_policy == "UNKNOWN"
            or self.open_at.astimezone(ZoneInfo("Asia/Kolkata")).date() != self.session_date
        ):
            raise ValueError("Open convention needs explicit same-date trading-session evidence")
        return self


class ExecutionCalendar(Contract):
    version: Literal["p10.execution_calendar.v1"] = "p10.execution_calendar.v1"
    canonical_input_id: Hash
    classification: Classification
    days: tuple[CalendarDay, ...]
    evidence_reference: str = Field(min_length=1)
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def ordered(self) -> Self:
        dates = [d.session_date for d in self.days]
        if (
            not dates
            or dates != sorted(set(dates))
            or self.classification == Classification.PRODUCTION
        ):
            raise ValueError("Unique chronological development calendar required")
        return self

    @property
    def calendar_id(self) -> str:
        return digest(self.model_dump(mode="json"))
