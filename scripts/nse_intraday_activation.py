"""Prepare and verify a two-file source activation; execution needs a new exact grant.

Preparation/verification never contacts a provider or NTP server, starts workers,
changes tasks, installs packages, or changes protected observations/forecasts.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts import nse_collector_cutover as cutover

from alphalens_api.auth.permissions import restrict, verify

ORDER = ("workers/nse_market/engine.py", "workers/nse_market/daily.py")
SOURCE_COMMIT = "4ed22cca8eb668a54c3d1510d38240fde5543f08"
ACTIVE_COMMIT = "6a5b73af588624cadc1e464d8ca90b5944421893"
SCOPE = "TWO_FILE_INTRADAY_V3_SOURCE_ACTIVATION"
PROCEDURE = """# Approval-gated source-only procedure (DO NOT EXECUTE DURING PREPARATION)

The CLI exposes prepare and verify-plan only. There is no activation command.
An operator must approve the exact plan.json SHA256, both source hashes, proposed
runtime fingerprint and conditional source rollback. Previous task-action grants
do not authorize this source replacement. Keep the approval with private evidence.

Before any write, load_plan(folder, approved_sha) must verify the protected plan
and every artifact. Run verify_plan from the reviewed preparation checkout and
patched interpreter with PYTHONDONTWRITEBYTECODE=1. Record new read-only database,
full 2485-file/47-alert/945-forecast-body preservation and zero-advisory dependency
checks, and compare their runtime/source identities to this plan. Stop if they
differ or if the plan has expired. The verify-plan receipt explicitly covers only
its documented subset; it never grants authorization or clears the remaining gates.

Recheck both exact task XMLs, all active collector/launcher processes, Ready/enabled
state, remaining trigger distance, unchanged config/approval/request ledgers, stable
AC and untouched reservations immediately before EACH byte replacement. A failed
gate means stop. Do not disable or modify tasks to create an idle window.

After a NEW grant and all gates, the reviewed replace_sources(active, folder, plan,
rollback=False, checkpoint=guard) primitive applies engine.py FIRST, daily.py SECOND.
The guard must run task_invariants(plan) at every checkpoint, compare unchanged
request/reservation state, and record private before/after receipts. Original and
proposed exact disk bytes are protected artifacts; source-only.patch is review aid,
not an instruction to merge, normalize line endings, or reset the checkout.

Post-apply: compare both file hashes and recompute candidate_identity using the
SAME patched interpreter; require the exact proposed fingerprint. With bytecode
writes disabled, compile/import the two modules offline without running collectors.
Keep HEAD at active_commit with exactly these two reviewed tracked modifications;
do not require a clean working tree after intended activation. Verify tasks,
config, reservations, candles, original forecast bodies and alerts unchanged.
Do not start a worker: await only an existing authorized trigger. Correlate actual
worker exit, clock evidence, GETs, durable terminal receipt and accepted candles.
An empty response or unavailable independent clock is not successful collection.

Conditional rollback requires a NEW grant that explicitly permits it, exact current
tasks idle/Ready, zero processes, safe AC and BOTH files matching reviewed old/new
hashes. Call replace_sources(active, folder, plan, rollback=True, checkpoint=guard).
Restore daily.py FIRST, engine.py SECOND, including a partial-apply state. Unknown
edits block overwrite; retain evidence and escalate. Recompute the original runtime
fingerprint and verify byte-for-byte originals, clean original HEAD, task hashes and
unchanged ledgers/data. Record the failure and rollback. No git reset, task changes,
package changes, reservation repair/reset, data rollback or manual collection.

