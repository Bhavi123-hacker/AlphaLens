"""Bounded, exact user-entered records. Defaults are editable research assumptions."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=80)]
Key = Annotated[str, Field(pattern=r"^NSE_EQ\|[A-Z0-9]{12}$")]
ID = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


def amount(value: str, *, maximum: str = "1000000000000", zero: bool = True) -> Decimal:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("EXACT_DECIMAL_STRING_REQUIRED")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("EXACT_DECIMAL_STRING_REQUIRED") from None
    if (
        not number.is_finite()
        or number < 0
        or (not zero and number == 0)
        or number > Decimal(maximum)
        or not isinstance(number.as_tuple().exponent, int)
        or int(number.as_tuple().exponent) < -8
    ):
        raise ValueError("BOUNDED_NONNEGATIVE_DECIMAL_REQUIRED")
    return number


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)


class Profile(Closed):
    budget_inr: str | None = None
    risk_tolerance: Literal["Low", "Moderate", "High"] = "Moderate"
    horizon: Literal["Short", "Medium", "Long"] = "Medium"
    preferred_sectors: list[Name] = Field(default_factory=list, max_length=20)
    avoided_sectors: list[Name] = Field(default_factory=list, max_length=20)
    market_caps: list[Literal["Large", "Mid", "Small"]] = Field(default_factory=list, max_length=3)
    dividend_preference: Literal["Any", "Preferred"] = "Any"
    style: Literal["Any", "Growth", "Value"] = "Any"
    maximum_drawdown_percent: str = "20"
    maximum_stock_allocation_percent: str = "20"
    maximum_sector_exposure_percent: str = "40"
    desired_stocks: int = Field(default=10, ge=1, le=50)
    consider_holdings: bool = True
    minimum_volume: int | None = Field(default=None, ge=0, le=100000000000)
    maximum_daily_volatility_percent: str | None = None
    minimum_momentum_percent: str | None = None
    minimum_rsi: str | None = None
    maximum_rsi: str | None = None
    technical_condition: Literal["Any", "ABOVE_SMA20", "MACD_POSITIVE"] = "Any"

    @field_validator("minimum_momentum_percent")
    @classmethod
    def momentum(cls, value: str | None) -> str | None:
        if value is not None:
            amount(value.removeprefix("-"), maximum="100000")
        return value

    @field_validator("minimum_rsi", "maximum_rsi")
    @classmethod
    def rsi(cls, value: str | None) -> str | None:
        if value is not None:
            amount(value, maximum="100")
        return value

    @model_validator(mode="after")
    def ordered_rsi(self) -> "Profile":
        if (
            self.minimum_rsi is not None
            and self.maximum_rsi is not None
            and Decimal(self.minimum_rsi) > Decimal(self.maximum_rsi)
        ):
            raise ValueError("ORDERED_RSI_RANGE_REQUIRED")
        return self

    @field_validator("budget_inr")
    @classmethod
    def budget(cls, value: str | None) -> str | None:
        if value is not None:
            amount(value)
        return value

    @field_validator(
        "maximum_drawdown_percent",
        "maximum_stock_allocation_percent",
        "maximum_sector_exposure_percent",
        "maximum_daily_volatility_percent",
    )
    @classmethod
    def percent(cls, value: str | None) -> str | None:
        if value is not None:
            amount(value, maximum="100", zero=False)
        return value


class NamedList(Closed):
    name: Name
    instrument_keys: list[Key] = Field(default_factory=list, max_length=50)

    @field_validator("instrument_keys")
    @classmethod
    def distinct(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("DUPLICATE_INSTRUMENT")
        return value


class ManualEntry(Closed):
    request_id: ID
    kind: Literal["OPENING_POSITION", "BUY", "SELL", "CASH_DEPOSIT", "CASH_WITHDRAWAL"]
    instrument_key: Key | None = None
    session: date
    quantity: str = "0"
    price: str = "0"
    fees: str = "0"
    fees_known: bool = False
    cash_amount: str = "0"
    notes: str = Field(default="", max_length=500)

    @field_validator("quantity", "price", "fees", "cash_amount")
    @classmethod
    def numeric(cls, value: str) -> str:
        amount(value)
        return value


class JournalEntry(Closed):
    title: Name
    instrument_key: Key | None = None
    hypothesis: str = Field(default="", max_length=2000)
    intended_horizon: str = Field(default="", max_length=100)
    risk_assumptions: str = Field(default="", max_length=2000)
    outcome: str = Field(default="", max_length=2000)
    lessons: str = Field(default="", max_length=2000)


class AlertRule(Closed):
    name: Name
    kind: Literal[
        "PRICE_ABOVE",
        "PRICE_BELOW",
        "CHANGE_ABOVE",
        "CHANGE_BELOW",
        "VOLUME_ABOVE",
        "VOLATILITY_ABOVE",
        "DRAWDOWN_BELOW",
        "RSI_ABOVE",
        "RSI_BELOW",
        "CONCENTRATION_ABOVE",
        "STALE_DATA",
        "PROVIDER_UNAVAILABLE",
        "PREFERENCE_MATCH",
    ]
    instrument_key: Key | None = None
    portfolio_id: ID | None = None
    threshold: str = "0"
    enabled: bool = True
    evidence_source: Literal["LATEST_SUPPORTED", "QUOTE_ONLY", "DAILY_CANDLES"] = "LATEST_SUPPORTED"

    @field_validator("threshold")
    @classmethod
    def numeric(cls, value: str) -> str:
        # Direction is in the closed rule kind; thresholds are positive magnitudes.
        amount(value)
        return value


class Scenario(Closed):
    shock_percent: str = "0"
    instrument_key: Key | None = None
    quantity_delta: str = "0"
    cash_delta: str = "0"
    target_weights: dict[Key, str] = Field(default_factory=dict, max_length=50)
    transaction_cost_inr: str = "0"

    @field_validator("transaction_cost_inr")
    @classmethod
    def costs(cls, value: str) -> str:
        amount(value)
        return value

    @field_validator("shock_percent", "quantity_delta", "cash_delta")
    @classmethod
    def signed(cls, value: str) -> str:
        amount(value.removeprefix("-"))
        return value


UNSUPPORTED = (
    "VERIFIED_SECTORS",
    "MARKET_CAP",
    "DIVIDENDS",
    "PIT_FUNDAMENTALS_GROWTH_VALUE",
    "TOTAL_ECONOMIC_RETURNS",
    "CURRENT_ACCEPTED_ML_RANKINGS",
)
