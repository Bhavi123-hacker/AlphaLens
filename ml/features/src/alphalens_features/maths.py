"""Bounded trailing numerical operations; float64 derived values, no fitted transforms."""

import math
from statistics import mean, stdev


def ema(values: list[float], span: int) -> list[float]:
    if len(values) < span:
        return []
    result = [mean(values[:span])]
    alpha = 2 / (span + 1)
    for value in values[span:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def wilder(values: list[float], span: int) -> float:
    result = mean(values[:span])
    for value in values[span:]:
        result = ((span - 1) * result + value) / span
    return result


def calculate(
    name: str, close: list[float], high: list[float], low: list[float], volume: list[float]
) -> float | None:
    if name.startswith("return_"):
        return close[-1] / close[0] - 1
    if name == "log_return_1":
        return math.log(close[-1] / close[0])
    if name.startswith("distance_sma_"):
        return close[-1] / mean(close) - 1
    if name.startswith("sma_"):
        return mean(close)
    if name.startswith("ema_"):
        return ema(close, int(name.split("_")[-1]))[-1]
    if name.startswith("macd"):
        fast = ema(close, 12)[14:]
        slow = ema(close, 26)
        differences = [a - b for a, b in zip(fast, slow, strict=True)]
        signal = ema(differences, 9)[-1]
        return (
            differences[-1]
            if name == "macd"
            else signal
            if name == "macd_signal"
            else differences[-1] - signal
        )
    if name == "rsi_14":
        changes = [b - a for a, b in zip(close, close[1:], strict=False)]
        gain = wilder([max(c, 0) for c in changes], 14)
        loss = wilder([max(-c, 0) for c in changes], 14)
        return 50.0 if gain == loss == 0 else 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    if name == "atr_14":
        ranges = [
            max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
            for i in range(1, len(close))
        ]
        return wilder(ranges, 14)
    if name.startswith("volatility_"):
        return stdev([b / a - 1 for a, b in zip(close, close[1:], strict=False)])
    if name == "volume_sma_20":
        return mean(volume)
    if name == "volume_ratio_20":
        return volume[-1] / mean(volume) if mean(volume) else None
    if name == "volume_zscore_20":
        spread = stdev(volume)
        return (volume[-1] - mean(volume)) / spread if spread else None
    if name == "close_to_high_20":
        return close[-1] / max(high) - 1
    if name == "range_location_20":
        spread = max(high) - min(low)
        return (close[-1] - min(low)) / spread if spread else None
    if name == "drawdown_20":
        return close[-1] / max(close) - 1
    if name == "bollinger_location_20":
        spread = stdev(close)
        return (close[-1] - (mean(close) - 2 * spread)) / (4 * spread) if spread else None
    if name == "bollinger_width_20":
        return 4 * stdev(close) / mean(close)
    raise ValueError("Unsupported versioned feature definition")
