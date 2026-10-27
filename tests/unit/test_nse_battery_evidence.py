"""TEST_ONLY plan-boundary and evidence-format regression; no scheduler access."""

import copy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from scripts import nse_collector_cutover as cutover
from scripts import review_nse_battery_evidence as review

EXPIRES = datetime(2026, 10, 27, 15, 45, tzinfo=UTC)


def evidence() -> tuple[dict[str, Any], str, str, dict[str, Any], dict[str, Any]]:
    original = (
        f'<Task xmlns="{cutover.NS}"><Triggers><CalendarTrigger>'
        "<StartBoundary>2026-10-27T22:30:00+05:30</StartBoundary>"
        "</CalendarTrigger></Triggers><Settings><DisallowStartIfOnBatteries>true"
        "</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>"
        "<ExecutionTimeLimit>PT30M</ExecutionTimeLimit></Settings>"
        "<Actions><Exec><Command>TEST_ONLY.cmd</Command></Exec></Actions></Task>"
    )
    proposed = original.replace(">true<", ">false<")
    identity: dict[str, Any] = {
        "checks": dict.fromkeys(review.CHECKS, True),
        "source": {"sha256": "TEST_ONLY_SOURCE"},
    }
    identity["fresh_fingerprint_sha256"] = review.digest(cutover.encoded(identity))
    plan = {
        "schema": "alphalens.nse-task-two-battery-flags.proposal.v1",
        "task": cutover.TASK,
        "expires_at": EXPIRES.isoformat(),
        "original_xml_sha256": review.digest(original.encode()),
        "proposed_xml_sha256": review.digest(proposed.encode()),
        "exact_changes": [
            {"path": "Settings/" + name, "before": True, "after": False} for name in review.FLAGS
        ],
        "preserved_collector_runtime_fingerprint": identity["fresh_fingerprint_sha256"],
        "source_inventory_sha256": "TEST_ONLY_SOURCE",
    }
    runtime = {
        "state": "PASS",
        "identity": identity,
        "source_sha256": "TEST_ONLY_SOURCE",
        "at": (EXPIRES - timedelta(seconds=60)).isoformat(),
    }
    return plan, original, proposed, runtime, {"dependencies": [{"name": "TEST_ONLY", "vulns": []}]}


@pytest.mark.parametrize("remaining", [31, 30, 1, 0.001])
def test_exact_approved_expiry_has_no_extra_thirty_second_cutoff(remaining: float) -> None:
    result = review.review(*evidence(), now=EXPIRES - timedelta(seconds=remaining))
    assert result["extra_deadline_margin_seconds"] == 0
    assert result["task_changes"] == 0 and result["activation_authorized_by_this_review"] is False


@pytest.mark.parametrize("late", [0, 0.001, 3600])
def test_expired_plan_is_never_renewed(late: float) -> None:
    with pytest.raises(ValueError, match="PLAN_EXPIRED"):
        review.review(*evidence(), now=EXPIRES + timedelta(seconds=late))


def test_nested_real_report_shape_is_read_without_mutating_it() -> None:
    bundle = evidence()
    before = copy.deepcopy(bundle)
    assert review.review(*bundle, now=EXPIRES - timedelta(seconds=60))["dependency_advisories"] == 0
    assert bundle == before


def test_flat_runtime_shape_is_rejected_with_a_stable_error() -> None:
    plan, original, proposed, report, audit = evidence()
    with pytest.raises(ValueError, match="NESTED_RUNTIME_REPORT_REQUIRED"):
        review.review(
            plan, original, proposed, report["identity"], audit, now=EXPIRES - timedelta(seconds=60)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("identity.checks.installed_record_hashes_match", False),
        ("identity.fresh_fingerprint_sha256", "TEST_ONLY_WRONG"),
        ("identity.source.sha256", "TEST_ONLY_TAMPERED"),
        ("source_sha256", "TEST_ONLY_WRONG"),
    ],
)
def test_failed_or_tampered_runtime_evidence_is_rejected(field: str, value: Any) -> None:
    plan, original, proposed, report, audit = evidence()
    target = report
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    with pytest.raises(ValueError):
        review.review(plan, original, proposed, report, audit, now=EXPIRES - timedelta(seconds=60))


