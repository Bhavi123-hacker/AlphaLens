"""Offline release/catch-up scenarios never infer weekdays or provider publication clocks."""

from datetime import timedelta

from scripts.build_p19_test_evidence import AT, DAY, calendar
from workers.providers.session_plan import Release, plan


def test_missing_release_requires_documented_availability_window() -> None:
    result = plan(calendar([DAY]), DAY, DAY, AT, "upstox")
    assert result["sessions"][0]["state"] == "AWAITING_RELEASE_WINDOW_UNKNOWN"
    result = plan(
        calendar([DAY]),
        DAY,
        DAY,
        AT,
        "upstox",
        expected_availability={DAY: AT - timedelta(hours=1)},
    )
    assert result["sessions"][0]["state"] == "EXPECTED_RELEASE_MISSING"
    assert result["collection_enabled"] is False


def test_partial_duplicate_and_correction_revisions_are_distinct() -> None:
    release = Release(provider="upstox", session=DAY, revision_sha256="a" * 64, observed_at=AT)
    assert (
        plan(calendar([DAY]), DAY, DAY, AT, "upstox", (release,))["sessions"][0]["state"]
        == "INCOMPLETE_RELEASE_RETRY_NOT_PUBLISHABLE"
    )
    release = release.model_copy(update={"complete": True})
    assert (
        plan(calendar([DAY]), DAY, DAY, AT, "upstox", (release,), {DAY: "a" * 64})["sessions"][0][
            "state"
        ]
        == "DUPLICATE_ACCEPTED_REVISION_NO_FETCH"
    )
    assert (
        plan(calendar([DAY]), DAY, DAY, AT, "upstox", (release,), {DAY: "b" * 64})["sessions"][0][
            "state"
        ]
        == "CHANGED_REVISION_PRESERVE_ORIGINAL"
    )


def test_unknown_calendar_does_not_become_missing_trading_session() -> None:
    day = DAY + timedelta(days=1)
    assert (
        plan(calendar([DAY]), day, day, AT, "upstox")["sessions"][0]["state"]
        == "UNKNOWN_SESSION_NO_MISSING_ALERT"
    )
