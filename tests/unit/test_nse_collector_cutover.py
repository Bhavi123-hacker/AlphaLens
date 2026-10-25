"""TEST_ONLY task XML and fake runtimes. No task API, collector or provider requests."""

import base64
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from scripts import nse_collector_cutover as cutover


def task_xml(repo: Path, config: Path) -> str:
    arguments = (
        '/d /c ""'
        + cutover.native(repo / "scripts/windows/run-nse-market.cmd")
        + '" "'
        + cutover.native(config)
        + '" auto --scheduled"'
    )
    arguments = arguments.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    triggers = "".join(
        "<CalendarTrigger><StartBoundary>2025-01-03T" + slot + ":00+05:30</StartBoundary>"
        "<Enabled>true</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>"
        for slot in ("20:30", "21:30", "22:30")
    )
    return (
        '<Task xmlns="' + cutover.NS + '" version="1.2"><Triggers>' + triggers + "</Triggers>"
        '<Principals><Principal id="LocalOperator"><UserId>TEST_ONLY_SID</UserId>'
        "<LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel>"
        "</Principal></Principals><Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>"
        "<StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT30M</ExecutionTimeLimit>"
        "<RestartOnFailure><Interval>PT1M</Interval><Count>2</Count></RestartOnFailure>"
        '<Enabled>true</Enabled></Settings><Actions Context="LocalOperator"><Exec>'
        "<Command>C:\\Windows\\System32\\cmd.exe</Command><Arguments>" + arguments + "</Arguments>"
        "<WorkingDirectory>" + cutover.native(repo) + "</WorkingDirectory></Exec></Actions></Task>"
    )


def test_proposal_changes_only_reviewed_action_and_retains_exact_rollback_bytes(
    tmp_path: Path,
) -> None:
    config = tmp_path / "TEST_ONLY_config.json"
    before = task_xml(tmp_path, config)
    plan = cutover.proposal(before, tmp_path, config)
    after = plan["proposed_xml"]
    assert cutover.invariant_hash(before) == cutover.invariant_hash(after)
    assert "run-nse-collector-isolated.cmd" in plan["proposed_action"]["Arguments"]
    assert "auto --scheduled" not in plan["proposed_action"]["Arguments"]
    assert plan["before_action"] == cutover.action(cutover.parse(before))
    # This is an in-memory transaction simulation, never a Windows scheduler adapter.
    simulated = {"xml": before}
    try:
        simulated["xml"] = after
        raise ValueError("TEST_ONLY_POST_UPDATE_VERIFICATION_FAILED")
    except ValueError:
        simulated["xml"] = before
    assert simulated["xml"].encode() == before.encode()


@pytest.mark.parametrize(
    "old,new",
    [
        ("auto --scheduled", "auto --scheduled --unreviewed-secret TEST_ONLY_VALUE"),
        ("LeastPrivilege", "HighestAvailable"),
        ("InteractiveToken", "Password"),
        ("20:30", "19:30"),
        ("IgnoreNew", "Parallel"),
        ("C:\\Windows\\System32\\cmd.exe", "D:\\TEST_ONLY\\System32\\cmd.exe"),
    ],
)
def test_unreviewed_arguments_or_policy_drift_are_rejected_without_echoing_values(
    tmp_path: Path, old: str, new: str
) -> None:
    config = tmp_path / "TEST_ONLY_config.json"
    before = task_xml(tmp_path, config).replace(old, new)
    with pytest.raises(ValueError) as failed:
        cutover.proposal(before, tmp_path, config)
    assert "TEST_ONLY_VALUE" not in str(failed.value)


def test_task_entity_expansion_is_rejected() -> None:
    with pytest.raises(ValueError, match="CONTRACT_REJECTED"):
        cutover.parse('<!DOCTYPE Task [<!ENTITY value "TEST_ONLY">]><Task/>')


def test_omitted_xml_defaults_require_independent_native_getters(tmp_path: Path) -> None:
    config = tmp_path / "TEST_ONLY_config.json"
    xml = (
        task_xml(tmp_path, config)
        .replace("<RunLevel>LeastPrivilege</RunLevel>", "")
        .replace("<Enabled>true</Enabled>", "")
    )
    with pytest.raises(ValueError, match="POLICY_REJECTED"):
        cutover.proposal(xml, tmp_path, config)
    plan = cutover.proposal(
        xml,
        tmp_path,
        config,
        native_defaults={"principal_run_level": "Limited", "triggers_enabled": [True, True, True]},
    )
    assert cutover.invariant_hash(xml) == cutover.invariant_hash(plan["proposed_xml"])
    with pytest.raises(ValueError, match="POLICY_REJECTED"):
        cutover.proposal(
            xml,
            tmp_path,
            config,
            native_defaults={
                "principal_run_level": "Highest",
                "triggers_enabled": [True, True, True],
            },
        )


def record_fixture(root: Path) -> tuple[Path, Path]:
    site = root / "Lib/site-packages"
    meta = site / "TEST_ONLY-1.dist-info"
    meta.mkdir(parents=True)
    module = site / "TEST_ONLY.py"
    module.write_bytes(b"TEST_ONLY_NO_PACKAGE_IMPORT_OR_EXECUTION")
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(module.read_bytes()).digest()).decode().rstrip("=")
    )
    (meta / "RECORD").write_text(
        "TEST_ONLY.py,sha256="
        + expected
        + ",41\nTEST_ONLY-1.dist-info/RECORD,,\nTEST_ONLY.pyc,,\n",
        encoding="utf-8",
    )
    return module, meta / "RECORD"