This rollback retains the SAME patched zero-advisory runtime. It does not restore
the older 41-advisory interpreter. Ancestor interruption, power instability and
unavailable clock calibration remain independent faults requiring their own evidence.
"""


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def write_new(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    restrict(path)


def checked_path(root: Path, relative: str) -> Path:
    if relative not in ORDER:
        raise ValueError("SOURCE_PATH_NOT_REVIEWED")
    path = root / relative
    for entry in (path, *path.parents):
        if entry.is_symlink() or entry.is_junction():
            raise ValueError("SOURCE_REPARSE_REJECTED")
        if entry == root:
            break
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("SOURCE_PATH_OUTSIDE_WORKTREE")
    return path


def collector_process_count(active: Path) -> int:
    """Use the ACTIVE config path, never the isolated review tool's own checkout."""
    import ctypes

    if sys.platform != "win32":
        raise ValueError("NATIVE_WINDOWS_PROCESS_QUERY_REQUIRED")
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer)):
        raise ValueError("NATIVE_WINDOWS_DIRECTORY_UNAVAILABLE")
    shell = Path(buffer.value) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    config = cutover.native(active / ".local-data/full-nse-runtime/market-workflow-500.json")
    code = (
        "$ErrorActionPreference='Stop';$config='" + config.replace("'", "''") + "';"
        "$p=@(Get-CimInstance Win32_Process | Where-Object {"
        "$_.Name -in @('python.exe','pythonw.exe','cmd.exe') -and $_.CommandLine -and "
        "$_.CommandLine.IndexOf($config,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and "
        "($_.CommandLine -match 'workers[.]nse_market|"
        "run-nse-collector-isolated|run-nse-market[.]cmd')});"
        "[int]$p.Count"
    )
    return int(
        subprocess.check_output([str(shell), "-NoProfile", "-NonInteractive", "-Command", code])
    )


def state_snapshot(config: Path) -> dict[str, Any]:
    """Immutable receipt hashes and logical ledgers; no SQLite initialization or writes."""
    from workers.nse_market import operational, reliability

    cfg = operational.configured(config)
    runs = cfg.root / "operational/runs"
    state = {
        "approval_sha256": cutover.digest(cfg.root / "operational/collection-approval.json"),
        "run_receipts": {p.name: cutover.digest(p) for p in sorted(runs.glob("*.json"))},
        "shared_request_accounting": reliability._request_counts(cfg.provider_root),
        "market_pointer_sha256": cutover.digest(cfg.root / "market-view-latest.json"),
        "scores_pointer_sha256": cutover.digest(cfg.root / "scores-latest.json"),
    }
    return state


def source_inventory(root: Path) -> dict[str, str]:
    def checksum(path: Path) -> str:
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("SOURCE_INVENTORY_ESCAPE")
        for entry in (path, *path.parents):
            if entry.is_symlink() or entry.is_junction():
                raise ValueError("SOURCE_INVENTORY_REPARSE_REJECTED")
            if entry == root:
                break
        return cutover.digest(path)

    result = {}
    for folder in cutover.SOURCE_ROOTS:
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".json", ".sql", ".toml", ".cmd"}:
                result[path.relative_to(root).as_posix()] = checksum(path)
    for name in (
        "uv.lock",
        "pyproject.toml",
        "scripts/nse_collector_cutover.py",
        *cutover.FOCUSED_TESTS,
    ):
        result[name] = checksum(root / name)
    return result


def project_identity(before: dict[str, Any], inventory: dict[str, str]) -> dict[str, Any]:
    value = {k: v for k, v in before.items() if k != "fresh_fingerprint_sha256"}
    value["source"] = {"files": len(inventory), "sha256": sha(encoded(inventory))}
    value["fresh_fingerprint_sha256"] = sha(encoded(value))
    return value


def task_invariants(plan: dict[str, Any], *, rollback: bool = False) -> dict[str, Any]:
    task, other = cutover.query_task(cutover.TASK), cutover.query_task(cutover.PRESERVED_TASK)
    if sha(task["xml"].encode()) != plan["task_xml_sha256"]:
        raise ValueError("MARKET_TASK_CHANGED")
    if sha(other["xml"].encode()) != plan["watchlist_xml_sha256"]:
        raise ValueError("EXCLUDED_WATCHLIST_CHANGED")
    if task["state"] != "Ready" or task["matching_collector_process_count"] != 0:
        raise ValueError("IDLE_READY_ZERO_WORKERS_REQUIRED")
    if collector_process_count(Path(plan["active_root"])) != 0:
        raise ValueError("ACTIVE_CHECKOUT_COLLECTOR_PROCESS_PRESENT")
    if task["triggers_enabled"] != [True, True, True]:
        raise ValueError("ORIGINAL_ENABLED_TRIGGERS_REQUIRED")
    if not rollback:
        next_run = datetime.fromisoformat(task["next_run_at"].replace("Z", "+00:00"))
        if next_run <= datetime.now(UTC) + timedelta(minutes=15):
            raise ValueError("FIFTEEN_MINUTE_TRIGGER_DISTANCE_REQUIRED")
    return {k: v for k, v in task.items() if k != "xml"}


