"""Reconcile trade-level cash flows, exact rupee transaction fees, and market-regime protection.

Evaluates on verified historical NSE dataset (500 equities, 120 sessions):
1. Exact Portfolio Cash Flow Ledger with discrete shares, order fees, cash balances.
2. Reconciliation of original reported returns (-20.46% at 45 bps vs -21.00% at ₹50k ticket).
3. Evaluation of Market-Regime Protection Filter (Cash Conservation during market downturn).
4. Outputs comprehensive reconciliation artifact to release/alphalens_portfolio_cashflow_reconciliation.json.
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
    """Load verified market view with 500 stocks and 120 sessions."""
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


def run_reconciliation() -> None:
    print("Loading market data...")
    sessions, histories, ml_scores = load_market_data()
    print(f"Loaded {len(sessions)} sessions across {len(histories)} stocks.")

    STARTING_CAPITAL = 500000.0  # ₹5,00,000 portfolio (₹50k per stock for Top 10)
    HORIZON = 5
    TOP_N = 10
    cost_engine = IndianEquityCostEngine()

    # Precompute prices: session -> isin -> (open, close)
    session_prices: dict[str, dict[str, tuple[float, float]]] = {}
    for s in sessions:
        session_prices[s] = {}
        for k, bars in histories.items():
            for b in bars:
                d = str(b.get("session") or b.get("date") or b.get("timestamp", "")[:10])
                if d == s:
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

    # Strategy score selectors
    strategies = [
        "HYBRID_INTELLIGENCE",
        "ML_ONLY",
        "TECHNICAL_ONLY",
        "MOMENTUM_BASELINE",
        "UNIVERSE_EQUAL_WEIGHT",
        "HYBRID_REGIME_PROTECTED",  # Cash Conservation when broad market in downtrend
    ]

    # Precompute broad market trend for regime filter
    # Broad market indicator: % of universe stocks trading above their 20-day SMA at decision date
    market_breadth_above_sma20: dict[str, float] = {}
    for s_idx in range(36, len(sessions)):
        s_date = sessions[s_idx]
        count_above = 0
        total_counted = 0
        for k, bars in histories.items():
            closes_until = [float(b["close"]) for b in bars if str(b.get("session") or b.get("date") or b.get("timestamp", "")[:10]) <= s_date and b.get("close") is not None]
            if len(closes_until) >= 20:
                sma20 = np.mean(closes_until[-20:])
                if closes_until[-1] > sma20:
                    count_above += 1
                total_counted += 1
        pct_above = (count_above / total_counted * 100.0) if total_counted > 0 else 50.0
        market_breadth_above_sma20[s_date] = pct_above

    trade_ledgers: dict[str, list[dict[str, Any]]] = {s: [] for s in strategies}
    portfolio_equity_curves: dict[str, list[dict[str, Any]]] = {s: [{"session": sessions[36], "equity": STARTING_CAPITAL, "cash": STARTING_CAPITAL}] for s in strategies}

    # Step through test period: indices 36 to 119 step 5 (16 cycles)
    cycle_indices = list(range(36, len(sessions) - HORIZON, HORIZON))
    print(f"Evaluating {len(cycle_indices)} non-overlapping cycles from {sessions[cycle_indices[0]]} to {sessions[cycle_indices[-1]]}...")

    # Current capital tracking for each strategy
    current_equity = {s: STARTING_CAPITAL for s in strategies}

    for cycle_num, idx in enumerate(cycle_indices, 1):
        dec_session = sessions[idx]
        exit_session = sessions[idx + HORIZON]

        eligible_keys = [k for k in histories.keys() if k in session_prices.get(dec_session, {}) and k in session_prices.get(exit_session, {})]

        # Calculate scores
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

            norm_ml = base_ml * 100.0
            norm_tech = tf["composite"]
            vol_penalty = min(20.0, tf["volatility"] * 4.0)
            hybrid = 0.40 * norm_ml + 0.35 * norm_tech + 0.25 * (mom * 100.0) - vol_penalty
            comb_scores[k] = hybrid

        # Selections for each strategy
        def pick_top(d: dict[str, float]) -> list[str]:
            return sorted(d.keys(), key=lambda x: d[x], reverse=True)[:TOP_N]

        selections: dict[str, list[str]] = {
            "HYBRID_INTELLIGENCE": pick_top(comb_scores),
            "ML_ONLY": pick_top(ml_ranks),
            "TECHNICAL_ONLY": pick_top(tech_scores),
            "MOMENTUM_BASELINE": pick_top(mom_scores),
            "UNIVERSE_EQUAL_WEIGHT": eligible_keys,  # All 500
        }

        # Check regime filter for cash conservation
        # If market breadth is deteriorating (< 35% stocks above 20-day SMA), preserve cash!
        breadth = market_breadth_above_sma20.get(dec_session, 50.0)
        is_bullish_regime = breadth >= 35.0

        if is_bullish_regime:
            selections["HYBRID_REGIME_PROTECTED"] = pick_top(comb_scores)
        else:
            selections["HYBRID_REGIME_PROTECTED"] = []  # 100% Cash mode!

        # Execute portfolio allocation for each strategy
        for strat in strategies:
            picks = selections[strat]
            capital_available = current_equity[strat]

            if not picks:
                # 100% Cash conservation
                trade_ledgers[strat].append({
                    "cycle_num": cycle_num,
                    "entry_session": dec_session,
                    "exit_session": exit_session,
                    "action": "CASH_CONSERVATION_MODE",
                    "stocks_held": 0,
                    "gross_return_pct": 0.0,
                    "net_return_pct": 0.0,
                    "rupee_costs": 0.0,
                    "start_equity": capital_available,
                    "end_equity": capital_available,
                })
                portfolio_equity_curves[strat].append({
                    "session": exit_session,
                    "equity": capital_available,
                    "cash": capital_available,
                })
                continue

            n_picks = len(picks)
            alloc_per_stock = capital_available / n_picks
            cycle_trades = []
            cycle_gross_profit = 0.0
            cycle_costs = 0.0
            unallocated_cash = 0.0

            for isin in picks:
                p_buy = session_prices[dec_session][isin][1]
                p_sell = session_prices[exit_session][isin][1]
                qty = int(alloc_per_stock / p_buy) if p_buy > 0 else 0

                if qty <= 0:
                    unallocated_cash += alloc_per_stock
                    continue

                actual_buy_turnover = qty * p_buy
                unallocated_cash += (alloc_per_stock - actual_buy_turnover)

                rt = cost_engine.calculate_roundtrip(isin, p_buy, p_sell, qty)
                cycle_trades.append({
                    "isin": isin,
                    "qty": qty,
                    "buy_price": p_buy,
                    "sell_price": p_sell,
                    "buy_turnover": actual_buy_turnover,
                    "sell_turnover": qty * p_sell,
                    "gross_profit_inr": rt["gross_profit_inr"],
                    "total_costs_inr": rt["costs"]["total_costs_inr"],
                    "net_profit_inr": rt["net_profit_inr"],
                    "effective_friction_bps": rt["roundtrip_friction_bps"],
                })
                cycle_gross_profit += rt["gross_profit_inr"]
                cycle_costs += rt["costs"]["total_costs_inr"]

            cycle_net_profit = cycle_gross_profit - cycle_costs
            new_equity = capital_available + cycle_net_profit
            current_equity[strat] = new_equity

            gross_ret_pct = (cycle_gross_profit / capital_available) * 100.0 if capital_available > 0 else 0.0
            net_ret_pct = (cycle_net_profit / capital_available) * 100.0 if capital_available > 0 else 0.0

            trade_ledgers[strat].append({
                "cycle_num": cycle_num,
                "entry_session": dec_session,
                "exit_session": exit_session,
                "action": "EQUITY_ALLOCATION",
                "stocks_held": len(cycle_trades),
                "gross_profit_inr": round(cycle_gross_profit, 2),
                "rupee_costs": round(cycle_costs, 2),
                "net_profit_inr": round(cycle_net_profit, 2),
                "gross_return_pct": round(gross_ret_pct, 4),
                "net_return_pct": round(net_ret_pct, 4),
                "start_equity": round(capital_available, 2),
                "end_equity": round(new_equity, 2),
                "trades": cycle_trades,
            })

            portfolio_equity_curves[strat].append({
                "session": exit_session,
                "equity": round(new_equity, 2),
                "cash": round(new_equity, 2),
            })

    # Summary reconciliation
    summary_table = []
    original_reported_45bps = {
        "HYBRID_INTELLIGENCE": -20.46,
        "ML_ONLY": -25.16,
        "TECHNICAL_ONLY": -15.82,
        "MOMENTUM_BASELINE": -16.51,
        "UNIVERSE_EQUAL_WEIGHT": -14.48,
        "HYBRID_REGIME_PROTECTED": "N/A (New Investigation)",
    }

    original_reported_ticket50k = {
        "HYBRID_INTELLIGENCE": -21.00,
        "ML_ONLY": -25.68,
        "TECHNICAL_ONLY": -16.38,
        "MOMENTUM_BASELINE": -17.06,
        "UNIVERSE_EQUAL_WEIGHT": -15.03,
        "HYBRID_REGIME_PROTECTED": "N/A (New Investigation)",
    }

    for s in strategies:
        final_eq = current_equity[s]
        net_ret_pct = ((final_eq - STARTING_CAPITAL) / STARTING_CAPITAL) * 100.0

        # Total rupee costs
        total_costs_inr = sum(c.get("rupee_costs", 0.0) for c in trade_ledgers[s])
        total_gross_profit = sum(c.get("gross_profit_inr", 0.0) for c in trade_ledgers[s])
        gross_ret_compounded = float(np.prod([1.0 + (c.get("gross_return_pct", 0.0) / 100.0) for c in trade_ledgers[s]]) - 1.0) * 100.0

        # Max Drawdown
        eq_series = [p["equity"] for p in portfolio_equity_curves[s]]
        running_max = np.maximum.accumulate(eq_series)
        dd = (running_max - eq_series) / running_max
        max_dd = float(np.max(dd)) * 100.0

        summary_table.append({
            "strategy": s,
            "starting_capital_inr": STARTING_CAPITAL,
            "final_equity_inr": round(final_eq, 2),
            "original_reported_45bps_pct": original_reported_45bps[s],
            "original_reported_50k_ticket_pct": original_reported_ticket50k[s],
            "actual_recomputed_gross_return_pct": round(gross_ret_compounded, 2),
            "actual_total_rupee_costs": round(total_costs_inr, 2),
            "actual_recomputed_net_return_pct": round(net_ret_pct, 2),
            "max_drawdown_pct": round(max_dd, 2),
        })

    # Prepare complete output artifact
    output = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "starting_capital_inr": STARTING_CAPITAL,
        "evaluation_period": {
            "start_session": sessions[36],
            "end_session": sessions[116],
            "total_cycles": len(cycle_indices),
            "holding_days_per_cycle": HORIZON,
        },
        "reconciliation_summary_table": summary_table,
        "portfolio_equity_curves": portfolio_equity_curves,
        "detailed_cycle_ledgers": {s: trade_ledgers[s] for s in strategies},
    }

    out_file = REPO_ROOT / "release" / "alphalens_portfolio_cashflow_reconciliation.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Reconciliation complete. Output written to {out_file}")

    print("\n--- RECONCILIATION SUMMARY TABLE ---")
    for r in summary_table:
        print(f"Strategy: {r['strategy']}")
        print(f"  Final Equity: INR {r['final_equity_inr']:,} | Net Return: {r['actual_recomputed_net_return_pct']}%")
        print(f"  Gross Return: {r['actual_recomputed_gross_return_pct']}% | Total Costs: INR {r['actual_total_rupee_costs']:,}")
        print(f"  Max Drawdown: {r['max_drawdown_pct']}%")
        print()


if __name__ == "__main__":
    run_reconciliation()
