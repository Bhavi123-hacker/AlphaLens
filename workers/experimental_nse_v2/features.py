"""V2 split/bonus-adjusted price features, fixed current-cohort final-vintage research.

Provider staff confirms adjusted OHLC, excluding dividends. This is price return,
not total shareholder return, historical PIT membership or verified execution.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from workers.experimental_nse.features import Candle, candle

FAMILY = "ALPHALENS_EXPERIMENTAL_NSE_V2"
FEATURE_VERSION = "nse.adjusted-price-context.20.v2"
TARGET_VERSION = "prior-eod.next-open-to-fifth-close.price-return.v2"
HORIZON = 5
LOOKBACK = 61
FEATURE_NAMES = (
    "price_return_1",
    "price_return_5",
    "price_return_20",
    "price_return_60",
    "return_sd_20",
    "return_sd_60",
    "ma_distance_20",
    "ma_distance_60",
    "rsi_14",
    "macd_12_26_over_close",
    "drawdown_60",
    "atr_14_over_close",
    "range_over_open",
    "open_close_return",
    "oc_mean_20",
    "oc_positive_fraction_20",
    "cohort_mean_return_5",
    "cohort_mean_return_20",
    "stock_minus_cohort_return_5",
    "stock_minus_cohort_return_20",
)
LOCAL_FEATURE_VERSION = "nse.adjusted-price-only.16.v2"
LOCAL_FEATURE_NAMES = FEATURE_NAMES[:16]
FEATURE_CONTRACTS = {
    FEATURE_VERSION: FEATURE_NAMES,
    LOCAL_FEATURE_VERSION: LOCAL_FEATURE_NAMES,
}


@dataclass(frozen=True)
class Sample:
    key: str
    symbol: str
    session: str
    vector: tuple[float, ...]
    price: str
    target_session: str | None
    target_return: float | None
    target: int | None
    target_path: tuple[float, ...]
    risk: dict[str, Any]


@dataclass(frozen=True)
class FeatureDataset:
    samples: tuple[Sample, ...]
    sessions: tuple[str, ...]
    exclusions: tuple[dict[str, str], ...]
    observation_count: int
    security_count: int


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _sd(values: Sequence[float]) -> float:
    mean = _mean(values)
    return math.sqrt(_mean([(value - mean) ** 2 for value in values]))


def _ema(values: Sequence[float], period: int) -> float:
    result = values[0]
    weight = 2 / (period + 1)
    for value in values[1:]:
        result = weight * value + (1 - weight) * result
    return result


def build(
    rows: Sequence[Mapping[str, Any]],
    sessions: Sequence[str],
    excluded_sessions: Mapping[str, Iterable[str]] | None = None,
    horizon: int = HORIZON,
    include_context: bool = True,
) -> FeatureDataset:
    """Never fill missing slots; known action hazards exclude lookbacks and targets.

    Same-date context requires >=80% of this fixed snapshot cohort with complete
    lookbacks. Its membership is explicitly not historical NSE/index membership.
    """
    if horizon not in (5, 10, 20):
        raise ValueError("PREDECLARED_HORIZON_REQUIRED")
    reference = tuple(sessions)
    if not reference or reference != tuple(sorted(set(reference))):
        raise ValueError("SORTED_UNIQUE_OBSERVED_SESSIONS_REQUIRED")
    for day in reference:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("ISO_OBSERVED_SESSION_REQUIRED")
    hazards = {key: set(values) for key, values in (excluded_sessions or {}).items()}
    reference_set = set(reference)
    grouped: dict[str, dict[str, Candle]] = {}
    symbols: dict[str, str] = {}
    for row in rows:
        item = candle(row)
        if item.session not in reference_set:
            raise ValueError("OBSERVATION_OUTSIDE_REFERENCE")
        if item.key in symbols and symbols[item.key] != item.symbol:
            raise ValueError("IDENTITY_SYMBOL_CHANGED_WITHIN_SNAPSHOT")
        symbols[item.key] = item.symbol
        instrument = grouped.setdefault(item.key, {})
        if item.session in instrument:
            raise ValueError("DUPLICATE_SECURITY_SESSION")
        instrument[item.session] = item
    if not grouped:
        raise ValueError("NONEMPTY_FIXED_COHORT_REQUIRED")
    prepared: dict[tuple[str, str], tuple[list[float], dict[str, Any]]] = {}
    exclusions: list[dict[str, str]] = []
    for key, observations in sorted(grouped.items()):
        for index, day in enumerate(reference):
            window = reference[max(0, index - LOOKBACK + 1) : index + 1]
            reason = None
            if day not in observations:
                reason = "MISSING_OBSERVED_SESSION"
            elif len(window) != LOOKBACK:
                reason = "INSUFFICIENT_61_OBSERVED_SESSION_LOOKBACK"
            elif any(slot not in observations for slot in window):
                reason = "MISSING_LOOKBACK_SLOT"
            elif set(window) & hazards.get(key, set()):
                reason = "KNOWN_CORPORATE_ACTION_LOOKBACK_EXCLUSION"
            elif any(
                (date.fromisoformat(right) - date.fromisoformat(left)).days > 7
                for left, right in zip(window, window[1:], strict=False)
            ):
                reason = "OBSERVED_CALENDAR_GAP_OVER_7_DAYS"
            if reason:
                exclusions.append({"key": key, "session": day, "reason": reason})
                continue
            items = [observations[slot] for slot in window]
            closes = [float(item.close) for item in items]
            returns = [right / left - 1 for left, right in zip(closes, closes[1:], strict=False)]
            current = items[-1]
            changes = [
                right - left for left, right in zip(closes[-15:-1], closes[-14:], strict=True)
            ]
            gain = _mean([max(value, 0) for value in changes])
            loss = _mean([max(-value, 0) for value in changes])
            rsi = 100 * gain / (gain + loss) if gain + loss else 50.0
            true_ranges = [
                max(
                    float(item.high - item.low),
                    abs(float(item.high) - previous),
                    abs(float(item.low) - previous),
                )
                for item, previous in zip(items[-14:], closes[-15:-1], strict=True)
            ]
            oc = [item.movement for item in items[-20:]]
            values = [closes[-1] / closes[-1 - length] - 1 for length in (1, 5, 20, 60)]
            values.extend(
                (
                    _sd(returns[-20:]),
                    _sd(returns),
                    closes[-1] / _mean(closes[-20:]) - 1,
                    closes[-1] / _mean(closes[-60:]) - 1,
                    rsi,
                    (_ema(closes, 12) - _ema(closes, 26)) / closes[-1],
                    closes[-1] / max(closes[-60:]) - 1,
                    _mean(true_ranges) / closes[-1],
                    float((current.high - current.low) / current.open),
                    current.movement,
                    _mean(oc),
                    _mean([float(value > 0) for value in oc]),
                )
            )
            equity, peak, max_drawdown = 1.0, 1.0, 0.0
            for movement in returns:
                equity *= 1 + movement
                peak = max(peak, equity)
                max_drawdown = min(max_drawdown, equity / peak - 1)
            prepared[key, day] = (
                values,
                {
                    "return_daily_sd_20": values[4],
                    "open_close_daily_sd_20": _sd(oc),
                    "annualized_volatility_252_assumption": values[4] * math.sqrt(252),
                    "historical_price_drawdown_60": max_drawdown,
                    "volume": current.volume,
                    "basis": "SPLIT_BONUS_ADJUSTED_PRICE_NOT_DIVIDEND_TOTAL_RETURN",
                    "adjustment_basis": "UPSTOX_STAFF_CONFIRMED_SPLIT_BONUS_ADJUSTED_OHLC",
                },
            )
    context: dict[str, tuple[float, float, int]] = {}
    for day in reference:
        members = [prepared[key, day][0] for key in grouped if (key, day) in prepared]
        if len(members) >= math.ceil(len(grouped) * 0.8):
            context[day] = (
                _mean([values[1] for values in members]),
                _mean([values[2] for values in members]),
                len(members),
            )
    samples: list[Sample] = []
    for (key, day), (values, risk) in sorted(prepared.items()):
        if include_context and day not in context:
            exclusions.append(
                {
                    "key": key,
                    "session": day,
                    "reason": "INSUFFICIENT_80_PERCENT_FIXED_COHORT_CONTEXT",
                }
            )
            continue
        vector: tuple[float, ...] = tuple(values)
        context_count: int | None = None
        if include_context:
            mean5, mean20, context_count = context[day]
            vector = (*values, mean5, mean20, values[1] - mean5, values[2] - mean20)
        names = FEATURE_NAMES if include_context else LOCAL_FEATURE_NAMES
        if len(vector) != len(names) or not all(map(math.isfinite, vector)):
            raise ValueError("EXACT_FINITE_V2_FEATURE_CONTRACT_REQUIRED")
        index = reference.index(day)
        future = reference[index + 1 : index + 1 + horizon]
        observations = grouped[key]
        target_day, target_return, target = None, None, None
        reason = None
        if len(future) != horizon:
            reason = "TARGET_UNMATURED"
        elif any(slot not in observations for slot in future):
            reason = "MISSING_TARGET_SLOT"
        elif set(future) & hazards.get(key, set()):
            reason = "KNOWN_CORPORATE_ACTION_TARGET_EXCLUSION"
        elif any(
            (date.fromisoformat(right) - date.fromisoformat(left)).days > 7
            for left, right in zip((day, *future), future, strict=False)
        ):
            reason = "TARGET_CALENDAR_GAP_OVER_7_DAYS"
        else:
            target_day = future[-1]
            target_return = float(observations[future[-1]].close / observations[future[0]].open - 1)
            target = int(target_return > 0)
        if reason:
            exclusions.append({"key": key, "session": day, "reason": reason})
        risk = {
            **risk,
            "fixed_cohort_context_members": context_count,
            "feature_context": "FIXED_COHORT" if include_context else "SINGLE_SECURITY",
            "horizon_observed_sessions": horizon,
            "entry_reference": "NEXT_OBSERVED_SESSION_OPEN_AFTER_DECISION",
        }
        samples.append(
            Sample(
                key,
                symbols[key],
                day,
                tuple(vector),
                str(observations[day].close),
                target_day,
                target_return,
                target,
                (target_return,) if target_return is not None else (),
                risk,
            )
        )
    return FeatureDataset(tuple(samples), reference, tuple(exclusions), len(rows), len(grouped))