def test_record_verification_binds_real_files_and_excludes_mutable_bytecode(tmp_path: Path) -> None:
    module, _ = record_fixture(tmp_path)
    before = cutover.installed_records(tmp_path)
    assert before["verified_files"] == 2 and before["mismatches"] == []
    assert before["excluded_pyc_entries"] == 1
    module.with_suffix(".pyc").write_bytes(b"TEST_ONLY_MUTABLE_BYTECODE")
    assert cutover.installed_records(tmp_path) == before
    module.write_bytes(b"TEST_ONLY_FILE_DRIFT")
    after = cutover.installed_records(tmp_path)
    assert after["mismatches"] == [str(Path("Lib/site-packages/TEST_ONLY.py"))]
    assert after["files_sha256"] != before["files_sha256"]


def test_record_paths_cannot_escape_runtime(tmp_path: Path) -> None:
    _, record = record_fixture(tmp_path)
    record.write_text("../../../TEST_ONLY_outside.py,sha256=AAAA,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="PATH_REJECTED"):
        cutover.installed_records(tmp_path)


def setup_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, dict[str, Any]]:
    repo = tmp_path / "TEST_ONLY_repo"
    (repo / ".local-data").mkdir(parents=True)
    original_python = repo / ".venv/Scripts/python.exe"
    original_python.parent.mkdir(parents=True)
    original_python.write_bytes(b"TEST_ONLY_NONEXECUTABLE_ORIGINAL_RUNTIME")
    config = repo / ".local-data/full-nse-runtime/market-workflow-500.json"
    xml = task_xml(repo, config)
    monkeypatch.setattr(
        cutover,
        "query_task",
        lambda name: {
            "xml": xml,
            "state": "Ready",
            "matching_collector_process_count": 0,
            "next_run_at": "2025-01-03T15:00:00+00:00",
        },
    )
    identity = {
        "fresh_fingerprint_sha256": "a" * 64,
        "checks": {"TEST_ONLY_check": True},
        "source": {"sha256": "e" * 64},
    }
    monkeypatch.setattr(cutover, "source_identity", lambda *args: {"sha256": "e" * 64})
    monkeypatch.setattr(cutover, "candidate_identity", lambda *args: copy.deepcopy(identity))
    monkeypatch.setattr(cutover, "policy_identity", lambda *args: {"TEST_ONLY_policy": True})

    def run(command: list[str], **kwargs: Any) -> Any:
        assert "--basetemp" not in command
        assert kwargs["env"]["ALPHALENS_TEST_TEMP_ROOT"] == str(Path(repo.anchor) / "al-tests")
        assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", run)
    folder = repo / ".local-data/TEST_ONLY_cutover"
    cutover.prepare(repo, folder, run_tests=True)
    return repo, folder, identity


def test_preflight_is_read_only_and_requires_unchanged_test_bound_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, folder, identity = setup_plan(tmp_path, monkeypatch)
    before = {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()}
    checked = cutover.verify_plan(repo, folder)
    assert checked["status"] == "BLOCKED_APPROVAL" and checked["preflight"] == "VERIFIED_COMPLETE"
    assert checked["tasks_modified"] is False and checked["provider_requests"] == 0
    assert {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()} == before
    identity["fresh_fingerprint_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="CHANGED_SINCE_TESTED_PLAN"):
        cutover.verify_plan(repo, folder)


@pytest.mark.parametrize("state", ["Running", "Queued", "Disabled", "Unknown", ""])
def test_preflight_requires_exact_ready_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    repo, folder, _ = setup_plan(tmp_path, monkeypatch)
    xml = (folder / "market-before.xml").read_text(encoding="utf-8")
    monkeypatch.setattr(cutover, "query_task", lambda name: {"xml": xml, "state": state})
    with pytest.raises(ValueError, match="ENABLED_IDLE_READY_REQUIRED"):
        cutover.verify_plan(repo, folder)


@pytest.mark.parametrize("count", [1, 2, None])
def test_ready_does_not_clear_surviving_collector_or_missing_process_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int | None
) -> None:
    repo, folder, _ = setup_plan(tmp_path, monkeypatch)
    xml = (folder / "market-before.xml").read_text(encoding="utf-8")
    monkeypatch.setattr(
        cutover,
        "query_task",
        lambda name: {"xml": xml, "state": "Ready", "matching_collector_process_count": count},
    )
    with pytest.raises(ValueError, match="LIFETIME_MUST_BE_QUIESCENT"):
        cutover.verify_plan(repo, folder)


@pytest.mark.parametrize("failure", ["task", "backup", "tests"])
def test_preflight_refuses_task_backup_or_test_receipt_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repo, folder, _ = setup_plan(tmp_path, monkeypatch)
    if failure == "task":
        config = repo / ".local-data/full-nse-runtime/market-workflow-500.json"
        changed = task_xml(repo, config).replace("PT30M", "PT45M")
        monkeypatch.setattr(cutover, "query_task", lambda name: {"xml": changed, "state": "Ready"})
    elif failure == "backup":
        (folder / "market-rollback.xml").write_text("TEST_ONLY_TAMPERING", encoding="utf-8")
    else:
        value = json.loads((folder / "plan.json").read_bytes())
        value["focused_tests"]["exit_code"] = 1
        (folder / "plan.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        cutover.verify_plan(repo, folder)
