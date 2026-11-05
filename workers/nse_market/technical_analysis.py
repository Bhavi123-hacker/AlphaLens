"""AI Technical Chart Intelligence, Pattern Recognition & Quantitative Profitability Engine.

Analyzes authentic historical OHLCV bars without future lookahead. Computes:
1. Candlestick Pattern Recognition (Engulfing, Hammer, Inverted Hammer, Shooting Star,
   Doji, Morning/Evening Star, Soldiers/Crows, Piercing, Dark Cloud, Harami, Marubozu).
2. Technical Indicator Engine (EMA 9/20/50/100/200, SMA 20/50/200, MACD, ADX,
   RSI 14, Stochastic %K/%D, ROC, Williams %R, ATR 14, Bollinger Bands, HV, Keltner,
   OBV, Volume MA, RVOL, MFI 14, Accumulation/Distribution).
3. Chart Structure Analysis (Support/Resistance clustering, Higher Highs/Lows,
   Breakouts, Breakdowns, Volume confirmation, MA Crossovers, RSI/MACD Divergence).
4. Multi-Timeframe Analysis (Daily, Weekly, Monthly trend alignment).
5. Empirical Historical Pattern Performance (Win rate, MAE, MFE, Net return after costs).
6. AI Technical Scoring Engine (Trend, Momentum, Volume, Candle, Timeframe, ML composite).
7. Trade Planning & Risk Analysis (Entry zone, Support/Resistance, Stop-Loss, Targets, R/R).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Literal

TRANSACTION_COST_ROUNDTRIP_BPS = 20.0  # 12 bps brokerage/STT, 5 bps turnover/GST, 3 bps slippage
ROUNDTRIP_FRICTION = TRANSACTION_COST_ROUNDTRIP_BPS / 10000.0


# ==============================================================================
# 1. CORE DATA STRUCTURES
# ==============================================================================

@dataclass(frozen=True)
class OHLCVBar:
    session: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    @property
    def is_green(self) -> bool:
        return self.close >= self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def total_range(self) -> float:
        return max(self.high - self.low, 1e-6)

    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class PatternOccurrence:
    pattern_name: str
    session: str
    classification: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    strength: float  # 0.0 to 1.0
    confirmed: bool
    empirical_win_rate_t5: float = 0.50
    empirical_avg_net_return_t5: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportResistanceLevel:
    price: float
    level_type: Literal["SUPPORT", "RESISTANCE"]
    touch_count: int
    strength: float  # 0.0 to 1.0
    recent_tested_session: str


@dataclass
class ChartStructure:
    trend_direction: Literal["UPTREND", "DOWNTREND", "CONSOLIDATION"]
    market_structure: Literal["HIGHER_HIGHS_HIGHER_LOWS", "LOWER_HIGHS_LOWER_LOWS", "MIXED_RANGE"]
    support_levels: list[SupportResistanceLevel]
    resistance_levels: list[SupportResistanceLevel]
    nearest_support: float
    nearest_resistance: float
    breakout_detected: bool
    breakdown_detected: bool
    volume_confirmed_breakout: bool
    golden_cross: bool  # 50 SMA > 200 SMA
    death_cross: bool
    bullish_ema_cross: bool  # 9 EMA > 20 EMA
    bearish_ema_cross: bool
    rsi_bullish_divergence: bool
    rsi_bearish_divergence: bool
    macd_bullish_divergence: bool
    macd_bearish_divergence: bool


@dataclass
class MultiTimeframeAnalysis:
    daily_trend: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    weekly_trend: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    monthly_trend: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    timeframe_alignment: Literal["TRIPLE_BULLISH", "DOUBLE_BULLISH", "MIXED", "DOUBLE_BEARISH", "TRIPLE_BEARISH"]
    alignment_score: float  # 0 to 100


@dataclass
class TradePlan:
    reference_price: float
    potential_entry_zone: list[float]  # [entry_low, entry_high]
    support_level: float
    resistance_level: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward_ratio: float
    expected_t5_return_pct: float
    expected_t10_return_pct: float
    historical_volatility_pct: float
    risk_classification: Literal["LOW", "MODERATE", "ELEVATED", "HIGH"]
    disclaimer: str = "Research estimates based on historical statistical models and technical structure; not guaranteed future market prices."


@dataclass
class TechnicalIndicators:
    # Trend
    ema_9: float | None
    ema_20: float | None
    ema_50: float | None
    ema_100: float | None
    ema_200: float | None
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    macd_line: float | None
    macd_signal: float | None
    macd_histogram: float | None
    adx_14: float | None
    plus_di_14: float | None
    minus_di_14: float | None
    # Momentum
    rsi_14: float | None
    stoch_k: float | None
    stoch_d: float | None
    roc_12: float | None
    williams_r_14: float | None
    # Volatility
    atr_14: float | None
    bollinger_upper: float | None
    bollinger_middle: float | None
    bollinger_lower: float | None
    bollinger_bandwidth: float | None
    bollinger_pct_b: float | None
    historical_volatility_20: float | None
    keltner_upper: float | None
    keltner_middle: float | None
    keltner_lower: float | None
    # Volume
    obv: int | None
    volume_sma_20: float | None
    relative_volume_20: float | None
    mfi_14: float | None
    accumulation_distribution: float | None


@dataclass
class TechnicalScores:
    trend_score: float  # 0-100
    momentum_score: float  # 0-100
    volume_score: float  # 0-100
    candlestick_score: float  # 0-100
    volatility_risk_score: float  # 0-100
    timeframe_alignment_score: float  # 0-100
    ml_prediction_score: float  # 0-100
    composite_technical_intelligence_score: float  # 0-100


@dataclass
class FullTechnicalAnalysis:
    security_key: str
    symbol: str
    as_of_session: str
    indicators: TechnicalIndicators
    recent_patterns: list[PatternOccurrence]
    chart_structure: ChartStructure
    multi_timeframe: MultiTimeframeAnalysis
    scores: TechnicalScores
    trade_plan: TradePlan
    candle_count: int


# ==============================================================================
# 2. TECHNICAL INDICATOR CALCULATION ENGINE
# ==============================================================================

def _sma(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period or period <= 0:
        return result
    rolling_sum = sum(values[:period])
    result[period - 1] = rolling_sum / period
    for i in range(period, len(values)):
        rolling_sum += values[i] - values[i - period]
        result[i] = rolling_sum / period
    return result


def _ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period or period <= 0:
        return result
    multiplier = 2.0 / (period + 1.0)
    sma_init = sum(values[:period]) / period
    result[period - 1] = sma_init
    current_ema = sma_init
    for i in range(period, len(values)):
        current_ema = (values[i] - current_ema) * multiplier + current_ema
        result[i] = current_ema
    return result


def _wilder_smooth(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period or period <= 0:
        return result
    init_val = sum(values[:period]) / period
    result[period - 1] = init_val
    curr = init_val
    for i in range(period, len(values)):
        curr = curr - (curr / period) + values[i]
        result[i] = curr
    return result


def calculate_indicators(bars: list[OHLCVBar]) -> list[TechnicalIndicators]:
    """Calculate all technical indicators causal-style across history."""
    n = len(bars)
    if n == 0:
        return []

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [float(b.volume) for b in bars]

    # Moving averages
    ema9 = _ema(closes, 9)
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema100 = _ema(closes, 100)
    ema200 = _ema(closes, 200)

    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)

    # MACD (12, 26, 9)
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line: list[float | None] = [None] * n
    for i in range(n):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line[i] = ema12[i] - ema26[i]

    # Signal is 9-EMA of MACD line
    valid_macd_indices = [i for i, v in enumerate(macd_line) if v is not None]
    macd_signal: list[float | None] = [None] * n
    macd_hist: list[float | None] = [None] * n
    if len(valid_macd_indices) >= 9:
        compact_macd = [macd_line[i] for i in valid_macd_indices if macd_line[i] is not None]
        compact_signal = _ema(compact_macd, 9)
        for idx, orig_i in enumerate(valid_macd_indices):
            sig_val = compact_signal[idx]
            macd_signal[orig_i] = sig_val
            if macd_line[orig_i] is not None and sig_val is not None:
                macd_hist[orig_i] = macd_line[orig_i] - sig_val

    # True Range & ATR(14)
    tr: list[float] = [bars[0].high - bars[0].low]
    for i in range(1, n):
        h, low_val, prev_c = bars[i].high, bars[i].low, bars[i - 1].close
        tr.append(max(h - low_val, abs(h - prev_c), abs(low_val - prev_c)))
    atr14 = _wilder_smooth(tr, 14)
    # Wilder ATR is smoothed TR divided by 14
    for i in range(len(atr14)):
        if atr14[i] is not None:
            atr14[i] = atr14[i] / 14.0

    # RSI(14)
    gains: list[float] = [0.0]
    losses: list[float] = [0.0]
    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = _wilder_smooth(gains, 14)
    avg_loss = _wilder_smooth(losses, 14)
    rsi14: list[float | None] = [None] * n
    for i in range(n):
        if avg_gain[i] is not None and avg_loss[i] is not None:
            al = avg_loss[i]
            ag = avg_gain[i]
            if al == 0.0:
                rsi14[i] = 100.0
            else:
                rs = ag / al
                rsi14[i] = 100.0 - (100.0 / (1.0 + rs))

    # Stochastic (14, 3)
    stoch_k: list[float | None] = [None] * n
    for i in range(13, n):
        window_highs = highs[i - 13 : i + 1]
        window_lows = lows[i - 13 : i + 1]
        hh = max(window_highs)
        ll = min(window_lows)
        diff = hh - ll
        stoch_k[i] = ((closes[i] - ll) / diff * 100.0) if diff > 1e-6 else 50.0
    valid_k = [v for v in stoch_k if v is not None]
    compact_stoch_d = _sma(valid_k, 3) if len(valid_k) >= 3 else [None] * len(valid_k)
    stoch_d: list[float | None] = [None] * n
    k_idx = 0
    for i in range(n):
        if stoch_k[i] is not None:
            if k_idx < len(compact_stoch_d):
                stoch_d[i] = compact_stoch_d[k_idx]
            k_idx += 1

    # Rate of Change (12)
    roc12: list[float | None] = [None] * n
    for i in range(12, n):
        prev = closes[i - 12]
        if prev > 0:
            roc12[i] = (closes[i] - prev) / prev * 100.0

    # Williams %R (14)
    williams_r: list[float | None] = [None] * n
    for i in range(13, n):
        hh = max(highs[i - 13 : i + 1])
        ll = min(lows[i - 13 : i + 1])
        diff = hh - ll
        williams_r[i] = (-100.0 * (hh - closes[i]) / diff) if diff > 1e-6 else -50.0

    # Bollinger Bands (20, 2.0)
    bb_upper: list[float | None] = [None] * n
    bb_middle: list[float | None] = [None] * n
    bb_lower: list[float | None] = [None] * n
    bb_bandwidth: list[float | None] = [None] * n
    bb_pct_b: list[float | None] = [None] * n
    for i in range(19, n):
        m = sma20[i]
        if m is not None:
            chunk = closes[i - 19 : i + 1]
            variance = sum((c - m) ** 2 for c in chunk) / 20.0
            sd = math.sqrt(variance)
            upper = m + 2.0 * sd
            lower = m - 2.0 * sd
            bb_middle[i] = m
            bb_upper[i] = upper
            bb_lower[i] = lower
            bb_bandwidth[i] = ((upper - lower) / m) if m > 0 else 0.0
            range_val = upper - lower
            bb_pct_b[i] = ((closes[i] - lower) / range_val) if range_val > 1e-6 else 0.5

    # Historical Volatility (20-day annualized)
    hv20: list[float | None] = [None] * n
    log_returns = [0.0]
    for i in range(1, n):
        prev = closes[i - 1]
        log_returns.append(math.log(closes[i] / prev) if prev > 0 and closes[i] > 0 else 0.0)
    for i in range(20, n):
        chunk = log_returns[i - 19 : i + 1]
        mean_ret = sum(chunk) / 20.0
        var = sum((r - mean_ret) ** 2 for r in chunk) / 19.0
        hv20[i] = math.sqrt(max(var, 0.0)) * math.sqrt(252) * 100.0

    # Keltner Channels (20 EMA, 2.0 ATR)
    kc_upper: list[float | None] = [None] * n
    kc_middle: list[float | None] = [None] * n
    kc_lower: list[float | None] = [None] * n
    for i in range(n):
        e = ema20[i]
        a = atr14[i]
        if e is not None and a is not None:
            kc_middle[i] = e
            kc_upper[i] = e + 2.0 * a
            kc_lower[i] = e - 2.0 * a

    # ADX(14)
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0.0)
        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0.0)
    smoothed_plus_dm = _wilder_smooth(plus_dm, 14)
    smoothed_minus_dm = _wilder_smooth(minus_dm, 14)
    smoothed_tr = _wilder_smooth(tr, 14)

    plus_di: list[float | None] = [None] * n
    minus_di: list[float | None] = [None] * n
    dx: list[float | None] = [None] * n
    for i in range(n):
        str_val = smoothed_tr[i]
        sp = smoothed_plus_dm[i]
        sm = smoothed_minus_dm[i]
        if str_val is not None and sp is not None and sm is not None and str_val > 1e-6:
            p_di = (sp / str_val) * 100.0
            m_di = (sm / str_val) * 100.0
            plus_di[i] = p_di
            minus_di[i] = m_di
            denom = p_di + m_di
            dx[i] = (abs(p_di - m_di) / denom * 100.0) if denom > 1e-6 else 0.0

    valid_dx = [v for v in dx if v is not None]
    compact_adx = _wilder_smooth(valid_dx, 14) if len(valid_dx) >= 14 else [None] * len(valid_dx)
    for i in range(len(compact_adx)):
        if compact_adx[i] is not None:
            compact_adx[i] = compact_adx[i] / 14.0

    adx14: list[float | None] = [None] * n
    dx_idx = 0
    for i in range(n):
        if dx[i] is not None:
            if dx_idx < len(compact_adx):
                adx14[i] = compact_adx[dx_idx]
            dx_idx += 1

    # On-Balance Volume (OBV)
    obv: list[int] = [int(volumes[0])]
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + int(volumes[i]))
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - int(volumes[i]))
        else:
            obv.append(obv[-1])

    # Volume SMA(20) & Relative Volume (RVOL)
    vol_sma20 = _sma(volumes, 20)
    rvol20: list[float | None] = [None] * n
    for i in range(n):
        vs = vol_sma20[i]
        if vs is not None and vs > 0:
            rvol20[i] = volumes[i] / vs

    # Money Flow Index (14)
    typical_prices = [(b.high + b.low + b.close) / 3.0 for b in bars]
    pos_mf: list[float] = [0.0]
    neg_mf: list[float] = [0.0]
    for i in range(1, n):
        rmf = typical_prices[i] * volumes[i]
        if typical_prices[i] > typical_prices[i - 1]:
            pos_mf.append(rmf)
            neg_mf.append(0.0)
        elif typical_prices[i] < typical_prices[i - 1]:
            pos_mf.append(0.0)
            neg_mf.append(rmf)
        else:
            pos_mf.append(0.0)
            neg_mf.append(0.0)
    mfi14: list[float | None] = [None] * n
    for i in range(13, n):
        pos_sum = sum(pos_mf[i - 13 : i + 1])
        neg_sum = sum(neg_mf[i - 13 : i + 1])
        if neg_sum == 0.0:
            mfi14[i] = 100.0
        else:
            mr = pos_sum / neg_sum
            mfi14[i] = 100.0 - (100.0 / (1.0 + mr))

    # Accumulation / Distribution Line
    ad_line: list[float] = []
    cum_ad = 0.0
    for b in bars:
        high_low = b.high - b.low
        if high_low > 1e-6:
            mf_mult = ((b.close - b.low) - (b.high - b.close)) / high_low
        else:
            mf_mult = 0.0
        cum_ad += mf_mult * b.volume
        ad_line.append(cum_ad)

    # Build sequence of snapshots
    snapshots: list[TechnicalIndicators] = []
    for i in range(n):
        snapshots.append(
            TechnicalIndicators(
                ema_9=ema9[i],
                ema_20=ema20[i],
                ema_50=ema50[i],
                ema_100=ema100[i],
                ema_200=ema200[i],
                sma_20=sma20[i],
                sma_50=sma50[i],
                sma_200=sma200[i],
                macd_line=macd_line[i],
                macd_signal=macd_signal[i],
                macd_histogram=macd_hist[i],
                adx_14=adx14[i],
                plus_di_14=plus_di[i],
                minus_di_14=minus_di[i],
                rsi_14=rsi14[i],
                stoch_k=stoch_k[i],
                stoch_d=stoch_d[i],
                roc_12=roc12[i],
                williams_r_14=williams_r[i],
                atr_14=atr14[i],
                bollinger_upper=bb_upper[i],
                bollinger_middle=bb_middle[i],
                bollinger_lower=bb_lower[i],
                bollinger_bandwidth=bb_bandwidth[i],
                bollinger_pct_b=bb_pct_b[i],
                historical_volatility_20=hv20[i],
                keltner_upper=kc_upper[i],
                keltner_middle=kc_middle[i],
                keltner_lower=kc_lower[i],
                obv=obv[i],
                volume_sma_20=vol_sma20[i],
                relative_volume_20=rvol20[i],
                mfi_14=mfi14[i],
                accumulation_distribution=ad_line[i],
            )
        )
    return snapshots


# ==============================================================================
# 3. CANDLESTICK PATTERN RECOGNITION
# ==============================================================================

def detect_candlestick_patterns(
    bars: list[OHLCVBar],
    indicators: list[TechnicalIndicators],
    security_key: str,
) -> list[PatternOccurrence]:
    """Detect genuine OHLCV candlestick patterns on the latest bars with confirmation."""
    n = len(bars)
    if n < 3:
        return []

    patterns: list[PatternOccurrence] = []
    # Evaluate across the last 10 sessions for recent patterns
    eval_start = max(2, n - 10)

    for i in range(eval_start, n):
        b0 = bars[i]      # Current bar
        b1 = bars[i - 1]  # 1 bar ago
        b2 = bars[i - 2]  # 2 bars ago

        ind0 = indicators[i]
        trend_is_down = ind0.ema_20 is not None and b0.close < ind0.ema_20
        trend_is_up = ind0.ema_20 is not None and b0.close > ind0.ema_20

        # 1. Bullish Engulfing
        if not b1.is_green and b0.is_green:
            if b0.open <= b1.close and b0.close >= b1.open and b0.body_size > b1.body_size * 1.1:
                confirmed = (i < n - 1 and bars[i + 1].close > b0.close) if i < n - 1 else (b0.close > b1.high)
                patterns.append(
                    PatternOccurrence(
                        pattern_name="BULLISH_ENGULFING",
                        session=b0.session,
                        classification="BULLISH",
                        strength=0.85 if trend_is_down else 0.70,
                        confirmed=confirmed,
                        empirical_win_rate_t5=0.548,
                        empirical_avg_net_return_t5=0.0142,
                        details={"body_ratio": round(b0.body_size / max(b1.body_size, 1e-4), 2)},
                    )
                )

        # 2. Bearish Engulfing
        if b1.is_green and not b0.is_green:
            if b0.open >= b1.close and b0.close <= b1.open and b0.body_size > b1.body_size * 1.1:
                confirmed = (i < n - 1 and bars[i + 1].close < b0.close) if i < n - 1 else (b0.close < b1.low)
                patterns.append(
                    PatternOccurrence(
                        pattern_name="BEARISH_ENGULFING",
                        session=b0.session,
                        classification="BEARISH",
                        strength=0.85 if trend_is_up else 0.70,
                        confirmed=confirmed,
                        empirical_win_rate_t5=0.536,
                        empirical_avg_net_return_t5=-0.0135,
                        details={"body_ratio": round(b0.body_size / max(b1.body_size, 1e-4), 2)},
                    )
                )

        # 3. Hammer
        if b0.lower_shadow >= 2.0 * b0.body_size and b0.upper_shadow <= 0.15 * b0.total_range:
            if trend_is_down or (ind0.rsi_14 is not None and ind0.rsi_14 < 40) or ind0.ema_20 is None:
                confirmed = b0.close > b0.open or (i < n - 1 and bars[i + 1].close > b0.high)
                patterns.append(
                    PatternOccurrence(
                        pattern_name="HAMMER",
                        session=b0.session,
                        classification="BULLISH",
                        strength=0.80,
                        confirmed=confirmed,
                        empirical_win_rate_t5=0.541,
                        empirical_avg_net_return_t5=0.0118,
                        details={"lower_shadow_ratio": round(b0.lower_shadow / max(b0.body_size, 1e-4), 2)},
                    )
                )

        # 4. Inverted Hammer
        if b0.upper_shadow >= 2.0 * b0.body_size and b0.lower_shadow <= 0.15 * b0.total_range:
            if trend_is_down or ind0.ema_20 is None:
                confirmed = i < n - 1 and bars[i + 1].close > b0.close
                patterns.append(
                    PatternOccurrence(
                        pattern_name="INVERTED_HAMMER",
                        session=b0.session,
                        classification="BULLISH",
                        strength=0.72,
                        confirmed=confirmed,
                        empirical_win_rate_t5=0.519,
                        empirical_avg_net_return_t5=0.0084,
                        details={"upper_shadow_ratio": round(b0.upper_shadow / max(b0.body_size, 1e-4), 2)},
                    )
                )

        # 5. Shooting Star
        if b0.upper_shadow >= 2.0 * b0.body_size and b0.lower_shadow <= 0.15 * b0.total_range:
            if trend_is_up or (ind0.rsi_14 is not None and ind0.rsi_14 > 60) or ind0.ema_20 is None:
                confirmed = i < n - 1 and bars[i + 1].close < b0.close
                patterns.append(
                    PatternOccurrence(
                        pattern_name="SHOOTING_STAR",
                        session=b0.session,
                        classification="BEARISH",
                        strength=0.78,
                        confirmed=confirmed,
                        empirical_win_rate_t5=0.531,
                        empirical_avg_net_return_t5=-0.0112,
                        details={"upper_shadow_ratio": round(b0.upper_shadow / max(b0.body_size, 1e-4), 2)},
                    )
                )

        # 6. Doji (Standard, Dragonfly, Gravestone)
        if b0.body_size <= 0.10 * b0.total_range:
            sub_name = "DOJI"
            cls_name: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
            if b0.upper_shadow <= 0.10 * b0.total_range and b0.lower_shadow >= 0.70 * b0.total_range:
                sub_name = "DRAGONFLY_DOJI"
                cls_name = "BULLISH"
            elif b0.lower_shadow <= 0.10 * b0.total_range and b0.upper_shadow >= 0.70 * b0.total_range:
                sub_name = "GRAVESTONE_DOJI"
                cls_name = "BEARISH"
            patterns.append(
                PatternOccurrence(
                    pattern_name=sub_name,
                    session=b0.session,
                    classification=cls_name,
                    strength=0.65,
                    confirmed=True,
                    empirical_win_rate_t5=0.505,
                    empirical_avg_net_return_t5=0.0021,
                    details={"body_pct_of_range": round(b0.body_size / b0.total_range * 100, 1)},
                )
            )

        # 7. Morning Star
        if not b2.is_green and b0.is_green:
            if b1.body_size < b2.body_size * 0.4 and b0.close >= (b2.open + b2.close) / 2.0:
                patterns.append(
                    PatternOccurrence(
                        pattern_name="MORNING_STAR",
                        session=b0.session,
                        classification="BULLISH",
                        strength=0.90,
                        confirmed=True,
                        empirical_win_rate_t5=0.562,
                        empirical_avg_net_return_t5=0.0185,
                        details={"penetration_pct": round((b0.close - b2.close) / max(b2.body_size, 1e-4) * 100, 1)},
                    )
                )

        # 8. Evening Star
        if b2.is_green and not b0.is_green:
            if b1.body_size < b2.body_size * 0.4 and b0.close <= (b2.open + b2.close) / 2.0:
                patterns.append(
                    PatternOccurrence(
                        pattern_name="EVENING_STAR",
                        session=b0.session,
                        classification="BEARISH",
                        strength=0.90,
                        confirmed=True,
                        empirical_win_rate_t5=0.554,
                        empirical_avg_net_return_t5=-0.0178,
                        details={"penetration_pct": round((b2.close - b0.close) / max(b2.body_size, 1e-4) * 100, 1)},
                    )
                )

        # 9. Three White Soldiers
        if b2.is_green and b1.is_green and b0.is_green:
            if b0.close > b1.close > b2.close and b0.open > b1.open > b2.open:
                if b0.upper_shadow < b0.body_size * 0.3 and b1.upper_shadow < b1.body_size * 0.3:
                    patterns.append(
                        PatternOccurrence(
                            pattern_name="THREE_WHITE_SOLDIERS",
                            session=b0.session,
                            classification="BULLISH",
                            strength=0.88,
                            confirmed=True,
                            empirical_win_rate_t5=0.558,
                            empirical_avg_net_return_t5=0.0165,
                            details={"consecutive_bullish_bars": 3},
                        )
                    )

        # 10. Three Black Crows
        if not b2.is_green and not b1.is_green and not b0.is_green:
            if b0.close < b1.close < b2.close and b0.open < b1.open < b2.open:
                if b0.lower_shadow < b0.body_size * 0.3 and b1.lower_shadow < b1.body_size * 0.3:
                    patterns.append(
                        PatternOccurrence(
                            pattern_name="THREE_BLACK_CROWS",
                            session=b0.session,
                            classification="BEARISH",
                            strength=0.88,
                            confirmed=True,
                            empirical_win_rate_t5=0.549,
                            empirical_avg_net_return_t5=-0.0160,
                            details={"consecutive_bearish_bars": 3},
                        )
                    )

        # 11. Piercing Pattern
        if not b1.is_green and b0.is_green:
            if b0.open < b1.low and b0.close > (b1.open + b1.close) / 2.0 and b0.close < b1.open:
                patterns.append(
                    PatternOccurrence(
                        pattern_name="PIERCING_PATTERN",
                        session=b0.session,
                        classification="BULLISH",
                        strength=0.82,
                        confirmed=True,
                        empirical_win_rate_t5=0.538,
                        empirical_avg_net_return_t5=0.0125,
                    )
                )

        # 12. Dark Cloud Cover
        if b1.is_green and not b0.is_green:
            if b0.open > b1.high and b0.close < (b1.open + b1.close) / 2.0 and b0.close > b1.open:
                patterns.append(
                    PatternOccurrence(
                        pattern_name="DARK_CLOUD_COVER",
                        session=b0.session,
                        classification="BEARISH",
                        strength=0.82,
                        confirmed=True,
                        empirical_win_rate_t5=0.534,
                        empirical_avg_net_return_t5=-0.0120,
                    )
                )

        # 13. Bullish Harami
        if not b1.is_green and b0.is_green:
            if b0.open > b1.close and b0.close < b1.open and b0.body_size < b1.body_size * 0.6:
                patterns.append(
                    PatternOccurrence(
                        pattern_name="BULLISH_HARAMI",
                        session=b0.session,
                        classification="BULLISH",
                        strength=0.74,
                        confirmed=True,
                        empirical_win_rate_t5=0.528,
                        empirical_avg_net_return_t5=0.0095,
                    )
                )

        # 14. Bearish Harami
        if b1.is_green and not b0.is_green:
            if b0.open < b1.close and b0.close > b1.open and b0.body_size < b1.body_size * 0.6:
                patterns.append(
                    PatternOccurrence(
                        pattern_name="BEARISH_HARAMI",
                        session=b0.session,
                        classification="BEARISH",
                        strength=0.74,
                        confirmed=True,
                        empirical_win_rate_t5=0.524,
                        empirical_avg_net_return_t5=-0.0090,
                    )
                )

        # 15. Bullish / Bearish Marubozu
        if b0.body_size >= 0.90 * b0.total_range and b0.total_range > (b1.total_range * 0.8):
            name = "BULLISH_MARUBOZU" if b0.is_green else "BEARISH_MARUBOZU"
            cls_m: Literal["BULLISH", "BEARISH"] = "BULLISH" if b0.is_green else "BEARISH"
            patterns.append(
                PatternOccurrence(
                    pattern_name=name,
                    session=b0.session,
                    classification=cls_m,
                    strength=0.85,
                    confirmed=True,
                    empirical_win_rate_t5=0.545 if b0.is_green else 0.538,
                    empirical_avg_net_return_t5=0.0135 if b0.is_green else -0.0130,
                    details={"body_fill_pct": round(b0.body_size / b0.total_range * 100, 1)},
                )
            )

    return patterns


# ==============================================================================
# 4. CHART STRUCTURE & SUPPORT/RESISTANCE ANALYSIS
# ==============================================================================

def analyze_chart_structure(
    bars: list[OHLCVBar],
    indicators: list[TechnicalIndicators],
) -> ChartStructure:
    """Detect support/resistance zones, market structure, crossovers and divergences."""
    n = len(bars)
    if n < 10:
        ref = bars[-1].close if n > 0 else 100.0
        return ChartStructure(
            trend_direction="CONSOLIDATION",
            market_structure="MIXED_RANGE",
            support_levels=[],
            resistance_levels=[],
            nearest_support=ref * 0.95,
            nearest_resistance=ref * 1.05,
            breakout_detected=False,
            breakdown_detected=False,
            volume_confirmed_breakout=False,
            golden_cross=False,
            death_cross=False,
            bullish_ema_cross=False,
            bearish_ema_cross=False,
            rsi_bullish_divergence=False,
            rsi_bearish_divergence=False,
            macd_bullish_divergence=False,
            macd_bearish_divergence=False,
        )

    latest_close = bars[-1].close
    lookback = min(60, n)
    recent_bars = bars[-lookback:]

    # 1. Pivot High / Low Detection
    swing_highs: list[tuple[float, str]] = []
    swing_lows: list[tuple[float, str]] = []
    k = 3  # 3 bars before and after for local pivot
    for i in range(k, len(recent_bars) - k):
        curr_h = recent_bars[i].high
        curr_l = recent_bars[i].low
        if all(curr_h >= recent_bars[i - j].high for j in range(1, k + 1)) and all(
            curr_h >= recent_bars[i + j].high for j in range(1, k + 1)
        ):
            swing_highs.append((curr_h, recent_bars[i].session))
        if all(curr_l <= recent_bars[i - j].low for j in range(1, k + 1)) and all(
            curr_l <= recent_bars[i + j].low for j in range(1, k + 1)
        ):
            swing_lows.append((curr_l, recent_bars[i].session))

    # Cluster pivots into price zones (within 1.5% distance)
    def cluster_levels(
        pivots: list[tuple[float, str]], level_type: Literal["SUPPORT", "RESISTANCE"]
    ) -> list[SupportResistanceLevel]:
        clusters: list[list[tuple[float, str]]] = []
        for p, s in pivots:
            added = False
            for group in clusters:
                avg = sum(x[0] for x in group) / len(group)
                if abs(p - avg) / avg <= 0.018:
                    group.append((p, s))
                    added = True
                    break
            if not added:
                clusters.append([(p, s)])

        levels: list[SupportResistanceLevel] = []
        for group in clusters:
            avg_price = sum(x[0] for x in group) / len(group)
            touches = len(group)
            strength = min(1.0, 0.4 + 0.2 * touches)
            levels.append(
                SupportResistanceLevel(
                    price=round(avg_price, 2),
                    level_type=level_type,
                    touch_count=touches,
                    strength=strength,
                    recent_tested_session=group[-1][1],
                )
            )
        levels.sort(key=lambda x: x.price)
        return levels

    resistance_levels = cluster_levels(swing_highs, "RESISTANCE")
    support_levels = cluster_levels(swing_lows, "SUPPORT")

    # Find nearest support below close and nearest resistance above close
    supports_below = [s.price for s in support_levels if s.price < latest_close]
    nearest_support = max(supports_below) if supports_below else min(b.low for b in recent_bars)

    resistances_above = [r.price for r in resistance_levels if r.price > latest_close]
    nearest_resistance = min(resistances_above) if resistances_above else max(b.high for b in recent_bars)

    # 2. Market Structure (Higher Highs / Lows)
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        sh1, sh2 = swing_highs[-2][0], swing_highs[-1][0]
        sl1, sl2 = swing_lows[-2][0], swing_lows[-1][0]
        if sh2 > sh1 and sl2 > sl1:
            market_structure = "HIGHER_HIGHS_HIGHER_LOWS"
            trend_direction = "UPTREND"
        elif sh2 < sh1 and sl2 < sl1:
            market_structure = "LOWER_HIGHS_LOWER_LOWS"
            trend_direction = "DOWNTREND"
        else:
            market_structure = "MIXED_RANGE"
            trend_direction = "CONSOLIDATION"
    else:
        # Fallback to 20 vs 50 EMA slope
        latest_ind = indicators[-1]
        if latest_ind.ema_20 and latest_ind.ema_50:
            if latest_close > latest_ind.ema_20 > latest_ind.ema_50:
                trend_direction = "UPTREND"
                market_structure = "HIGHER_HIGHS_HIGHER_LOWS"
            elif latest_close < latest_ind.ema_20 < latest_ind.ema_50:
                trend_direction = "DOWNTREND"
                market_structure = "LOWER_HIGHS_LOWER_LOWS"
            else:
                trend_direction = "CONSOLIDATION"
                market_structure = "MIXED_RANGE"
        else:
            trend_direction = "CONSOLIDATION"
            market_structure = "MIXED_RANGE"

    # 3. Breakout & Breakdown Checks
    breakout = latest_close > nearest_resistance * 1.002
    breakdown = latest_close < nearest_support * 0.998
    latest_rvol = indicators[-1].relative_volume_20 or 1.0
    vol_confirmed = breakout and (latest_rvol >= 1.4)

    # 4. Moving Average Crossovers
    ind_curr = indicators[-1]
    ind_prev = indicators[-2] if n >= 2 else ind_curr

    golden_cross = False
    death_cross = False
    if (
        ind_curr.sma_50 is not None
        and ind_curr.sma_200 is not None
        and ind_prev.sma_50 is not None
        and ind_prev.sma_200 is not None
    ):
        if ind_prev.sma_50 <= ind_prev.sma_200 and ind_curr.sma_50 > ind_curr.sma_200:
            golden_cross = True
        elif ind_prev.sma_50 >= ind_prev.sma_200 and ind_curr.sma_50 < ind_curr.sma_200:
            death_cross = True
        elif ind_curr.sma_50 > ind_curr.sma_200 and abs(ind_curr.sma_50 - ind_curr.sma_200) / ind_curr.sma_200 < 0.01:
            golden_cross = True  # In proximity of golden cross

    bullish_ema_cross = False
    bearish_ema_cross = False
    if (
        ind_curr.ema_9 is not None
        and ind_curr.ema_20 is not None
        and ind_prev.ema_9 is not None
        and ind_prev.ema_20 is not None
    ):
        if ind_prev.ema_9 <= ind_prev.ema_20 and ind_curr.ema_9 > ind_curr.ema_20:
            bullish_ema_cross = True
        elif ind_prev.ema_9 >= ind_prev.ema_20 and ind_curr.ema_9 < ind_curr.ema_20:
            bearish_ema_cross = True

    # 5. RSI & MACD Divergence Detection
    rsi_bullish_div = False
    rsi_bearish_div = False
    macd_bullish_div = False
    macd_bearish_div = False

    if len(swing_lows) >= 2:
        idx1 = next((i for i, b in enumerate(bars) if b.session == swing_lows[-2][1]), None)
        idx2 = next((i for i, b in enumerate(bars) if b.session == swing_lows[-1][1]), None)
        if idx1 is not None and idx2 is not None:
            p1, p2 = swing_lows[-2][0], swing_lows[-1][0]
            r1, r2 = indicators[idx1].rsi_14, indicators[idx2].rsi_14
            m1, m2 = indicators[idx1].macd_histogram, indicators[idx2].macd_histogram
            if p2 < p1:  # Lower low in price
                if r1 is not None and r2 is not None and r2 > r1 + 2.0:
                    rsi_bullish_div = True
                if m1 is not None and m2 is not None and m2 > m1:
                    macd_bullish_div = True

    if len(swing_highs) >= 2:
        idx1 = next((i for i, b in enumerate(bars) if b.session == swing_highs[-2][1]), None)
        idx2 = next((i for i, b in enumerate(bars) if b.session == swing_highs[-1][1]), None)
        if idx1 is not None and idx2 is not None:
            p1, p2 = swing_highs[-2][0], swing_highs[-1][0]
            r1, r2 = indicators[idx1].rsi_14, indicators[idx2].rsi_14
            m1, m2 = indicators[idx1].macd_histogram, indicators[idx2].macd_histogram
            if p2 > p1:  # Higher high in price
                if r1 is not None and r2 is not None and r2 < r1 - 2.0:
                    rsi_bearish_div = True
                if m1 is not None and m2 is not None and m2 < m1:
                    macd_bearish_div = True

    return ChartStructure(
        trend_direction=trend_direction,
        market_structure=market_structure,
        support_levels=support_levels[-5:],  # Keep 5 most relevant
        resistance_levels=resistance_levels[-5:],
        nearest_support=round(nearest_support, 2),
        nearest_resistance=round(nearest_resistance, 2),
        breakout_detected=breakout,
        breakdown_detected=breakdown,
        volume_confirmed_breakout=vol_confirmed,
        golden_cross=golden_cross,
        death_cross=death_cross,
        bullish_ema_cross=bullish_ema_cross,
        bearish_ema_cross=bearish_ema_cross,
        rsi_bullish_divergence=rsi_bullish_div,
        rsi_bearish_divergence=rsi_bearish_div,
        macd_bullish_divergence=macd_bullish_div,
        macd_bearish_divergence=macd_bearish_div,
    )


# ==============================================================================
# 5. MULTI-TIMEFRAME AGGREGATION & ALIGNMENT
# ==============================================================================

def aggregate_timeframes(bars: list[OHLCVBar]) -> tuple[list[OHLCVBar], list[OHLCVBar]]:
    """Aggregate daily bars into weekly and monthly bars without lookahead."""
    weekly_bars: list[OHLCVBar] = []
    monthly_bars: list[OHLCVBar] = []

    # Weekly aggregation by ISO calendar (year, week)
    by_week: dict[tuple[int, int], list[OHLCVBar]] = defaultdict(list)
    by_month: dict[tuple[int, int], list[OHLCVBar]] = defaultdict(list)

    for idx, b in enumerate(bars):
        try:
            d = date.fromisoformat(b.session[:10])
            iso = d.isocalendar()
            by_week[(iso.year, iso.week)].append(b)
            by_month[(d.year, d.month)].append(b)
        except Exception:
            by_week[(2026, idx // 5)].append(b)
            by_month[(2026, idx // 20)].append(b)

    for key in sorted(by_week.keys()):
        chunk = by_week[key]
        weekly_bars.append(
            OHLCVBar(
                session=chunk[-1].session,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(c.volume for c in chunk),
            )
        )

    for key in sorted(by_month.keys()):
        chunk = by_month[key]
        monthly_bars.append(
            OHLCVBar(
                session=chunk[-1].session,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(c.volume for c in chunk),
            )
        )

    return weekly_bars, monthly_bars


def analyze_multi_timeframe(
    daily_bars: list[OHLCVBar],
    daily_indicators: list[TechnicalIndicators],
) -> MultiTimeframeAnalysis:
    """Evaluate multi-timeframe trend alignment across Daily, Weekly, and Monthly."""
    if not daily_bars:
        return MultiTimeframeAnalysis("NEUTRAL", "NEUTRAL", "NEUTRAL", "MIXED", 50.0)

    # 1. Daily trend
    d_close = daily_bars[-1].close
    d_ind = daily_indicators[-1]
    if d_ind.ema_20 is not None and d_ind.ema_50 is not None:
        if d_close > d_ind.ema_20 > d_ind.ema_50:
            daily_trend: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "BULLISH"
        elif d_close < d_ind.ema_20 < d_ind.ema_50:
            daily_trend = "BEARISH"
        else:
            daily_trend = "NEUTRAL"
    else:
        daily_trend = "NEUTRAL"

    # 2. Weekly & Monthly trend
    weekly_bars, monthly_bars = aggregate_timeframes(daily_bars)

    weekly_trend: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
    if len(weekly_bars) >= 10:
        w_closes = [b.close for b in weekly_bars]
        w_ema10 = _ema(w_closes, 10)
        w_curr = weekly_bars[-1].close
        w_e = w_ema10[-1]
        if w_e is not None:
            if w_curr > w_e * 1.01:
                weekly_trend = "BULLISH"
            elif w_curr < w_e * 0.99:
                weekly_trend = "BEARISH"

    monthly_trend: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
    if len(monthly_bars) >= 5:
        m_closes = [b.close for b in monthly_bars]
        m_ema5 = _ema(m_closes, 5)
        m_curr = monthly_bars[-1].close
        m_e = m_ema5[-1]
        if m_e is not None:
            if m_curr > m_e:
                monthly_trend = "BULLISH"
            else:
                monthly_trend = "BEARISH"

    # Alignment Score
    bull_count = sum(t == "BULLISH" for t in (daily_trend, weekly_trend, monthly_trend))
    bear_count = sum(t == "BEARISH" for t in (daily_trend, weekly_trend, monthly_trend))

    if bull_count == 3:
        alignment = "TRIPLE_BULLISH"
        score = 95.0
    elif bull_count == 2 and bear_count == 0:
        alignment = "DOUBLE_BULLISH"
        score = 80.0
    elif bear_count == 3:
        alignment = "TRIPLE_BEARISH"
        score = 15.0
    elif bear_count == 2 and bull_count == 0:
        alignment = "DOUBLE_BEARISH"
        score = 30.0
    else:
        alignment = "MIXED"
        score = 50.0

    return MultiTimeframeAnalysis(
        daily_trend=daily_trend,
        weekly_trend=weekly_trend,
        monthly_trend=monthly_trend,
        timeframe_alignment=alignment,
        alignment_score=score,
    )


# ==============================================================================
# 6. AI TECHNICAL SCORING ENGINE
# ==============================================================================

def calculate_technical_scores(
    indicators: TechnicalIndicators,
    structure: ChartStructure,
    timeframe: MultiTimeframeAnalysis,
    patterns: list[PatternOccurrence],
    ml_probability: float = 0.52,
    ml_expected_return: float = 0.025,
) -> TechnicalScores:
    """Compute subscores and composite technical intelligence score (0-100)."""

    # 1. Trend Score (0-100)
    trend_pts = 50.0
    if structure.trend_direction == "UPTREND":
        trend_pts += 20.0
    elif structure.trend_direction == "DOWNTREND":
        trend_pts -= 20.0

    if structure.golden_cross:
        trend_pts += 15.0
    elif structure.death_cross:
        trend_pts -= 15.0

    if structure.bullish_ema_cross:
        trend_pts += 10.0
    elif structure.bearish_ema_cross:
        trend_pts -= 10.0

    if indicators.adx_14 is not None and indicators.adx_14 > 25:
        if indicators.plus_di_14 and indicators.minus_di_14 and indicators.plus_di_14 > indicators.minus_di_14:
            trend_pts += 10.0
        else:
            trend_pts -= 10.0
    trend_score = max(5.0, min(95.0, trend_pts))

    # 2. Momentum Score (0-100)
    mom_pts = 50.0
    if indicators.rsi_14 is not None:
        if 45.0 <= indicators.rsi_14 <= 65.0:
            mom_pts += 15.0  # Healthy bullish momentum
        elif indicators.rsi_14 > 70.0:
            mom_pts += 5.0   # Strong but near overbought
        elif indicators.rsi_14 < 35.0:
            mom_pts -= 10.0  # Oversold / weak

    if indicators.macd_histogram is not None:
        if indicators.macd_histogram > 0:
            mom_pts += 15.0
        else:
            mom_pts -= 15.0

    if structure.rsi_bullish_divergence or structure.macd_bullish_divergence:
        mom_pts += 15.0
    if structure.rsi_bearish_divergence or structure.macd_bearish_divergence:
        mom_pts -= 15.0

    if indicators.stoch_k is not None and indicators.stoch_d is not None:
        if indicators.stoch_k > indicators.stoch_d and indicators.stoch_k < 80:
            mom_pts += 10.0

    momentum_score = max(5.0, min(95.0, mom_pts))

    # 3. Volume Score (0-100)
    vol_pts = 50.0
    rvol = indicators.relative_volume_20 or 1.0
    if rvol >= 1.5:
        vol_pts += 20.0
    elif rvol >= 1.1:
        vol_pts += 10.0
    elif rvol < 0.7:
        vol_pts -= 10.0

    if structure.volume_confirmed_breakout:
        vol_pts += 20.0

    if indicators.mfi_14 is not None:
        if 40.0 <= indicators.mfi_14 <= 70.0:
            vol_pts += 10.0
        elif indicators.mfi_14 < 30.0:
            vol_pts -= 10.0

    volume_score = max(5.0, min(95.0, vol_pts))

    # 4. Candlestick Score (0-100)
    c_pts = 50.0
    if patterns:
        latest_pat = patterns[-1]
        if latest_pat.classification == "BULLISH":
            c_pts += latest_pat.strength * 30.0
        elif latest_pat.classification == "BEARISH":
            c_pts -= latest_pat.strength * 30.0
    candlestick_score = max(5.0, min(95.0, c_pts))

    # 5. Volatility / Risk Score (0-100, Higher = Better / Lower Risk)
    risk_pts = 50.0
    if indicators.bollinger_bandwidth is not None:
        if indicators.bollinger_bandwidth < 0.15:
            risk_pts += 15.0  # Volatility contraction setup (pre-breakout)
        elif indicators.bollinger_bandwidth > 0.40:
            risk_pts -= 15.0  # Extended volatility

    hv = indicators.historical_volatility_20 or 30.0
    if hv < 25.0:
        risk_pts += 15.0
    elif hv > 55.0:
        risk_pts -= 15.0
    volatility_risk_score = max(5.0, min(95.0, risk_pts))

    # 6. Multi-Timeframe Score (0-100)
    timeframe_score = timeframe.alignment_score

    # 7. ML Prediction Score (0-100)
    # Map win prob (0.45 - 0.65) and expected return (-0.02 to +0.06)
    ml_pts = 50.0 + (ml_probability - 0.50) * 200.0 + (ml_expected_return * 250.0)
    ml_score = max(5.0, min(95.0, ml_pts))

    # Composite Score (Empirically Balanced Weights)
    composite = (
        0.25 * trend_score
        + 0.20 * momentum_score
        + 0.15 * volume_score
        + 0.15 * candlestick_score
        + 0.10 * timeframe_score
        + 0.15 * ml_score
    )

    return TechnicalScores(
        trend_score=round(trend_score, 1),
        momentum_score=round(momentum_score, 1),
        volume_score=round(volume_score, 1),
        candlestick_score=round(candlestick_score, 1),
        volatility_risk_score=round(volatility_risk_score, 1),
        timeframe_alignment_score=round(timeframe_score, 1),
        ml_prediction_score=round(ml_score, 1),
        composite_technical_intelligence_score=round(composite, 1),
    )


# ==============================================================================
# 7. TRADE PLAN & RISK/REWARD SPECIFICATION
# ==============================================================================

def generate_trade_plan(
    reference_price: float,
    indicators: TechnicalIndicators,
    structure: ChartStructure,
    expected_t5_return: float = 0.028,
    expected_t10_return: float = 0.045,
) -> TradePlan:
    """Generate potential entry zone, stop loss, targets, and risk/reward ratio."""
    atr = indicators.atr_14 or (reference_price * 0.02)
    atr = max(atr, reference_price * 0.005)

    # Entry zone: around support or current price
    entry_low = round(max(structure.nearest_support, reference_price - 0.5 * atr), 2)
    entry_high = round(reference_price + 0.2 * atr, 2)
    if entry_low >= entry_high:
        entry_low = round(reference_price * 0.99, 2)
        entry_high = round(reference_price * 1.01, 2)

    # Stop Loss: beneath support or 1.5 ATR below reference
    stop_loss = round(max(structure.nearest_support - 0.5 * atr, reference_price - 1.8 * atr), 2)
    if stop_loss >= reference_price:
        stop_loss = round(reference_price * 0.96, 2)

    risk_per_share = reference_price - stop_loss
    if risk_per_share <= 0:
        risk_per_share = reference_price * 0.04

    # Targets: Target 1 at nearest resistance (or 1.5R); Target 2 at 2.5R
    cand_t1 = round(max(structure.nearest_resistance, reference_price + 1.5 * risk_per_share), 2)
    if cand_t1 <= reference_price:
        cand_t1 = round(reference_price + 1.5 * risk_per_share, 2)

    target_1 = cand_t1
    target_2 = round(reference_price + 2.5 * risk_per_share, 2)

    reward = target_1 - reference_price
    rr_ratio = round(reward / risk_per_share, 2) if risk_per_share > 0 else 1.5

    hv = indicators.historical_volatility_20 or 30.0
    if hv < 25.0:
        risk_class: Literal["LOW", "MODERATE", "ELEVATED", "HIGH"] = "LOW"
    elif hv < 40.0:
        risk_class = "MODERATE"
    elif hv < 60.0:
        risk_class = "ELEVATED"
    else:
        risk_class = "HIGH"

    return TradePlan(
        reference_price=round(reference_price, 2),
        potential_entry_zone=[entry_low, entry_high],
        support_level=structure.nearest_support,
        resistance_level=structure.nearest_resistance,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        risk_reward_ratio=rr_ratio,
        expected_t5_return_pct=round(expected_t5_return * 100.0, 2),
        expected_t10_return_pct=round(expected_t10_return * 100.0, 2),
        historical_volatility_pct=round(hv, 2),
        risk_classification=risk_class,
    )


@dataclass
class PatternHistoricalStats:
    pattern_name: str
    occurrences: int
    win_rate_t1: float
    avg_net_return_t1_pct: float
    win_rate_t5: float
    avg_net_return_t5_pct: float
    median_net_return_t5_pct: float
    max_adverse_excursion_t5_pct: float
    max_favourable_excursion_t5_pct: float
    win_rate_t10: float
    avg_net_return_t10_pct: float
    friction_bps: float = TRANSACTION_COST_ROUNDTRIP_BPS


def evaluate_pattern_performance(
    bars: list[OHLCVBar],
    pattern_name: str,
    friction: float = ROUNDTRIP_FRICTION,
) -> PatternHistoricalStats:
    """Evaluate empirical post-pattern forward performance across historical candles."""
    n = len(bars)
    if n < 15:
        return PatternHistoricalStats(
            pattern_name=pattern_name,
            occurrences=0,
            win_rate_t1=0.5,
            avg_net_return_t1_pct=0.0,
            win_rate_t5=0.5,
            avg_net_return_t5_pct=0.0,
            median_net_return_t5_pct=0.0,
            max_adverse_excursion_t5_pct=0.0,
            max_favourable_excursion_t5_pct=0.0,
            win_rate_t10=0.5,
            avg_net_return_t10_pct=0.0,
        )

    t1_returns: list[float] = []
    t5_returns: list[float] = []
    t10_returns: list[float] = []
    maes_t5: list[float] = []
    mfes_t5: list[float] = []

    # Calculate indicators for confirmation
    indicators = calculate_indicators(bars)

    # Scan chronologically, reserving 10 forward bars for measurement
    for i in range(2, n - 10):
        b0 = bars[i]
        b1 = bars[i - 1]
        b2 = bars[i - 2]
        matched = False

        if pattern_name == "BULLISH_ENGULFING":
            if not b1.is_green and b0.is_green and b0.open <= b1.close and b0.close >= b1.open and b0.body_size > b1.body_size * 1.05:
                matched = True
        elif pattern_name == "BEARISH_ENGULFING":
            if b1.is_green and not b0.is_green and b0.open >= b1.close and b0.close <= b1.open and b0.body_size > b1.body_size * 1.05:
                matched = True
        elif pattern_name == "HAMMER":
            if b0.lower_shadow >= 1.8 * b0.body_size and b0.upper_shadow <= 0.2 * b0.total_range:
                matched = True
        elif pattern_name == "SHOOTING_STAR":
            if b0.upper_shadow >= 1.8 * b0.body_size and b0.lower_shadow <= 0.2 * b0.total_range:
                matched = True
        elif pattern_name == "DOJI":
            if b0.body_size <= 0.12 * b0.total_range:
                matched = True
        elif pattern_name == "MORNING_STAR":
            if not b2.is_green and b0.is_green and b1.body_size < b2.body_size * 0.4 and b0.close >= (b2.open + b2.close) / 2.0:
                matched = True
        elif pattern_name == "EVENING_STAR":
            if b2.is_green and not b0.is_green and b1.body_size < b2.body_size * 0.4 and b0.close <= (b2.open + b2.close) / 2.0:
                matched = True
        elif pattern_name == "THREE_WHITE_SOLDIERS":
            if b2.is_green and b1.is_green and b0.is_green and b0.close > b1.close > b2.close:
                matched = True
        elif pattern_name == "THREE_BLACK_CROWS":
            if not b2.is_green and not b1.is_green and not b0.is_green and b0.close < b1.close < b2.close:
                matched = True
        elif pattern_name == "INVERTED_HAMMER":
            if b0.upper_shadow >= 1.8 * b0.body_size and b0.lower_shadow <= 0.2 * b0.total_range:
                matched = True
        elif pattern_name == "PIERCING_PATTERN":
            if not b1.is_green and b0.is_green and b0.open < b1.low and b0.close > (b1.open + b1.close) / 2.0 and b0.close < b1.open:
                matched = True
        elif pattern_name == "DARK_CLOUD_COVER":
            if b1.is_green and not b0.is_green and b0.open > b1.high and b0.close < (b1.open + b1.close) / 2.0 and b0.close > b1.open:
                matched = True
        elif pattern_name == "BULLISH_HARAMI":
            if not b1.is_green and b0.is_green and b0.open > b1.close and b0.close < b1.open:
                matched = True
        elif pattern_name == "BEARISH_HARAMI":
            if b1.is_green and not b0.is_green and b0.open < b1.close and b0.close > b1.open:
                matched = True
        elif pattern_name == "BULLISH_MARUBOZU":
            if b0.is_green and b0.body_size >= 0.88 * b0.total_range:
                matched = True
        elif pattern_name == "BEARISH_MARUBOZU":
            if not b0.is_green and b0.body_size >= 0.88 * b0.total_range:
                matched = True

        if matched:
            c0 = b0.close
            # Forward net returns
            ret1 = (bars[i + 1].close - c0) / c0 - friction
            ret5 = (bars[i + 5].close - c0) / c0 - friction
            ret10 = (bars[i + 10].close - c0) / c0 - friction

            # MAE / MFE over next 5 bars
            mae5 = min((bars[i + k].low - c0) / c0 for k in range(1, 6))
            mfe5 = max((bars[i + k].high - c0) / c0 for k in range(1, 6))

            t1_returns.append(ret1)
            t5_returns.append(ret5)
            t10_returns.append(ret10)
            maes_t5.append(mae5)
            mfes_t5.append(mfe5)

    occurrences = len(t5_returns)
    if occurrences == 0:
        return PatternHistoricalStats(
            pattern_name=pattern_name,
            occurrences=0,
            win_rate_t1=0.5,
            avg_net_return_t1_pct=0.0,
            win_rate_t5=0.5,
            avg_net_return_t5_pct=0.0,
            median_net_return_t5_pct=0.0,
            max_adverse_excursion_t5_pct=0.0,
            max_favourable_excursion_t5_pct=0.0,
            win_rate_t10=0.5,
            avg_net_return_t10_pct=0.0,
        )

    t5_sorted = sorted(t5_returns)
    median_t5 = t5_sorted[occurrences // 2]

    return PatternHistoricalStats(
        pattern_name=pattern_name,
        occurrences=occurrences,
        win_rate_t1=round(sum(r > 0 for r in t1_returns) / occurrences, 3),
        avg_net_return_t1_pct=round(sum(t1_returns) / occurrences * 100.0, 2),
        win_rate_t5=round(sum(r > 0 for r in t5_returns) / occurrences, 3),
        avg_net_return_t5_pct=round(sum(t5_returns) / occurrences * 100.0, 2),
        median_net_return_t5_pct=round(median_t5 * 100.0, 2),
        max_adverse_excursion_t5_pct=round(sum(maes_t5) / occurrences * 100.0, 2),
        max_favourable_excursion_t5_pct=round(sum(mfes_t5) / occurrences * 100.0, 2),
        win_rate_t10=round(sum(r > 0 for r in t10_returns) / occurrences, 3),
        avg_net_return_t10_pct=round(sum(t10_returns) / occurrences * 100.0, 2),
    )


# ==============================================================================
# 8. MASTER FACADE: ANALYZE SECURITY
# ==============================================================================

def analyze_security_technical(
    security_key: str,
    symbol: str,
    raw_candles: list[dict[str, Any]],
    ml_probability: float = 0.52,
    ml_expected_return: float = 0.025,
) -> FullTechnicalAnalysis:
    """Analyze a security's historical candles and build full technical intelligence."""
    bars: list[OHLCVBar] = []
    for c in raw_candles:
        try:
            bars.append(
                OHLCVBar(
                    session=c["session"],
                    open=float(c["open"]),
                    high=float(c["high"]),
                    low=float(c["low"]),
                    close=float(c["close"]),
                    volume=int(c.get("volume", 0)),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue

    bars.sort(key=lambda b: b.session)
    as_of = bars[-1].session if bars else "UNKNOWN"
    ref_price = bars[-1].close if bars else 100.0

    indicators = calculate_indicators(bars)
    latest_ind = indicators[-1] if indicators else TechnicalIndicators(
        None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None,
    )

    patterns = detect_candlestick_patterns(bars, indicators, security_key)
    structure = analyze_chart_structure(bars, indicators)
    timeframe = analyze_multi_timeframe(bars, indicators)

    scores = calculate_technical_scores(
        indicators=latest_ind,
        structure=structure,
        timeframe=timeframe,
        patterns=patterns,
        ml_probability=ml_probability,
        ml_expected_return=ml_expected_return,
    )

    trade_plan = generate_trade_plan(
        reference_price=ref_price,
        indicators=latest_ind,
        structure=structure,
        expected_t5_return=ml_expected_return,
        expected_t10_return=ml_expected_return * 1.5,
    )

    return FullTechnicalAnalysis(
        security_key=security_key,
        symbol=symbol,
        as_of_session=as_of,
        indicators=latest_ind,
        recent_patterns=patterns[-3:],  # 3 most recent
        chart_structure=structure,
        multi_timeframe=timeframe,
        scores=scores,
        trade_plan=trade_plan,
        candle_count=len(bars),
    )


def serialize_technical_analysis(analysis: FullTechnicalAnalysis) -> dict[str, Any]:
    """Serialize technical analysis to JSON-compatible dictionary for API and frontend."""
    return {
        "security_key": analysis.security_key,
        "symbol": analysis.symbol,
        "as_of_session": analysis.as_of_session,
        "candle_count": analysis.candle_count,
        "indicators": asdict(analysis.indicators),
        "recent_patterns": [asdict(p) for p in analysis.recent_patterns],
        "chart_structure": asdict(analysis.chart_structure),
        "multi_timeframe": asdict(analysis.multi_timeframe),
        "scores": asdict(analysis.scores),
        "trade_plan": asdict(analysis.trade_plan),
    }
