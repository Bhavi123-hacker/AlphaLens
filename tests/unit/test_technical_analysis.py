"""Unit tests for AlphaLens AI Technical Chart Intelligence Engine."""

import math
from dataclasses import asdict
import pytest
from workers.nse_market.technical_analysis import (
    OHLCVBar,
    TechnicalIndicators,
    calculate_indicators,
    detect_candlestick_patterns,
    analyze_chart_structure,
    analyze_multi_timeframe,
    evaluate_pattern_performance,
    calculate_technical_scores,
    generate_trade_plan,
    analyze_security_technical,
    serialize_technical_analysis,
    _ema,
    _sma,
    ROUNDTRIP_FRICTION,
)


def make_dummy_bar(
    session: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 100000,
) -> OHLCVBar:
    return OHLCVBar(
        session=session,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_sma_and_ema_pure_math():
    values = [10.0, 11.0, 12.0, 13.0, 14.0]
    # SMA 3 of [10, 11, 12] is 11.0, of [11, 12, 13] is 12.0, of [12, 13, 14] is 13.0
    sma3 = _sma(values, 3)
    assert sma3[0] is None
    assert sma3[1] is None
    assert sma3[2] == pytest.approx(11.0)
    assert sma3[3] == pytest.approx(12.0)
    assert sma3[4] == pytest.approx(13.0)

    # Constant sequence EMA must remain constant
    const_vals = [50.0] * 20
    ema5 = _ema(const_vals, 5)
    for v in ema5[4:]:
        assert v == pytest.approx(50.0)


def test_macd_and_rsi_indicators():
    # Build 60 bars of strictly upward trending prices
    bars = []
    base_price = 100.0
    for i in range(60):
        p = base_price + i * 2.0
        bars.append(
            make_dummy_bar(
                session=f"2026-01-{i+1:02d}",
                open_=p - 0.5,
                high=p + 1.0,
                low=p - 1.0,
                close=p + 0.5,
                volume=50000 + i * 1000,
            )
        )

    indicators = calculate_indicators(bars)
    assert len(indicators) == 60

    # For monotonic uptrend, RSI should be elevated (> 70)
    last_ind = indicators[-1]
    assert last_ind.rsi_14 is not None
    assert last_ind.rsi_14 > 70.0

    # MACD line should be positive since EMA12 > EMA26 in an uptrend
    assert last_ind.macd_line is not None
    assert last_ind.macd_line > 0.0

    # Bollinger Bands: upper > middle > lower
    assert last_ind.bollinger_upper is not None
    assert last_ind.bollinger_middle is not None
    assert last_ind.bollinger_lower is not None
    assert last_ind.bollinger_upper > last_ind.bollinger_middle > last_ind.bollinger_lower

    # ATR should be positive and non-zero
    assert last_ind.atr_14 is not None
    assert last_ind.atr_14 > 0.0


def test_strict_lookahead_prevention():
    """Modifying bar at t+1 must NEVER alter indicators or patterns at time t."""
    base_bars = [
        make_dummy_bar(
            session=f"2026-01-{i+1:02d}",
            open_=100.0 + (i % 5),
            high=105.0 + (i % 5),
            low=98.0 + (i % 5),
            close=103.0 + (i % 5),
            volume=100000,
        )
        for i in range(30)
    ]

    # Calculate indicators up to bar 25
    ind_orig = calculate_indicators(base_bars)
    val_at_25_orig = asdict(ind_orig[25])

    # Modify future bars (26, 27, 28, 29) drastically
    modified_bars = list(base_bars)
    for j in range(26, 30):
        modified_bars[j] = make_dummy_bar(
            session=base_bars[j].session,
            open_=5000.0,
            high=6000.0,
            low=4000.0,
            close=5500.0,
            volume=99999999,
        )

    ind_modified = calculate_indicators(modified_bars)
    val_at_25_mod = asdict(ind_modified[25])

    # Every single metric at bar 25 must remain strictly identical
    for k in val_at_25_orig:
        assert val_at_25_orig[k] == val_at_25_mod[k], f"Lookahead detected in indicator {k}!"


def test_candlestick_pattern_recognition_bullish_and_bearish_engulfing():
    bars = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 101.0),
        make_dummy_bar("2026-01-02", 101.0, 103.0, 98.0, 99.0),   # Red bar: open 101, close 99
        make_dummy_bar("2026-01-03", 98.0, 105.0, 97.0, 104.0),   # Green bar engulfing previous: open 98, close 104
    ]
    inds = calculate_indicators(bars)
    patterns = detect_candlestick_patterns(bars, inds, "TEST_SEC")
    names = [p.pattern_name for p in patterns]
    assert "BULLISH_ENGULFING" in names

    # Bearish engulfing
    bars_bear = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 100.0),
        make_dummy_bar("2026-01-02", 100.0, 104.0, 99.0, 103.0),  # Green bar
        make_dummy_bar("2026-01-03", 104.0, 105.0, 97.0, 98.0),   # Red engulfing bar
    ]
    inds_bear = calculate_indicators(bars_bear)
    patterns_bear = detect_candlestick_patterns(bars_bear, inds_bear, "TEST_SEC")
    names_bear = [p.pattern_name for p in patterns_bear]
    assert "BEARISH_ENGULFING" in names_bear


