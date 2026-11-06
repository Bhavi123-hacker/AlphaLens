"""Market Regime Classifier for AlphaLens Research Pipeline.

Identifies macro market regimes (Bull-Trending, Bear-Trending, High-Vol Choppy, Low-Vol Range)
using benchmark index and cross-sectional market breadth indicators.
Enables regime-conditional model weighting and volatility-adjusted risk filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np


class MarketRegime(StrEnum):
    BULL_TRENDING = "BULL_TRENDING"
    BEAR_TRENDING = "BEAR_TRENDING"
    HIGH_VOL_CHOPPY = "HIGH_VOL_CHOPPY"
    LOW_VOL_RANGE = "LOW_VOL_RANGE"


@dataclass(frozen=True)
class RegimeState:
    session: str
    regime: MarketRegime
    trend_score: float
    volatility_percentile: float
    breadth_ratio: float
    confidence: float
    recommended_equity_exposure: float


def classify_market_regime(
    benchmark_candles: list[dict[str, Any]],
    cross_sectional_returns: list[float] | None = None,
) -> RegimeState:
    """Classify market regime based on benchmark price action and market breadth."""
    if len(benchmark_candles) < 20:
        latest_session = benchmark_candles[-1]["session"] if benchmark_candles else "UNKNOWN"
        return RegimeState(
            session=latest_session,
            regime=MarketRegime.LOW_VOL_RANGE,
            trend_score=0.0,
            volatility_percentile=50.0,
            breadth_ratio=0.5,
            confidence=0.5,
            recommended_equity_exposure=0.5,
        )

    closes = np.array([float(c["close"]) for c in benchmark_candles], dtype=np.float64)
    session = str(benchmark_candles[-1]["session"])

    # 1. Trend Score: 20-day SMA distance & 5-day slope
    sma_20 = float(np.mean(closes[-20:]))
    current_close = float(closes[-1])
    sma_dist = (current_close - sma_20) / max(sma_20, 1e-4)

    ret_5 = (current_close - closes[-5]) / max(closes[-5], 1e-4)
    ret_20 = (current_close - closes[-20]) / max(closes[-20], 1e-4)
    trend_score = float(0.5 * sma_dist + 0.3 * ret_5 + 0.2 * ret_20)

    # 2. Realized Volatility: 20-day standard deviation of log returns
    log_returns = np.diff(np.log(np.maximum(closes[-21:], 1e-4)))
    realized_vol_annualized = float(np.std(log_returns) * np.sqrt(252))

    # Normalize volatility against historical typical range (10% to 30%)
    vol_pct = float(np.clip((realized_vol_annualized - 0.10) / (0.30 - 0.10) * 100.0, 0.0, 100.0))

    # 3. Market Breadth: fraction of universe with positive 1-day return
    if cross_sectional_returns and len(cross_sectional_returns) > 0:
        breadth = float(np.mean(np.array(cross_sectional_returns) > 0))
    else:
        breadth = 0.55 if trend_score > 0 else 0.45

    # 4. Regime Determination
    if vol_pct > 70.0:
        regime = MarketRegime.HIGH_VOL_CHOPPY
        exposure = 0.30
        confidence = float(np.clip(vol_pct / 100.0, 0.6, 0.95))
    elif trend_score > 0.01 and breadth > 0.50:
        regime = MarketRegime.BULL_TRENDING
        exposure = 1.00
        confidence = float(np.clip(0.5 + trend_score * 5.0, 0.6, 0.95))
    elif trend_score < -0.01 and breadth < 0.50:
        regime = MarketRegime.BEAR_TRENDING
        exposure = 0.20
        confidence = float(np.clip(0.5 - trend_score * 5.0, 0.6, 0.95))
    else:
        regime = MarketRegime.LOW_VOL_RANGE
        exposure = 0.60
        confidence = 0.65

    return RegimeState(
        session=session,
        regime=regime,
        trend_score=round(trend_score, 4),
        volatility_percentile=round(vol_pct, 2),
        breadth_ratio=round(breadth, 4),
        confidence=round(confidence, 4),
        recommended_equity_exposure=round(exposure, 2),
    )
