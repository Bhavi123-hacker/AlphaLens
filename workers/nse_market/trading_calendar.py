"""Authentic NSE Trading-Calendar Validation Engine for AlphaLens.

Provides verified exchange schedule checks for daily prospective settlement.
Supports regular weekday sessions, verified exchange holidays, exceptional weekend
trading sessions (e.g., Union Budget Sunday, Diwali Muhurat trading), and fail-closed
behavior when calendar evidence is unavailable or corrupt.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("alphalens.trading_calendar")

REPO_ROOT = Path(__file__).resolve().parents[2]


class CalendarSessionStatus(StrEnum):
    VERIFIED_TRADING_SESSION = "VERIFIED_TRADING_SESSION"
    VERIFIED_MARKET_HOLIDAY = "VERIFIED_MARKET_HOLIDAY"
    EXCEPTIONAL_TRADING_SESSION = "EXCEPTIONAL_TRADING_SESSION"
    MARKET_SESSION_WEEKEND_NON_TRADING = "MARKET_SESSION_WEEKEND_NON_TRADING"
    CALENDAR_EVIDENCE_UNAVAILABLE = "CALENDAR_EVIDENCE_UNAVAILABLE"
    REJECTED_INVALID_DATE = "REJECTED_INVALID_DATE"


def load_reference_calendar(
    calendar_path: Path | None = None,
    repo_root: Path | None = None,
    fallback_to_repo: bool = True,
) -> dict[str, Any] | None:
    """Load official versioned NSE calendar facts."""
    root = repo_root or REPO_ROOT
    candidates: list[Path] = []
    if calendar_path:
        candidates.append(calendar_path)
    if root:
        candidates.extend(
            [
                root / "data" / "reference" / "nse_calendar_2026.json",
                root.parent / ".local-data" / "p30-upstox-validation" / "provider-calendar.json",
                root / ".local-data" / "p30-upstox-validation" / "provider-calendar.json",
            ]
        )
    if fallback_to_repo and REPO_ROOT and root != REPO_ROOT:
        candidates.extend(
            [
                REPO_ROOT / "data" / "reference" / "nse_calendar_2026.json",
                REPO_ROOT.parent
                / ".local-data"
                / "p30-upstox-validation"
                / "provider-calendar.json",
                REPO_ROOT / ".local-data" / "p30-upstox-validation" / "provider-calendar.json",
            ]
        )

    for p in candidates:
        if p.exists() and p.is_file():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    continue
                data: dict[str, Any] = raw
                # Handle both reference schema and provider-calendar schema
                if "sessions" in data and isinstance(data["sessions"], list):
                    return data
                if "calendar" in data and isinstance(data["calendar"], dict):
                    cal_dict = data["calendar"]
                    if "sessions" in cal_dict and isinstance(cal_dict["sessions"], list):
                        return {
                            "schema": data.get("schema", "p30.provider-session-metadata.v1"),
                            "year": 2026,
                            "exchange": "NSE",
                            "timezone": cal_dict.get("timezone", "Asia/Kolkata"),
                            "source": "UPSTOX_OFFICIAL_MARKET_HOLIDAYS_CURRENT_YEAR",
                            "sessions": cal_dict["sessions"],
                        }
            except Exception as exc:
                logger.warning("Failed to parse calendar candidate %s: %s", p, exc)
                return None
    return None


def validate_nse_trading_session(
    session_str: str,
    calendar_path: Path | None = None,
    repo_root: Path | None = None,
    local_calendar_dir: Path | None = None,
    fallback_to_repo: bool = True,
) -> dict[str, Any]:
    """Validate whether session_str is an authenticated NSE trading session.

    Distinguishes:
    - VERIFIED_TRADING_SESSION: Open regular session.
    - VERIFIED_MARKET_HOLIDAY: Explicit official exchange holiday.
    - EXCEPTIONAL_TRADING_SESSION: Special weekend trading session.
    - MARKET_SESSION_WEEKEND_NON_TRADING: Standard closed weekend.
    - CALENDAR_EVIDENCE_UNAVAILABLE: Unverified date or missing calendar facts (fail closed).
    - REJECTED_INVALID_DATE: Malformed date string.
    """
    root = repo_root or REPO_ROOT

    # 1. Validate date format
    try:
        session_date = date.fromisoformat(session_str)
    except (ValueError, TypeError):
        return {
            "is_trading_day": False,
            "session": session_str,
            "status": CalendarSessionStatus.REJECTED_INVALID_DATE,
            "reason": "INVALID_DATE_FORMAT",
        }

    weekday_name = session_date.strftime("%A")
    is_weekend = session_date.weekday() in (5, 6)

    # 2. Check local daily authenticated timing evidence on host if available
    cal_dirs = [
        local_calendar_dir,
        root.parent / ".local-data" / "nse-market-expansion" / "calendar",
        root / ".local-data" / "nse-market-expansion" / "calendar",
    ]
    for cdir in cal_dirs:
        if cdir and cdir.exists():
            daily_file = cdir / f"{session_str}.json"
            if daily_file.exists():
                try:
                    daily_rec = json.loads(daily_file.read_text(encoding="utf-8"))
                    fact = daily_rec.get("fact")
                    if fact is None:
                        return {
                            "is_trading_day": False,
                            "session": session_str,
                            "weekday": weekday_name,
                            "status": CalendarSessionStatus.VERIFIED_MARKET_HOLIDAY
                            if not is_weekend
                            else CalendarSessionStatus.MARKET_SESSION_WEEKEND_NON_TRADING,
                            "reason": "OFFICIAL_SESSION_TIMING_RECORDED_CLOSED",
                            "evidence_source": "NSE_MARKET_EXPANSION_DAILY_TIMING_FILE",
                        }
                    if isinstance(fact, dict) and fact.get("open_at") and fact.get("close_at"):
                        status = (
                            CalendarSessionStatus.EXCEPTIONAL_TRADING_SESSION
                            if is_weekend
                            else CalendarSessionStatus.VERIFIED_TRADING_SESSION
                        )
                        return {
                            "is_trading_day": True,
                            "session": session_str,
                            "weekday": weekday_name,
                            "status": status,
                            "reason": "OFFICIAL_SESSION_TIMING_CONFIRMED_OPEN",
                            "open_at": fact.get("open_at"),
                            "close_at": fact.get("close_at"),
                            "evidence_source": "NSE_MARKET_EXPANSION_DAILY_TIMING_FILE",
                        }
                except Exception as exc:
                    logger.debug("Error reading daily timing file %s: %s", daily_file, exc)

    # 3. Load reference calendar facts
    cal_data = load_reference_calendar(
        calendar_path=calendar_path, repo_root=root, fallback_to_repo=fallback_to_repo
    )
    if not cal_data or not isinstance(cal_data.get("sessions"), list):
        return {
            "is_trading_day": False,
            "session": session_str,
            "weekday": weekday_name,
            "status": CalendarSessionStatus.CALENDAR_EVIDENCE_UNAVAILABLE,
            "reason": "AUTHENTICATED_CALENDAR_DATA_UNAVAILABLE",
        }

    # Verify coverage year
    covered_year = cal_data.get("year", 2026)
    if session_date.year != covered_year:
        return {
            "is_trading_day": False,
            "session": session_str,
            "weekday": weekday_name,
            "status": CalendarSessionStatus.CALENDAR_EVIDENCE_UNAVAILABLE,
            "reason": f"DATE_OUTSIDE_COVERED_CALENDAR_YEAR_{covered_year}",
        }

    # Check explicit session facts
    session_map = {s["session"]: s for s in cal_data["sessions"] if "session" in s}
    if session_str in session_map:
        fact = session_map[session_str]
        fact_status = fact.get("status")
        ev_ref = fact.get("evidence_reference", "UPSTOX_OFFICIAL_MARKET_HOLIDAYS")

        if fact_status == "NON_TRADING":
            return {
                "is_trading_day": False,
                "session": session_str,
                "weekday": weekday_name,
                "status": CalendarSessionStatus.VERIFIED_MARKET_HOLIDAY,
                "reason": "OFFICIAL_NSE_MARKET_HOLIDAY",
                "evidence_reference": ev_ref,
            }
        if fact_status == "TRADING":
            status = (
                CalendarSessionStatus.EXCEPTIONAL_TRADING_SESSION
                if is_weekend
                else CalendarSessionStatus.VERIFIED_TRADING_SESSION
            )
            return {
                "is_trading_day": True,
                "session": session_str,
                "weekday": weekday_name,
                "status": status,
                "reason": "OFFICIAL_SPECIAL_TRADING_SESSION"
                if is_weekend
                else "OFFICIAL_VERIFIED_TRADING_SESSION",
                "evidence_reference": ev_ref,
            }

    # If date is not an explicit holiday / special session:
    if is_weekend:
        return {
            "is_trading_day": False,
            "session": session_str,
            "weekday": weekday_name,
            "status": CalendarSessionStatus.MARKET_SESSION_WEEKEND_NON_TRADING,
            "reason": "WEEKEND_NON_TRADING_DAY",
        }

    # Monday through Friday regular trading day
    return {
        "is_trading_day": True,
        "session": session_str,
        "weekday": weekday_name,
        "status": CalendarSessionStatus.VERIFIED_TRADING_SESSION,
        "reason": "VERIFIED_REGULAR_WEEKDAY_SESSION",
        "evidence_reference": cal_data.get("source", "UPSTOX_OFFICIAL_MARKET_HOLIDAYS"),
    }
