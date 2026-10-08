"""Observed-row research eligibility; never a production membership fact."""

from datetime import datetime

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import CanonicalEOD, Classification
from alphalens_data.research import (
    UNIVERSE,
    ResearchAssessment,
    ResearchCalendar,
    ResearchProfile,
    assess,
    require_research,
)


class ResearchUniverse:
    universe_id = UNIVERSE

    def __init__(self, profile: ResearchProfile, sessions: ResearchCalendar) -> None:
        require_research(profile, profile.classification)
        self.profile = profile
        self.sessions = sessions
        self.availability = {d: sessions.availability(d) for d in sessions.dates}

    def resolve(
        self, row: CanonicalEOD, at: datetime, name: str | None = None
    ) -> ResearchAssessment | None:
        if row.classification != Classification.RESEARCH_ONLY:
            raise DataContractError("RESEARCH_ASSUMPTIONS_FORBIDDEN_OUTSIDE_RESEARCH_ONLY")
        available = self.availability.get(row.session_date)
        if available is None or at < available:
            return None
        # Only this historical row's identity; no current symbol/history/type lookup.
        return assess(row.series, row.isin, name)
