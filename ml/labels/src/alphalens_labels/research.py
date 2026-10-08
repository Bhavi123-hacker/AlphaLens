"""P7 exact research targets on calendar slots; no skipping missing required prices."""

from decimal import Decimal, localcontext
from typing import Any

import numpy as np

from alphalens_data.research import ResearchCalendar


def indexed_targets(
    sessions: ResearchCalendar,
    opening: list[Decimal | None],
    closing: list[Decimal | None],
    eligible: np.ndarray[Any, Any],
    actions: np.ndarray[Any, Any],
    horizon: int,
    indices: list[int],
) -> dict[int, dict[str, Any]]:
    if horizon not in (1, 5, 10, 20):
        raise ValueError("UNSUPPORTED_RESEARCH_HORIZON")
    dates = sessions.dates
    if not len(dates) == len(opening) == len(closing) == len(eligible) == len(actions):
        raise ValueError("RESEARCH_LABEL_CALENDAR_ALIGNMENT_REQUIRED")
    output = {}
    for i in indices:
        if not 0 <= i < len(dates):
            raise ValueError("RESEARCH_LABEL_DECISION_INDEX_OUT_OF_RANGE")
        session = dates[i]
        future = range(i + 1, i + horizon + 1)
        reasons = []
        maturity = "MATURE"
        value = None
        available = None
        if i + horizon >= len(dates) or sessions.availability(dates[i + horizon]) is None:
            maturity = "NOT_YET_MATURE"
            reasons.append("OUTCOME_OR_ASSUMED_AVAILABILITY_NOT_YET_OBSERVED")
        elif any(opening[j] is None or closing[j] is None for j in future):
            maturity = "UNAVAILABLE"
            reasons.append("REQUIRED_FUTURE_PRICE_UNAVAILABLE")
        elif any(not eligible[j] for j in future):
            maturity = "UNAVAILABLE"
            reasons.append("FUTURE_RESEARCH_UNIVERSE_OR_QUALITY_INELIGIBLE")
        else:
            entry = opening[i + 1]
            exit_value = closing[i + horizon]
            if entry is None or exit_value is None:
                raise ValueError("MATURE_RESEARCH_TARGET_WITHOUT_EVIDENCE")
            with localcontext() as ctx:
                ctx.prec = 76
                numerator = exit_value - entry
            with localcontext() as ctx:
                ctx.prec = 34
                value = str(numerator / entry)
            available = sessions.availability(dates[i + horizon])
            if any(actions[j] for j in future):
                reasons.append("CORPORATE_ACTION_UNADJUSTED")
        output[i] = dict(
            session_date=session,
            horizon=horizon,
            maturity=maturity,
            return_value=value,
            direction_value=int(Decimal(value) > 0) if value is not None else None,
            exact_numerator=str(numerator) if value is not None else None,
            exact_denominator=str(entry) if value is not None else None,
            label_available_at=available,
            entry_session=dates[i + 1] if i + 1 < len(dates) else None,
            target_session=dates[i + horizon] if i + horizon < len(dates) else None,
            outcome_reasons=reasons,
            terminal_event_status="UNAVAILABLE_NO_AUTHORITATIVE_TERMINAL_EVIDENCE",
        )
    return output


def targets(
    sessions: ResearchCalendar,
    opening: list[Decimal | None],
    closing: list[Decimal | None],
    eligible: np.ndarray[Any, Any],
    actions: np.ndarray[Any, Any],
    horizon: int,
) -> list[dict[str, Any]]:
    output = indexed_targets(
        sessions, opening, closing, eligible, actions, horizon, list(range(len(sessions.dates)))
    )
    return [output[i] for i in range(len(sessions.dates))]


def training_visible(label: dict[str, Any], cutoff: Any) -> bool:
    return label["label_available_at"] is not None and label["label_available_at"] <= cutoff
