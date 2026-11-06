"""Unit tests for IndianEquityCostEngine order-level accounting."""

import pytest
from workers.nse_market.order_cost_model import IndianEquityCostEngine


@pytest.fixture
def engine() -> IndianEquityCostEngine:
    return IndianEquityCostEngine()


def test_brokerage_below_cap(engine: IndianEquityCostEngine) -> None:
    # ₹10,000 order: 0.05% = ₹5.00 < ₹20 cap
    order = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=100.0, quantity=100)
    assert order.turnover == 10000.0
    assert order.brokerage == 5.0
    assert order.side == "BUY"


def test_brokerage_at_and_above_cap(engine: IndianEquityCostEngine) -> None:
    # ₹40,000 order: 0.05% = ₹20.00 (exact cap)
    order_at = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=100.0, quantity=400)
    assert order_at.brokerage == 20.0

    # ₹100,000 order: 0.05% = ₹50.00, capped strictly at ₹20.00
    order_above = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=100.0, quantity=1000)
    assert order_above.brokerage == 20.0


def test_buy_side_statutory_and_dp_charges(engine: IndianEquityCostEngine) -> None:
    order = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=500.0, quantity=100)
    # Buy side has Stamp duty (0.015% of ₹50,000 = ₹7.50)
    assert order.stamp_duty == 7.50
    # Buy side has ZERO DP charges
    assert order.dp_charges == 0.0
    # STT: 0.10% of ₹50,000 = ₹50.00
    assert order.stt == 50.0
    # Net cash flow must be negative for BUY
    assert order.net_cash_flow < 0
    assert order.net_cash_flow == -(order.turnover + order.total_cost)


def test_sell_side_statutory_and_dp_charges(engine: IndianEquityCostEngine) -> None:
    order = engine.calculate_order("NSE_EQ|INE002A01018", "SELL", price=500.0, quantity=100)
    # Sell side has ZERO Stamp duty
    assert order.stamp_duty == 0.0
    # Sell side has fixed DP charge ₹15.93
    assert order.dp_charges == 15.93
    # STT: 0.10% of ₹50,000 = ₹50.00
    assert order.stt == 50.0
    # Net cash flow must be positive for SELL
    assert order.net_cash_flow > 0
    assert order.net_cash_flow == order.turnover - order.total_cost


def test_gst_calculation_precision(engine: IndianEquityCostEngine) -> None:
    # GST is 18% of (Brokerage + Exchange + SEBI)
    order = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=250.0, quantity=200)
    expected_base = order.brokerage + order.exchange_charges + order.sebi_charges
    expected_gst = round(0.18 * expected_base, 2)
    assert order.gst == expected_gst


def test_complete_roundtrip_reconciliation(engine: IndianEquityCostEngine) -> None:
    # Buy 100 shares at ₹100, sell at ₹110
    rt = engine.calculate_roundtrip("NSE_EQ|INE002A01018", buy_price=100.0, sell_price=110.0, quantity=100)
    assert rt["gross_profit_inr"] == 1000.0
    assert rt["gross_return_pct"] == 10.0
    assert rt["net_profit_inr"] < 1000.0
    assert rt["net_profit_inr"] == round(rt["gross_profit_inr"] - rt["costs"]["total_costs_inr"], 2)


def test_zero_and_invalid_order_handling(engine: IndianEquityCostEngine) -> None:
    zero_qty = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=100.0, quantity=0)
    assert zero_qty.total_cost == 0.0
    assert zero_qty.net_cash_flow == 0.0

    neg_price = engine.calculate_order("NSE_EQ|INE002A01018", "BUY", price=-50.0, quantity=10)
    assert neg_price.total_cost == 0.0
    assert neg_price.net_cash_flow == 0.0


def test_ticket_size_exact_friction_bounds(engine: IndianEquityCostEngine) -> None:
    # 1. ₹10,000 ticket
    rt_10k = engine.calculate_roundtrip("TEST", buy_price=100.0, sell_price=100.0, quantity=100)
    assert rt_10k["costs"]["total_costs_inr"] == 63.97
    assert rt_10k["roundtrip_friction_bps"] == 63.97

    # 2. ₹25,000 ticket
    rt_25k = engine.calculate_roundtrip("TEST", buy_price=100.0, sell_price=100.0, quantity=250)
    assert rt_25k["costs"]["total_costs_inr"] == 135.98
    assert rt_25k["roundtrip_friction_bps"] == 54.39

    # 3. ₹50,000 ticket
    rt_50k = engine.calculate_roundtrip("TEST", buy_price=100.0, sell_price=100.0, quantity=500)
    assert rt_50k["costs"]["total_costs_inr"] == 244.27
    assert rt_50k["roundtrip_friction_bps"] == 48.85

    # 4. ₹100,000 ticket
    rt_100k = engine.calculate_roundtrip("TEST", buy_price=100.0, sell_price=100.0, quantity=1000)
    assert rt_100k["costs"]["total_costs_inr"] == 425.37
    assert rt_100k["roundtrip_friction_bps"] == 42.54

    # 5. ₹500,000 ticket
    rt_500k = engine.calculate_roundtrip("TEST", buy_price=100.0, sell_price=100.0, quantity=5000)
    assert rt_500k["costs"]["total_costs_inr"] == 1874.35
    assert rt_500k["roundtrip_friction_bps"] == 37.49


def test_multiple_orders_fixed_dp_charge_per_scrip(engine: IndianEquityCostEngine) -> None:
    # DP charge is ₹15.93 per unique ISIN sold per day from Demat
    # Multiple sells of SAME scrip: first order incurs DP charge, second does not if apply_dp_charge=False
    sell1 = engine.calculate_order("TEST", "SELL", price=100.0, quantity=50, apply_dp_charge=True)
    assert sell1.dp_charges == 15.93

    sell2 = engine.calculate_order("TEST", "SELL", price=100.0, quantity=50, apply_dp_charge=False)
    assert sell2.dp_charges == 0.0
