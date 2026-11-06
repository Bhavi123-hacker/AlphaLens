"""Read-only review of a hash-bound, two-setting proposal. Never changes tasks.

The CLI always uses the current UTC time. Historical replay is a pure Python
test operation and cannot authorize an expired plan or start a collector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts import nse_collector_cutover as cutover

FLAGS = ("DisallowStartIfOnBatteries", "StopIfGoingOnBatteries")
CHECKS = (
    "lock_matches_installation",
    "base_python_matches_installation",
    "package_versions_match_installation",
    "installed_record_hashes_match",
)
LOCAL_DISTRIBUTIONS = {
    "alphalens-" + name
    for name in (
        "api",
        "backtesting",
        "data",
        "decision",
        "evaluation",
        "features",
        "labels",
        "portfolio",
        "training",
    )
}


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def verify_delta(original: str, proposed: str) -> None:
    left, right = cutover.parse(original), cutover.parse(proposed)
    for name in FLAGS:
        path = "{" + cutover.NS + "}Settings/{" + cutover.NS + "}" + name
        first, second = left.find(path), right.find(path)
        if (
            first is None
            or second is None
            or first.attrib
            or second.attrib
            or len(first)
            or len(second)
            or first.text != "true"
            or second.text != "false"
        ):
            raise ValueError("EXACT_ORIGINAL_AND_PROPOSED_FLAGS_REQUIRED")
        first.text = second.text = "REVIEWED_FLAG_ONLY"
    if cutover.canonical(left) != cutover.canonical(right):
        raise ValueError("UNRELATED_TASK_CHANGE_REJECTED")


def review(
    plan: dict[str, Any],
    original: str,
    proposed: str,
    runtime_report: dict[str, Any],
    audit: dict[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Validate evidence shape and scope; live process/power checks remain separate."""
    if now.tzinfo is None:
        raise ValueError("AWARE_REVIEW_TIME_REQUIRED")
    expires = datetime.fromisoformat(plan["expires_at"])
    if expires.tzinfo is None or now >= expires:
        raise ValueError("PLAN_EXPIRED")
    if (
        plan["schema"] != "alphalens.nse-task-two-battery-flags.proposal.v1"
        or plan["task"] != cutover.TASK
        or plan["exact_changes"]
        != [{"path": "Settings/" + name, "before": True, "after": False} for name in FLAGS]
    ):
        raise ValueError("UNREVIEWED_PLAN_SCOPE")
    if (
        digest(original.encode()) != plan["original_xml_sha256"]
        or digest(proposed.encode()) != plan["proposed_xml_sha256"]
    ):
        raise ValueError("REVIEWED_XML_HASH_MISMATCH")
    verify_delta(original, proposed)
    identity = runtime_report.get("identity")
    if runtime_report.get("state") != "PASS" or not isinstance(identity, dict):
        raise ValueError("NESTED_RUNTIME_REPORT_REQUIRED")
    observed = datetime.fromisoformat(runtime_report["at"])
    if observed.tzinfo is None or not 0 <= (now - observed).total_seconds() <= 240:
        raise ValueError("RUNTIME_REPORT_NOT_FRESH")
    if any(identity.get("checks", {}).get(name) is not True for name in CHECKS):
        raise ValueError("RUNTIME_INTEGRITY_CHECK_FAILED")
    expected = plan["preserved_collector_runtime_fingerprint"]
    actual = digest(
        cutover.encoded({k: v for k, v in identity.items() if k != "fresh_fingerprint_sha256"})
    )
    if identity.get("fresh_fingerprint_sha256") != expected or actual != expected:
        raise ValueError("RUNTIME_FINGERPRINT_MISMATCH")
    if runtime_report.get("source_sha256") != plan["source_inventory_sha256"]:
        raise ValueError("RUNTIME_SOURCE_MISMATCH")
    rows = audit.get("dependencies")
    if not isinstance(rows, list) or not rows:
        raise ValueError("DEPENDENCY_AUDIT_MISSING")
    local_skips = []
    for row in rows:
        name = row.get("name")
        expected_skip = f"Dependency not found on PyPI and could not be audited: {name} (0.1.0)"
        if row.get("vulns"):
            raise ValueError("DEPENDENCY_AUDIT_NOT_CLEARED")
        if (
            name in LOCAL_DISTRIBUTIONS
            and row.get("skip_reason") == expected_skip
            and "vulns" not in row
        ):
            # These exact local workspace projects are covered by the source
            # fingerprint, tests and static checks, not a PyPI advisory lookup.
            # Retain their skipped status explicitly rather than calling them scanned.
            local_skips.append(name)
        elif not isinstance(row.get("vulns"), list) or row["vulns"]:
            raise ValueError("DEPENDENCY_AUDIT_NOT_CLEARED")
    return {
        "status": "READ_ONLY_EVIDENCE_REVIEW_PASSED",
        "expires_at": expires.isoformat(),
        "seconds_until_expiry": (expires - now).total_seconds(),
        "extra_deadline_margin_seconds": 0,
        "runtime_fingerprint": expected,
        "dependency_advisories": 0,
        "third_party_distributions_audited": len(rows) - len(local_skips),
        "local_workspace_distributions_not_in_pypi_advisory_database": sorted(local_skips),
        "task_changes": 0,
        "provider_requests": 0,
        "activation_authorized_by_this_review": False,
        "remaining_live_checks": [
            "operator_approval",
            "power",
            "idle_ready_zero_workers",
            "live_task_xml",
            "quotas",
            "preservation",
            "application_health",
            "fresh_dependency_audit_provenance",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--dependency-audit", type=Path, required=True)
    args = parser.parse_args()
    try:
        body = args.plan.read_bytes()
        if digest(body) != args.sha256:
            raise ValueError("PLAN_HASH_MISMATCH")
        plan = json.loads(body)
        folder = args.plan.parent
        result = review(
            plan,
            (folder / "nse-task-original.xml").read_bytes().decode(),
            (folder / "nse-task-proposed-INACTIVE.xml").read_bytes().decode(),
            json.loads(args.runtime_report.read_bytes()),
            json.loads(args.dependency_audit.read_bytes()),
            now=datetime.now(UTC),
        )
    except (OSError, ValueError, KeyError, TypeError):
        # Do not print arbitrary file content, paths, values or OS exceptions.
        print(json.dumps({"status": "READ_ONLY_REVIEW_REJECTED", "task_changes": 0}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
