"""Explicit TEST_ONLY operational event factory; never a runtime alert fallback."""

from datetime import UTC, datetime

from workers.alerts.contracts import Event

AT = datetime(2026, 10, 11, 12, tzinfo=UTC)


def event(code: str = "SOURCE_BLOCKED", identity: str = "TEST_ONLY_EVENT") -> Event:
    return Event(
        code=code,
        component="P19",
        evidence_ref="TEST_ONLY_RECEIPT",
        evidence_sha256="a" * 64,
        event_at=AT,
        time_basis="PERSISTED_EVENT_TIME",
        classification="TEST_ONLY",
        mode="TEST_ONLY",
        group="TEST_ONLY_GROUP",
        identity=identity,
        reasons=("TEST_ONLY_BLOCKER",),
    )
