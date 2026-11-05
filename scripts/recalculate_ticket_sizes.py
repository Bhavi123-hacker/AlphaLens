"""Recalculate exact Indian equity delivery charges for various ticket sizes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from workers.nse_market.order_cost_model import IndianEquityCostEngine

def run() -> None:
    engine = IndianEquityCostEngine()
    ticket_sizes = [10_000, 25_000, 50_000, 100_000, 500_000]

    table = []
    for capital in ticket_sizes:
        # Buy at 100, sell at 100 (flat market to measure pure friction)
        qty = int(capital / 100.0)
        res = engine.calculate_roundtrip(
            instrument="NSE_EQ|INE002A01018",
            buy_price=100.0,
            sell_price=100.0,
            quantity=qty,
        )
        c = res["costs"]
        turnover = res["gross_turnover_in"]
        total_costs = c["total_costs_inr"]
        friction_bps = res["roundtrip_friction_bps"]

        row = {
            "ticket_size_inr": capital,
            "actual_turnover_inr": turnover,
            "brokerage_inr": c["brokerage_inr"],
            "brokerage_bps": round((c["brokerage_inr"] / turnover) * 10000.0, 2),
            "stt_inr": c["stt_inr"],
            "stt_bps": round((c["stt_inr"] / turnover) * 10000.0, 2),
            "dp_charges_inr": c["dp_charges_inr"],
            "dp_charges_bps": round((c["dp_charges_inr"] / turnover) * 10000.0, 2),
            "statutory_and_gst_inr": round(c["exchange_charges_inr"] + c["gst_inr"] + c["stamp_duty_inr"] + c["sebi_charges_inr"], 2),
            "statutory_and_gst_bps": round(((c["exchange_charges_inr"] + c["gst_inr"] + c["stamp_duty_inr"] + c["sebi_charges_inr"]) / turnover) * 10000.0, 2),
            "slippage_inr": c["slippage_inr"],
            "slippage_bps": round((c["slippage_inr"] / turnover) * 10000.0, 2),
            "total_costs_inr": total_costs,
            "total_friction_bps": friction_bps,
        }
        table.append(row)

    print(json.dumps(table, indent=2))
    out_file = Path("D:/al-research/p28-worktree/.campaign-worktree/release/alphalens_ticket_size_cost_matrix.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(table, indent=2), encoding="utf-8")
    print(f"Saved to {out_file}")

if __name__ == "__main__":
    run()
