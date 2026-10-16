"""Provider session metadata: explicit holiday/special-session facts, no weekday fill."""

import json
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.daily.contracts import Calendar, Session
from alphalens_data.errors import DataContractError

from .upstox import Reply


def nse_holidays(reply: Reply) -> tuple[Session, ...]:
    data = json.loads(reply.body)
    if (
        reply.state != "ACCEPTED"
        or data.get("status") != "success"
        or not isinstance(data.get("data"), list)
    ):
        raise DataContractError("HOLIDAY_SCHEMA_REJECTED")
    if len(data["data"]) > 400:
        raise DataContractError("HOLIDAY_LIMIT")
    rows = []
    for item in data["data"]:
        day = date.fromisoformat(item["date"])
        if item["holiday_type"] == "SETTLEMENT_HOLIDAY":
            continue
        closed = "NSE" in item.get("closed_exchanges", [])
        opened = any(r.get("exchange") == "NSE" for r in item.get("open_exchanges", []))
        if closed and opened:
            raise DataContractError("AMBIGUOUS_NSE_HOLIDAY")
        if not closed and not opened:
            continue
        rows.append(
            Session(
                session=day,
                status="NON_TRADING" if closed else "TRADING",
                known_at=reply.received_at,
                evidence_reference="UPSTOX_OFFICIAL_MARKET_HOLIDAYS_CURRENT_YEAR",
                evidence_type="OFFICIAL_VERIFIED_SESSION",
            )
        )
    return tuple(sorted(rows, key=lambda r: r.session))


def nse_timing(reply: Reply, session: date) -> dict[str, Any]:
    data = json.loads(reply.body)
    if (
        reply.state != "ACCEPTED"
        or data.get("status") != "success"
        or not isinstance(data.get("data"), list)
    ):
        raise DataContractError("TIMING_SCHEMA_REJECTED")
    rows = [r for r in data["data"] if r.get("exchange") == "NSE"]
    if len(rows) != 1:
        raise DataContractError("NSE_TIMING_MISSING_OR_AMBIGUOUS")
    row = rows[0]
    start, end = (datetime.fromtimestamp(row[k] / 1000, UTC) for k in ("start_time", "end_time"))
    if (
        start >= end
        or start.astimezone(ZoneInfo("Asia/Kolkata")).date() != session
        or end.astimezone(ZoneInfo("Asia/Kolkata")).date() != session
    ):
        raise DataContractError("NSE_TIMING_DATE_REJECTED")
    return {
        "session": str(session),
        "exchange": "NSE",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "known_at": reply.received_at.isoformat(),
        "session_elapsed": end < reply.received_at,
        "eod_release_published": None,
        "official_final_close_verified": False,
    }


def past_session_fact(reply: Reply, session: date, lower: datetime) -> Session:
    """Dated official timing, including absence of an open NSE session."""
    data = json.loads(reply.body)
    rows = data.get("data")
    if (
        reply.state != "ACCEPTED"
        or reply.status != 200
        or data.get("status") != "success"
        or not isinstance(rows, list)
        or len(rows) > 32
        or any(not isinstance(r, dict) or not isinstance(r.get("exchange"), str) for r in rows)
    ):
        raise DataContractError("OFFICIAL_DATED_SESSION_RESPONSE_REQUIRED")
    if session >= lower.astimezone(ZoneInfo("Asia/Kolkata")).date():
        raise DataContractError("PAST_SESSION_REQUIRED")
    if any(r["exchange"] == "NSE" for r in rows):
        timing = nse_timing(reply, session)
        if not timing["session_elapsed"] or datetime.fromisoformat(timing["end"]) >= lower:
            raise DataContractError("OFFICIAL_SESSION_NOT_YET_ELAPSED")
        state = "TRADING"
    else:
        state = "NON_TRADING"
    return Session(
        session=session,
        status=state,
        known_at=reply.received_at,
        evidence_reference="UPSTOX_OFFICIAL_MARKET_TIMING"
        if state == "TRADING"
        else "UPSTOX_OFFICIAL_DATED_TIMING_NO_OPEN_NSE_SESSION",
        evidence_type="OFFICIAL_VERIFIED_SESSION",
    )


def calendar(sessions: tuple[Session, ...]) -> Calendar:
    # Chronological availability is retrieval, never backfilled into historical knowledge.
    return Calendar(
        sessions=tuple(sorted(sessions, key=lambda r: r.session)),
        completeness="EXPLICIT_PROVIDER_SCHEDULE_FACTS_ONLY_MISSING_DATES_UNKNOWN",
    )
