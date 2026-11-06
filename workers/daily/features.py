"""Incremental bounded execution delegates all feature formulas to P6."""

from collections import defaultdict
from datetime import date, datetime
from typing import Any

import numpy as np

from alphalens_data.daily.contracts import Calendar
from alphalens_data.errors import DataContractError
from alphalens_features.models import BuildPlan, Decision, FeatureDefinition
from alphalens_features.registry import default_set
from alphalens_features.research import numerical, window_flag


def definitions(session: date, cutoff: datetime) -> tuple[FeatureDefinition, ...]:
    return default_set(
        BuildPlan(
            history_start=session,
            decisions=(Decision(session_date=session, knowledge_cutoff=cutoff),),
        )
    ).definitions


def update(
    current: list[dict[str, Any]],
    history: list[dict[str, Any]],
    calendar: Calendar,
    session: date,
    cutoff: datetime,
) -> dict[str, Any]:
    registry = definitions(session, cutoff)
    count = max(d.lookback for d in registry)
    dates = calendar.trailing(session, cutoff, count)
    index = {d: i for i, d in enumerate(dates)}
    grouped: dict[str, dict[date, dict[str, Any]]] = defaultdict(dict)
    affected = {r["security_id"] for r in current}
    for row in history:
        day = date.fromisoformat(str(row["session_date"]))
        if row["security_id"] not in affected or day not in index:
            continue
        if row.get("received_at") and datetime.fromisoformat(row["received_at"]) > cutoff:
            continue
        if day in grouped[row["security_id"]]:
            raise DataContractError("AMBIGUOUS_TRAILING_REVISION")
        grouped[row["security_id"]][day] = row
    for row in current:
        day = date.fromisoformat(str(row["session_date"]))
        if day in index and (
            not row.get("received_at") or datetime.fromisoformat(row["received_at"]) <= cutoff
        ):
            grouped[row["security_id"]][day] = row
    output = []
    for security in sorted(affected):
        rows = grouped[security]
        arrays = {n: np.full(len(dates), np.nan) for n in ("close", "high", "low", "volume")}
        degraded = np.zeros(len(dates), dtype=bool)
        for day, row in rows.items():
            i = index[day]
            eligible = row.get("analytical_type") == "RESEARCH_EQUITY_CANDIDATE"
            if eligible and row["quality"] != "REJECTED":
                for name in arrays:
                    arrays[name][i] = float(row[name])
            degraded[i] = (
                row["quality"] != "VALID"
                or bool(row.get("economic_action"))
                or row.get("action_status") == "CURRENT_ACTION_EVIDENCE_UNAVAILABLE"
            )
        values: dict[str, Any] = {}
        for definition in registry:
            name = definition.feature_name
            if definition.feature_family in {
                "CROSS_SECTIONAL",
                "RELATIVE_STRENGTH",
                "MARKET_CONTEXT",
            }:
                values[name] = dict(
                    value=None,
                    state="UNAVAILABLE",
                    reasons=["REFERENCE_OR_COMPLETE_PEER_SCOPE_UNAVAILABLE"],
                )
                continue
            value = (
                numerical(
                    definition, arrays["close"], arrays["high"], arrays["low"], arrays["volume"]
                )[-1]
                if dates
                else np.nan
            )
            flag = bool(window_flag(degraded, definition.lookback)[-1]) if dates else False
            finite = bool(np.isfinite(value))
            values[name] = dict(
                value=float(value) if finite else None,
                state="DEGRADED" if finite and flag else "AVAILABLE" if finite else "UNAVAILABLE",
                reasons=["DEGRADED_OR_ACTION_CONTEXT"]
                if finite and flag
                else []
                if finite
                else ["REQUIRED_HISTORY_MISSING"],
            )
        output.append(dict(security_id=security, session=session.isoformat(), values=values))
    return dict(
        rows=output,
        registry=[d.model_dump(mode="json") for d in registry],
        bounded_session_slots=len(dates),
        affected_securities=len(affected),
        scope="AFFECTED_RELEASE_SECURITIES_NOT_FULL_EXCHANGE_UNIVERSE",
    )