def test_candlestick_pattern_hammer_and_shooting_star():
    # Hammer: long lower shadow >= 2x body, tiny upper shadow
    bars_hammer = [
        make_dummy_bar("2026-01-01", 105.0, 106.0, 102.0, 103.0),
        make_dummy_bar("2026-01-02", 103.0, 104.0, 100.0, 101.0),
        make_dummy_bar("2026-01-03", 100.0, 100.5, 90.0, 100.2), # Body=0.2, lower shadow=10.0
    ]
    inds_hammer = calculate_indicators(bars_hammer)
    pat_hammer = detect_candlestick_patterns(bars_hammer, inds_hammer, "TEST_SEC")
    assert any(p.pattern_name == "HAMMER" for p in pat_hammer)

    # Shooting Star: long upper shadow >= 2x body, tiny lower shadow
    bars_star = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 101.0),
        make_dummy_bar("2026-01-02", 101.0, 103.0, 100.0, 102.5),
        make_dummy_bar("2026-01-03", 103.0, 115.0, 102.8, 103.2), # Body=0.2, upper shadow=11.8
    ]
    inds_star = calculate_indicators(bars_star)
    pat_star = detect_candlestick_patterns(bars_star, inds_star, "TEST_SEC")
    assert any(p.pattern_name == "SHOOTING_STAR" for p in pat_star)


def test_candlestick_morning_star_and_three_white_soldiers():
    # Morning Star: large red, small body gap down, strong green
    bars_ms = [
        make_dummy_bar("2026-01-01", 100.0, 101.0, 90.0, 91.0),   # Big red
        make_dummy_bar("2026-01-02", 89.0, 90.0, 88.0, 89.2),     # Star
        make_dummy_bar("2026-01-03", 89.5, 98.0, 89.0, 97.0),     # Big green closing > midpoint of b0
    ]
    inds_ms = calculate_indicators(bars_ms)
    pat_ms = detect_candlestick_patterns(bars_ms, inds_ms, "TEST_SEC")
    assert any(p.pattern_name == "MORNING_STAR" for p in pat_ms)

    # Three White Soldiers
    bars_tws = [
        make_dummy_bar("2026-01-01", 100.0, 103.0, 99.0, 102.5),
        make_dummy_bar("2026-01-02", 102.0, 106.0, 101.5, 105.5),
        make_dummy_bar("2026-01-03", 105.0, 109.0, 104.5, 108.5),
    ]
    inds_tws = calculate_indicators(bars_tws)
    pat_tws = detect_candlestick_patterns(bars_tws, inds_tws, "TEST_SEC")
    assert any(p.pattern_name == "THREE_WHITE_SOLDIERS" for p in pat_tws)


def test_support_and_resistance_zones():
    # Create oscillating bars that bounce off support ~100 and reject at resistance ~120
    bars = []
    prices = [100, 110, 120, 110, 100, 110, 120, 110, 100, 112, 121, 111, 101, 115, 120]
    for i, p in enumerate(prices):
        bars.append(
            make_dummy_bar(
                session=f"2026-01-{i+1:02d}",
                open_=p - 1.0,
                high=p + 2.0,
                low=p - 2.0,
                close=p + 0.5,
                volume=150000,
            )
        )

    inds = calculate_indicators(bars)
    structure = analyze_chart_structure(bars, inds)

    assert len(structure.support_levels) > 0
    assert len(structure.resistance_levels) > 0
    assert structure.nearest_support is not None
    assert structure.nearest_resistance is not None
    assert structure.nearest_support <= structure.nearest_resistance


