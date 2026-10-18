"""Pure, explicit Decimal research sizing; no orders, cash claims or ledger writes."""

from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

from alphalens_data.errors import DataContractError


def _number(value: Decimal, *, allow_zero: bool = False) -> Decimal:
    if not isinstance(value, Decimal):
        raise DataContractError("FINITE_BOUNDED_EXACT_DECIMAL_RESEARCH_INPUT_REQUIRED")
    exponent = value.as_tuple().exponent
    if (
        not value.is_finite()
        or value < 0
        or (not allow_zero and value == 0)
        or value > Decimal("1e18")
        or not isinstance(exponent, int)
        or exponent < -18
    ):
        raise DataContractError("FINITE_BOUNDED_EXACT_DECIMAL_RESEARCH_INPUT_REQUIRED")
    return value


def calculate(
    *,
    observed_price: Decimal,
    budget: Decimal,
    loss_budget: Decimal,
    assumed_stop_percent: Decimal,
    round_trip_cost_bps: Decimal,
    observation_date: date,
    source: str,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Whole-unit ceiling under budget and a user-declared stop/cost assumption.

    The assumed stop does not cap actual loss. The reference price, costs and
    whole units do not establish a tradable lot, available cash or execution.
    """
    price = _number(observed_price)
    capital = _number(budget)
    risk = _number(loss_budget)
    stop = _number(assumed_stop_percent)
    cost_bps = _number(round_trip_cost_bps, allow_zero=True)
    today = as_of or datetime.now(UTC).date()
    if (
        stop > 100
        or cost_bps > 10000
        or type(observation_date) is not date
        or type(today) is not date
        or observation_date > today
        or not isinstance(source, str)
        or not 1 <= len(source.strip()) <= 200
    ):
        raise DataContractError("DATED_SOURCE_AND_BOUNDED_STOP_COST_ASSUMPTIONS_REQUIRED")
    with localcontext() as context:
        context.prec = 128
        stop_fraction, cost_fraction = stop / 100, cost_bps / 10000
        unit_total = price * (1 + cost_fraction)
        unit_assumed_loss = price * (stop_fraction + cost_fraction)
        # Fraction retains exact Decimal ratios before integer flooring.
        by_budget = Fraction(capital) // Fraction(unit_total)
        by_loss = Fraction(risk) // Fraction(unit_assumed_loss)
        quantity = min(by_budget, by_loss)
        nominal = price * quantity
        assumed_cost = nominal * cost_fraction
        assumed_loss = unit_assumed_loss * quantity
        values = {
            "observed_price": price,
            "research_budget": capital,
            "loss_budget": risk,
            "assumed_stop_percent": stop,
            "round_trip_cost_bps": cost_bps,
            "nominal_position_reference": nominal,
            "assumed_round_trip_cost": assumed_cost,
            "budget_used_including_assumed_cost": nominal + assumed_cost,
            "unallocated_research_budget": capital - nominal - assumed_cost,
            "assumed_stop_loss_including_cost": assumed_loss,
            "unused_assumed_loss_budget": risk - assumed_loss,
            "assumed_stop_price_reference": price * (1 - stop_fraction),
            "capital_at_risk_before_costs": nominal,
        }
        return {
            "state": "HYPOTHETICAL_RESEARCH_SIZING"
            if quantity
            else "NO_WHOLE_UNIT_WITHIN_ASSUMPTIONS",
            "classification": (
                "DATED_INDICATIVE_PRICE_REFERENCE_NOT_EXECUTION_OR_ACCEPTED_VALUATION"
            ),
            "quantity_whole_units": quantity,
            "budget_limited_units": by_budget,
            "assumed_loss_limited_units": by_loss,
            "limiting_assumption": "BUDGET"
            if by_budget < by_loss
            else "ASSUMED_LOSS_BUDGET"
            if by_loss < by_budget
            else "BOTH",
            "observation_date": observation_date.isoformat(),
            "source": source.strip(),
            "exact": {
                "quantity_whole_units": str(quantity),
                "budget_limited_units": str(by_budget),
                "assumed_loss_limited_units": str(by_loss),
                **{name: format(value, "f") for name, value in values.items()},
            },
            "verified_cash_balance": None,
            "stop_is_guaranteed": False,
            "lot_and_liquidity_eligibility": "UNKNOWN_WHOLE_UNITS_ARE_NOT_VERIFIED_TRADABLE_LOTS",
            "writes_performed": False,
            "allocation_percent_of_budget": format(nominal / capital * 100, "f"),
            "adverse_scenarios": [
                {
                    "adverse_move_percent": move,
                    "price_reference": format(price * (1 - Decimal(move) / 100), "f"),
                    "price_loss": format(nominal * Decimal(move) / 100, "f"),
                    "assumed_cost": format(assumed_cost, "f"),
                    "loss_including_cost": format(
                        nominal * Decimal(move) / 100 + assumed_cost, "f"
                    ),
                    "loss_budget_exceeded": nominal * Decimal(move) / 100 + assumed_cost > risk,
                }
                for move in (5, 10, 20)
            ],
            "limitations": [
                "A gap or failed stop may lose the full allocated capital plus costs; "
                "the assumed loss budget is not a guarantee.",
                "Both-leg costs are assumed on the observed price reference; future fees, "
                "taxes, spreads, slippage and fills are unverified.",
                "Research budget is user supplied and is not a verified cash balance "
                "or instruction to buy or sell.",
                "Lot size, suspension, liquidity, price bands and execution feasibility "
                "require separate evidence.",
            ],
        }
