"""Empirical Head-to-Head Comparison: ML-Only vs Technical-Only vs Hybrid Intelligence.

Evaluates on the exact same untouched historical dataset (500 NSE stocks, July-Nov 2026):
1. ML-Only Ranking
2. Technical-Only Ranking
3. Combined Hybrid ML + Technical Ranking
4. Benchmarks: Equal-Weight Universe, Momentum Baseline

Tested across:
- Horizons: T+1, T+5, T+10
- Portfolio Cohorts: Top 5, Top 10, Top 20
- Cost Models: 0 bps, 25 bps, 45 bps (realistic Indian delivery), 65 bps (conservative)
"""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path("D:/al-research/p28-worktree/.campaign-worktree")
LOCAL_DATA = Path("D:/al-research/p28-worktree/.local-data")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workers.nse_market.order_cost_model import IndianEquityCostEngine


def load_market_data() -> tuple[list[str], dict[str, list[dict[str, Any]]], dict[str, dict[str, float]]]:
    """Load the verified market view with 500 stocks and 120 sessions."""
    p_ptr = LOCAL_DATA / "nse-market-expansion" / "market-view-latest.json"
    meta = json.loads(p_ptr.read_text(encoding="utf-8"))
    mv_file = p_ptr.parent / meta["path"]
    data = json.loads(mv_file.read_text(encoding="utf-8"))

    histories: dict[str, list[dict[str, Any]]] = data["histories"]
    all_sessions = set()
    for bars in histories.values():
        for b in bars:
            d = b.get("session") or b.get("date") or b.get("timestamp", "")[:10]
            if d:
                all_sessions.add(str(d))
    sorted_sessions = sorted(all_sessions)

    # Load ML scores from workspace-latest.json
    ws_ptr = LOCAL_DATA / "nse-market-expansion" / "workspace-latest.json"
    ml_scores: dict[str, dict[str, float]] = {}
    if ws_ptr.exists():
        ws_meta = json.loads(ws_ptr.read_text(encoding="utf-8"))
        ws_file = ws_ptr.parent / ws_meta["path"]
        raw_ws = json.loads(ws_file.read_text(encoding="utf-8"))
        val = raw_ws.get("value", raw_ws)
        for c in val.get("candidates", []):
            k = c.get("key")
            s = c.get("score")
            if k and s is not None:
                try:
                    score_val = float(s)
                    ml_scores[k] = {
                        "score": score_val,
                        "volatility": float(c.get("volatility_percent", 2.0)),
                    }
                except (ValueError, TypeError):
                    pass

    return sorted_sessions, histories, ml_scores


def calculate_technical_features(candles: list[dict[str, Any]]) -> dict[str, float]:
    """Compute lightweight trend, momentum, volatility, and volume scores from clean candles."""
    valid_closes = []
    valid_vols = []
    for b in candles:
        try:
            c = b.get("close")
            v = b.get("volume")
            if c is not None and v is not None:
                c_f = float(c)
                v_f = float(v)
                if c_f > 0 and math.isfinite(c_f) and v_f >= 0 and math.isfinite(v_f):
                    valid_closes.append(c_f)
                    valid_vols.append(v_f)
        except (ValueError, TypeError):
            continue

    if len(valid_closes) < 30:
        return {"trend": 50.0, "momentum": 50.0, "volatility": 2.0, "composite": 50.0}

    closes = np.array(valid_closes, dtype=float)
    vols = np.array(valid_vols, dtype=float)

    # 1. Trend: Close vs SMA20 & SMA50
    sma20 = float(np.mean(closes[-20:]))
    sma50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else sma20
    trend_score = 50.0
    if closes[-1] > sma20:
        trend_score += 20.0
    if sma20 > sma50:
        trend_score += 20.0
    if closes[-1] < sma20:
        trend_score -= 20.0
    if sma20 < sma50:
        trend_score -= 20.0
    trend_score = max(0.0, min(100.0, trend_score))

    # 2. Momentum: RSI 14
    deltas = np.diff(closes[-15:])
    gains = np.maximum(deltas, 0)
    losses = np.maximum(-deltas, 0)
    avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    # 3. Volatility: 20-day returns std dev
    ret = np.diff(closes[-21:]) / closes[-21:-1]
    vol = float(np.std(ret) * 100.0) if len(ret) > 1 else 2.0

    # 4. Volume: Relative volume vs 20-day average
    vol20 = float(np.mean(vols[-20:])) if len(vols) >= 20 else 1.0
    rel_vol = vols[-1] / vol20 if vol20 > 0 else 1.0

    # Composite Technical Score
    comp = 0.40 * trend_score + 0.35 * rsi + 0.25 * min(100.0, rel_vol * 50.0)
    return {
        "trend": trend_score,
        "momentum": rsi,
        "volatility": vol,
        "composite": comp,
    }


