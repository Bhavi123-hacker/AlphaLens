"""Prepare/verify a private action-only collector cutover. No live mutation mode exists."""

from __future__ import annotations

import argparse
import base64
import csv
import ctypes
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any

TASK = "AlphaLens-Private-NSE-Market-Research"
PRESERVED_TASK = "AlphaLens-Private-EOD-Watchlist"
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
SOURCE_ROOTS = (
    "workers",
    "apps/api/src",
    "ml/data/src",
    "ml/features/src",
    "ml/labels/src",
    "ml/training/src",
    "ml/evaluation/src",
    "backtesting/src",
    "decision/src",
    "portfolio/src",
    "db",
    "scripts/windows",
)
FOCUSED_TESTS = (
    "tests/unit/test_nse_collector_cutover.py",
    "tests/unit/test_nse_process_diagnostics.py",
    "tests/unit/test_nse_windows_supervision.py",
    "tests/unit/test_nse_collection_faults.py",
    "tests/unit/test_nse_daily_market_publication.py",
    "tests/unit/test_nse_daily_fair_selection.py",
    "tests/unit/test_nse_market_operational.py",
    "tests/unit/test_nse_scheduled_preflight.py",
    "tests/unit/test_operational_daily_clock.py",
    "tests/unit/test_daily_clock_refresh.py",
    "tests/unit/test_daily_clock_continuity.py",
    "tests/unit/test_p34_quote_clock.py",
)
# Hardened parser is already present in the frozen audit runtime. Its absence
# blocks this tool; no unsafe XML-parser fallback is used.
ET = importlib.import_module("defusedxml.ElementTree")


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def native(path: Path) -> str:
    return str(path).replace("/", "\\")


def parse(xml: str) -> Any:
    if len(xml) > 262144 or "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ValueError("TASK_XML_CONTRACT_REJECTED")
    value = ET.fromstring(xml)
    if value.tag != "{" + NS + "}Task":
        raise ValueError("TASK_XML_CONTRACT_REJECTED")
    return value


def action(value: Any) -> dict[str, str]:
    actions = value.find("{" + NS + "}Actions")
    if actions is None or len(actions) != 1 or actions[0].tag != "{" + NS + "}Exec":
        raise ValueError("SINGLE_EXECUTABLE_TASK_ACTION_REQUIRED")
    return {
        name: actions[0].findtext("{" + NS + "}" + name, "")
        for name in ("Command", "Arguments", "WorkingDirectory")
    }


def canonical(value: Any, *, omit_actions: bool = False) -> Any:
    return [
        value.tag,
        sorted(value.attrib.items()),
        (value.text or "").strip(),
        [
            canonical(child, omit_actions=omit_actions)
            for child in value
            if not (omit_actions and child.tag == "{" + NS + "}Actions")
        ],
    ]


def invariant_hash(xml: str) -> str:
    return hashlib.sha256(encoded(canonical(parse(xml), omit_actions=True))).hexdigest()


