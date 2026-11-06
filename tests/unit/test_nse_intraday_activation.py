"""TEST_ONLY activation plans and files; no live sources, tasks or provider calls."""

import copy
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from scripts import nse_collector_cutover as cutover
from scripts import nse_intraday_activation as activation


@pytest.fixture(autouse=True)
def no_native_or_network_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    def prohibited(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("TEST_ONLY_NATIVE_OPERATIONS_PROHIBITED")

    monkeypatch.setattr(cutover, "query_task", prohibited)
    monkeypatch.setattr(subprocess, "check_output", prohibited)
    monkeypatch.setattr(activation, "collector_process_count", lambda *_: 0, raising=False)
    monkeypatch.setattr(activation, "restrict", lambda *args, **kwargs: None)
    monkeypatch.setattr(activation, "verify", lambda *args, **kwargs: None)


def fake_sources(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    active = tmp_path / "TEST_ONLY_active"
    folder = tmp_path / "TEST_ONLY_plan"
    files: dict[str, Any] = {}
    artifacts: dict[str, str] = {}
    for index, relative in enumerate(activation.ORDER):
        path = active / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        old = f"TEST_ONLY_ORIGINAL = {index}\n".encode()
        new = f"TEST_ONLY_PROPOSED = {index}\n".encode()
        path.write_bytes(old)
        entry = {"original_sha256": activation.sha(old), "proposed_sha256": activation.sha(new)}
        for label, body in (("original", old), ("proposed", new)):
            name = label + "/" + path.name
            artifact = folder / name
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(body)
            entry[label + "_artifact"] = name
            artifacts[name] = activation.sha(body)
        files[relative] = entry
    return (
        active,
        folder,
        {
            "scope": activation.SCOPE,
            "source_files": files,
            "apply_order": list(activation.ORDER),
            "rollback_order": list(reversed(activation.ORDER)),
            "artifacts_sha256": artifacts,
        },
    )


def write_plan(folder: Path, plan: dict[str, Any]) -> str:
    path = folder / "plan.json"
    path.write_bytes(activation.encoded(plan))
    return activation.sha(path.read_bytes())


def source_bytes(active: Path) -> dict[str, bytes]:
    return {relative: (active / relative).read_bytes() for relative in activation.ORDER}


def test_projected_identity_changes_source_only_and_does_not_mutate_original() -> None:
    original = {
        "checks": {"TEST_ONLY_RECORDS": True},
        "candidate_python_sha256": "a" * 64,
        "source": {"files": 2, "sha256": "b" * 64},
        "fresh_fingerprint_sha256": "c" * 64,
    }
    snapshot = copy.deepcopy(original)
    inventory = {activation.ORDER[0]: "d" * 64, activation.ORDER[1]: "e" * 64}
    projected = activation.project_identity(original, inventory)
    assert original == snapshot
    assert projected["checks"] == original["checks"]
    assert projected["candidate_python_sha256"] == original["candidate_python_sha256"]
    assert projected["source"] == {
        "files": 2,
        "sha256": activation.sha(activation.encoded(inventory)),
    }
    assert projected["fresh_fingerprint_sha256"] != original["fresh_fingerprint_sha256"]
    assert projected == activation.project_identity(
        original, dict(reversed(list(inventory.items())))
    )


@pytest.mark.parametrize(
    "relative",
    [
        "apps/web/src/pages/NseMarket.tsx",
        "workers/nse_market/../engine.py",
        "../engine.py",
        "/engine.py",
    ],
)
def test_only_exact_two_source_paths_are_allowed(tmp_path: Path, relative: str) -> None:
    active, _, _ = fake_sources(tmp_path)
    with pytest.raises(ValueError, match="SOURCE_PATH_NOT_REVIEWED"):
        activation.checked_path(active, relative)


@pytest.mark.parametrize("kind", ["file_symlink", "parent_junction"])
def test_source_reparse_is_rejected_without_creating_real_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    active, _, _ = fake_sources(tmp_path)
    checked = active / activation.ORDER[0]
    target = checked if kind == "file_symlink" else checked.parent
    attribute = "is_symlink" if kind == "file_symlink" else "is_junction"
    original = getattr(Path, attribute)
    monkeypatch.setattr(Path, attribute, lambda self: self == target or original(self))
    with pytest.raises(ValueError, match="REPARSE"):
        activation.checked_path(active, activation.ORDER[0])


def test_missing_source_is_never_created_by_validation(tmp_path: Path) -> None:
    active, _, _ = fake_sources(tmp_path)
    missing = active / activation.ORDER[1]
    missing.unlink()  # Delete only this test's constructed file.
    with pytest.raises(ValueError):
        activation.checked_path(active, activation.ORDER[1])
    assert not missing.exists()


def test_apply_engine_first_rollback_reverse_and_both_replays_are_idempotent(
    tmp_path: Path,
) -> None:
    active, folder, plan = fake_sources(tmp_path)
    original = source_bytes(active)
    events: list[tuple[str, str]] = []
    changed = activation.replace_sources(
        active,
        folder,
        plan,
        rollback=False,
        checkpoint=lambda stage, path: events.append((stage, path)),
    )
    assert changed == list(activation.ORDER)
    assert events == [(stage, path) for path in activation.ORDER for stage in ("before", "after")]
    assert all(
        activation.sha((active / path).read_bytes())
        == plan["source_files"][path]["proposed_sha256"]
        for path in activation.ORDER
    )
    assert activation.replace_sources(active, folder, plan, rollback=False) == []
    events.clear()
    restored = activation.replace_sources(
        active,
        folder,
        plan,
        rollback=True,
        checkpoint=lambda stage, path: events.append((stage, path)),
    )
    assert restored == list(reversed(activation.ORDER))
    assert events == [
        (stage, path) for path in reversed(activation.ORDER) for stage in ("before", "after")
    ]
    assert source_bytes(active) == original
    assert activation.replace_sources(active, folder, plan, rollback=True) == []


def test_interrupted_first_replace_requires_rollback_and_restores_exact_originals(
    tmp_path: Path,
) -> None:
    active, folder, plan = fake_sources(tmp_path)
    original = source_bytes(active)

    def interrupt(stage: str, path: str) -> None:
        if stage == "after" and path == activation.ORDER[0]:
            raise RuntimeError("TEST_ONLY_INTERRUPTED_AFTER_ENGINE")

    with pytest.raises(RuntimeError, match="TEST_ONLY_INTERRUPTED_AFTER_ENGINE"):
        activation.replace_sources(active, folder, plan, rollback=False, checkpoint=interrupt)
    assert (active / activation.ORDER[1]).read_bytes() == original[activation.ORDER[1]]
    with pytest.raises(ValueError, match="PARTIAL_APPLY_REQUIRES_REVIEWED_ROLLBACK"):
        activation.replace_sources(active, folder, plan, rollback=False)
    assert activation.replace_sources(active, folder, plan, rollback=True) == list(
        reversed(activation.ORDER)
    )
    assert source_bytes(active) == original


@pytest.mark.parametrize("rollback", [False, True])
def test_unknown_active_hashes_prevent_any_replacement(tmp_path: Path, rollback: bool) -> None:
    active, folder, plan = fake_sources(tmp_path)
    (active / activation.ORDER[1]).write_bytes(b"TEST_ONLY_EXTERNAL_EDIT_DO_NOT_OVERWRITE")
    before = source_bytes(active)
    with pytest.raises(ValueError, match="UNKNOWN_SOURCE_BYTES_DO_NOT_OVERWRITE"):
        activation.replace_sources(active, folder, plan, rollback=rollback)
    assert source_bytes(active) == before


def test_artifact_tampering_is_rejected_and_partial_state_remains_reversibly_recorded(
    tmp_path: Path,
) -> None:
    active, folder, plan = fake_sources(tmp_path)
    original = source_bytes(active)
    daily = activation.ORDER[1]
    artifact = folder / plan["source_files"][daily]["proposed_artifact"]
    artifact.write_bytes(b"TEST_ONLY_TAMPERED_PAYLOAD")
    with pytest.raises(ValueError, match="REVIEWED_SOURCE_ARTIFACT_CHANGED"):
        activation.replace_sources(active, folder, plan, rollback=False)
    assert (active / daily).read_bytes() == original[daily]
    activation.replace_sources(active, folder, plan, rollback=True)
    assert source_bytes(active) == original


def test_external_change_during_checkpoint_is_not_overwritten(tmp_path: Path) -> None:
    active, folder, plan = fake_sources(tmp_path)
    unexpected = b"TEST_ONLY_CONCURRENT_EDIT"

    def edit(stage: str, relative: str) -> None:
        if stage == "before" and relative == activation.ORDER[0]:
            (active / relative).write_bytes(unexpected)

    with pytest.raises(ValueError, match="SOURCE_CHANGED_DURING_OPERATION"):
        activation.replace_sources(active, folder, plan, rollback=False, checkpoint=edit)
    assert (active / activation.ORDER[0]).read_bytes() == unexpected


def test_valid_plan_verifies_bytes_without_changing_active_sources(tmp_path: Path) -> None:
    active, folder, plan = fake_sources(tmp_path)
    original = source_bytes(active)
    checksum = write_plan(folder, plan)
    assert activation.load_plan(folder, checksum) == plan
    assert source_bytes(active) == original


@pytest.mark.parametrize(
    "change", ["sha", "scope", "extra_source", "apply_order", "rollback_order", "payload"]
)
def test_plan_sha_scope_order_and_payload_tampering_are_rejected(
    tmp_path: Path, change: str
) -> None:
    _, folder, plan = fake_sources(tmp_path)
    if change == "scope":
        plan["scope"] = "TEST_ONLY_UNREVIEWED_SCOPE"
    elif change == "extra_source":
        plan["source_files"]["apps/web/src/pages/NseMarket.tsx"] = {}
    elif change in {"apply_order", "rollback_order"}:
        plan[change] = list(reversed(plan[change]))
    checksum = write_plan(folder, plan)
    if change == "sha":
        checksum = "0" * 64
    elif change == "payload":
        (folder / "proposed/engine.py").write_bytes(b"TEST_ONLY_CORRUPT_PLAN_ARTIFACT")
    with pytest.raises(ValueError):
        activation.load_plan(folder, checksum)


def test_plan_artifact_scope_cannot_escape_protected_directory(tmp_path: Path) -> None:
    _, folder, plan = fake_sources(tmp_path)
    outside = tmp_path / "TEST_ONLY_outside.py"
    outside.write_bytes(b"TEST_ONLY_NOT_AN_APPROVED_ARTIFACT")
    plan["artifacts_sha256"]["../TEST_ONLY_outside.py"] = activation.sha(outside.read_bytes())
    with pytest.raises(ValueError, match="PATH|SCOPE|ARTIFACT"):
        activation.load_plan(folder, write_plan(folder, plan))


def test_plan_artifact_parent_reparse_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, folder, plan = fake_sources(tmp_path)
    checksum = write_plan(folder, plan)
    original = Path.is_junction
    monkeypatch.setattr(
        Path, "is_junction", lambda self: self == folder / "proposed" or original(self)
    )
    with pytest.raises(ValueError, match="PATH|REPARSE|ARTIFACT"):
        activation.load_plan(folder, checksum)


@pytest.mark.parametrize("direction", ["original", "proposed"])
def test_source_artifact_fields_must_match_reviewed_payload_mapping(
    tmp_path: Path, direction: str
) -> None:
    _, folder, plan = fake_sources(tmp_path)
    plan["source_files"][activation.ORDER[0]][direction + "_artifact"] = "../TEST_ONLY_escape.py"
    with pytest.raises(ValueError, match="PATH|SCOPE|ARTIFACT"):
        activation.load_plan(folder, write_plan(folder, plan))


def mock_tasks(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], dict[str, Any]]:
    task = {
        "xml": "TEST_ONLY_MARKET_TASK_XML",
        "state": "Ready",
        "matching_collector_process_count": 0,
        "triggers_enabled": [True, True, True],
        "next_run_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    watchlist = {"xml": "TEST_ONLY_UNCHANGED_WATCHLIST_XML"}
    monkeypatch.setattr(
        cutover,
        "query_task",
        lambda name: task if name == cutover.TASK else watchlist,
    )
    monkeypatch.setattr(
        activation, "collector_process_count", lambda *_: task["matching_collector_process_count"]
    )
    return task, watchlist


def task_plan(task: dict[str, Any], watchlist: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_root": "TEST_ONLY_MOCK_ROOT_NEVER_ACCESSED",
        "task_xml_sha256": activation.sha(task["xml"].encode()),
        "watchlist_xml_sha256": activation.sha(watchlist["xml"].encode()),
    }


def test_task_invariants_require_saved_configuration_and_return_no_xml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task, watchlist = mock_tasks(monkeypatch)
    before = copy.deepcopy((task, watchlist))
    observed = activation.task_invariants(task_plan(task, watchlist))
    assert observed["state"] == "Ready" and "xml" not in observed
    assert (task, watchlist) == before


@pytest.mark.parametrize(
    "change", ["task", "watchlist", "state", "workers", "triggers", "near_trigger"]
)
def test_task_configuration_activity_and_trigger_drift_fail_closed(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    task, watchlist = mock_tasks(monkeypatch)
    plan = task_plan(task, watchlist)
    if change == "task":
        task["xml"] += "TEST_ONLY_CHANGED"
    elif change == "watchlist":
        watchlist["xml"] += "TEST_ONLY_CHANGED"
    elif change == "state":
        task["state"] = "Running"
    elif change == "workers":
        task["matching_collector_process_count"] = 1
    elif change == "triggers":
        task["triggers_enabled"] = [True, False, True]
    else:
        task["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError):
        activation.task_invariants(plan)


def test_rollback_still_requires_idle_task_but_not_future_trigger_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task, watchlist = mock_tasks(monkeypatch)
    plan = task_plan(task, watchlist)
    task["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    assert activation.task_invariants(plan, rollback=True)["state"] == "Ready"
    task["matching_collector_process_count"] = 1
    with pytest.raises(ValueError, match="IDLE_READY_ZERO_WORKERS_REQUIRED"):
        activation.task_invariants(plan, rollback=True)


@pytest.mark.parametrize(
    "drift",
    ["none", "power", "expired", "runtime_after_power", "state_after_power", "source_after_power"],
)
def test_readonly_verification_reports_subset_and_rejects_drift_after_power(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    active, folder, plan = fake_sources(tmp_path)
    original = source_bytes(active)
    source = tmp_path / "TEST_ONLY_source"
    config = tmp_path / "TEST_ONLY_config.json"
    config.write_bytes(b"{}")
    (folder / "state-before.json").write_bytes(b"{}")
    plan.update(
        active_root=str(active),
        source_root=str(source),
        active_commit="TEST_ONLY_COMMIT",
        current_source_fingerprint="TEST_ONLY_FINGERPRINT",
        config=str(config),
        config_sha256=cutover.digest(config),
        policy={"TEST_ONLY": True},
        runtime="TEST_ONLY_NOT_READ",
        expires_at=(
            datetime.now(UTC) + timedelta(hours=-1 if drift == "expired" else 1)
        ).isoformat(),
    )
    plan["artifacts_sha256"]["activation-tool.py"] = cutover.digest(Path(activation.__file__))
    monkeypatch.setattr(activation, "load_plan", lambda *_: plan)
    monkeypatch.setattr(
        activation,
        "git",
        lambda root, *args: b"TEST_ONLY_COMMIT" if args[0] == "rev-parse" else b"",
    )
    monkeypatch.setattr(cutover, "policy_identity", lambda *_: plan["policy"])
    after_power = {"value": False}

    def observe(*args: Any, **kwargs: Any) -> dict[str, bool]:
        after_power["value"] = True
        return {"activation_power_ready": drift != "power"}

    monkeypatch.setattr(activation, "power_observation", observe)
    monkeypatch.setattr(activation, "task_invariants", lambda *_: {"state": "Ready"})
    monkeypatch.setattr(
        activation,
        "state_snapshot",
        lambda *_: (
            {"TEST_ONLY_DRIFT": True}
            if after_power["value"] and drift == "state_after_power"
            else {}
        ),
    )
    monkeypatch.setattr(
        cutover,
        "candidate_identity",
        lambda *_: {
            "fresh_fingerprint_sha256": "TEST_ONLY_CHANGED"
            if after_power["value"] and drift == "runtime_after_power"
            else plan["current_source_fingerprint"]
        },
    )

    def inventory(root: Path) -> dict[str, str]:
        result = {
            relative: item["original_sha256" if root == active else "proposed_sha256"]
            for relative, item in plan["source_files"].items()
        }
        if root == active and drift == "source_after_power":
            result["TEST_ONLY_UNREVIEWED_FILE"] = "TEST_ONLY_CHANGED"
        return result

    monkeypatch.setattr(activation, "source_inventory", inventory)
    if drift in {"none", "power"}:
        receipt = activation.verify_plan(folder, "TEST_ONLY_APPROVED_SHA")
        assert receipt["status"] == "BLOCKED_APPROVAL"
        assert receipt["activation_authorized"] is receipt["activation_performed"] is False
        assert receipt["provider_requests"] == receipt["ntp_requests"] == 0
        assert receipt["read_only_identity_and_power_subset_passed"] == (drift == "none")
        assert "FRESH_DEPENDENCY_AUDIT" in receipt["remaining_required_gates"]
    else:
        with pytest.raises(ValueError, match="EXPIRED|DURING_PREFLIGHT"):
            activation.verify_plan(folder, "TEST_ONLY_APPROVED_SHA")
    assert source_bytes(active) == original
