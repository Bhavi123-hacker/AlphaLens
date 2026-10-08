"""D70 research assumptions, deliberately separate from verified PIT provenance."""

import re
from bisect import bisect_right
from datetime import date, datetime, time
from functools import cached_property
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import model_validator

from alphalens_data.contracts import Contract
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum

PROFILE: Literal["RESEARCH_EOD_FINAL_VINTAGE_V1"] = "RESEARCH_EOD_FINAL_VINTAGE_V1"
UNIVERSE = "NSE_RESEARCH_EQUITY_CANDIDATE_UNIVERSE_V1"
WARNING: Literal["FINAL_VINTAGE_RESEARCH_ASSUMPTION"] = "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
MISSING_MUHURAT = tuple(
    date.fromisoformat(d)
    for d in ("2013-11-03", "2016-10-30", "2019-10-27", "2020-11-14", "2023-11-12")
)


class ResearchProfile(Contract):
    profile: Literal["RESEARCH_EOD_FINAL_VINTAGE_V1"] = PROFILE
    version: Literal["1"] = "1"
    classification: Literal[Classification.RESEARCH_ONLY] = Classification.RESEARCH_ONLY
    data_reality: Literal["REAL_MARKET_OBSERVATIONS"] = "REAL_MARKET_OBSERVATIONS"
    final_vintage: Literal["FINAL_VINTAGE_RESEARCH_ASSUMPTION"] = WARNING
    availability: Literal["ASSUMED_NEXT_SESSION_AVAILABILITY"] = "ASSUMED_NEXT_SESSION_AVAILABILITY"
    clock_semantics: Literal["NEXT_SESSION_LOCAL_MIDNIGHT_PRE_OPEN_STAGE_NOT_EXCHANGE_CLOCK"] = (
        "NEXT_SESSION_LOCAL_MIDNIGHT_PRE_OPEN_STAGE_NOT_EXCHANGE_CLOCK"
    )
    calendar_version: Literal["research.calendar.v1"] = "research.calendar.v1"
    universe_version: Literal["research.universe.v1"] = "research.universe.v1"
    identity_version: Literal["research.observed_identity.v1"] = "research.observed_identity.v1"
    canonical_version: Literal["p5.research.canonical.v1"] = "p5.research.canonical.v1"
    production_claims_permitted: Literal[False] = False
    pit_claim: Literal["NOT PRODUCTION PIT"] = "NOT PRODUCTION PIT"

    @property
    def profile_id(self) -> str:
        return checksum(stable_json(self.model_dump(mode="json")))


class ResearchSession(Contract):
    session_date: date
    evidence: Literal["OFFICIAL_VERIFIED_SESSION", "OBSERVED_DATASET_SESSION"]
    status: Literal["SESSION_EXISTS"] = "SESSION_EXISTS"
    price_status: Literal["SOURCE_ROWS_PRESENT", "PRICE_OBSERVATION_MISSING"]


class ResearchCalendar(Contract):
    profile: ResearchProfile
    sessions: tuple[ResearchSession, ...]
    completeness: Literal["OBSERVED_PLUS_FIVE_VERIFIED_NOT_AUTHORITATIVE_COMPLETE"] = (
        "OBSERVED_PLUS_FIVE_VERIFIED_NOT_AUTHORITATIVE_COMPLETE"
    )

    @model_validator(mode="after")
    def ordered(self) -> "ResearchCalendar":
        dates = [s.session_date for s in self.sessions]
        if not dates or dates != sorted(set(dates)):
            raise ValueError("RESEARCH_CALENDAR_REQUIRES_ORDERED_UNIQUE_DATES")
        return self

    @cached_property
    def dates(self) -> tuple[date, ...]:
        return tuple(s.session_date for s in self.sessions)

    @property
    def calendar_id(self) -> str:
        return checksum(stable_json(self.model_dump(mode="json")))

    def next_session(self, session: date) -> date | None:
        dates = self.dates
        index = bisect_right(dates, session)
        return dates[index] if index < len(dates) else None

    def availability(self, session: date) -> datetime | None:
        following = self.next_session(session)
        return (
            datetime.combine(following, time.min, ZoneInfo("Asia/Kolkata")) if following else None
        )

    def entry_allowed(self, source_session: date, entry: date, decision: datetime) -> bool:
        assumed = self.availability(source_session)
        return (
            assumed is not None
            and entry == self.next_session(source_session)
            and entry > source_session
            and decision == assumed
        )


