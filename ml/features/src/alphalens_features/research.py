"""Bounded array execution of the existing P6 registry on P5 research slots.

No fitted statistics. Missing calendar slots stay NaN internally and null on disk.
The scalar P6 maths implementation remains the reference tested against this path.
"""

from typing import Any

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from alphalens_features.maths import calculate
from alphalens_features.models import FeatureDefinition


def numerical(
    definition: FeatureDefinition,
    close: np.ndarray[Any, Any],
    high: np.ndarray[Any, Any],
    low: np.ndarray[Any, Any],
    volume: np.ndarray[Any, Any],
) -> np.ndarray[Any, Any]:
    n = definition.lookback
    name = definition.feature_name
    output = np.full(len(close), np.nan)
    if len(close) < n:
        limit = len(close)
    else:
        c, h, lo, v = (sliding_window_view(x, n) for x in (close, high, low, volume))
        valid = np.isfinite(c).all(axis=1) & np.isfinite(h).all(axis=1)
        valid &= np.isfinite(lo).all(axis=1) & np.isfinite(v).all(axis=1)
        # Domain masking happens before division; NaN slots are never filled.
        with np.errstate(divide="ignore", invalid="ignore"):
            if name.startswith("return_"):
                result = c[:, -1] / c[:, 0] - 1
            elif name == "log_return_1":
                result = np.log(c[:, -1] / c[:, 0])
            elif name.startswith("distance_sma_"):
                result = c[:, -1] / c.mean(axis=1) - 1
            elif name.startswith("sma_"):
                result = c.mean(axis=1)
            elif name.startswith("ema_"):
                result = _ema(c, int(name.split("_")[-1]))[:, -1]
            elif name.startswith("macd"):
                differences = _ema(c, 12)[:, 14:] - _ema(c, 26)
                signal = _ema(differences, 9)[:, -1]
                result = (
                    differences[:, -1]
                    if name == "macd"
                    else (signal if name == "macd_signal" else differences[:, -1] - signal)
                )
            elif name == "rsi_14":
                changes = np.diff(c, axis=1)
                gain = _wilder(np.maximum(changes, 0), 14)
                loss = _wilder(np.maximum(-changes, 0), 14)
                result = np.where(
                    (gain == 0) & (loss == 0),
                    50,
                    np.where(loss == 0, 100, 100 - 100 / (1 + gain / loss)),
                )
            elif name == "atr_14":
                ranges = np.maximum(
                    h[:, 1:] - lo[:, 1:],
                    np.maximum(abs(h[:, 1:] - c[:, :-1]), abs(lo[:, 1:] - c[:, :-1])),
                )
                result = _wilder(ranges, 14)
            elif name.startswith("volatility_"):
                result = (c[:, 1:] / c[:, :-1] - 1).std(axis=1, ddof=1)
            elif name == "volume_sma_20":
                result = v.mean(axis=1)
            elif name == "volume_ratio_20":
                result = v[:, -1] / v.mean(axis=1)
            elif name == "volume_zscore_20":
                result = (v[:, -1] - v.mean(axis=1)) / v.std(axis=1, ddof=1)
            elif name == "close_to_high_20":
                result = c[:, -1] / h.max(axis=1) - 1
            elif name == "range_location_20":
                result = (c[:, -1] - lo.min(axis=1)) / (h.max(axis=1) - lo.min(axis=1))
            elif name == "drawdown_20":
                result = c[:, -1] / c.max(axis=1) - 1
            elif name == "bollinger_location_20":
                spread = c.std(axis=1, ddof=1)
                result = (c[:, -1] - (c.mean(axis=1) - 2 * spread)) / (4 * spread)
            elif name == "bollinger_width_20":
                result = 4 * c.std(axis=1, ddof=1) / c.mean(axis=1)
            else:
                raise ValueError("UNSUPPORTED_P6_RESEARCH_NUMERICAL_FEATURE")
        output[n - 1 :] = np.where(valid & np.isfinite(result), result, np.nan)
        limit = n - 1
    # The original registry permits shorter early-global-history EMA/Wilder windows.
    for i in range(definition.minimum_history - 1, limit):
        bars = (x[: i + 1].tolist() for x in (close, high, low, volume))
        if np.isfinite(close[: i + 1]).all() and np.isfinite(volume[: i + 1]).all():
            result = calculate(name, *bars)
            if result is not None and np.isfinite(result):
                output[i] = result
    return output


def _ema(values: np.ndarray[Any, Any], span: int) -> np.ndarray[Any, Any]:
    result = [values[:, :span].mean(axis=1)]
    alpha = 2 / (span + 1)
    for i in range(span, values.shape[1]):
        result.append(alpha * values[:, i] + (1 - alpha) * result[-1])
    return np.column_stack(result)


def _wilder(values: np.ndarray[Any, Any], span: int) -> np.ndarray[Any, Any]:
    result = values[:, :span].mean(axis=1)
    for i in range(span, values.shape[1]):
        result = ((span - 1) * result + values[:, i]) / span
    return result


def window_flag(flags: np.ndarray[Any, Any], lookback: int) -> np.ndarray[Any, Any]:
    """Any flagged slot in the trailing registry window, including early prefixes."""
    total = np.concatenate(([0], np.cumsum(flags.astype("int64"))))
    index = np.arange(len(flags))
    return total[index + 1] - total[np.maximum(0, index + 1 - lookback)] > 0