def test_multi_timeframe_aggregation():
    # Create 30 daily bars (spanning across ~6 weeks)
    bars = []
    for i in range(30):
        # Format Monday to Friday dates
        day = (i % 25) + 1
        bars.append(
            make_dummy_bar(
                session=f"2026-02-{day:02d}",
                open_=100.0 + i,
                high=102.0 + i,
                low=99.0 + i,
                close=101.5 + i,
                volume=100000,
            )
        )

    inds = calculate_indicators(bars)
    mtf = analyze_multi_timeframe(bars, inds)

    assert mtf.daily_trend in ["BULLISH", "BEARISH", "NEUTRAL"]
    assert mtf.weekly_trend in ["BULLISH", "BEARISH", "NEUTRAL"]
    assert mtf.monthly_trend in ["BULLISH", "BEARISH", "NEUTRAL"]
    assert mtf.timeframe_alignment in ["TRIPLE_BULLISH", "DOUBLE_BULLISH", "MIXED", "DOUBLE_BEARISH", "TRIPLE_BEARISH"]


def test_trade_plan_and_risk_reward():
    bars = [
        make_dummy_bar("2026-01-01", 100.0, 105.0, 98.0, 104.0),
        make_dummy_bar("2026-01-02", 104.0, 108.0, 102.0, 106.0),
        make_dummy_bar("2026-01-03", 106.0, 110.0, 105.0, 109.0),
    ]
    inds = calculate_indicators(bars)
    struct = analyze_chart_structure(bars, inds)
    mtf = analyze_multi_timeframe(bars, inds)
    scores = calculate_technical_scores(inds[-1], struct, mtf, [], 0.65, 0.025)

    plan = generate_trade_plan(
        reference_price=bars[-1].close,
        indicators=inds[-1],
        structure=struct,
        expected_t5_return=0.028,
        expected_t10_return=0.045,
    )

    assert plan.reference_price == 109.0
    assert plan.stop_loss < plan.reference_price
    assert plan.target_1 > plan.reference_price
    assert plan.target_2 > plan.target_1
    assert plan.risk_reward_ratio > 0.0
    assert plan.disclaimer != ""


