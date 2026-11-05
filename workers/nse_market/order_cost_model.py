"""Order-level statutory transaction cost and portfolio accounting engine for Indian Equities.

Models exact Indian cash delivery fee schedules:
1. Brokerage: Capped per executed order leg (min(₹20, 0.05% turnover) or configurable).
2. STT: 0.10% on Buy and 0.10% on Sell (Income Tax Act).
3. Exchange Transaction Charges: NSE 0.00297% per leg.
4. GST: 18% on (Brokerage + Exchange Charges + SEBI Charges).
5. Stamp Duty: 0.015% on Buy turnover only.
6. SEBI Turnover Fee: ₹10 per crore (0.0001% per leg).
7. DP Charges: ₹15.93 (₹13.50 + 18% GST) per unique ISIN sold per day from Demat.
8. Slippage: Modeled separately from statutory fees based on liquidity.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class OrderCostBreakdown:
    instrument: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    turnover: float
    brokerage: float
    stt: float
    exchange_charges: float
    gst: float
    stamp_duty: float
    sebi_charges: float
    dp_charges: float
    slippage: float
    statutory_total: float
    total_cost: float
    net_cash_flow: float  # Negative for BUY (cash outflow), Positive for SELL (cash inflow)
    effective_friction_bps: float


class IndianEquityCostEngine:
    """Calculates order-level rupee charges and portfolio cash flows."""

    def __init__(
        self,
        brokerage_rate: float = 0.0005,  # 0.05%
        brokerage_cap: float = 20.0,     # ₹20 cap
        dp_charge_per_scrip: float = 15.93, # ₹13.50 + 18% GST
        exchange_rate: float = 0.0000297,  # NSE 0.00297%
        stt_rate: float = 0.0010,        # 0.10% delivery
        stamp_duty_rate: float = 0.00015, # 0.015% buy
        sebi_rate: float = 0.0000010,     # ₹10 / crore
        gst_rate: float = 0.18,          # 18%
        default_slippage_bps: float = 7.0, # 7 bps each side = 14 bps roundtrip
    ) -> None:
        self.brokerage_rate = brokerage_rate
        self.brokerage_cap = brokerage_cap
        self.dp_charge_per_scrip = dp_charge_per_scrip
        self.exchange_rate = exchange_rate
        self.stt_rate = stt_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.sebi_rate = sebi_rate
        self.gst_rate = gst_rate
        self.default_slippage_bps = default_slippage_bps

    def calculate_order(
        self,
        instrument: str,
        side: Literal["BUY", "SELL"],
        price: float,
        quantity: int,
        slippage_bps: float | None = None,
        apply_dp_charge: bool = True,
    ) -> OrderCostBreakdown:
        if quantity <= 0 or price <= 0:
            return OrderCostBreakdown(
                instrument=instrument,
                side=side,
                price=max(0.0, price),
                quantity=max(0, quantity),
                turnover=0.0,
                brokerage=0.0,
                stt=0.0,
                exchange_charges=0.0,
                gst=0.0,
                stamp_duty=0.0,
                sebi_charges=0.0,
                dp_charges=0.0,
                slippage=0.0,
                statutory_total=0.0,
                total_cost=0.0,
                net_cash_flow=0.0,
                effective_friction_bps=0.0,
            )

        turnover = round(price * quantity, 2)
        slip_bps = slippage_bps if slippage_bps is not None else self.default_slippage_bps

        # 1. Brokerage with cap
        raw_brokerage = self.brokerage_rate * turnover
        brokerage = round(min(self.brokerage_cap, raw_brokerage), 2)

        # 2. STT (0.10% on delivery buy and sell)
        stt = round(self.stt_rate * turnover, 2)

        # 3. Exchange charges
        exchange = round(self.exchange_rate * turnover, 2)

        # 4. SEBI turnover fee
        sebi = round(self.sebi_rate * turnover, 2)

        # 5. Stamp duty (buy only)
        stamp = round(self.stamp_duty_rate * turnover, 2) if side == "BUY" else 0.0

        # 6. GST (18% on brokerage, exchange, and sebi charges)
        gst = round(self.gst_rate * (brokerage + exchange + sebi), 2)

        # 7. DP Charges (sell only)
        dp = round(self.dp_charge_per_scrip, 2) if (side == "SELL" and apply_dp_charge) else 0.0

        # 8. Slippage (separate from statutory fees)
        slippage = round((slip_bps / 10000.0) * turnover, 2)

        # Totals
        statutory = round(stt + exchange + stamp + sebi + gst, 2)
        total_cost = round(brokerage + statutory + dp + slippage, 2)

        if side == "BUY":
            net_cash_flow = -round(turnover + total_cost, 2)
        else:
            net_cash_flow = round(turnover - total_cost, 2)

        friction_bps = round((total_cost / turnover) * 10000.0, 2) if turnover > 0 else 0.0

        return OrderCostBreakdown(
            instrument=instrument,
            side=side,
            price=price,
            quantity=quantity,
            turnover=turnover,
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange,
            gst=gst,
            stamp_duty=stamp,
            sebi_charges=sebi,
            dp_charges=dp,
            slippage=slippage,
            statutory_total=statutory,
            total_cost=total_cost,
            net_cash_flow=net_cash_flow,
            effective_friction_bps=friction_bps,
        )

    def calculate_roundtrip(
        self,
        instrument: str,
        buy_price: float,
        sell_price: float,
        quantity: int,
        buy_slippage_bps: float | None = None,
        sell_slippage_bps: float | None = None,
    ) -> dict[str, Any]:
        """Calculate complete buy-to-sell roundtrip with exact fees and PnL."""
        buy = self.calculate_order(instrument, "BUY", buy_price, quantity, buy_slippage_bps)
        sell = self.calculate_order(instrument, "SELL", sell_price, quantity, sell_slippage_bps)

        gross_profit = round((sell_price - buy_price) * quantity, 2)
        total_costs = round(buy.total_cost + sell.total_cost, 2)
        net_profit = round(gross_profit - total_costs, 2)
        total_turnover = round(buy.turnover + sell.turnover, 2)

        gross_return_pct = round((gross_profit / buy.turnover) * 100.0, 2) if buy.turnover > 0 else 0.0
        net_return_pct = round((net_profit / abs(buy.net_cash_flow)) * 100.0, 2) if buy.net_cash_flow != 0 else 0.0
        total_friction_bps = round((total_costs / buy.turnover) * 10000.0, 2) if buy.turnover > 0 else 0.0

        return {
            "instrument": instrument,
            "quantity": quantity,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "gross_turnover_in": buy.turnover,
            "gross_turnover_out": sell.turnover,
            "total_turnover": total_turnover,
            "gross_profit_inr": gross_profit,
            "gross_return_pct": gross_return_pct,
            "buy_breakdown": asdict(buy),
            "sell_breakdown": asdict(sell),
            "costs": {
                "brokerage_inr": round(buy.brokerage + sell.brokerage, 2),
                "stt_inr": round(buy.stt + sell.stt, 2),
                "exchange_charges_inr": round(buy.exchange_charges + sell.exchange_charges, 2),
                "gst_inr": round(buy.gst + sell.gst, 2),
                "stamp_duty_inr": round(buy.stamp_duty + sell.stamp_duty, 2),
                "sebi_charges_inr": round(buy.sebi_charges + sell.sebi_charges, 2),
                "dp_charges_inr": round(buy.dp_charges + sell.dp_charges, 2),
                "slippage_inr": round(buy.slippage + sell.slippage, 2),
                "statutory_total_inr": round(buy.statutory_total + sell.statutory_total, 2),
                "total_costs_inr": total_costs,
            },
            "net_profit_inr": net_profit,
            "net_return_pct": net_return_pct,
            "roundtrip_friction_bps": total_friction_bps,
        }