def evaluate_strategies() -> None:
    print("Loading market data...")
    sessions, histories, ml_scores = load_market_data()
    print(f"Loaded {len(sessions)} sessions across {len(histories)} stocks. ML scores available for {len(ml_scores)} stocks.")

    test_sessions = sessions[36:]
    total_test_sessions = len(test_sessions)

    FRICTION_LEVELS = [0, 25, 45, 65]
    TICKET_SIZES = [10000, 25000, 50000, 100000, 500000]
    cost_engine = IndianEquityCostEngine()
    ticket_friction_map = {
        ts: cost_engine.calculate_roundtrip("SAMPLE", 1000.0, 1000.0, max(1, int(ts / 1000.0)))["roundtrip_friction_bps"]
        for ts in TICKET_SIZES
    }
    horizons = [1, 5, 10]
    cohort_sizes = [5, 10, 20]
    strategies = ["ML_ONLY", "TECHNICAL_ONLY", "HYBRID_INTELLIGENCE", "MOMENTUM_BASELINE", "UNIVERSE_EQUAL_WEIGHT"]

    # Precompute prices map: session -> key -> (open, close)
    session_prices: dict[str, dict[str, tuple[float, float]]] = {}
    for s in sessions:
        session_prices[s] = {}
        for k, bars in histories.items():
            for b in bars:
                d = b.get("session") or b.get("date") or b.get("timestamp", "")[:10]
                if str(d) == s:
                    try:
                        o_val = b.get("open")
                        c_val = b.get("close")
                        if o_val is not None and c_val is not None:
                            o = float(o_val)
                            c = float(c_val)
                            if o > 0 and c > 0 and math.isfinite(o) and math.isfinite(c):
                                session_prices[s][k] = (o, c)
                    except (ValueError, TypeError):
                        pass

    results: dict[str, Any] = {}

    for h in horizons:
        results[f"T+{h}"] = {}
        for n_stocks in cohort_sizes:
            scenario_key = f"Top_{n_stocks}"
            results[f"T+{h}"][scenario_key] = {}

            strat_trades: dict[str, list[float]] = {s: [] for s in strategies}

            # Step through test sessions at step size h
            for idx in range(36, len(sessions) - h, h):
                dec_session = sessions[idx]
                exit_session = sessions[idx + h]

                eligible_keys = [k for k in histories.keys() if k in session_prices.get(dec_session, {}) and k in session_prices.get(exit_session, {})]
                if len(eligible_keys) < 50:
                    continue

                univ_returns = []
                for k in eligible_keys:
                    p_entry = session_prices[dec_session][k][1]
                    p_exit = session_prices[exit_session][k][1]
                    ret = (p_exit - p_entry) / p_entry
                    univ_returns.append(ret)
                if univ_returns:
                    strat_trades["UNIVERSE_EQUAL_WEIGHT"].append(float(np.mean(univ_returns)))

                mom_scores = {}
                tech_scores = {}
                comb_scores = {}
                ml_ranks = {}

                for k in eligible_keys:
                    clean_bars = []
                    for b in histories[k]:
                        d = str(b.get("session") or b.get("date") or b.get("timestamp", "")[:10])
                        if d <= dec_session and b.get("close") is not None:
                            clean_bars.append(b)

                    if len(clean_bars) < 20:
                        continue

                    try:
                        c_now = float(clean_bars[-1]["close"])
                        c_prev = float(clean_bars[-20]["close"])
                        mom = (c_now - c_prev) / c_prev if c_prev > 0 else 0.0
                    except (ValueError, TypeError, KeyError):
                        continue

                    mom_scores[k] = mom

                    tf = calculate_technical_features(clean_bars)
                    tech_scores[k] = tf["composite"]

                    base_ml = ml_scores.get(k, {}).get("score", 0.50)
                    ml_ranks[k] = base_ml

                    # Combined Hybrid Score:
                    # 40% ML + 35% Tech + 25% Momentum - Volatility Penalty
                    norm_ml = base_ml * 100.0
                    norm_tech = tf["composite"]
                    vol_penalty = min(20.0, tf["volatility"] * 4.0)
                    hybrid = 0.40 * norm_ml + 0.35 * norm_tech + 0.25 * (mom * 100.0) - vol_penalty
                    comb_scores[k] = hybrid

                def select_and_return(score_dict: dict[str, float]) -> float:
                    sorted_k = sorted(score_dict.keys(), key=lambda x: score_dict[x], reverse=True)[:n_stocks]
                    rets = []
                    for k in sorted_k:
                        p_entry = session_prices[dec_session][k][1]
                        p_exit = session_prices[exit_session][k][1]
                        rets.append((p_exit - p_entry) / p_entry)
                    return float(np.mean(rets)) if rets else 0.0

                strat_trades["ML_ONLY"].append(select_and_return(ml_ranks))
                strat_trades["TECHNICAL_ONLY"].append(select_and_return(tech_scores))
                strat_trades["HYBRID_INTELLIGENCE"].append(select_and_return(comb_scores))
                strat_trades["MOMENTUM_BASELINE"].append(select_and_return(mom_scores))

            for strat in strategies:
                gross_rets = strat_trades[strat]
                results[f"T+{h}"][scenario_key][strat] = {}

                for f_bps in FRICTION_LEVELS:
                    friction_dec = f_bps / 10000.0
                    net_rets = [r - friction_dec for r in gross_rets]
                    cum_ret = float(np.prod([1.0 + r for r in net_rets]) - 1.0) if net_rets else 0.0

                    equity_curve = np.cumprod([1.0 + r for r in net_rets])
                    running_max = np.maximum.accumulate(equity_curve)
                    dd = (running_max - equity_curve) / running_max
                    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

                    win_rate = float(np.mean([1.0 if r > 0 else 0.0 for r in net_rets]) * 100.0) if net_rets else 0.0

                    trades_per_year = 250.0 / h
                    mean_r = float(np.mean(net_rets)) if net_rets else 0.0
                    std_r = float(np.std(net_rets)) if len(net_rets) > 1 else 1.0
                    rf_per_trade = 0.065 / trades_per_year
                    sharpe = float((mean_r - rf_per_trade) / std_r * math.sqrt(trades_per_year)) if std_r > 0 else 0.0

                    pos_sum = sum(r for r in net_rets if r > 0)
                    neg_sum = abs(sum(r for r in net_rets if r < 0))
                    profit_factor = round(pos_sum / neg_sum, 2) if neg_sum > 0 else (999.0 if pos_sum > 0 else 0.0)

                    results[f"T+{h}"][scenario_key][strat][f"{f_bps}_bps"] = {
                        "cumulative_net_return_pct": round(cum_ret * 100.0, 2),
                        "annualized_sharpe_ratio": round(sharpe, 2),
                        "max_drawdown_pct": round(max_dd * 100.0, 2),
                        "win_rate_pct": round(win_rate, 2),
                        "profit_factor": profit_factor,
                        "trades_evaluated": len(net_rets),
                    }

                for ts, f_bps in ticket_friction_map.items():
                    friction_dec = f_bps / 10000.0
                    net_rets = [r - friction_dec for r in gross_rets]
                    cum_ret = float(np.prod([1.0 + r for r in net_rets]) - 1.0) if net_rets else 0.0

                    equity_curve = np.cumprod([1.0 + r for r in net_rets])
                    running_max = np.maximum.accumulate(equity_curve)
                    dd = (running_max - equity_curve) / running_max
                    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

                    win_rate = float(np.mean([1.0 if r > 0 else 0.0 for r in net_rets]) * 100.0) if net_rets else 0.0

                    trades_per_year = 250.0 / h
                    mean_r = float(np.mean(net_rets)) if net_rets else 0.0
                    std_r = float(np.std(net_rets)) if len(net_rets) > 1 else 1.0
                    rf_per_trade = 0.065 / trades_per_year
                    sharpe = float((mean_r - rf_per_trade) / std_r * math.sqrt(trades_per_year)) if std_r > 0 else 0.0

                    pos_sum = sum(r for r in net_rets if r > 0)
                    neg_sum = abs(sum(r for r in net_rets if r < 0))
                    profit_factor = round(pos_sum / neg_sum, 2) if neg_sum > 0 else (999.0 if pos_sum > 0 else 0.0)

                    results[f"T+{h}"][scenario_key][strat][f"ticket_{ts}"] = {
                        "ticket_size_inr": ts,
                        "effective_friction_bps": f_bps,
                        "cumulative_net_return_pct": round(cum_ret * 100.0, 2),
                        "annualized_sharpe_ratio": round(sharpe, 2),
                        "max_drawdown_pct": round(max_dd * 100.0, 2),
                        "win_rate_pct": round(win_rate, 2),
                        "profit_factor": profit_factor,
                        "trades_evaluated": len(net_rets),
                    }

    top10_t5 = results["T+5"]["Top_10"]
    comparison_table = []
    for s in strategies:
        metrics = top10_t5[s]["45_bps"]
        comparison_table.append({
            "strategy": s,
            "cumulative_net_return_pct": metrics["cumulative_net_return_pct"],
            "annualized_sharpe_ratio": metrics["annualized_sharpe_ratio"],
            "max_drawdown_pct": metrics["max_drawdown_pct"],
            "win_rate_pct": metrics["win_rate_pct"],
            "profit_factor": metrics["profit_factor"],
        })

    output_payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "evaluation_period": {
            "start_session": test_sessions[0],
            "end_session": test_sessions[-1],
            "total_test_sessions": total_test_sessions,
            "universe_equities": 500,
        },
        "friction_breakdown_rationale": {
            "0_bps": "Gross Theoretical (No Frictions)",
            "25_bps": "Institutional / High Liquidity Large-Cap",
            "45_bps": "Realistic Standard Indian Retail Delivery (Brokerage 6 bps + STT 20 bps + Statutory/DP 5 bps + Slippage 14 bps)",
            "65_bps": "Conservative Mid/Small-Cap Delivery (Brokerage 8 bps + STT 20 bps + Statutory/DP 7 bps + Slippage 30 bps)",
        },
        "order_level_ticket_size_frictions_bps": ticket_friction_map,
        "headline_comparison_top10_t5_45bps": comparison_table,
        "all_results": results,
    }

    out_file = REPO_ROOT / "docs" / "ml" / "hybrid_vs_ml_empirical_comparison.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    print(f"Empirical comparison complete. Output written to {out_file}")


if __name__ == "__main__":
    evaluate_strategies()