def power_observation(task: dict[str, Any], *, sample_seconds: int) -> dict[str, Any]:
    shell = Path(task["system_command"]).parent / "WindowsPowerShell/v1.0/powershell.exe"
    code = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
$samples=@(); $timer=[Diagnostics.Stopwatch]::StartNew()
do {
  $online=[System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus
  $samples+=@{at=(Get-Date).ToUniversalTime().ToString('o');ac=($online.ToString() -eq 'Online')}
  if ($timer.Elapsed.TotalSeconds -ge __SECONDS__) {break}
  Start-Sleep -Seconds 2
} while ($true)
$filter=@{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';Id=105;
StartTime=(Get-Date).AddMinutes(-10)}
$errors=@(); $events=@(Get-WinEvent -FilterHashtable $filter `
  -ErrorAction SilentlyContinue -ErrorVariable errors)
$readErrors=@($errors | Where-Object {$_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'})
$dc=@($events | Where-Object { [xml]$x=$_.ToXml();
  @($x.Event.EventData.Data | Where-Object {
    $_.Name -eq 'AcOnline' -and $_.InnerText -ne 'true'}).Count -gt 0 })
@{samples=$samples;sample_seconds=$timer.Elapsed.TotalSeconds;recent_dc_events=$dc.Count;
power_history_available=($readErrors.Count -eq 0)} | ConvertTo-Json -Depth 5 -Compress
""".replace("__SECONDS__", str(sample_seconds))
    raw = subprocess.check_output([str(shell), "-NoProfile", "-NonInteractive", "-Command", code])
    value: dict[str, Any] = json.loads(raw)
    value["activation_power_ready"] = (
        sample_seconds >= 60
        and value["sample_seconds"] >= 60
        and all(row["ac"] for row in value["samples"])
        and value["power_history_available"]
        and value["recent_dc_events"] == 0
    )
    return value


def prepare(
    active: Path, source: Path, config: Path, evidence: Path, destination: Path
) -> dict[str, Any]:
    if destination.exists() or destination.is_symlink():
        raise ValueError("NEW_PROTECTED_PLAN_DIRECTORY_REQUIRED")
    if git(active, "rev-parse", "HEAD").decode().strip() != ACTIVE_COMMIT:
        raise ValueError("ACTIVE_COMMIT_CHANGED")
    if git(active, "status", "--porcelain").strip():
        raise ValueError("ACTIVE_TRACKED_OR_UNTRACKED_CHANGES")
    all_changed = git(source, "diff", "--name-only", ACTIVE_COMMIT, "HEAD").decode().splitlines()
    inventory = source_inventory(active)
    before = cutover.candidate_identity(
        active, active / ".local-data/production-collector-runtime-20261024/venv"
    )
    if not all(before["checks"].values()):
        raise ValueError("ACTIVE_PACKAGE_INTEGRITY_FAILED")
    task, watchlist = cutover.query_task(cutover.TASK), cutover.query_task(cutover.PRESERVED_TASK)
    destination.mkdir(parents=True)
    restrict(destination)
    files = {}
    for relative in ORDER:
        original = checked_path(active, relative).read_bytes()
        proposed = checked_path(source, relative).read_bytes()
        expected = git(source, "rev-parse", f"{SOURCE_COMMIT}:{relative}").decode().strip()
        actual = (
            git(source, "hash-object", "--path", relative, str(source / relative)).decode().strip()
        )
        if expected != actual:
            raise ValueError("PROPOSED_BYTES_NOT_REVIEWED_SOURCE_COMMIT")
        ast.parse(proposed)
        name = Path(relative).name
        write_new(destination / "original" / name, original)
        write_new(destination / "proposed" / name, proposed)
        files[relative] = {
            "original_sha256": sha(original),
            "proposed_sha256": sha(proposed),
            "source_git_blob": expected,
            "original_artifact": "original/" + name,
            "proposed_artifact": "proposed/" + name,
        }
        inventory[relative] = sha(proposed)
    # Reject any unnoticed collector import/dependency/launcher/clock change.
    desired_inventory = source_inventory(source)
    if inventory != desired_inventory:
        raise ValueError("UNRELATED_COLLECTOR_SOURCE_CHANGE")
    proposed_identity = project_identity(before, inventory)
    write_new(destination / "activation-tool.py", Path(__file__).read_bytes())
    write_new(
        destination / "source-only.patch",
        git(source, "diff", "--binary", ACTIVE_COMMIT, SOURCE_COMMIT, "--", *ORDER),
    )
    write_new(destination / "market-task.xml", task["xml"].encode())
    write_new(destination / "watchlist-task.xml", watchlist["xml"].encode())
    write_new(destination / "runtime-current.json", encoded(before))
    write_new(destination / "runtime-proposed.json", encoded(proposed_identity))
    checks = {}
    for name in (
        "qualification.json",
        "dependency-audit.json",
        "preservation.json",
        "forecasts.json",
        "provider-review.json",
        "failure-review.json",
    ):
        value = json.loads((evidence / name).read_bytes())
        checks[name] = value
        write_new(destination / "evidence" / name, encoded(value))
    audit = checks["dependency-audit.json"]
    if sum(len(row.get("vulns", [])) for row in audit["dependencies"]):
        raise ValueError("DEPENDENCY_SECURITY_NOT_CLEAR")
    if (
        checks["preservation.json"].get("verified_files") != 2485
        or checks["preservation.json"].get("original_alerts") != 47
    ):
        raise ValueError("PROTECTED_PRESERVATION_NOT_VERIFIED")
    if checks["forecasts.json"].get("original_bodies_preserved") != 945:
        raise ValueError("ORIGINAL_FORECASTS_NOT_PRESERVED")
    if checks["qualification.json"].get("all_required_checks_passed") is not True:
        raise ValueError("OFFLINE_QUALIFICATION_NOT_PASSED")
    qualification = checks["qualification.json"]
    if (
        qualification.get("preparation_commit") != git(source, "rev-parse", "HEAD").decode().strip()
        or qualification.get("source_commit") != SOURCE_COMMIT
        or qualification.get("active_runtime_fingerprint") != before["fresh_fingerprint_sha256"]
    ):
        raise ValueError("QUALIFICATION_SOURCE_OR_RUNTIME_IDENTITY_MISMATCH")
    write_new(destination / "state-before.json", encoded(state_snapshot(config)))
    write_new(destination / "procedure.md", PROCEDURE.encode())
    artifacts = {
        p.relative_to(destination).as_posix(): cutover.digest(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    plan = {
        "version": "alphalens.intraday-source-activation.v1",
        "status": "BLOCKED_APPROVAL",
        "scope": SCOPE,
        "created_at": datetime.now(UTC).isoformat(),
        "active_root": str(active),
        "active_commit": ACTIVE_COMMIT,
        "source_root": str(source),
        "source_commit": SOURCE_COMMIT,
        "preparation_commit": git(source, "rev-parse", "HEAD").decode().strip(),
        "source_files": files,
        "apply_order": list(ORDER),
        "rollback_order": list(reversed(ORDER)),
        "excluded_candidate_changes": [p for p in all_changed if p not in ORDER],
        "current_source_fingerprint": before["fresh_fingerprint_sha256"],
        "proposed_source_fingerprint": proposed_identity["fresh_fingerprint_sha256"],
        "proposed_fingerprint_basis": (
            "SAME_VERIFIED_INSTALLATION_WITH_ONLY_TWO_REVIEWED_SOURCE_FILES_REPLACED;"
            "NOT_YET_OBSERVED_LIVE"
        ),
        "config": str(config),
        "config_sha256": cutover.digest(config),
        "policy": cutover.policy_identity(config),
        "task_xml_sha256": sha(task["xml"].encode()),
        "watchlist_xml_sha256": sha(watchlist["xml"].encode()),
        "task_invariants_sha256": cutover.invariant_hash(task["xml"]),
        "runtime": str(active / ".local-data/production-collector-runtime-20261024/venv"),
        "expires_at": task["next_run_at"],
        "preflight_limit": (
            "READ_ONLY_IDENTITY_AND_POWER_SUBSET;"
            "FRESH_FULL_SECURITY_PRESERVATION_DATABASE_AND_OPERATOR_GRANT_STILL_REQUIRED"
        ),
        "activation_preconditions": [
            "NEW_EXPLICIT_OPERATOR_GRANT_BINDS_EXACT_PLAN_SHA_AND_SCOPE",
            "ALL_ARTIFACT_AND_SOURCE_HASHES_UNCHANGED;ACTIVE_HEAD_AND_WORKTREE_MATCH",
            "ENABLED_IDLE_READY_TASK;ZERO_COLLECTOR_PROCESSES;NEXT_TRIGGER_MORE_THAN_15_MINUTES",
            "60_SECONDS_AC_SAMPLES_AND_NO_DC_EVENT_IN_PREVIOUS_10_MINUTES",
            "PACKAGE_RECORDS_AND_RUNTIME_IDENTICAL;DEPENDENCY_AUDIT_HAS_ZERO_ADVISORIES",
            "CONFIG_APPROVAL_DATABASE_CREDENTIAL_TARGETS_AND_REQUEST_POLICIES_UNCHANGED",
            "NO_ACTIVE_RESERVATION_INTERRUPTED;HISTORICAL_MISSING_TERMINALS_RETAINED",
            "READ_ONLY_DATABASE_AND_ALL_PRESERVATION_CHECKS_PASS",
        ],
        "rollback_conditions": [
            "PARTIAL_APPLICATION_OR_POST_APPLY_SOURCE_FINGERPRINT_OR_IMPORT_CHECK_FAILURE",
            "REVIEWED_NEW_ROUTE_CONTRACT_OR_PERMISSION_FAILURE_DURING_AN_EXISTING_AUTHORIZED_RUN",
            "REQUEST_ACCOUNTING_OR_DATA_INTEGRITY_VIOLATION_ATTRIBUTABLE_TO_THE_SOURCE_CHANGE",
        ],
        "rollback_preconditions": [
            "OPERATOR_GRANT_EXPLICITLY_ALLOWS_CONDITIONAL_SOURCE_ROLLBACK",
            "TASKS_IDENTICAL_AND_IDLE_READY;ZERO_COLLECTORS;EVERY_FILE_HAS_A_REVIEWED_OLD_OR_NEW_HASH",
            "RESTORE_DAILY_FIRST_THEN_ENGINE;VERIFY_ORIGINAL_SOURCE_FINGERPRINT",
        ],
        "rollback_restores": (
            "ORIGINAL_TWO_SOURCE_FILES_ONLY;SAME_PATCHED_ZERO_ADVISORY_INTERPRETER;"
            "NO_41_ADVISORY_RUNTIME_SWITCH"
        ),
        "independent_failures_not_fixed_or_automatically_cured": [
            "21_30_ANCESTOR_INTERRUPTION_AND_MISSING_TERMINAL",
            "22_30_INDEPENDENT_CLOCK_UNAVAILABLE",
            "PROVIDER_EMPTY_ARRAYS_OR_UNVERIFIED_AFTER_CLOSE_FINALITY",
        ],
        "forbidden_actions": [
            "TASK_MUTATION",
            "MANUAL_COLLECTION",
            "EXTRA_PROVIDER_OR_NTP_PROBE",
            "INSTALLATION_OR_INTERPRETER_CHANGE",
            "QUOTA_RESET",
            "DATA_OR_FORECAST_ROLLBACK",
            "PUBLIC_DEPLOYMENT",
        ],
        "artifacts_sha256": artifacts,
    }
    task_invariants(plan)
    write_new(destination / "plan.json", json.dumps(plan, indent=2, sort_keys=True).encode())
    return {
        "status": "BLOCKED_APPROVAL",
        "plan_path": str(destination / "plan.json"),
        "plan_sha256": cutover.digest(destination / "plan.json"),
        "current_source_fingerprint": plan["current_source_fingerprint"],
        "proposed_source_fingerprint": plan["proposed_source_fingerprint"],
        "activation_performed": False,
    }


def load_plan(folder: Path, expected_sha: str) -> dict[str, Any]:
    verify(folder)
    if cutover.digest(folder / "plan.json") != expected_sha:
        raise ValueError("APPROVED_PLAN_HASH_CHANGED")
    plan: dict[str, Any] = json.loads((folder / "plan.json").read_bytes())
    # JSON sorting may change object order; apply_order is the ordering authority.
    if plan.get("scope") != SCOPE or set(plan["source_files"]) != set(ORDER):
        raise ValueError("UNREVIEWED_SOURCE_SCOPE")
    if plan["apply_order"] != list(ORDER) or plan["rollback_order"] != list(reversed(ORDER)):
        raise ValueError("DEPENDENCY_ORDER_CHANGED")
    for relative, value in plan["source_files"].items():
        for label in ("original", "proposed"):
            name = label + "/" + Path(relative).name
            if (
                value[label + "_artifact"] != name
                or plan["artifacts_sha256"].get(name) != value[label + "_sha256"]
            ):
                raise ValueError("SOURCE_ARTIFACT_MAPPING_REJECTED")
    for relative, checksum in plan["artifacts_sha256"].items():
        path = folder / relative
        entries = [path]
        parent = path.parent
        while parent.is_relative_to(folder):
            entries.append(parent)
            if parent == folder:
                break
            parent = parent.parent
        if not path.resolve().is_relative_to(folder.resolve()) or any(
            p.is_symlink() or p.is_junction() for p in entries
        ):
            raise ValueError("PLAN_ARTIFACT_PATH_REJECTED")
        if cutover.digest(path) != checksum:
            raise ValueError("PLAN_ARTIFACT_CHANGED")
    return plan


def verify_plan(folder: Path, expected_sha: str, *, power_seconds: int = 60) -> dict[str, Any]:
    plan = load_plan(folder, expected_sha)
    if cutover.digest(Path(__file__)) != plan["artifacts_sha256"]["activation-tool.py"]:
        raise ValueError("REVIEWED_VERIFIER_IMPLEMENTATION_CHANGED")
    if datetime.now(UTC) >= datetime.fromisoformat(
        plan["expires_at"].replace("Z", "+00:00")
    ) - timedelta(minutes=15):
        raise ValueError("PLAN_EXPIRED_BEFORE_NEXT_TRIGGER")
    active = Path(plan["active_root"])
    if (
        git(active, "rev-parse", "HEAD").decode().strip() != plan["active_commit"]
        or git(active, "status", "--porcelain").strip()
    ):
        raise ValueError("ACTIVE_WORKTREE_CHANGED")
    for relative, value in plan["source_files"].items():
        if cutover.digest(checked_path(active, relative)) != value["original_sha256"]:
            raise ValueError("ACTIVE_SOURCE_CHANGED")
    if cutover.digest(Path(plan["config"])) != plan["config_sha256"]:
        raise ValueError("CONFIG_CHANGED")
    if cutover.policy_identity(Path(plan["config"])) != plan["policy"]:
        raise ValueError("APPROVED_POLICY_CHANGED")
    if state_snapshot(Path(plan["config"])) != json.loads(
        (folder / "state-before.json").read_bytes()
    ):
        raise ValueError("RESERVATION_ACCOUNTING_OR_PUBLICATION_STATE_CHANGED")
    task = task_invariants(plan)
    identity = cutover.candidate_identity(active, Path(plan["runtime"]))
    if identity["fresh_fingerprint_sha256"] != plan["current_source_fingerprint"]:
        raise ValueError("RUNTIME_OR_SOURCE_IDENTITY_CHANGED")
    power = power_observation(task, sample_seconds=power_seconds)
    # A scheduler start or another edit during the expensive checks invalidates the receipt.
    task = task_invariants(plan)
    if (
        cutover.candidate_identity(active, Path(plan["runtime"]))["fresh_fingerprint_sha256"]
        != plan["current_source_fingerprint"]
    ):
        raise ValueError("RUNTIME_CHANGED_DURING_PREFLIGHT")
    if source_inventory(active) != source_inventory(Path(plan["source_root"])) | {
        relative: value["original_sha256"] for relative, value in plan["source_files"].items()
    }:
        raise ValueError("SOURCE_CHANGED_DURING_PREFLIGHT")
    if cutover.digest(Path(plan["config"])) != plan["config_sha256"] or state_snapshot(
        Path(plan["config"])
    ) != json.loads((folder / "state-before.json").read_bytes()):
        raise ValueError("CONFIG_OR_STATE_CHANGED_DURING_PREFLIGHT")
    return {
        "status": "BLOCKED_APPROVAL",
        "plan_integrity": "VERIFIED_COMPLETE",
        "observed_at": datetime.now(UTC).isoformat(),
        "task": task,
        "power": power,
        "read_only_identity_and_power_subset_passed": power["activation_power_ready"],
        "activation_authorized": False,
        "remaining_required_gates": [
            "NEW_EXACT_OPERATOR_APPROVAL",
            "FRESH_DEPENDENCY_AUDIT",
            "FULL_RESEARCH_ALERT_AND_FORECAST_PRESERVATION",
            "READ_ONLY_DATABASE_PROBE",
            "IMMEDIATE_QUIESCENCE_RECHECK_BEFORE_EACH_FILE_REPLACEMENT",
        ],
        "activation_performed": False,
        "provider_requests": 0,
        "ntp_requests": 0,
    }


def replace_sources(
    active: Path,
    folder: Path,
    plan: dict[str, Any],
    *,
    rollback: bool,
    checkpoint: Callable[[str, str], None] = lambda *_: None,
) -> list[str]:
    """Reviewed byte replacement, used only after live approval or in TEST_ONLY fixtures."""
    if set(plan["source_files"]) != set(ORDER):
        raise ValueError("UNREVIEWED_SOURCE_SCOPE")
    states = {}
    for relative in ORDER:
        value = plan["source_files"][relative]
        current = cutover.digest(checked_path(active, relative))
        if current not in {value["original_sha256"], value["proposed_sha256"]}:
            raise ValueError("UNKNOWN_SOURCE_BYTES_DO_NOT_OVERWRITE")
        states[relative] = current
    target = "original" if rollback else "proposed"
    if all(states[p] == plan["source_files"][p][target + "_sha256"] for p in ORDER):
        return []
    if not rollback and any(states[p] != plan["source_files"][p]["original_sha256"] for p in ORDER):
        raise ValueError("PARTIAL_APPLY_REQUIRES_REVIEWED_ROLLBACK")
    changed = []
    for relative in reversed(ORDER) if rollback else ORDER:
        value = plan["source_files"][relative]
        path = checked_path(active, relative)
        checkpoint("before", relative)
        if cutover.digest(path) != states[relative]:
            raise ValueError("SOURCE_CHANGED_DURING_OPERATION")
        if value[target + "_artifact"] != target + "/" + Path(relative).name:
            raise ValueError("SOURCE_ARTIFACT_MAPPING_REJECTED")
        artifact = folder / value[target + "_artifact"]
        if (
            not artifact.resolve().is_relative_to(folder.resolve())
            or artifact.is_symlink()
            or artifact.is_junction()
        ):
            raise ValueError("SOURCE_ARTIFACT_PATH_REJECTED")
        if artifact.parent.is_symlink() or artifact.parent.is_junction():
            raise ValueError("SOURCE_ARTIFACT_PATH_REJECTED")
        body = artifact.read_bytes()
        if sha(body) != value[target + "_sha256"]:
            raise ValueError("REVIEWED_SOURCE_ARTIFACT_CHANGED")
        staged = path.with_name(path.name + ".activation-" + uuid.uuid4().hex + ".tmp")
        with staged.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        if cutover.digest(path) != value[target + "_sha256"]:
            raise ValueError("SOURCE_REPLACEMENT_HASH_MISMATCH")
        changed.append(relative)
        checkpoint("after", relative)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("prepare")
    for name in ("active-root", "source-root", "config", "evidence", "output"):
        new.add_argument("--" + name, type=Path, required=True)
    check = sub.add_parser("verify-plan")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--expected-sha256", required=True)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.active_root.absolute(),
            args.source_root.absolute(),
            args.config.absolute(),
            args.evidence.absolute(),
            args.output.absolute(),
        )
    else:
        result = verify_plan(args.plan.absolute(), args.expected_sha256)
        write_new(args.output, json.dumps(result, indent=2).encode())
        result = {key: value for key, value in result.items() if key != "task"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
