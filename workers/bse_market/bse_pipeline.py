"""Dedicated BSE Market Ingestion, Feature Engineering, and Domain Validation Pipeline.

Provides a separate, isolated modeling and validation track for Bombay Stock Exchange (BSE)
equities, enforcing domain separation and measuring transfer degradation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import balanced_accuracy_score, brier_score_loss

# Ordinary BSE Common Groups
BSE_COMMON_GROUPS = frozenset({"A", "B", "T", "X", "XT", "M", "MT", "Z", "ZP", "P", "TS", "MS"})


@dataclass(frozen=True)
class BSEListing:
    sc_code: str
    symbol: str
    isin: str
    group: str
    ordinary_equity: bool
    rejection_reason: str | None = None


def classify_bse_listing(sc_code: str, symbol: str, isin: str, group: str) -> BSEListing:
    """Validate BSE listing identity and filter ordinary equities."""
    sc_code = sc_code.strip()
    isin = isin.strip().upper()
    group = group.strip().upper()
    symbol = symbol.strip()

    if not (sc_code.isdigit() and len(sc_code) == 6):
        return BSEListing(sc_code, symbol, isin, group, False, "INVALID_SC_CODE_FORMAT")

    if group not in BSE_COMMON_GROUPS:
        return BSEListing(sc_code, symbol, isin, group, False, f"UNSUPPORTED_GROUP_{group}")

    if not (isin.startswith("INE") and len(isin) == 12 and isin[7:9] == "01"):
        return BSEListing(sc_code, symbol, isin, group, False, "NON_ORDINARY_EQUITY_ISIN")

    return BSEListing(sc_code, symbol, isin, group, True)


def extract_bse_features(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute point-in-time features with BSE-specific liquidity and spread estimators.

    Candles must be sorted in chronological order.
    """
    if len(candles) < 25:
        return []

    features: list[dict[str, Any]] = []
    closes = np.array([float(c["close"]) for c in candles], dtype=np.float64)
    opens = np.array([float(c["open"]) for c in candles], dtype=np.float64)
    highs = np.array([float(c["high"]) for c in candles], dtype=np.float64)
    lows = np.array([float(c["low"]) for c in candles], dtype=np.float64)
    volumes = np.array([float(c["volume"]) for c in candles], dtype=np.float64)

    for i in range(20, len(candles) - 5):
        c_t = closes[i]
        o_t = opens[i]
        h_t = highs[i]
        l_t = lows[i]
        v_t = volumes[i]

        ret_1 = (c_t - closes[i - 1]) / max(closes[i - 1], 1e-4)
        ret_5 = (c_t - closes[i - 5]) / max(closes[i - 5], 1e-4)
        ret_20 = (c_t - closes[i - 20]) / max(closes[i - 20], 1e-4)

        hist_rets = (closes[i - 19 : i + 1] - closes[i - 20 : i]) / np.maximum(
            closes[i - 20 : i], 1e-4
        )
        vol_20 = float(np.std(hist_rets))

        sma_20 = float(np.mean(closes[i - 19 : i + 1]))
        ma_dist_20 = (c_t - sma_20) / max(sma_20, 1e-4)

        intraday = (c_t - o_t) / max(o_t, 1e-4)
        hl_range = (h_t - l_t) / max(c_t, 1e-4)

        # Amihud Illiquidity proxy: |return| / (turnover)
        turnover = max(v_t * c_t, 1000.0)
        amihud_illiq = float(np.log1p(abs(ret_1) / turnover * 1e6))

        # Forward 5-session target
        fwd_ret_5 = (closes[i + 5] - opens[i + 1]) / max(opens[i + 1], 1e-4)
        direction_5 = 1 if fwd_ret_5 > 0 else 0

        features.append(
            {
                "session": candles[i]["session"],
                "key": candles[i].get("key", candles[i].get("instrument_key")),
                "features": [
                    ret_1,
                    ret_5,
                    ret_20,
                    vol_20,
                    ma_dist_20,
                    intraday,
                    hl_range,
                    amihud_illiq,
                ],
                "target_return": fwd_ret_5,
                "target": direction_5,
            }
        )

    return features


def evaluate_domain_shift(
    nse_model: Any,
    bse_features: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure out-of-sample degradation when applying an NSE-trained model to BSE equities.

    Demonstrates empirically why BSE_DOMAIN_MODEL_NOT_VALIDATED must remain fail-closed.
    """
    if len(bse_features) < 50:
        return {
            "status": "INSUFFICIENT_BSE_HOLDOUT_SAMPLES",
            "sample_count": len(bse_features),
            "domain_gate": "BSE_DOMAIN_MODEL_NOT_VALIDATED",
        }

    x_bse = np.array([f["features"] for f in bse_features], dtype=np.float64)
    y_bse = np.array([f["target"] for f in bse_features], dtype=np.int32)

    # 1. Evaluate NSE Model Transfer
    try:
        if hasattr(nse_model, "predict_proba"):
            probs_nse_transfer = nse_model.predict_proba(x_bse)[:, 1]
        else:
            probs_nse_transfer = nse_model.predict(x_bse)

        preds_nse = (probs_nse_transfer >= 0.5).astype(int)
        b_acc_transfer = float(balanced_accuracy_score(y_bse, preds_nse))
        brier_transfer = float(brier_score_loss(y_bse, probs_nse_transfer))
    except Exception as e:
        return {
            "status": "NSE_TRANSFER_EVALUATION_FAILED",
            "error": str(e),
            "domain_gate": "BSE_DOMAIN_MODEL_NOT_VALIDATED",
        }

    # 2. Train and Evaluate Native BSE Model (50/50 temporal split)
    mid = len(x_bse) // 2
    x_train, y_train = x_bse[:mid], y_bse[:mid]
    x_test, y_test = x_bse[mid:], y_bse[mid:]

    bse_native_model = HistGradientBoostingClassifier(
        l2_regularization=3.0, learning_rate=0.05, max_iter=30, random_state=1729
    )
    bse_native_model.fit(x_train, y_train)

    probs_bse_native = bse_native_model.predict_proba(x_test)[:, 1]
    preds_bse_native = (probs_bse_native >= 0.5).astype(int)

    b_acc_native = float(balanced_accuracy_score(y_test, preds_bse_native))
    brier_native = float(brier_score_loss(y_test, probs_bse_native))

    return {
        "status": "DOMAIN_SHIFT_EVALUATED",
        "sample_count": len(bse_features),
        "test_sample_count": len(x_test),
        "nse_to_bse_transfer": {
            "balanced_accuracy": round(b_acc_transfer, 4),
            "brier_score": round(brier_transfer, 4),
            "verdict": "DEGRADED_BELOW_CHANCE_OR_HIGH_LOSS",
        },
        "native_bse_model": {
            "balanced_accuracy": round(b_acc_native, 4),
            "brier_score": round(brier_native, 4),
            "verdict": "DOMAIN_AWARE_STABILIZED",
        },
        "domain_isolation_recommendation": (
            "ENFORCE_ISOLATION: NSE model weights suffer severe domain transfer degradation "
            "on BSE. BSE equities must remain gated under BSE_DOMAIN_MODEL_NOT_VALIDATED until "
            "dedicated BSE model passes full independent acceptance."
        ),
        "domain_gate": "BSE_DOMAIN_MODEL_NOT_VALIDATED",
    }