def proposal(
    xml: str, repo: Path, config: Path, *, native_defaults: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Pure XML proposal: reviewed known arguments only, all other fields invariant."""
    value = parse(xml)
    before = action(value)
    expected = (
        '/d /c ""'
        + native(repo / "scripts/windows/run-nse-market.cmd")
        + '" "'
        + native(config)
        + '" auto --scheduled"'
    )
    command = PureWindowsPath(before["Command"])
    expected_command = (native_defaults or {}).get(
        "system_command", "C:\\Windows\\System32\\cmd.exe"
    )
    if (
        not command.is_absolute()
        or str(command).casefold() != expected_command.casefold()
        or before["Arguments"] != expected
        or before["WorkingDirectory"].casefold() != native(repo).casefold()
    ):
        raise ValueError("TASK_ACTION_REVIEW_REQUIRED")
    required = {
        "RunLevel": "LeastPrivilege",
        "LogonType": "InteractiveToken",
        "MultipleInstancesPolicy": "IgnoreNew",
        "StartWhenAvailable": "true",
    }
    for name, expected_value in required.items():
        actual = value.findtext(".//{" + NS + "}" + name)
        if (
            name == "RunLevel"
            and actual is None
            and (native_defaults or {}).get("principal_run_level") == "Limited"
        ):
            actual = "LeastPrivilege"
        if actual != expected_value:
            raise ValueError("TASK_PRINCIPAL_OR_RECOVERY_POLICY_REJECTED")
    triggers = value.find("{" + NS + "}Triggers")
    times = []
    for index, trigger in enumerate(triggers if triggers is not None else []):
        stamp = trigger.findtext("{" + NS + "}StartBoundary", "")
        enabled = trigger.findtext("{" + NS + "}Enabled")
        native_enabled = (native_defaults or {}).get("triggers_enabled", [])
        if enabled is None and index < len(native_enabled) and native_enabled[index] is True:
            enabled = "true"
        if enabled != "true":
            raise ValueError("APPROVED_TASK_TRIGGER_POLICY_REJECTED")
        times.append(datetime.fromisoformat(stamp).strftime("%H:%M"))
    if sorted(times) != ["20:30", "21:30", "22:30"]:
        raise ValueError("APPROVED_TASK_TRIGGER_POLICY_REJECTED")
    after = {
        "Command": before["Command"],
        "Arguments": '/d /c ""'
        + native(repo / "scripts/windows/run-nse-collector-isolated.cmd")
        + '" "'
        + native(config)
        + '""',
        "WorkingDirectory": before["WorkingDirectory"],
    }
    exec_node = value.find(".//{" + NS + "}Exec")
    if exec_node is None:
        raise ValueError("SINGLE_EXECUTABLE_TASK_ACTION_REQUIRED")
    for name, content in after.items():
        node = exec_node.find("{" + NS + "}" + name)
        if node is None:
            node = ET.SubElement(exec_node, "{" + NS + "}" + name)
        node.text = content
    proposed_xml = ET.tostring(value, encoding="unicode")
    if invariant_hash(xml) != invariant_hash(proposed_xml):
        raise ValueError("ACTION_ONLY_TASK_TRANSITION_REQUIRED")
    return {
        "before_action": before,
        "proposed_action": after,
        "proposed_xml": proposed_xml,
        "invariants_sha256": invariant_hash(xml),
    }


def query_task(name: str) -> dict[str, Any]:
    """Fixed local getter/export only. Captured XML/arguments never reach stdout."""
    if sys.platform != "win32" or name not in {TASK, PRESERVED_TASK}:
        raise ValueError("FIXED_WINDOWS_TASK_READ_REQUIRED")
    worker_config = native(
        Path(__file__).resolve().parents[1]
        / ".local-data/full-nse-runtime/market-workflow-500.json"
    ).replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop';"
        f"$task=Get-ScheduledTask -TaskName '{name}';"
        f"$info=Get-ScheduledTaskInfo -TaskName '{name}';"
        f"$workerConfig='{worker_config}';"
        "$workers=@(Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" |"
        "Where-Object{$_.CommandLine -and "
        "$_.CommandLine.IndexOf('workers.nse_market',[StringComparison]::Ordinal) -ge 0 -and "
        "$_.CommandLine.IndexOf($workerConfig,[StringComparison]::OrdinalIgnoreCase) -ge 0});"
        f"@{{xml=[string](Export-ScheduledTask -TaskName '{name}');"
        "state=[string]$task.State;last_result=[long]$info.LastTaskResult;"
        "matching_collector_process_count=[int]$workers.Count;"
        "principal_run_level=[string]$task.Principal.RunLevel;"
        "triggers_enabled=@($task.Triggers|ForEach-Object{[bool]$_.Enabled});"
        "next_run_at=$info.NextRunTime.ToUniversalTime().ToString('o')}|ConvertTo-Json -Compress"
    )
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer)):
        raise ValueError("NATIVE_WINDOWS_DIRECTORY_UNAVAILABLE")
    shell = Path(buffer.value) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        check=False,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise ValueError("LOCAL_TASK_EXPORT_UNAVAILABLE")
    value: dict[str, Any] = json.loads(result.stdout)
    value["system_command"] = str(Path(buffer.value) / "System32/cmd.exe")
    parse(value["xml"])
    return value


def versions(site: Path) -> dict[str, str]:
    return {
        str(item.metadata["Name"]).lower(): item.version
        for item in importlib.metadata.distributions(path=[str(site)])
    }


def installed_records(venv: Path) -> dict[str, Any]:
    """Verify immutable installed files against RECORD; do not import package code."""
    site = venv / "Lib/site-packages"
    resolved_root = venv.resolve()
    checked: dict[str, str] = {}
    metadata_records: dict[str, str] = {}
    unhashed: list[str] = []
    mismatches: list[str] = []
    skipped_bytecode = 0
    parents: dict[Path, Path] = {}
    hash_jobs: list[tuple[str, Path, str, str]] = []

    def resolve_file(path: Path) -> Path:
        if path.parent not in parents:
            parents[path.parent] = path.parent.resolve()
        parent = parents[path.parent]
        if not parent.is_relative_to(resolved_root):
            raise ValueError("INSTALLED_RECORD_PATH_REJECTED")
        return parent / path.name

    def reparse(metadata: os.stat_result) -> bool:
        return bool(getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)

    for record in sorted(site.glob("*.dist-info/RECORD")):
        resolved_record = resolve_file(record)
        if reparse(record.lstat()) or stat.S_ISLNK(record.lstat().st_mode):
            raise ValueError("INSTALLED_RECORD_PATH_REJECTED")
        metadata_records[str(record.relative_to(venv))] = digest(resolved_record)
        with record.open(encoding="utf-8", newline="") as stream:
            for relative, expected, _size in csv.reader(stream):
                target = site / Path(relative.replace("/", os.sep))
                if target.suffix == ".pyc":
                    skipped_bytecode += 1
                    continue
                resolved = resolve_file(target)
                label = str(resolved.relative_to(resolved_root))
                try:
                    metadata = target.lstat()
                except FileNotFoundError:
                    mismatches.append(label)
                    continue
                if reparse(metadata) or stat.S_ISLNK(metadata.st_mode):
                    raise ValueError("INSTALLED_RECORD_PATH_REJECTED")
                if not expected:
                    unhashed.append(label)
                    if stat.S_ISREG(metadata.st_mode):
                        checked[label] = digest(resolved)
                    else:
                        mismatches.append(label)
                    continue
                mode, wanted = expected.split("=", 1)
                if mode not in {"sha256", "sha384", "sha512"}:
                    raise ValueError("INSTALLED_RECORD_HASH_ALGORITHM_REJECTED")
                if not stat.S_ISREG(metadata.st_mode):
                    mismatches.append(label)
                    continue
                hash_jobs.append((label, resolved, mode, wanted))

    def verify_file(job: tuple[str, Path, str, str]) -> tuple[str, str, bool]:
        label, path, mode, wanted = job
        with path.open("rb") as body:
            actual = hashlib.file_digest(body, mode).digest()
        return label, actual.hex(), base64.urlsafe_b64encode(actual).decode().rstrip("=") == wanted

    # Bounded read-only hashing overlaps Windows file-open latency; no installers,
    # provider clients, estimator operations or background services are started.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for label, actual_hash, matches in pool.map(verify_file, hash_jobs):
            checked[label] = actual_hash
            if not matches:
                mismatches.append(label)
    if not metadata_records:
        raise ValueError("INSTALLED_DISTRIBUTION_RECORDS_REQUIRED")
    verified_files = len(checked)
    unregistered = []
    for path in sorted(venv.rglob("*")):
        if path.suffix.casefold() == ".pyc":
            continue
        metadata = path.lstat()
        if reparse(metadata) or stat.S_ISLNK(metadata.st_mode):
            raise ValueError("INSTALLED_RECORD_PATH_REJECTED")
        if not stat.S_ISREG(metadata.st_mode):
            continue
        label = str(resolve_file(path).relative_to(resolved_root))
        if label not in checked:
            checked[label] = digest(path)
            unregistered.append(label)
    return {
        "verified_files": verified_files,
        "fresh_fingerprinted_files": len(checked),
        "unregistered_files": unregistered,
        "mismatches": mismatches,
        "unhashed_record_entries": sorted(unhashed),
        "excluded_pyc_entries": skipped_bytecode,
        "files_sha256": hashlib.sha256(encoded(checked)).hexdigest(),
        "records_sha256": hashlib.sha256(encoded(metadata_records)).hexdigest(),
    }


def source_identity(repo: Path) -> dict[str, Any]:
    files: dict[str, str] = {}
    for root in SOURCE_ROOTS:
        for path in sorted((repo / root).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".json", ".sql", ".toml", ".cmd"}:
                if (
                    path.is_symlink()
                    or path.is_junction()
                    or not path.resolve().is_relative_to(repo.resolve())
                ):
                    raise ValueError("COLLECTOR_SOURCE_REPARSE_REJECTED")
                files[path.relative_to(repo).as_posix()] = digest(path)
    for name in ("uv.lock", "pyproject.toml", "scripts/nse_collector_cutover.py", *FOCUSED_TESTS):
        files[name] = digest(repo / name)
    return {"files": len(files), "sha256": hashlib.sha256(encoded(files)).hexdigest()}


def candidate_identity(repo: Path, runtime: Path) -> dict[str, Any]:
    receipt_path = runtime.parent / "installation-receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    if (
        receipt.get("install_exit") != 0
        or receipt.get("package_link_mode") != "copy"
        or receipt.get("shared_metadata_unchanged") is not True
    ):
        raise ValueError("PREVIOUS_FROZEN_INSTALLATION_RECEIPT_REQUIRED")
    for path in (runtime, *runtime.parents):
        if path.is_symlink() or path.is_junction():
            raise ValueError("CANDIDATE_RUNTIME_REPARSE_REJECTED")
        if path == repo:
            break
    if not runtime.resolve().is_relative_to((repo / ".local-data").resolve()):
        raise ValueError("ISOLATED_PRIVATE_RUNTIME_REQUIRED")
    config = dict(
        line.strip().split(" = ", 1)
        for line in (runtime / "pyvenv.cfg").read_text().splitlines()
        if " = " in line
    )
    base = Path(config.get("executable", str(Path(config["home"]) / "python.exe")))
    current_versions = versions(runtime / "Lib/site-packages")
    records = installed_records(runtime)
    checks = {
        "lock_matches_installation": digest(repo / "uv.lock") == receipt["lock_sha256"],
        "base_python_matches_installation": digest(base) == receipt["base_python_sha256"],
        "package_versions_match_installation": current_versions == receipt["packages"],
        "installed_record_hashes_match": not records["mismatches"],
    }
    identity = {
        "checks": checks,
        "records": records,
        "candidate_python_sha256": digest(runtime / "Scripts/python.exe"),
        "installation_receipt_sha256": digest(receipt_path),
        "pyvenv_config_sha256": digest(runtime / "pyvenv.cfg"),
        "source": source_identity(repo),
        "prior_bitwise_fingerprint_available": False,
    }
    identity["fresh_fingerprint_sha256"] = hashlib.sha256(encoded(identity)).hexdigest()
    return identity


def policy_identity(config: Path) -> dict[str, Any]:
    from workers.nse_market import operational

    configured = operational.configured(config)
    policy = operational.policy(configured)
    operational._approval(configured, policy)
    expected = {
        "expected_securities": 500,
        "max_stocks_per_run": 250,
        "max_requests_per_run": 600,
        "max_requests_per_day": 1800,
        "max_runs_per_day": 3,
        "cooldown_minutes": 60,
        "cadence_ist": ["20:30", "21:30", "22:30"],
    }
    if any(policy.get(key) != value for key, value in expected.items()):
        raise ValueError("EXACT_APPROVED_500_SECURITY_POLICY_REQUIRED")
    return {
        "config_sha256": digest(config),
        "policy_sha256": policy["policy_sha256"],
        "scope": expected,
        "recurring_acquisition_enabled": configured.recurring_acquisition_enabled,
    }


def prepare(repo: Path, output: Path, *, run_tests: bool = False) -> dict[str, Any]:
    """Only new private proposal artifacts and optional offline test outputs are writable."""
    from scripts.prepare_nse_collector_runtime import fresh_destination

    from alphalens_api.auth.permissions import restrict, verify

    output = fresh_destination(repo, output)
    source_before = source_identity(repo)
    config = repo / ".local-data/full-nse-runtime/market-workflow-500.json"
    runtime = repo / ".local-data/production-collector-runtime-20261024/venv"
    policy = policy_identity(config)
    observed = query_task(TASK)
    preserved = query_task(PRESERVED_TASK)
    planned = proposal(observed["xml"], repo, config, native_defaults=observed)
    identity = candidate_identity(repo, runtime)
    source_stable = source_before == identity["source"]
    original = {
        "resolved_path": str((repo / ".venv").resolve()),
        "python_sha256": digest(repo / ".venv/Scripts/python.exe"),
        "package_versions": versions(repo / ".venv/Lib/site-packages"),
    }
    output.mkdir(parents=True)
    restrict(output)
    verify(output)
    files = {
        "market-before.xml": observed["xml"],
        "market-proposed.xml": planned.pop("proposed_xml"),
        "watchlist-preserved.xml": preserved["xml"],
        "market-rollback.xml": observed["xml"],
    }
    for name, body in files.items():
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            stream.write(body)
    tests: dict[str, Any] = {"executed": False}
    if run_tests:
        test_temp_root = Path(repo.anchor) / "al-tests"
        environment = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=str(repo),
            ALPHALENS_TEST_TEMP_ROOT=str(test_temp_root),
        )
        command = [
            str(runtime / "Scripts/python.exe"),
            "-m",
            "pytest",
            *FOCUSED_TESTS,
            "-q",
            "-p",
            "no:cacheprovider",
        ]
        with (output / "focused-tests.log").open("xb") as log:
            result = subprocess.run(
                command,
                cwd=repo,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        after = candidate_identity(repo, runtime)
        tests = {
            "executed": True,
            "exit_code": result.returncode,
            "before_after_fingerprint_equal": identity["fresh_fingerprint_sha256"]
            == after["fresh_fingerprint_sha256"],
            "log_sha256": digest(output / "focused-tests.log"),
            "temporary_root": str(test_temp_root),
            "temporary_allocation": "EXISTING_CONFTEST_UNIQUE_ABSENT_OWNED_CHILD",
        }
        source_stable = source_stable and source_before == after["source"]
    safe: dict[str, Any] = {
        "version": "nse-collector-cutover-plan.v1",
        "prepared_at": datetime.now(UTC).isoformat(),
        "status": "BLOCKED_APPROVAL"
        if source_stable
        and observed["state"] == "Ready"
        and observed.get("matching_collector_process_count") == 0
        and all(identity["checks"].values())
        and (
            not run_tests
            or (tests.get("exit_code") == 0 and tests.get("before_after_fingerprint_equal"))
        )
        else "BLOCKED_SECURITY",
        "tasks_modified": False,
        "provider_requests": 0,
        "task_name": TASK,
        "preserved_task_name": PRESERVED_TASK,
        "task_state": observed["state"],
        "next_scheduled_run": observed["next_run_at"],
        "task_idle_for_cutover": observed["state"] == "Ready"
        and observed.get("matching_collector_process_count") == 0,
        "matching_collector_process_count": observed.get("matching_collector_process_count"),
        "candidate_runtime": str(runtime),
        "source_stable_during_preflight": source_stable,
        "original_runtime": str(repo / ".venv"),
        "original_environment": original,
        "config": str(config),
        "policy": policy,
        "candidate": identity,
        "actions": planned,
        "focused_tests": tests,
        "artifacts_sha256": {name: digest(output / name) for name in files},
        "automatic_fallback_permitted": False,
    }
    with (output / "plan.json").open("x", encoding="utf-8") as stream:
        json.dump(safe, stream, indent=2)
    return safe


def verify_plan(repo: Path, folder: Path) -> dict[str, Any]:
    from alphalens_api.auth.permissions import verify

    if not folder.resolve().is_relative_to((repo / ".local-data").resolve()):
        raise ValueError("PROTECTED_PRIVATE_PLAN_REQUIRED")
    for path in (folder, *folder.parents):
        if path.is_symlink() or path.is_junction():
            raise ValueError("CUTOVER_PLAN_REPARSE_REJECTED")
        if path == repo:
            break
    verify(folder)
    value = json.loads((folder / "plan.json").read_bytes())
    if (
        Path(value["candidate_runtime"]).resolve()
        != (repo / ".local-data/production-collector-runtime-20261024/venv").resolve()
        or Path(value["config"]).resolve()
        != (repo / ".local-data/full-nse-runtime/market-workflow-500.json").resolve()
    ):
        raise ValueError("REVIEWED_CANDIDATE_AND_CONFIGURATION_REQUIRED")
    if set(value["artifacts_sha256"]) != {
        "market-before.xml",
        "market-proposed.xml",
        "watchlist-preserved.xml",
        "market-rollback.xml",
    }:
        raise ValueError("EXPECTED_CUTOVER_ARTIFACTS_REQUIRED")
    if any(
        digest(folder / name) != expected for name, expected in value["artifacts_sha256"].items()
    ):
        raise ValueError("CUTOVER_BACKUP_OR_PROPOSAL_CHANGED")
    actual = query_task(TASK)
    original = (folder / "market-before.xml").read_text(encoding="utf-8")
    preserved = query_task(PRESERVED_TASK)
    if canonical(parse(actual["xml"])) != canonical(parse(original)):
        raise ValueError("TASK_CHANGED_SINCE_CUTOVER_REVIEW")
    rebuilt = proposal(original, repo, Path(value["config"]), native_defaults=actual)
    if canonical(parse(rebuilt["proposed_xml"])) != canonical(
        parse((folder / "market-proposed.xml").read_text(encoding="utf-8"))
    ):
        raise ValueError("REVIEWED_ACTION_ONLY_PROPOSAL_REQUIRED")
    if canonical(parse(preserved["xml"])) != canonical(
        parse((folder / "watchlist-preserved.xml").read_text(encoding="utf-8"))
    ):
        raise ValueError("ORIGINAL_WATCHLIST_TASK_CHANGED")
    runtime = Path(value["candidate_runtime"])
    candidate = candidate_identity(repo, runtime)
    if candidate["fresh_fingerprint_sha256"] != value["candidate"]["fresh_fingerprint_sha256"]:
        raise ValueError("CANDIDATE_OR_SOURCE_CHANGED_SINCE_TESTED_PLAN")
    if not all(candidate["checks"].values()):
        raise ValueError("CANDIDATE_INSTALLATION_OR_RECORDS_REJECTED")
    tests = value.get("focused_tests", {})
    if (
        value.get("source_stable_during_preflight") is not True
        or tests.get("executed") is not True
        or tests.get("exit_code") != 0
        or tests.get("before_after_fingerprint_equal") is not True
        or digest(folder / "focused-tests.log") != tests.get("log_sha256")
    ):
        raise ValueError("FOCUSED_CANDIDATE_GATE_REQUIRED")
    if policy_identity(Path(value["config"])) != value["policy"]:
        raise ValueError("APPROVED_COLLECTION_POLICY_CHANGED")
    if value["original_environment"] != {
        "resolved_path": str((repo / ".venv").resolve()),
        "python_sha256": digest(repo / ".venv/Scripts/python.exe"),
        "package_versions": versions(repo / ".venv/Lib/site-packages"),
    }:
        raise ValueError("ORIGINAL_ENVIRONMENT_CHANGED_SINCE_REVIEW")
    if actual["state"] != "Ready":
        raise ValueError("EXISTING_COLLECTOR_ENABLED_IDLE_READY_REQUIRED")
    if actual.get("matching_collector_process_count") != 0:
        raise ValueError("COLLECTOR_PROCESS_LIFETIME_MUST_BE_QUIESCENT")
    return {
        "status": "BLOCKED_APPROVAL",
        "preflight": "VERIFIED_COMPLETE",
        "provider_requests": 0,
        "tasks_modified": False,
        "prior_bitwise_identity_claimed": False,
        "fresh_fingerprint_sha256": candidate["fresh_fingerprint_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify-plan"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--run-focused-tests", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    try:
        if args.mode == "prepare":
            value = prepare(repo, args.directory, run_tests=args.run_focused_tests)
            result = {
                "status": value["status"],
                "provider_requests": 0,
                "tasks_modified": False,
                "candidate_checks": value["candidate"]["checks"],
                "focused_tests": value["focused_tests"],
                "fresh_fingerprint_sha256": value["candidate"]["fresh_fingerprint_sha256"],
            }
        else:
            result = verify_plan(repo, args.directory)
    except (ValueError, OSError, KeyError, ET.ParseError, subprocess.SubprocessError) as exc:
        safe_reason = str(exc)
        print(
            json.dumps(
                {
                    "status": "BLOCKED_SECURITY",
                    "reason": safe_reason
                    if re.fullmatch(r"[A-Z0-9_]{1,100}", safe_reason)
                    else "CUTOVER_PREFLIGHT_REJECTED_REVIEW_PRIVATE_EVIDENCE",
                    "tasks_modified": False,
                    "provider_requests": 0,
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(result))


if __name__ == "__main__":
    main()