def calendar(observed: set[date], profile: ResearchProfile) -> ResearchCalendar:
    extra = {d for d in MISSING_MUHURAT if min(observed) <= d <= max(observed)}
    return ResearchCalendar(
        profile=profile,
        sessions=tuple(
            ResearchSession(
                session_date=d,
                evidence="OFFICIAL_VERIFIED_SESSION" if d in extra else "OBSERVED_DATASET_SESSION",
                price_status="SOURCE_ROWS_PRESENT"
                if d in observed
                else "PRICE_OBSERVATION_MISSING",
            )
            for d in sorted(observed | extra)
        ),
    )


class ResearchAssessment(Contract):
    analytical_type: Literal["RESEARCH_EQUITY_CANDIDATE", "EXCLUDED_NON_EQUITY", "UNKNOWN_UNUSABLE"]
    reason: str
    production_security_type: Literal["UNKNOWN"] = "UNKNOWN"
    evidence_fields: tuple[str, ...]


def assess(series: str | None, isin: str | None, name: str | None) -> ResearchAssessment:
    text = (name or "").upper()
    rules = (
        (r"\bETF\b|EXCHANGE TRADED|\bBEES\b", "ETF"),
        (r"\bREIT\b|REAL ESTATE INVESTMENT TRUST", "REIT"),
        (r"\bINVIT\b|INFRASTRUCTURE INVESTMENT TRUST", "INVIT"),
        (r"PREFERENCE|\bPREF\b", "PREFERENCE"),
        (r"DEBENTURE|\bBOND\b|\bNCD\b", "DEBT"),
        (r"MUTUAL FUND|\bFUND\b", "FUND"),
        (r"\bINDEX\b", "INDEX"),
    )
    for expression, kind in rules:
        if re.search(expression, text):
            return ResearchAssessment(
                analytical_type="EXCLUDED_NON_EQUITY",
                reason=f"EXPLICIT_NAME_{kind}",
                evidence_fields=("name",),
            )
    if isin and isin.startswith("INF"):
        return ResearchAssessment(
            analytical_type="EXCLUDED_NON_EQUITY",
            reason="RESEARCH_INF_ISIN_FUND_LIKE_HEURISTIC",
            evidence_fields=("isin",),
        )
    if series not in {"EQ", "BE", "BZ"} or (isin and not isin.startswith("INE")):
        return ResearchAssessment(
            analytical_type="UNKNOWN_UNUSABLE",
            reason="UNSUPPORTED_SERIES_OR_ISIN_PATTERN",
            evidence_fields=("series", "isin"),
        )
    return ResearchAssessment(
        analytical_type="RESEARCH_EQUITY_CANDIDATE",
        reason="OBSERVED_CASH_SERIES_EQUITY_LIKE_NOT_AUTHORITATIVE"
        if isin
        else "OBSERVED_CASH_SERIES_PROVISIONAL_ID_NOT_AUTHORITATIVE",
        evidence_fields=("series", "isin") if isin else ("series", "P2_SOURCE_SCOPED_ID"),
    )


def require_research(profile: ResearchProfile, classification: Classification) -> None:
    if classification != Classification.RESEARCH_ONLY:
        raise DataContractError("RESEARCH_ASSUMPTIONS_FORBIDDEN_OUTSIDE_RESEARCH_ONLY")
    ResearchProfile.model_validate(profile.model_dump())


def lineage(profile: ResearchProfile) -> dict[str, object]:
    return {
        "research_profile": profile.model_dump(mode="json"),
        "research_profile_id": profile.profile_id,
        "data_reality": "REAL_MARKET_OBSERVATIONS",
        "usage_classification": "RESEARCH_ONLY",
        "final_vintage": WARNING,
        "historical_revision_timing": "UNKNOWN_FINAL_VINTAGE_REVISION_RISK",
        "production_market_data_use": "NOT_CLEARED",
    }
