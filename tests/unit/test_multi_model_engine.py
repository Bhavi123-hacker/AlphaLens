"""Unit tests for Multi-Model Multi-Horizon Training and Prospective Prediction Engine."""

from __future__ import annotations

import numpy as np
from workers.nse_market.multi_model_engine import (
    extract_features_and_targets,
    generate_prospective_rankings,
    train_and_evaluate_all_models,
)


def _generate_synthetic_history(n_sessions: int = 60, seed: int = 42) -> dict[str, list[dict]]:
    np.random.seed(seed)
    histories = {}
    for k in ["NSE_EQ|INE002A01018", "NSE_EQ|INE009A01021", "NSE_EQ|INE040A01034"]:
        candles = []
        price = 1000.0
        for i in range(n_sessions):
            ret = np.random.normal(0.0005, 0.015)
            price *= 1.0 + ret
            open_p = price * (1.0 - np.random.uniform(-0.005, 0.005))
            high_p = max(price, open_p) * 1.01
            low_p = min(price, open_p) * 0.99
            candles.append(
                {
                    "session": f"2026-08-{i + 1:02d}" if i < 30 else f"2026-09-{i - 29:02d}",
                    "open": round(open_p, 2),
                    "high": round(high_p, 2),
                    "low": round(low_p, 2),
                    "close": round(price, 2),
                    "volume": int(np.random.uniform(10000, 500000)),
                }
            )
        histories[k] = candles
    return histories


def test_extract_features_and_targets() -> None:
    histories = _generate_synthetic_history(n_sessions=60)
    samples, feature_names = extract_features_and_targets(histories)

    assert len(feature_names) == 12
    assert len(samples) > 0

    first = samples[0]
    assert len(first["features"]) == 12
    assert "target_ret_1" in first
    assert "target_dir_1" in first
    assert "target_ret_5" in first
    assert "target_dir_5" in first
    assert "target_ret_10" in first
    assert "target_dir_10" in first
    assert "target_ret_20" in first
    assert "target_dir_20" in first

    # Check prospective horizon: the very last sample of a series has None forward targets
    last_samples = [s for s in samples if s["session"] == "2026-09-30"]
    for s in last_samples:
        assert s["target_ret_1"] is None
        assert s["target_ret_5"] is None
        assert s["target_ret_10"] is None
        assert s["target_ret_20"] is None


def test_multi_model_training_and_rankings() -> None:
    # Generate larger history across 10 securities for training
    np.random.seed(123)
    histories = {}
    for s_idx in range(10):
        isin = f"INE{s_idx:07d}01"
        key = f"NSE_EQ|{isin}"
        candles = []
        price = 500.0 + s_idx * 50
        for i in range(95):
            ret = np.random.normal(0.0003, 0.015)
            price *= 1.0 + ret
            open_ret = np.random.normal(0.0, 0.01)
            open_p = price * (1.0 + open_ret)
            high_p = max(price, open_p) * 1.01
            low_p = min(price, open_p) * 0.99
            candles.append(
                {
                    "session": f"2026-06-{i + 1:02d}"
                    if i < 30
                    else (f"2026-07-{i - 29:02d}" if i < 60 else f"2026-08-{i - 59:02d}"),
                    "open": round(open_p, 2),
                    "high": round(high_p, 2),
                    "low": round(low_p, 2),
                    "close": round(price, 2),
                    "volume": 25000 + s_idx * 1000,
                }
            )
        histories[key] = candles

    samples, feature_names = extract_features_and_targets(histories)
    train_res = train_and_evaluate_all_models(samples, feature_names)

    assert "metrics" in train_res
    assert "models" in train_res
    assert len(train_res["metrics"]) > 0

    # Generate prospective rankings for latest session
    latest_session = max(s["session"] for s in samples)
    rankings = generate_prospective_rankings(
        samples, train_res["models"], as_of_session=latest_session
    )

    assert "Horizon_1" in rankings
    assert "Horizon_5" in rankings
    assert "Horizon_10" in rankings
    assert "Horizon_20" in rankings

    h5 = rankings["Horizon_5"]
    assert len(h5["top_5"]) <= 5
    assert len(h5["top_10"]) <= 10
    assert len(h5["top_20"]) <= 20
    assert h5["as_of_session"] == latest_session

    # Verify descending sort order on expected returns
    rets = [item["expected_return"] for item in h5["top_5"]]
    assert rets == sorted(rets, reverse=True)
