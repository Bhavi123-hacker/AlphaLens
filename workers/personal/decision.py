"""Descriptive research desk; independent of frozen predictive decision policies."""

from fractions import Fraction
from typing import Any

from .analytics import candidate, mark, money, selected_mark
from .contracts import Profile, Scenario


def entry_desk(
    items: dict[str, dict[str, Any]], keys: tuple[str, ...], profile: Profile
) -> dict[str, Any]:
    rows = [candidate(items[k], profile) for k in keys if k in items]
    return {
        "classification": "DESCRIPTIVE_RESEARCH_NOT_BUY_SELL_ADVICE",
        "entries": [
            r for r in rows if r["preferences"]["state"] == "MATCHES_SUPPORTED_CONSTRAINTS"
        ],
        "exclusions": [
            r for r in rows if r["preferences"]["state"] != "MATCHES_SUPPORTED_CONSTRAINTS"
        ],
        "missing_instruments": [k for k in keys if k not in items],
        "applied_profile": profile.model_dump(),
        "current_ml_predictions": 0,
        "model_evidence": "/research",
        "model_acceptance": "INDEPENDENT_ACCEPTANCE_REQUIRED_ALL_38_FEATURES_AND_PEERS",
    }


def holding_thresholds(
    review: dict[str, Any],
    rules: list[dict[str, Any]],
    items: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Price rules supply explicit user targets/stops, never model-derived instructions."""
    for holding in review["holdings"]:
        holding["threshold_reviews"] = []
        if Fraction(holding["quantity"]) <= 0:
            continue
        for record in rules:
            rule = record["value"]
            if (
                not rule.get("enabled", True)
                or rule.get("instrument_key") != holding["instrument_key"]
                or rule.get("portfolio_id") not in {None, review["portfolio_id"]}
                or rule["kind"] not in {"PRICE_ABOVE", "PRICE_BELOW"}
            ):
                continue
            observation = (
                selected_mark(
                    items.get(holding["instrument_key"]),
                    rule.get("evidence_source", "LATEST_SUPPORTED"),
                )
                if items is not None
                else holding["mark"]
            )
            price = observation["price"]
            reached = price is not None and (
                Fraction(price) > Fraction(rule["threshold"])
                if rule["kind"] == "PRICE_ABOVE"
                else Fraction(price) < Fraction(rule["threshold"])
            )
            code = (
                "PRICE_TARGET_REACHED"
                if rule["kind"] == "PRICE_ABOVE"
                else "USER_RISK_THRESHOLD_REACHED"
            )
            holding["threshold_reviews"].append(
                {
                    "rule_id": record["id"],
                    "name": rule["name"],
                    "threshold": rule["threshold"],
                    "state": code
                    if reached
                    else "NOT_REACHED"
                    if price is not None
                    else "INSUFFICIENT_EVIDENCE",
                    "evidence": observation,
                }
            )
            if reached:
                holding["diagnostics"] = [
                    r for r in holding["diagnostics"] if r != "HOLDING_WITHIN_APPLIED_USER_LIMITS"
                ]
                holding["diagnostics"].append(code)
    return review


def exit_impact(
    value: dict[str, Any], scenario: Scenario, item: dict[str, Any] | None
) -> dict[str, Any]:
    """Reuse original P15 reconstruction for the hypothetical FIFO effect; zero writes."""
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    from alphalens_portfolio.accounting import append, reconstruct
    from alphalens_portfolio.contracts import Ledger, Transaction

    delta = Fraction(scenario.quantity_delta)
    indicative = mark(item)
    if delta >= 0 or not scenario.instrument_key or indicative["price"] is None:
        return {"state": "NO_REDUCTION_OR_PRICE_EVIDENCE", "writes_performed": False}
    at = datetime.now(UTC)
    session = at.astimezone(ZoneInfo("Asia/Kolkata")).date()
    ledger = Ledger.model_validate(value["ledger"])
    before = reconstruct(ledger, session, at)
    original = next(
        p for p in before.positions if p.security_id == "upstox:" + scenario.instrument_key
    )
    price = Fraction(indicative["price"]) * (1 + Fraction(scenario.shock_percent) / 100)
    if price <= 0:
        return {"state": "NONPOSITIVE_HYPOTHETICAL_EXECUTION_PRICE", "writes_performed": False}
    tx = Transaction(
        transaction_id="p33:hypothetical:reduction",
        portfolio_id=ledger.portfolio.portfolio_id,
        kind="SELL",
        security_id=original.security_id,
        symbol=original.transaction_symbol,
        session=session,
        effective_at=at,
        recorded_at=at,
        quantity=-delta,
        price=price,
        fees=Fraction(scenario.transaction_cost_inr),
        source="USER_HYPOTHETICAL_SCENARIO",
        classification="USER_RECORDED",
    )
    after = reconstruct(append(ledger, tx), session, at)
    position = next(p for p in after.positions if p.security_id == original.security_id)
    return {
        "state": "HYPOTHETICAL_P15_FIFO_NOT_REALIZED_ACTIVITY",
        "quantity_reduced": str(-delta),
        "remaining_quantity": str(position.quantity),
        "remaining_basis_exact": str(position.cost_basis),
        "fifo_realized_change_exact": str(position.realized_pnl - original.realized_pnl),
        "fifo_realized_change": money(position.realized_pnl - original.realized_pnl),
        "assumed_price": str(price),
        "declared_cost": scenario.transaction_cost_inr,
        "source": indicative,
        "writes_performed": False,
    }
