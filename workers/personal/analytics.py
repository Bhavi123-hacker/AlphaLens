"""Exact P15 accounting plus explicitly indicative marks and descriptive diagnostics."""

import math
import statistics
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_portfolio.accounting import reconstruct
from alphalens_portfolio.contracts import Ledger

from .contracts import UNSUPPORTED, Profile, Scenario, amount

IST = ZoneInfo("Asia/Kolkata")


def money(value: Fraction) -> str:
    """Exact half-up display; the rational value remains in *_exact fields."""
    scaled = abs(value) * 100
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    whole += remainder * 2 >= scaled.denominator
    return ("-" if value < 0 else "") + f"{whole // 100}.{whole % 100:02d}"


def observed(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Observed-slot raw-price diagnostics, never total economic performance."""
    good = [r for r in rows if r.get("close") is not None]
    missing = len(rows) - len(good)
    moves: list[float] = []
    peak: Fraction | None = None
    maximum_drawdown = Fraction(0)
    previous: Fraction | None = None
    for row in rows:
        close = Fraction(str(row["close"])) if row.get("close") is not None else None
        if close is not None and close <= 0:
            raise ValueError("POSITIVE_OBSERVED_PRICE_REQUIRED")
        if close is not None:
            peak = max(peak or close, close)
            maximum_drawdown = min(maximum_drawdown, close / peak - 1)
            if previous is not None:
                moves.append(float(close / previous - 1))
        previous = close
    complete = bool(rows) and not missing
    total = (
        Fraction(str(good[-1]["close"])) / Fraction(str(good[0]["close"])) - 1 if complete else None
    )
    vol = statistics.stdev(moves) if len(moves) >= 2 and complete else None
    mean = statistics.mean(moves) if moves and complete else None
    volume = good[-1].get("volume") if good else None
    prior_volumes = [r["volume"] for r in rows[-21:-1] if r.get("volume") is not None]
    return {
        "sample_count": len(rows),
        "observed_count": len(good),
        "missing_count": missing,
        "first_session": rows[0]["session"] if rows else None,
        "last_session": rows[-1]["session"] if rows else None,
        "price_return_percent": float(total * 100) if total is not None else None,
        "maximum_drawdown_percent": float(maximum_drawdown * 100) if complete else None,
        "daily_volatility_percent": vol * 100 if vol is not None else None,
        "mean_daily_return_over_volatility": mean / vol if mean is not None and vol else None,
        "positive_period_fraction": sum(x > 0 for x in moves) / len(moves)
        if moves and complete
        else None,
        "volume": volume,
        "relative_volume": volume / statistics.mean(prior_volumes)
        if volume is not None and len(prior_volumes) == 20 and statistics.mean(prior_volumes) > 0
        else None,
        "interpretation": "OBSERVED_SLOT_RAW_PRICE_DIAGNOSTICS_NOT_TOTAL_RETURN_OR_SHARPE",
        "corporate_actions": "UNVERIFIED",
        "calendar_completeness": "UNVERIFIED",
    }


def latest_indicator(item: dict[str, Any], name: str) -> float | None:
    points = item.get("indicators", {}).get(name, {}).get("points", [])
    value = points[-1].get("value") if points else None
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def provider_request_failed(item: dict[str, Any] | None) -> bool | None:
    """Absence/expiry or clock rejection is not evidence of a connection outage."""
    if item is None:
        return None
    state = item.get("quote", {}).get("state")
    if state in {
        "AUTH_REJECTED",
        "PERMISSION_OR_SEGMENT_REJECTED",
        "RATE_LIMITED",
        "PROVIDER_OUTAGE",
        "NETWORK_UNAVAILABLE",
        "DNS_UNAVAILABLE",
        "TLS_REJECTED",
        "REQUEST_REJECTED",
    }:
        return True
    if state == "VALIDATED_SNAPSHOT":
        return False
    return None


def mark(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {
            "price": None,
            "basis": "UNAVAILABLE",
            "session": None,
            "source": None,
            "freshness": "UNAVAILABLE",
        }
    quote = item["quote"]
    expiry = max(0, item.get("cache_ttl_seconds", 600) - item.get("cache_age_seconds", 0))
    if quote["state"] == "VALIDATED_SNAPSHOT":
        return {
            "price": quote["ltp"],
            "basis": "LTP_SNAPSHOT",
            "session": quote["last_trade_at"],
            "source": "UPSTOX_FULL_QUOTE_V3",
            "freshness": quote["freshness"],
            "quote_timestamp": quote["snapshot_at"],
            "expires_in_seconds": expiry,
        }
    if item.get("latest_close") is not None:
        return {
            "price": item["latest_close"],
            "basis": "PROVIDER_EOD_CANDLE_NOT_LTP",
            "session": item["latest_session"],
            "source": item["source"],
            "freshness": "DATED_PROVIDER_CANDLE",
            "quote_state": quote["state"],
            "expires_in_seconds": expiry,
        }
    return {
        "price": None,
        "basis": "UNAVAILABLE",
        "session": None,
        "source": "UPSTOX",
        "freshness": quote["state"],
    }


def preference_match(profile: Profile, metrics: dict[str, Any]) -> dict[str, Any]:
    matched: list[str] = []
    excluded: list[str] = []
    missing: list[str] = []
    constraints = (
        (
            "minimum_momentum_percent",
            metrics.get("price_return_percent"),
            float(profile.minimum_momentum_percent)
            if profile.minimum_momentum_percent is not None
            else None,
            "min",
        ),
        (
            "minimum_rsi",
            metrics.get("rsi_14"),
            float(profile.minimum_rsi) if profile.minimum_rsi is not None else None,
            "min",
        ),
        (
            "maximum_rsi",
            metrics.get("rsi_14"),
            float(profile.maximum_rsi) if profile.maximum_rsi is not None else None,
            "max",
        ),
        (
            "one_share_gross_research_budget_cap",
            metrics.get("gross_price"),
            float(
                Decimal(profile.budget_inr)
                * Decimal(profile.maximum_stock_allocation_percent)
                / 100
            )
            if profile.budget_inr is not None
            else None,
            "max",
        ),
        (
            "maximum_drawdown_percent",
            metrics.get("maximum_drawdown_percent"),
            float(profile.maximum_drawdown_percent),
            "max_abs",
        ),
        ("minimum_volume", metrics.get("volume"), profile.minimum_volume, "min"),
        (
            "maximum_daily_volatility_percent",
            metrics.get("daily_volatility_percent"),
            float(profile.maximum_daily_volatility_percent)
            if profile.maximum_daily_volatility_percent
            else None,
            "max",
        ),
    )
    for name, actual, threshold, direction in constraints:
        if threshold is None:
            continue
        if actual is None:
            missing.append(name)
        elif (
            (abs(actual) if direction == "max_abs" else actual) > threshold
            if direction != "min"
            else actual < threshold
        ):
            excluded.append(name)
        else:
            matched.append(name)
    if profile.technical_condition != "Any":
        name = profile.technical_condition
        value = metrics.get("sma_distance" if name == "ABOVE_SMA20" else "macd")
        (missing if value is None else matched if value > 0 else excluded).append(name)
    unsupported = ["RISK_TOLERANCE_CATEGORY_CALIBRATION"]
    if profile.preferred_sectors or profile.avoided_sectors:
        sector = metrics.get("provider_current_sector")
        if sector is None:
            unsupported.append("VERIFIED_SECTORS")
        else:
            if profile.preferred_sectors:
                (
                    matched
                    if sector.casefold() in {s.casefold() for s in profile.preferred_sectors}
                    else excluded
                ).append("PREFERRED_PROVIDER_CURRENT_SECTOR")
            if profile.avoided_sectors:
                (
                    excluded
                    if sector.casefold() in {s.casefold() for s in profile.avoided_sectors}
                    else matched
                ).append("AVOIDED_PROVIDER_CURRENT_SECTOR")
    if profile.market_caps:
        unsupported.append("MARKET_CAP")
    if profile.dividend_preference != "Any":
        unsupported.append("DIVIDENDS")
    if profile.style != "Any":
        unsupported.append("PIT_FUNDAMENTALS_GROWTH_VALUE")
    return {
        "state": "EXCLUDED_BY_SUPPORTED_CONSTRAINT"
        if excluded
        else "INSUFFICIENT_EVIDENCE"
        if missing
        else "MATCHES_SUPPORTED_CONSTRAINTS",
        "matched": matched,
        "excluded": excluded,
        "missing": missing,
        "unsupported": unsupported,
        "risk_tolerance": profile.risk_tolerance,
        "risk_tolerance_calibration": "UNAVAILABLE_NOT_A_VALIDATED_RISK_CLASS",
        "all_preferences_verified": not (missing or excluded or unsupported),
    }


def candidate(item: dict[str, Any], profile: Profile) -> dict[str, Any]:
    count = {"Short": 20, "Medium": 60, "Long": 252}[profile.horizon]
    metrics = observed(item.get("rows", [])[-count:])
    metrics["requested_observation_slots"] = count
    sector_evidence = item.get("provider_sector_evidence")
    metrics["provider_current_sector"] = sector_evidence["value"] if sector_evidence else None
    if not item.get("rows") and item["quote"].get("volume") is not None:
        metrics["volume"] = item["quote"]["volume"]
    metrics.update(
        {
            "gross_price": float(mark(item)["price"]) if mark(item)["price"] is not None else None,
            "rsi_14": latest_indicator(item, "rsi_14"),
            "macd": latest_indicator(item, "macd"),
            "sma_distance": latest_indicator(item, "distance_sma_20"),
        }
    )
    observations = []
    if metrics["price_return_percent"] is not None:
        observations.append(
            "POSITIVE_OBSERVED_PRICE_MOMENTUM"
            if metrics["price_return_percent"] > 0
            else "NONPOSITIVE_OBSERVED_PRICE_MOMENTUM"
        )
    if metrics["rsi_14"] is not None:
        observations.append(
            "RSI_ABOVE_70_DESCRIPTIVE"
            if metrics["rsi_14"] > 70
            else "RSI_BELOW_30_DESCRIPTIVE"
            if metrics["rsi_14"] < 30
            else "RSI_BETWEEN_30_AND_70_DESCRIPTIVE"
        )
    preferences = preference_match(profile, metrics)
    if metrics["sample_count"] < count:
        preferences["missing"].append("SUFFICIENT_HORIZON_OBSERVATIONS")
        if not preferences["excluded"]:
            preferences["state"] = "INSUFFICIENT_EVIDENCE"
    return {
        "instrument_key": item["instrument_key"],
        "symbol": item["symbol"],
        "mark": mark(item),
        "metrics": metrics,
        "provider_sector_evidence": sector_evidence,
        "preferences": preferences,
        "technical_observations": observations,
        "current_ml": "UNAVAILABLE",
        "confidence": None,
        "source": item["source"],
        "evidence_link": "/stocks/" + "upstox:" + item["instrument_key"],
        "missing_evidence": list(UNSUPPORTED),
    }


def portfolio_review(
    value: dict[str, Any],
    profile: Profile,
    items: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    at = now or datetime.now(UTC)
    ledger = Ledger.model_validate(value["ledger"])
    state = reconstruct(ledger, at.astimezone(IST).date(), at)
    held = [p for p in state.positions if p.quantity > 0]
    total_basis = sum((p.cost_basis for p in held), Fraction(0))
    records: list[dict[str, Any]] = []
    for position in state.positions:
        key = position.security_id.removeprefix("upstox:")
        item = items.get(key)
        price_mark = mark(item) if position.quantity else mark(None)
        price_value = Fraction(price_mark["price"]) if price_mark["price"] else None
        marked = position.quantity * price_value if price_value is not None else None
        weight = (
            position.cost_basis / total_basis * 100
            if total_basis and position.quantity
            else Fraction(0)
        )
        diagnostics = []
        if weight > Fraction(profile.maximum_stock_allocation_percent):
            diagnostics.append("CONCENTRATION_RISK")
        count = {"Short": 20, "Medium": 60, "Long": 252}[profile.horizon]
        metrics = observed(item.get("rows", [])[-count:]) if item else observed([])
        sector_evidence = item.get("provider_sector_evidence") if item else None
        metrics["provider_current_sector"] = sector_evidence["value"] if sector_evidence else None
        metrics["gross_price"] = (
            float(price_mark["price"]) if price_mark["price"] is not None else None
        )
        match = preference_match(profile, metrics)
        if "maximum_daily_volatility_percent" in match["excluded"]:
            diagnostics.append("VOLATILITY_REVIEW")
        if "maximum_drawdown_percent" in match["excluded"]:
            diagnostics.append("DRAWDOWN_REVIEW")
        if metrics.get("price_return_percent") is not None and metrics["price_return_percent"] < 0:
            diagnostics.append("DECLINING_OBSERVED_MOMENTUM")
        if position.quantity and price_value is None or position.quantity and match["missing"]:
            diagnostics.append("INSUFFICIENT_EVIDENCE")
        if price_mark["freshness"] == "OLDER_TRADE":
            diagnostics.append("DATA_TOO_STALE")
        if not diagnostics and position.quantity:
            diagnostics.append("HOLDING_WITHIN_APPLIED_USER_LIMITS")
        details = [
            d for d in value["manual_details"].values() if d["entered"].get("instrument_key") == key
        ]
        records.append(
            {
                "instrument_key": key,
                "symbol": position.transaction_symbol,
                "quantity": str(position.quantity),
                "cost_basis": money(position.cost_basis),
                "cost_basis_exact": str(position.cost_basis),
                "average_cost": money(position.cost_basis / position.quantity)
                if position.quantity
                else None,
                "realized_pnl": money(position.realized_pnl),
                "realized_pnl_exact": str(position.realized_pnl),
                "mark": price_mark,
                "indicative_market_value": money(marked) if marked is not None else None,
                "indicative_market_value_exact": str(marked) if marked is not None else None,
                "indicative_unrealized_pnl": money(marked - position.cost_basis)
                if marked is not None
                else None,
                "indicative_unrealized_percent": float((marked / position.cost_basis - 1) * 100)
                if marked is not None and position.cost_basis
                else None,
                "cost_allocation_percent": float(weight),
                "diagnostics": diagnostics,
                "metrics": metrics,
                "provider_sector_evidence": sector_evidence,
                "preference_match": match,
                "lots": [lot.model_dump(mode="json") for lot in position.lots],
                "fees_complete": all(d["entered"]["fees_known"] for d in details),
                "corporate_actions": "UNRECONCILED_OPERATOR_DECLARED_QUANTITY",
                "sector": None,
            }
        )
    priced = [
        r
        for r in records
        if Fraction(r["quantity"]) > 0 and r["indicative_market_value_exact"] is not None
    ]
    sector_weights: dict[str, float] = {}
    sector_covered = 0
    for record in records:
        if Fraction(record["quantity"]) > 0 and record.get("provider_sector_evidence"):
            sector_covered += 1
            sector = record["provider_sector_evidence"]["value"]
            sector_weights[sector] = (
                sector_weights.get(sector, 0) + record["cost_allocation_percent"]
            )
    for record in records:
        if record.get("provider_sector_evidence") and sector_weights.get(
            record["provider_sector_evidence"]["value"], 0
        ) > float(profile.maximum_sector_exposure_percent):
            record["diagnostics"].append("PROVIDER_CURRENT_SECTOR_COST_CONCENTRATION_REVIEW")
    complete_marks = len(priced) == len(held)
    total_marked = sum((Fraction(r["indicative_market_value_exact"]) for r in priced), Fraction(0))
    realized = sum((p.realized_pnl for p in state.positions), Fraction(0))
    return {
        "portfolio_id": ledger.portfolio.portfolio_id,
        "name": ledger.portfolio.portfolio_name,
        "ledger_state_id": state.ledger_state_id,
        "classification": "USER_RECORDED_NOT_BROKER_VERIFIED",
        "recorded_at": at.isoformat(),
        "holdings": records,
        "remaining_cost_basis": money(total_basis),
        "remaining_cost_basis_exact": str(total_basis),
        "realized_pnl": money(realized),
        "realized_pnl_exact": str(realized),
        "indicative_holdings_value": money(total_marked) if complete_marks else None,
        "indicative_unrealized_pnl": money(total_marked - total_basis) if complete_marks else None,
        "indicative_holdings_value_exact": str(total_marked) if complete_marks else None,
        "priced_holdings": len(priced),
        "holding_count": len(held),
        "all_holdings_marked": complete_marks,
        "ledger_cash": money(state.cash),
        "cash_balance": None,
        "cash_reason": "ACQUISITION_FUNDING_AND_EXTERNAL_BANK_BALANCE_NOT_RECONSTRUCTED",
        "net_declared_capital": money(state.net_external_capital),
        "portfolio_value": None,
        "portfolio_drawdown": None,
        "sector_allocation": None,
        "provider_current_sector_cost_allocation": sector_weights,
        "provider_sector_coverage": {
            "classified_holdings": sector_covered,
            "holding_count": len(held),
            "complete_current_coverage": sector_covered == len(held) and bool(held),
            "historical_taxonomy_verified": False,
        },
        "valuation_status": "INDICATIVE_UNRECONCILED_ACTIONS_NOT_P15_ACCEPTED_VALUATION"
        if complete_marks and held
        else "INSUFFICIENT_PRICE_EVIDENCE",
        "transactions": [t.model_dump(mode="json") for t in ledger.transactions],
        "manual_details": value["manual_details"],
        "diversification": "SINGLE_STOCK_CONCENTRATION"
        if len(held) == 1
        else "SECTOR_DIVERSIFICATION_UNVERIFIED",
        "current_ml": "UNAVAILABLE",
        "unsupported": list(UNSUPPORTED),
        "disclaimer": (
            "Exact original P15 FIFO accounting. Provider marks are indicative and transient; "
            "purchase quantities, costs and unreconciled actions are operator-declared. "
            "No buy/sell instruction or total economic performance claim."
        ),
    }


def simulate(
    review: dict[str, Any], scenario: Scenario, items: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    shock = Fraction(scenario.shock_percent)
    if not -100 <= shock <= 100:
        raise ValueError("SHOCK_RANGE_MINUS100_TO100_REQUIRED")
    weights = {k: Fraction(amount(v, maximum="100")) for k, v in scenario.target_weights.items()}
    if sum(weights.values()) > 100:
        raise ValueError("TARGET_WEIGHTS_EXCEED_100_PERCENT")
    quantities = {
        r["instrument_key"]: Fraction(r["quantity"])
        for r in review["holdings"]
        if Fraction(r["quantity"]) > 0
    }
    if scenario.instrument_key:
        delta = Fraction(scenario.quantity_delta)
        if delta.denominator != 1:
            raise ValueError("WHOLE_SHARE_SCENARIO_REQUIRED")
        quantities[scenario.instrument_key] = (
            quantities.get(scenario.instrument_key, Fraction(0)) + delta
        )
    elif Fraction(scenario.quantity_delta):
        raise ValueError("SCENARIO_INSTRUMENT_REQUIRED")
    if any(q < 0 for q in quantities.values()):
        raise ValueError("HYPOTHETICAL_NO_SHORT_SELLING")
    rows = []
    for key, quantity in quantities.items():
        price_mark = mark(items.get(key))
        value = quantity * Fraction(price_mark["price"]) if price_mark["price"] else None
        shocked = value * (1 + shock / 100) if value is not None else None
        rows.append(
            {
                "instrument_key": key,
                "quantity": str(quantity),
                "base_value": money(value) if value is not None else None,
                "shocked_value": money(shocked) if shocked is not None else None,
                "shocked_value_exact": str(shocked) if shocked is not None else None,
                "source": price_mark,
            }
        )
    total = (
        sum(
            (
                Fraction(r["shocked_value_exact"])
                for r in rows
                if r["shocked_value_exact"] is not None
            ),
            Fraction(0),
        )
        if all(r["shocked_value_exact"] is not None for r in rows)
        else None
    )
    trade_flow: Fraction | None = -Fraction(scenario.transaction_cost_inr)
    if scenario.instrument_key and Fraction(scenario.quantity_delta):
        trade_mark = mark(items.get(scenario.instrument_key))
        trade_flow = (
            (
                -Fraction(scenario.quantity_delta)
                * Fraction(trade_mark["price"])
                * (1 + shock / 100)
                - Fraction(scenario.transaction_cost_inr)
            )
            if trade_mark["price"] is not None
            else None
        )
    return {
        "classification": "HYPOTHETICAL_NOT_ORDERS_OR_RECORDED_HOLDINGS",
        "ledger_state_id": review["ledger_state_id"],
        "holdings": rows,
        "shock_percent": scenario.shock_percent,
        "cash_delta": scenario.cash_delta,
        "shocked_holdings_value": money(total) if total is not None else None,
        "target_allocations": {
            k: money(total * w / 100) if total is not None else None for k, w in weights.items()
        },
        "target_cash_weight_percent": str(100 - sum(weights.values())) if weights else None,
        "shocked_holdings_plus_cash_delta": (
            money(total + Fraction(scenario.cash_delta) - Fraction(scenario.transaction_cost_inr))
            if total is not None
            else None
        ),
        "transaction_cost_inr": scenario.transaction_cost_inr,
        "hypothetical_trade_cash_flow": money(trade_flow) if trade_flow is not None else None,
        "remaining_holdings_plus_trade_flow_and_declared_cash": money(
            total + trade_flow + Fraction(scenario.cash_delta)
        )
        if total is not None and trade_flow is not None
        else None,
        "cash_flow_interpretation": "HYPOTHETICAL_PROCEEDS_OR_FUNDING_NOT_ACTUAL_BANK_CASH",
        "cost_basis": "USER_DECLARED_SCENARIO_COST_NOT_VERIFIED_BROKER_TARIFF",
        "writes_performed": False,
        "assumptions": [
            "STATIC_OPERATOR_DECLARED_QUANTITIES",
            "UNIFORM_USER_DEFINED_PRICE_SHOCK",
            "USER_DECLARED_COSTS_NO_ORDERS",
            "ACTION_BASIS_UNRECONCILED",
            "TARGET_WEIGHTS_EDUCATIONAL_NOT_ADVICE",
        ],
    }