@pytest.mark.parametrize(
    "old,new", [("TEST_ONLY.cmd", "OTHER.cmd"), ("PT30M", "PT60M"), ("22:30:00", "22:31:00")]
)
def test_even_hash_bound_unrelated_task_changes_are_rejected(old: str, new: str) -> None:
    plan, original, proposed, report, audit = evidence()
    proposed = proposed.replace(old, new)
    plan["proposed_xml_sha256"] = review.digest(proposed.encode())
    with pytest.raises(ValueError, match="UNRELATED_TASK_CHANGE_REJECTED"):
        review.review(plan, original, proposed, report, audit, now=EXPIRES - timedelta(seconds=60))


@pytest.mark.parametrize("rows", [[], [{"name": "TEST_ONLY"}], [{"vulns": [{"id": "TEST_ONLY"}]}]])
def test_missing_and_failed_dependency_audits_are_rejected(rows: list[Any]) -> None:
    plan, original, proposed, report, _ = evidence()
    with pytest.raises(ValueError):
        review.review(
            plan,
            original,
            proposed,
            report,
            {"dependencies": rows},
            now=EXPIRES - timedelta(seconds=60),
        )


def test_exact_local_workspace_skip_is_visible_and_not_called_advisory_scanned() -> None:
    plan, original, proposed, report, audit = evidence()
    audit["dependencies"].append(
        {
            "name": "alphalens-api",
            "skip_reason": (
                "Dependency not found on PyPI and could not be audited: alphalens-api (0.1.0)"
            ),
        }
    )
    result = review.review(
        plan, original, proposed, report, audit, now=EXPIRES - timedelta(seconds=60)
    )
    assert result["third_party_distributions_audited"] == 1
    assert result["local_workspace_distributions_not_in_pypi_advisory_database"] == [
        "alphalens-api"
    ]


@pytest.mark.parametrize("name", ["TEST_ONLY_UNKNOWN", "alphalens-api"])
def test_unknown_or_changed_skip_reason_is_rejected(name: str) -> None:
    plan, original, proposed, report, _ = evidence()
    with pytest.raises(ValueError, match="DEPENDENCY_AUDIT_NOT_CLEARED"):
        review.review(
            plan,
            original,
            proposed,
            report,
            {"dependencies": [{"name": name, "skip_reason": "TEST_ONLY_UNREVIEWED"}]},
            now=EXPIRES - timedelta(seconds=60),
        )


@pytest.mark.parametrize("offset", [-1, 241])
def test_future_or_stale_runtime_report_cannot_be_relabelled_fresh(offset: int) -> None:
    plan, original, proposed, report, audit = evidence()
    now = EXPIRES - timedelta(seconds=60)
    report["at"] = (now - timedelta(seconds=offset)).isoformat()
    with pytest.raises(ValueError, match="RUNTIME_REPORT_NOT_FRESH"):
        review.review(plan, original, proposed, report, audit, now=now)


def test_local_project_skip_can_never_hide_a_reported_vulnerability() -> None:
    plan, original, proposed, report, _ = evidence()
    audit = {
        "dependencies": [
            {
                "name": "alphalens-api",
                "skip_reason": (
                    "Dependency not found on PyPI and could not be audited: alphalens-api (0.1.0)"
                ),
                "vulns": [{"id": "TEST_ONLY_ADVISORY"}],
            }
        ]
    }
    with pytest.raises(ValueError, match="DEPENDENCY_AUDIT_NOT_CLEARED"):
        review.review(plan, original, proposed, report, audit, now=EXPIRES - timedelta(seconds=60))
