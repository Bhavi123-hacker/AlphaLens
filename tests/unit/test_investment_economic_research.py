"""TEST_ONLY constructed price references; no real-market performance claims."""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

import pytest
from workers.nse_market import economic_research as research


def rows() -> list[dict[str, Any]]:
    """Constructed daily clock avoids claiming an exchange holiday calendar."""
    start = date(2025, 1, 1)
    return [
        {
            "decision_session": (start + timedelta(days=index)).isoformat(),
            "target_session": (start + timedelta(days=index + 4)).isoformat(),
            "key": f"NSE_EQ|INETEST{key:04}",
            "actual_price_component_return": 0.01 * (key + 1),
            "actual_positive": 1,
            "classification": "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE",
            "scores": {"LSTM": key / 10, "XGBOOST": key / 11, "mean_reversion": (5 - key) / 10},
        }
        for index in range(41)
        for key in range(6)
    ]


def test_sparse_policy_uses_saved_original_targets_and_fewer_round_trips() -> None:
    days = research.validate_rows(rows())
    full = research.references(days, "LSTM", 5)
    sparse = research.references(days, "LSTM", 20)
    assert len(full) == 9 and len(sparse) == 3
    assert sparse[0]["gross_return"] == full[0]["gross_return"]
    assert sparse[0]["exit_session"] == "2025-01-05"
    assert sparse[1]["decision_session"] == "2025-01-21"
    assert sparse[0]["selected_count"] == 5
    assert sparse[0]["membership_turnover"] == 1
    assert sparse[1]["membership_turnover"] == 0


def test_every_round_trip_charged_even_when_membership_unchanged() -> None:
    path = research.references(research.validate_rows(rows()), "LSTM", 20)
    report = research.compound(path)
    movement = path[0]["gross_return"]
    assert report["net_compounded_reference_return"] == pytest.approx(
        (1 + movement - 0.006) ** 3 - 1
    )
    assert report["cost_log_wealth_drag"] > report["slippage_log_wealth_drag"] > 0
    assert report["gross_log_wealth"] - report["cost_log_wealth_drag"] - report[
        "slippage_log_wealth_drag"
    ] == pytest.approx(report["net_log_wealth"])
    assert len(report["curve"]) == 3


@pytest.mark.parametrize(
    "change",
    ["duplicate", "future", "nonfinite", "missing_target", "mixed_target", "wrong_direction"],
)
def test_invalid_source_rejected(change: str) -> None:
    source = rows()
    if change == "duplicate":
        source.append(deepcopy(source[0]))
    elif change == "future":
        source[0]["target_session"] = source[0]["decision_session"]
    elif change == "nonfinite":
        source[0]["scores"]["LSTM"] = float("nan")
    elif change == "missing_target":
        source[0]["actual_price_component_return"] = -1
    elif change == "mixed_target":
        source[0]["target_session"] = "2025-01-06"
    else:
        source[0]["actual_positive"] = 0
    with pytest.raises(ValueError):
        research.validate_rows(source)


def test_overlapping_target_clocks_rejected() -> None:
    source = rows()
    for row in source:
        row["target_session"] = (
            date.fromisoformat(row["decision_session"]) + timedelta(days=12)
        ).isoformat()
    with pytest.raises(ValueError, match="HORIZONS_OVERLAP"):
        research.references(research.validate_rows(source), "LSTM", 10)


def test_paired_uncertainty_matches_dates_and_is_deterministic() -> None:
    days = research.validate_rows(rows())
    path = research.references(days, "LSTM", 10)
    baseline = research.references(days, "mean_reversion", 10)
    assert research.paired(path, baseline) == research.paired(path, baseline)
    result = research.paired(path, baseline)
    assert result["mean_net_reference_return_difference"] > 0
    assert result["independent_confirmation"] is False
    with pytest.raises(ValueError, match="PAIRED_DATES"):
        research.paired(path, baseline[1:])


def test_rules_costs_and_empty_inputs_are_bounded() -> None:
    days = research.validate_rows(rows())
    with pytest.raises(ValueError, match="REGISTERED_ECONOMIC_RULE"):
        research.references(days, "LSTM", 15)
    with pytest.raises(ValueError):
        research.compound([], 50)
    with pytest.raises(ValueError):
        research.compound(research.references(days, "LSTM", 5), 0)
    with pytest.raises(ValueError, match="EMPTY"):
        research.validate_rows([])


def test_drawdown_endpoint_accounts_for_losses_and_cost_sensitivity() -> None:
    path = research.references(research.validate_rows(rows()), "LSTM", 20)
    path[1]["gross_return"] = -0.2
    low = research.compound(path, 25)
    high = research.compound(path, 100)
    assert high["net_compounded_reference_return"] < low["net_compounded_reference_return"]
    assert high["maximum_endpoint_drawdown"] == pytest.approx(-0.211)
    assert high["losing_net_references"] == 1
