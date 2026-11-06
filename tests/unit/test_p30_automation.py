"""TEST_ONLY scheduler/calendar guards; no task activation or provider requests."""

from pathlib import Path
from xml.etree.ElementTree import fromstring

from scripts.build_p28_test_inputs import AT, DAY
from workers.providers.automation import readiness, task_xml

from alphalens_data.daily.contracts import Calendar, Session
from alphalens_data.providers.multi_contracts import Access


def test_operator_token_does_not_clear_retention_or_session_quality() -> None:
    calendar = Calendar(
        sessions=(
            Session(
                session=DAY,
                status="TRADING",
                known_at=AT,
                evidence_reference="TEST_ONLY",
                evidence_type="TEST_ONLY",
            ),
        )
    )
    result = readiness(
        Access(
            provider="upstox",
            credential_configured=True,
            token_kind="READ_ONLY_ANALYTICS",
            nse_verified=True,
        ),
        calendar,
        AT,
    )
    assert result["scheduler_enabled"] is False and result["network_calls"] == 0
    assert "SOURCE_USAGE_NOT_CLEARED" in result["blockers"]
    assert "AUTHORITATIVE_EXCHANGE_CALENDAR_REQUIRED" in result["blockers"]


def test_task_is_disabled_least_privilege_and_has_no_secret_arguments(tmp_path: Path) -> None:
    payload = task_xml(tmp_path / "config.json")
    root = fromstring(payload)
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert root.findtext("t:Settings/t:Enabled", namespaces=ns) == "false"
    assert root.findtext("t:Triggers/t:CalendarTrigger/t:Enabled", namespaces=ns) == "false"
    assert root.findtext("t:Principals/t:Principal/t:RunLevel", namespaces=ns) == "LeastPrivilege"
    assert b"apii.txt" not in payload and b"token=" not in payload
