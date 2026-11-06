"""TEST_ONLY sequence contracts; never genuine market or performance evidence."""

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

import numpy as np
import pytest
from workers.experimental_nse_v2.features import Sample
from workers.nse_market import sequence


def sample(day: str, index: int) -> Sample:
    return Sample(
        "TEST_ONLY_KEY",
        "TEST_ONLY",
        day,
        tuple(float(index + i) for i in range(16)),
        "100",
        day,
        0.01,
        1,
        (0.01,),
        {"return_daily_sd_20": 0.01},
    )


def test_trailing_sequence_excludes_future_values_targets_and_missing_states() -> None:
    days = [str(date(2023, 1, 1) + timedelta(days=i)) for i in range(25)]
    samples = tuple(sample(day, i) for i, day in enumerate(days))
    before = sequence.sequences(samples, days)
    assert len(before) == 6
    assert len(before[0].values) == 20 and len(before[0].values[0]) == 8
    assert before[0].values[-1][0] == samples[19].vector[0]
    altered = (*samples[:-1], replace(samples[-1], vector=(999.0,) * 16, target=0))
    assert sequence.sequences(altered, days)[0].values == before[0].values
    assert (
        sequence.sequences(tuple(replace(s, target=0, target_return=-0.9) for s in samples), days)[
            0
        ].values
        == before[0].values
    )
    assert sequence.sequences(samples[:10] + samples[11:], days) == []


def test_shared_date_partition_purges_targets_and_embargoes_boundaries() -> None:
    days = [str(date(2023, 12, 1) + timedelta(days=i)) for i in range(430)]
    items = [sequence.Sequence(sample(day, i), ((0.0,) * 8,) * 20) for i, day in enumerate(days)]
    items[20] = replace(items[20], sample=replace(items[20].sample, target_session="2024-01-05"))
    parts = sequence.partitions(items, days)
    assert items[20] not in parts["training"]
    assert min(x.sample.session for x in parts["validation"]) == "2024-01-21"
    assert min(x.sample.session for x in parts["development_report"]) == "2025-01-21"
    assert max(str(x.sample.target_session) for x in parts["training"]) < "2024-01-01"


def test_plain_numeric_lstm_model_contract_and_prediction() -> None:
    model: dict[str, Any] = {
        "family": sequence.FAMILY,
        "feature_version": sequence.VERSION,
        "feature_names": list(sequence.NAMES),
        "sequence_length": 20,
        "mean": [0] * 8,
        "scale": [1] * 8,
        "state": {
            "0.weight_ih_l0": np.zeros((64, 8)).tolist(),
            "0.weight_hh_l0": np.zeros((64, 16)).tolist(),
            "0.bias_ih_l0": [0] * 64,
            "0.bias_hh_l0": [0] * 64,
            "2.weight": [[0] * 16],
            "2.bias": [0],
        },
    }
    assert np.array_equal(sequence.predict(model, np.zeros((2, 20, 8))), [0.5, 0.5])
    with pytest.raises(ValueError, match="ORDERED_SEQUENCE"):
        sequence.predict(model, np.zeros((2, 19, 8)))
    with pytest.raises(ValueError, match="SCALING"):
        sequence.predict({**model, "scale": [0] * 8}, np.zeros((1, 20, 8)))
    with pytest.raises(ValueError, match="MODEL_REQUIRED"):
        sequence.predict(
            {**model, "feature_names": list(reversed(sequence.NAMES))}, np.zeros((1, 20, 8))
        )
    with pytest.raises(ValueError, match="STATE_REQUIRED"):
        sequence.predict(
            {**model, "state": {**model["state"], "unreviewed.executable": []}},
            np.zeros((1, 20, 8)),
        )


def test_predeclared_costs_are_charged_even_when_membership_is_unchanged() -> None:
    samples = [
        replace(
            sample(str(date(2023, 1, 1) + timedelta(days=i)), i),
            target_return=0.001,
            target_session=str(date(2023, 1, 6) + timedelta(days=i)),
        )
        for i in range(10)
    ]
    result = sequence.economics(samples, [0.6] * 10)
    strategy = result["strategies"]["top5"]
    assert strategy["decision_count"] == 2
    assert strategy["scenarios"][0]["round_trip_cost_bps"] == 25
    assert strategy["scenarios"][0]["net_compounded_reference_return"] == pytest.approx(
        (1 + 0.001 - 0.0035) ** 2 - 1
    )
    assert result["full_path_economic_compatibility_verified"] is False
