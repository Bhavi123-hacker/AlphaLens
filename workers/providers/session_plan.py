"""Bounded catch-up planning from dated calendar/release evidence; no scheduler or fetching."""

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime

from alphalens_data.contracts import Contract
from alphalens_data.daily.contracts import Calendar
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Hash
from alphalens_data.providers.multi_contracts import ProviderName


class Release(Contract):
    provider: ProviderName
    session: date
    revision_sha256: Hash
    observed_at: AwareDatetime
    source_publication_time: AwareDatetime | None = None
    complete: bool = False


def plan(
    calendar: Calendar,
    start: date,
    end: date,
    at: datetime,
    provider: ProviderName,
    releases: tuple[Release, ...] = (),
    accepted: dict[date, str] | None = None,
    expected_availability: dict[date, datetime] | None = None,
) -> dict[str, Any]:
    if at.tzinfo is None or start > end or (end - start).days > 30:
        raise DataContractError("BOUNDED_AWARE_CATCHUP_SCOPE_REQUIRED")
    if len(releases) > 31 or len({r.session for r in releases}) != len(releases):
        raise DataContractError("UNAMBIGUOUS_RELEASE_REVISION_REQUIRED")
    if any(
        r.provider != provider
        or r.observed_at > at
        or r.source_publication_time
        and r.source_publication_time > r.observed_at
        for r in releases
    ):
        raise DataContractError("PROVIDER_RELEASE_CHRONOLOGY_INVALID")
    known = {s.session: s for s in calendar.sessions if s.known_at <= at}
    found = {r.session: r for r in releases}
    rows = []
    day = start
    while day <= end:
        session = known.get(day)
        release = found.get(day)
        state = "UNKNOWN_SESSION_NO_MISSING_ALERT"
        if session and session.status == "NON_TRADING":
            state = "NON_TRADING_NO_FETCH"
        elif session and session.status == "TRADING":
            if day >= at.astimezone(ZoneInfo("Asia/Kolkata")).date():
                state = "CURRENT_OR_FUTURE_SESSION_NOT_VERIFIED_COMPLETE"
            elif session.evidence_type not in {"OFFICIAL_VERIFIED_SESSION", "TEST_ONLY"}:
                state = "OBSERVED_CALENDAR_NOT_AUTHORITATIVE_EXPECTATION"
            elif release:
                prior = (accepted or {}).get(day)
                state = (
                    "INCOMPLETE_RELEASE_RETRY_NOT_PUBLISHABLE"
                    if not release.complete
                    else "DUPLICATE_ACCEPTED_REVISION_NO_FETCH"
                    if prior == release.revision_sha256
                    else "CHANGED_REVISION_PRESERVE_ORIGINAL"
                    if prior
                    else "NEW_RELEASE_READY_FOR_DISABLED_WORKFLOW"
                )
            else:
                deadline = (expected_availability or {}).get(day)
                if deadline and deadline.tzinfo is None:
                    raise DataContractError("AWARE_DOCUMENTED_RELEASE_WINDOW_REQUIRED")
                state = (
                    "EXPECTED_RELEASE_MISSING"
                    if deadline and at > deadline
                    else "AWAITING_RELEASE_WINDOW_UNKNOWN"
                    if deadline is None
                    else "AWAITING_DOCUMENTED_RELEASE_WINDOW"
                )
        rows.append(
            {
                "session": day.isoformat(),
                "state": state,
                "source_publication_time": release.source_publication_time.isoformat()
                if release and release.source_publication_time
                else None,
                "revision_sha256": release.revision_sha256 if release else None,
            }
        )
        day += timedelta(days=1)
    return {
        "calendar_sha256": calendar.identity,
        "provider": provider,
        "sessions": rows,
        "collection_enabled": False,
        "scheduler_enabled": False,
        "classification": "TEST_ONLY"
        if all(s.evidence_type == "TEST_ONLY" for s in calendar.sessions)
        else "RESEARCH_ONLY",
        "gate": "SOURCE_ACCOUNT_PERMISSION_AND_OPERATOR_ACTIVATION_REQUIRED",
    }
