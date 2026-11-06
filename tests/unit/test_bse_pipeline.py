"""Unit tests for dedicated BSE Market Pipeline and Domain Shift Evaluation."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from workers.bse_market.bse_pipeline import (
    classify_bse_listing,
    evaluate_domain_shift,
    extract_bse_features,
)


def test_classify_bse_listing_valid_ordinary_equity() -> None:
    listing = classify_bse_listing(
        sc_code="500325",
        symbol="RELIANCE",
        isin="INE002A01018",
        group="A",
    )
    assert listing.ordinary_equity is True
    assert listing.rejection_reason is None
    assert listing.sc_code == "500325"
    assert listing.symbol == "RELIANCE"
    assert listing.isin == "INE002A01018"
    assert listing.group == "A"


def test_classify_bse_listing_invalid_sc_code() -> None:
    # 5 digits instead of 6
    listing = classify_bse_listing(
        sc_code="50032",
        symbol="INVALID",
        isin="INE002A01018",
        group="A",
    )
    assert listing.ordinary_equity is False
    assert listing.rejection_reason == "INVALID_SC_CODE_FORMAT"

    # Non-digit sc_code
    listing2 = classify_bse_listing(
        sc_code="ABCDEF",
        symbol="INVALID",
        isin="INE002A01018",
        group="A",
    )
    assert listing2.ordinary_equity is False
    assert listing2.rejection_reason == "INVALID_SC_CODE_FORMAT"


def test_classify_bse_listing_unsupported_group() -> None:
    listing = classify_bse_listing(
        sc_code="599999",
        symbol="DERIV",
        isin="INE002A01018",
        group="DEBENTURES",
    )
    assert listing.ordinary_equity is False
    assert "UNSUPPORTED_GROUP" in str(listing.rejection_reason)


def test_classify_bse_listing_non_ordinary_equity_isin() -> None:
    # Preference share / debt ISIN (not ending with equity sub-type 01)
    listing = classify_bse_listing(
        sc_code="500112",
        symbol="SBIN-PREF",
        isin="INE062A04012",
        group="A",
    )
    assert listing.ordinary_equity is False
    assert listing.rejection_reason == "NON_ORDINARY_EQUITY_ISIN"


def test_extract_bse_features_insufficient_candles() -> None:
    candles = [
        {
            "session": f"2026-10-{i:02d}",
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000,
        }
        for i in range(1, 15)
    ]
    features = extract_bse_features(candles)
    assert features == []


def test_extract_bse_features_computation() -> None:
    # 40 trading sessions
    candles = []
    base_price = 200.0
    for i in range(40):
        c_p = base_price + (i % 5) * 2.0
        candles.append(
            {
                "session": f"2026-09-{i + 1:02d}",
                "key": "BSE_EQ|INE002A01018",
                "open": c_p - 1.0,
                "high": c_p + 3.0,
                "low": c_p - 2.0,
                "close": c_p,
                "volume": 50000 + (i * 1000),
            }
        )

    features = extract_bse_features(candles)
    assert len(features) > 0
    first = features[0]
    assert "features" in first
    assert len(first["features"]) == 8  # 8 extracted features including Amihud illiq
    assert "target_return" in first
    assert first["target"] in (0, 1)


def test_evaluate_domain_shift_insufficient_samples() -> None:
    res = evaluate_domain_shift(None, [])
    assert res["status"] == "INSUFFICIENT_BSE_HOLDOUT_SAMPLES"
    assert res["domain_gate"] == "BSE_DOMAIN_MODEL_NOT_VALIDATED"


def test_evaluate_domain_shift_active_evaluation() -> None:
    # Generate 100 synthetic BSE feature records
    np.random.seed(42)
    bse_features = []
    for i in range(100):
        bse_features.append(
            {
                "session": f"2026-08-{i % 30 + 1:02d}",
                "key": f"BSE_EQ|INE{i:07d}01",
                "features": np.random.randn(8).tolist(),
                "target": int(np.random.rand() > 0.5),
            }
        )

    # Train a mock NSE model on random inputs
    nse_model = LogisticRegression(random_state=42)
    x_dummy = np.random.randn(50, 8)
    y_dummy = np.random.randint(0, 2, size=50)
    nse_model.fit(x_dummy, y_dummy)

    res = evaluate_domain_shift(nse_model, bse_features)
    assert res["status"] == "DOMAIN_SHIFT_EVALUATED"
    assert res["domain_gate"] == "BSE_DOMAIN_MODEL_NOT_VALIDATED"
    assert "nse_to_bse_transfer" in res
    assert "native_bse_model" in res
    assert "ENFORCE_ISOLATION" in res["domain_isolation_recommendation"]