def test_full_security_analysis_and_serialization():
    from datetime import date, timedelta
    start_date = date(2026, 1, 1)
    # 35 bars to allow rolling indicators to initialize
    bars = []
    for i in range(35):
        cur_date = start_date + timedelta(days=i)
        bars.append(
            make_dummy_bar(
                session=cur_date.isoformat(),
                open_=500.0 + i * 2,
                high=505.0 + i * 2,
                low=498.0 + i * 2,
                close=503.0 + i * 2,
                volume=200000 + i * 5000,
            )
        )

    raw_candles = [
        {
            "session": b.session,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in bars
    ]

    analysis = analyze_security_technical(
        security_key="NSE_EQ|INE002A01018",
        symbol="RELIANCE",
        raw_candles=raw_candles,
        ml_probability=0.65,
        ml_expected_return=0.025,
    )

    serialized = serialize_technical_analysis(analysis)
    assert serialized["security_key"] == "NSE_EQ|INE002A01018"
    assert serialized["symbol"] == "RELIANCE"
    assert "scores" in serialized
    assert "trade_plan" in serialized
    assert "indicators" in serialized
    assert "chart_structure" in serialized
    assert "multi_timeframe" in serialized
    assert "recent_patterns" in serialized
    assert serialized["scores"]["composite_technical_intelligence_score"] > 0.0


def test_all_remaining_candlestick_patterns():
    # 1. Inverted Hammer
    bars_inv = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 100.5),
        make_dummy_bar("2026-01-02", 100.5, 101.0, 97.0, 98.0),
        make_dummy_bar("2026-01-03", 97.0, 108.0, 96.8, 97.5), # body=0.5, upper shadow=10.5
    ]
    p_inv = detect_candlestick_patterns(bars_inv, calculate_indicators(bars_inv), "S")
    assert any(p.pattern_name == "INVERTED_HAMMER" for p in p_inv)

    # 2. Doji (Standard, Dragonfly, Gravestone)
    bars_doji = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 101.0),
        make_dummy_bar("2026-01-02", 101.0, 103.0, 100.0, 101.5),
        make_dummy_bar("2026-01-03", 101.5, 108.0, 95.0, 101.6), # body=0.1, range=13.0
    ]
    p_doji = detect_candlestick_patterns(bars_doji, calculate_indicators(bars_doji), "S")
    assert any("DOJI" in p.pattern_name for p in p_doji)

    # 3. Evening Star
    bars_es = [
        make_dummy_bar("2026-01-01", 90.0, 101.0, 89.0, 100.0),   # Big green
        make_dummy_bar("2026-01-02", 101.0, 102.0, 100.5, 101.2), # Star
        make_dummy_bar("2026-01-03", 100.5, 101.0, 91.0, 92.0),   # Big red closing < midpoint
    ]
    p_es = detect_candlestick_patterns(bars_es, calculate_indicators(bars_es), "S")
    assert any(p.pattern_name == "EVENING_STAR" for p in p_es)

    # 4. Three Black Crows
    bars_tbc = [
        make_dummy_bar("2026-01-01", 105.0, 105.5, 101.5, 102.0),
        make_dummy_bar("2026-01-02", 101.8, 102.0, 98.0, 98.5),
        make_dummy_bar("2026-01-03", 98.2, 98.5, 94.0, 94.5),
    ]
    p_tbc = detect_candlestick_patterns(bars_tbc, calculate_indicators(bars_tbc), "S")
    assert any(p.pattern_name == "THREE_BLACK_CROWS" for p in p_tbc)

    # 5. Piercing Pattern
    bars_pierce = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 101.0),
        make_dummy_bar("2026-01-02", 101.0, 102.0, 90.0, 91.0),   # Big red (low 90)
        make_dummy_bar("2026-01-03", 88.0, 98.0, 87.5, 97.0),     # Open < 90, close > (101+91)/2=96 and < 101
    ]
    p_pierce = detect_candlestick_patterns(bars_pierce, calculate_indicators(bars_pierce), "S")
    assert any(p.pattern_name == "PIERCING_PATTERN" for p in p_pierce)

    # 6. Dark Cloud Cover
    bars_dcc = [
        make_dummy_bar("2026-01-01", 90.0, 92.0, 89.0, 91.0),
        make_dummy_bar("2026-01-02", 91.0, 101.0, 90.0, 100.0),   # Big green (high 101)
        make_dummy_bar("2026-01-03", 102.0, 102.5, 92.0, 93.0),   # Open > 101, close < 95.5 and > 91
    ]
    p_dcc = detect_candlestick_patterns(bars_dcc, calculate_indicators(bars_dcc), "S")
    assert any(p.pattern_name == "DARK_CLOUD_COVER" for p in p_dcc)

    # 7. Bullish & Bearish Harami
    bars_bharami = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 101.0),
        make_dummy_bar("2026-01-02", 100.0, 101.0, 88.0, 90.0),   # Big red
        make_dummy_bar("2026-01-03", 92.0, 96.0, 91.0, 95.0),     # Small green inside red body
    ]
    p_bharami = detect_candlestick_patterns(bars_bharami, calculate_indicators(bars_bharami), "S")
    assert any(p.pattern_name == "BULLISH_HARAMI" for p in p_bharami)

    # 8. Bullish & Bearish Marubozu
    bars_maru = [
        make_dummy_bar("2026-01-01", 100.0, 102.0, 99.0, 101.0),
        make_dummy_bar("2026-01-02", 100.0, 100.5, 99.5, 100.2),
        make_dummy_bar("2026-01-03", 100.0, 110.0, 99.9, 109.8),  # 9.8 body out of 10.1 range (~97%)
    ]
    p_maru = detect_candlestick_patterns(bars_maru, calculate_indicators(bars_maru), "S")
    assert any(p.pattern_name == "BULLISH_MARUBOZU" for p in p_maru)
