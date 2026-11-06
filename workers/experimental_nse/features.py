"""Scale-invariant, final-vintage experimental NSE observations, never accepted ML.

Only ratios of the same daily candle are used. Unknown cross-session adjustments,
volume adjustments and corporate-action coverage are not promoted to known facts.
The target compounds five independent daily open-to-close movements; it is neither
a close-to-close investment return nor a claim about an executable strategy.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any

FAMILY = "ALPHALENS_EXPERIMENTAL_NSE_V1"
FEATURE_VERSION = "nse.same-session-ratios.11.v1"
TARGET_VERSION = "next5.observed-cohort-sessions.compound-open-close.v1"
HORIZON = 5
LOOKBACK = 20
FEATURE_NAMES = (
    "open_close_return",
    "intraday_range_over_open",
    "open_close_mean_5",
    "open_close_sd_5",
    "open_close_positive_fraction_5",
    "open_close_mean_10",
    "open_close_sd_10",
    "open_close_positive_fraction_10",
    "open_close_mean_20",
    "open_close_sd_20",
    "open_close_positive_fraction_20",
)


@dataclass(frozen=True)
class Candle:
    key: str
    symbol: str
    session: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    @property
    def movement(self) -> float:
        return float(self.close / self.open - 1)


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


def _number(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("INVALID_CANDLE_NUMBER")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("INVALID_CANDLE_NUMBER") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError("POSITIVE_FINITE_CANDLE_REQUIRED")
    return result


def candle(row: Mapping[str, Any]) -> Candle:
    """Validate normalized exact identity, OHLCV and an actual ISO observation date."""
    key, symbol, session = row.get("key"), row.get("symbol"), row.get("session")
    if not isinstance(key, str) or not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", key):
        raise ValueError("EXACT_NSE_KEY_REQUIRED")
    if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9&_.-]{1,40}", symbol):
        raise ValueError("EXACT_NSE_SYMBOL_REQUIRED")
    if not isinstance(session, str) or date.fromisoformat(session).isoformat() != session:
        raise ValueError("ISO_SESSION_REQUIRED")
    values = [_number(row.get(name)) for name in ("open", "high", "low", "close")]
    opening, high, low, close = values
    volume = row.get("volume")
    if isinstance(volume, bool) or not isinstance(volume, int) or volume < 0:
        raise ValueError("NONNEGATIVE_INTEGER_VOLUME_REQUIRED")
    if high < max(opening, close) or low > min(opening, close) or high < low:
        raise ValueError("CONTRADICTORY_OHLC")
    return Candle(key, symbol, session, opening, high, low, close, volume)


def _complete(window: Sequence[str], observations: Mapping[str, Candle]) -> bool:
    return all(session in observations for session in window) and all(
        (date.fromisoformat(right) - date.fromisoformat(left)).days <= 7
        for left, right in zip(window, window[1:], strict=False)
    )


def _drawdown(movements: Sequence[float]) -> float:
    equity, peak, worst = 1.0, 1.0, 0.0
    for movement in movements:
        equity *= 1 + movement
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    return worst


def build(rows: Sequence[Mapping[str, Any]], sessions: Sequence[str]) -> FeatureDataset:
    """Require every lookback/target slot; never fill a missing provider observation.

    The reference is an explicitly supplied union of observed cohort dates, not an
    official complete historical NSE calendar. Gaps over seven days are excluded.
    """
    reference = tuple(sessions)
    if not reference or tuple(sorted(set(reference))) != reference:
        raise ValueError("SORTED_UNIQUE_REFERENCE_SESSIONS_REQUIRED")
    for session in reference:
        if date.fromisoformat(session).isoformat() != session:
            raise ValueError("ISO_REFERENCE_SESSION_REQUIRED")
    reference_set = set(reference)
    grouped: dict[str, dict[str, Candle]] = {}
    symbols: dict[str, str] = {}
    for row in rows:
        observation = candle(row)
        if observation.session not in reference_set:
            raise ValueError("OBSERVATION_OUTSIDE_REFERENCE")
        if observation.key in symbols and symbols[observation.key] != observation.symbol:
            raise ValueError("IDENTITY_SYMBOL_CHANGED_WITHIN_SNAPSHOT")
        symbols[observation.key] = observation.symbol
        instrument = grouped.setdefault(observation.key, {})
        if observation.session in instrument:
            raise ValueError("DUPLICATE_SECURITY_SESSION")
        instrument[observation.session] = observation
    samples: list[Sample] = []
    excluded: list[dict[str, str]] = []
    for key in sorted(grouped):
        observations = grouped[key]
        for index, session in enumerate(reference):
            window = reference[max(0, index - LOOKBACK + 1) : index + 1]
            reason = None
            if session not in observations:
                reason = "MISSING_OBSERVED_SESSION"
            elif len(window) < LOOKBACK:
                reason = "INSUFFICIENT_20_SESSION_LOOKBACK"
            elif not _complete(window, observations):
                reason = "MISSING_LOOKBACK_SLOT_OR_GAP_OVER_7_DAYS"
            if reason:
                excluded.append({"key": key, "session": session, "reason": reason})
                continue
            current = observations[session]
            movements = [observations[day].movement for day in window]
            values = [current.movement, float((current.high - current.low) / current.open)]
            for length in (5, 10, 20):
                recent = movements[-length:]
                mean = math.fsum(recent) / length
                values.extend(
                    (
                        mean,
                        math.sqrt(math.fsum((value - mean) ** 2 for value in recent) / length),
                        sum(value > 0 for value in recent) / length,
                    )
                )
            if len(values) != len(FEATURE_NAMES) or not all(map(math.isfinite, values)):
                raise ValueError("NONFINITE_FEATURE_VECTOR")
            target_window = reference[index + 1 : index + 1 + HORIZON]
            target_session, target_return, target = None, None, None
            target_path: tuple[float, ...] = ()
            if len(target_window) == HORIZON and _complete((session, *target_window), observations):
                target_path = tuple(observations[day].movement for day in target_window)
                exact_target = (
                    math.prod(
                        Fraction(observations[day].close) / Fraction(observations[day].open)
                        for day in target_window
                    )
                    - 1
                )
                target_return = float(exact_target)
                if not math.isfinite(target_return):
                    raise ValueError("NONFINITE_EXPERIMENTAL_TARGET")
                target = int(exact_target > 0)
                target_session = target_window[-1]
            else:
                excluded.append(
                    {"key": key, "session": session, "reason": "TARGET_UNMATURED_OR_MISSING_SLOT"}
                )
            samples.append(
                Sample(
                    key,
                    current.symbol,
                    session,
                    tuple(values),
                    str(current.close),
                    target_session,
                    target_return,
                    target,
                    target_path,
                    {
                        "open_close_daily_sd_20": values[9],
                        "open_close_compounded_drawdown_20": _drawdown(movements),
                        "basis": "INDEPENDENT_DAILY_OPEN_CLOSE_MOVEMENTS_NOT_HOLDING_RETURN",
                        "adjustment_basis": "UNKNOWN_SAME_SESSION_RATIOS_ONLY",
                        "volume": current.volume,
                    },
                )
            )
    return FeatureDataset(tuple(samples), reference, tuple(excluded), len(rows), len(grouped))
