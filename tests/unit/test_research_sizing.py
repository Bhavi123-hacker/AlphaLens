"""TEST_ONLY exact financial scenarios; no real prices, orders or portfolio writes."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from workers.personal.research_sizing import calculate

from alphalens_data.errors import DataContractError

DAY = date(2026, 10, 16)


def inputs(**changes: Any) -> dict[str, Any]:
    return {
        "observed_price": Decimal("100"),
        "budget": Decimal("10000"),
        "loss_budget": Decimal("100"),
        "assumed_stop_percent": Decimal("5"),
        "round_trip_cost_bps": Decimal("100"),
        "observation_date": DAY,
        "source": "TEST_ONLY_DATED_REFERENCE",
        "as_of": DAY,
        **changes,
    }


def test_assumed_loss_budget_is_exact_and_cannot_be_presented_as_actual_loss_cap() -> None:
    result = calculate(**inputs())
    assert result["quantity_whole_units"] == 16
    assert result["assumed_loss_limited_units"] == 16 and result["budget_limited_units"] == 99
    assert Decimal(result["exact"]["assumed_stop_loss_including_cost"]) == Decimal("96")
    assert Decimal(result["exact"]["budget_used_including_assumed_cost"]) == Decimal("1616")
    assert result["verified_cash_balance"] is None
    assert result["writes_performed"] is result["stop_is_guaranteed"] is False
    assert "full allocated capital" in result["limitations"][0]


def test_capital_budget_limits_units_and_preserves_full_round_trip_cost_reserve() -> None:
    result = calculate(**inputs(budget=Decimal("1000"), loss_budget=Decimal("1000")))
    assert result["quantity_whole_units"] == 9
    assert result["limiting_assumption"] == "BUDGET"
    assert Decimal(result["exact"]["unallocated_research_budget"]) == 91


def test_fractional_price_stop_and_costs_keep_exact_decimal_amounts() -> None:
    result = calculate(
        **inputs(
            observed_price=Decimal("19.99"),
            budget=Decimal("100"),
            loss_budget=Decimal("10"),
            assumed_stop_percent=Decimal("4.5"),
            round_trip_cost_bps=Decimal("25"),
        )
    )
    assert result["quantity_whole_units"] == 4
    exact = {key: Decimal(value) for key, value in result["exact"].items()}
    assert exact["nominal_position_reference"] == Decimal("79.96")
    assert exact["assumed_round_trip_cost"] == Decimal("0.1999")
    assert exact["assumed_stop_loss_including_cost"] == Decimal("3.7981")
    assert exact["unallocated_research_budget"] == Decimal("19.8401")


def test_zero_units_and_explicit_zero_cost_are_valid_descriptive_results() -> None:
    result = calculate(**inputs(budget=Decimal("20")))
    assert result["quantity_whole_units"] == 0
    assert result["state"] == "NO_WHOLE_UNIT_WITHIN_ASSUMPTIONS"
    result = calculate(**inputs(round_trip_cost_bps=Decimal("0")))
    assert result["quantity_whole_units"] == 20
    assert Decimal(result["exact"]["assumed_round_trip_cost"]) == 0


def test_large_whole_unit_results_also_have_lossless_json_string_representations() -> None:
    result = calculate(
        **inputs(
            observed_price=Decimal("0.000000000000000001"),
            budget=Decimal("1e18"),
            loss_budget=Decimal("1e18"),
            round_trip_cost_bps=Decimal("0"),
        )
    )
    assert result["quantity_whole_units"] == 10**36
    assert result["exact"]["quantity_whole_units"] == "1" + "0" * 36


@pytest.mark.parametrize(
    "change",
    [
        {"observed_price": 100.0},
        {"budget": Decimal("NaN")},
        {"loss_budget": Decimal("Infinity")},
        {"observed_price": Decimal("0")},
        {"budget": Decimal("-1")},
        {"loss_budget": Decimal("0")},
        {"assumed_stop_percent": Decimal("0")},
        {"assumed_stop_percent": Decimal("100.01")},
        {"round_trip_cost_bps": Decimal("-1")},
        {"round_trip_cost_bps": Decimal("10001")},
        {"observed_price": Decimal("1e-19")},
        {"budget": Decimal("1e19")},
        {"observation_date": DAY + timedelta(days=1)},
        {"source": " "},
    ],
)
def test_invalid_unknown_or_future_inputs_are_rejected(change: dict[str, Any]) -> None:
    with pytest.raises(DataContractError):
        calculate(**inputs(**change))
