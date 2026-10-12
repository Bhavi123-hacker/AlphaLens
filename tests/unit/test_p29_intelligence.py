"""Constructed TEST_ONLY research descriptors, never performance or real market labels."""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from workers.intelligence.methods import drift, regime, reliability

DAY = date(2024, 1, 2)


def cohort(day: date = DAY, **changes: Any) -> list[dict[str, Any]]:
    defaults = dict(
        session=str(day),
        close="100",
        quality="VALID",
        return_1=0.001,
        return_20=0.04,
        volatility_20=0.01,
        distance_sma_20=0.02,
        drawdown_20=-0.01,
        rsi_14=55,
        volume_ratio_20=1.1,
    )
    return [{**defaults, "security_id": f"TEST_ONLY:{i}", **changes} for i in range(128)]


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "BROAD_OBSERVED_UPTREND"),
        ({"return_20": -0.04, "distance_sma_20": -0.01}, "BROAD_OBSERVED_DOWNTREND"),
        ({"return_20": 0.001}, "MIXED_SIDEWAYS"),
        ({"volatility_20": 0.04, "drawdown_20": -0.15}, "HIGH_VOLATILITY_STRESS"),
    ],
)
def test_predeclared_descriptive_labels_replay(changes: dict[str, Any], expected: str) -> None:
    rows = cohort(**changes)
    result = regime(rows, DAY)
    assert result == regime(rows, DAY)
    assert result["classification"] == expected
    assert "NOT_FORECAST" in result["interpretation"]
    assert "NOT_ENTIRE_NSE" in result["universe"]


def test_missing_features_prices_and_pit_clocks_never_become_neutral() -> None:
    result = regime(cohort(return_20=None), DAY)
    assert result["classification"] == "INSUFFICIENT_EVIDENCE"
    assert result["metrics"]["return_20"]["median"] is None
    pit = regime(cohort(), DAY, strict_pit=True)
    assert pit["classification"] == "INSUFFICIENT_EVIDENCE"
    assert pit["exclusions"]["ACTUAL_AVAILABILITY_UNKNOWN"] == 128
    assert pit["metric_coverage"]["return_20"] is None
    assert regime(cohort(close=None), DAY)["eligible_observed"] == 0


def test_future_availability_and_rows_do_not_enter_earlier_description() -> None:
    cutoff = datetime(2024, 1, 3, tzinfo=UTC)
    result = regime(
        cohort(available_at="2024-01-04T00:00:00+00:00"), DAY, strict_pit=True, cutoff=cutoff
    )
    assert result["eligible_observed"] == 0
    original = regime(cohort(), DAY)
    future = [{**cohort(date(2025, 1, 2))[0], "security_id": "TEST_ONLY:FUTURE"}]
    later = regime(cohort() + future, DAY)
    assert original["classification"] == later["classification"]
    assert original["metrics"] == later["metrics"]
    assert original["observed_cohort"] == later["observed_cohort"]


def test_drift_is_empirical_units_and_separates_composition() -> None:
    past = date(2024, 1, 1)
    a, b = cohort(past), cohort(return_20=0.05)
    result = drift(a, b, past, DAY)
    feature = next(f for f in result["features"] if f["feature"] == "return_20")
    assert feature["wasserstein_1"] == pytest.approx(0.01)
    assert feature["paired_median_change"] == pytest.approx(0.01)
    assert result["statistical_significance"] == "NOT_TESTED"
    assert result["automatic_model_action"] == "DISABLED"
    b[0]["security_id"] = "TEST_ONLY:ENTERED"
    result = drift(a, b, past, DAY)
    assert result["entered_observed"] == result["departed_observed"] == 1
    assert result["common"] == 127


def test_small_or_future_drift_reference_is_unavailable() -> None:
    result = drift(cohort(date(2024, 1, 1))[:2], cohort()[:2], date(2024, 1, 1), DAY)
    assert all(f["wasserstein_1"] is None for f in result["features"])
    with pytest.raises(ValueError, match="PAST_ONLY"):
        drift(cohort(), cohort(), DAY, DAY)


def test_reliability_held_out_results_do_not_change_development_stability() -> None:
    row = {
        "model_run_id": "TEST_ONLY",
        "model_family": "TEST_ONLY",
        "task": "classification",
        "horizon": 1,
        "phase": "development",
        "fold_id": "TEST_ONLY",
        "scored_test_rows": 200,
        "metrics": {"balanced_accuracy": 0.5},
        "naive": {"balanced_accuracy": 0.5},
    }
    original = reliability([row])
    result = reliability(
        [
            row,
            {**row, "phase": "2026", "metrics": {"balanced_accuracy": 1.0}},
            {**row, "phase": "confirmation", "metrics": {"balanced_accuracy": 1.0}},
        ]
    )
    assert result["development_stability"] == original["development_stability"]
    assert all(r["current_inference"] == "NOT_ELIGIBLE" for r in result["matrix"])
    assert all(r["calibration"] == "CALIBRATION_UNAVAILABLE" for r in result["matrix"])
