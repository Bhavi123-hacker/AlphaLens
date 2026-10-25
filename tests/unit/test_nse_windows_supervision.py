"""TEST_ONLY native process lifecycles; never import or launch a collector."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from workers.nse_market.windows_supervision import PARENT_INTERRUPTED, _Windows

pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows Job Object lifecycle")
BASE = getattr(sys, "_base_executable", sys.executable)
RUNNER = """
import json, os, sys
from pathlib import Path
from workers.nse_market.windows_supervision import _Windows, supervise
folder = Path(sys.argv[1]); command = json.loads(
    (folder / 'command.json').read_text() if sys.argv[3] == 'file' else sys.argv[3])
windows = _Windows()
handle = (windows.cmd_parent() if sys.argv[2] == 'cmd' else
    windows.checked(windows.api.OpenProcess(0x100000, False, int(sys.argv[2]))))
(folder / 'supervisor.pid').write_text(str(os.getpid()))
def record(stage, code):
    with (folder / 'facts.jsonl').open('a') as stream:
        stream.write(json.dumps({'stage': stage, 'code': code}) + '\\n')
try:
    result = supervise(command, parent_handle=handle, record=record)
finally:
    windows.close(handle)
raise SystemExit(result)
"""
WORKER = """
import os, sys, time, subprocess
from pathlib import Path
folder = Path(sys.argv[1]); mode = sys.argv[2]
(folder / 'worker.pid').write_text(str(os.getpid()))
if mode == 'grandchild':
    subprocess.Popen([sys.executable, '-c',
        'import os,sys,time;from pathlib import Path;'
        'Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(60)',
        str(folder / 'grandchild.pid')])
if mode == 'delayed_child':
    subprocess.Popen([sys.executable, '-c',
        'import sys,time;from pathlib import Path;time.sleep(0.8);'
        'Path(sys.argv[1]).write_text("TEST_ONLY")', str(folder / 'child.done')])
if mode in ('wait', 'grandchild'):
    time.sleep(60)
else:
    time.sleep(0.35)
(folder / 'worker.done').write_text('TEST_ONLY_COMPLETED')
raise SystemExit(17 if mode == 'failure' else 0)
"""


def environment() -> dict[str, str]:
    value = os.environ.copy()
    value["PYTHONPATH"] = os.pathsep.join(str(Path(part).resolve()) for part in sys.path if part)
    return value


def ready(path: Path, process: subprocess.Popen[bytes] | None = None) -> int:
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if path.exists() and path.stat().st_size:
            return int(path.read_text())
        if process is not None and process.poll() is not None:
            raise AssertionError(f"TEST_ONLY_PROCESS_EXITED_EARLY_{process.returncode}")
        time.sleep(0.02)
    raise AssertionError("TEST_ONLY_PROCESS_READY_TIMEOUT")


def open_process(pid: int) -> int:
    windows = _Windows()
    return windows.checked(windows.api.OpenProcess(0x100000, False, pid))


def ended(handle: int) -> None:
    windows = _Windows()
    try:
        assert windows.api.WaitForSingleObject(handle, 7000) == 0
    finally:
        windows.close(handle)


def launch(folder: Path, mode: str, parent: int | None = None) -> subprocess.Popen[bytes]:
    command = [BASE, "-c", WORKER, str(folder), mode]
    return subprocess.Popen(
        [BASE, "-c", RUNNER, str(folder), str(parent or os.getpid()), json.dumps(command)],
        env=environment(),
    )


@pytest.mark.parametrize("mode,expected", [("normal", 0), ("failure", 17), ("delayed_child", 0)])
def test_waits_for_real_worker_and_propagates_exit(
    tmp_path: Path, mode: str, expected: int
) -> None:
    process = launch(tmp_path, mode)
    ready(tmp_path / "worker.pid", process)
    assert process.poll() is None
    assert not (tmp_path / "worker.done").exists()
    assert process.wait(timeout=15) == expected
    facts = [json.loads(line) for line in (tmp_path / "facts.jsonl").read_text().splitlines()]
    assert facts[-1] == {"stage": "CONTAINED_WORKER_EXIT", "code": expected}
    assert (tmp_path / "worker.done").exists()
    if mode == "delayed_child":
        assert (tmp_path / "child.done").exists()


def test_hard_supervisor_termination_kills_worker_and_grandchild(tmp_path: Path) -> None:
    process = launch(tmp_path, "grandchild")
    supervisor = ready(tmp_path / "supervisor.pid", process)
    worker = open_process(ready(tmp_path / "worker.pid", process))
    grandchild = open_process(ready(tmp_path / "grandchild.pid", process))
    os.kill(supervisor, signal.SIGTERM)
    process.wait(timeout=15)
    ended(worker)
    ended(grandchild)
    assert not (tmp_path / "worker.done").exists()
    assert "CONTAINED_WORKER_EXIT" not in (tmp_path / "facts.jsonl").read_text()


def test_ancestor_termination_interrupts_contained_worker(tmp_path: Path) -> None:
    ancestor = subprocess.Popen([BASE, "-c", "import time;time.sleep(60)"])
    process = launch(tmp_path, "grandchild", ancestor.pid)
    try:
        worker = open_process(ready(tmp_path / "worker.pid", process))
        grandchild = open_process(ready(tmp_path / "grandchild.pid", process))
        ancestor.kill()  # TEST_ONLY representation of task/power-stop ancestor termination.
        ancestor.wait(timeout=10)
        assert process.wait(timeout=15) == PARENT_INTERRUPTED
        ended(worker)
        ended(grandchild)
        assert not (tmp_path / "worker.done").exists()
        assert "ANCESTOR_EXITED_WORKER_INTERRUPTED" in (tmp_path / "facts.jsonl").read_text()
    finally:
        if ancestor.poll() is None:
            ancestor.kill()
            ancestor.wait(timeout=10)
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def test_interrupted_worker_exit_is_not_success_and_restart_can_complete(tmp_path: Path) -> None:
    process = launch(tmp_path, "wait")
    worker = ready(tmp_path / "worker.pid", process)
    os.kill(worker, signal.SIGTERM)
    assert process.wait(timeout=15) != 0
    assert not (tmp_path / "worker.done").exists()
    restart = tmp_path / "TEST_ONLY_restart"
    restart.mkdir()
    assert launch(restart, "normal").wait(timeout=15) == 0


def test_cmd_guard_unwraps_real_venv_redirector(tmp_path: Path) -> None:
    script = tmp_path / "TEST_ONLY_probe.py"
    output = tmp_path / "TEST_ONLY_probe.json"
    script.write_text(
        "import json,sys;from pathlib import Path;"
        "from workers.nse_market.windows_supervision import _Windows;"
        "w=_Windows();h=w.cmd_parent();"
        "Path(sys.argv[1]).write_text(json.dumps({'alive':w.alive(h)}));w.close(h)"
    )
    wrapper = tmp_path / "TEST_ONLY_wrapper.cmd"
    wrapper.write_text(
        f'@echo off\n"{sys.executable}" "{script}" "{output}"\nexit /b %errorlevel%\n'
    )
    cmd = str(Path(os.environ["SYSTEMROOT"]) / "System32/cmd.exe")
    result = subprocess.run([cmd, "/d", "/c", str(wrapper)], env=environment(), timeout=15)
    assert result.returncode == 0 and json.loads(output.read_text())["alive"] is True


def test_unknown_ancestor_fails_closed(tmp_path: Path) -> None:
    code = "from workers.nse_market.windows_supervision import _Windows;_Windows().cmd_parent()"
    result = subprocess.run([BASE, "-c", code], env=environment(), capture_output=True, timeout=15)
    assert result.returncode != 0 and b"SCHEDULER_CMD_ANCESTOR_REQUIRED" in result.stderr


def test_duplicate_real_store_lock_and_recovery_after_hard_kill(tmp_path: Path) -> None:
    # Reuse the actual nonblocking OS-backed worker lock, without running a worker.
    script = """
import sys,time
from pathlib import Path
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError
folder=Path(sys.argv[1])
try:
    with Store(folder).lock():
        (folder / 'TEST_ONLY_locked').write_text('TEST_ONLY')
        time.sleep(60)
except DataContractError:
    raise SystemExit(23)
"""
    first = subprocess.Popen([BASE, "-c", script, str(tmp_path)], env=environment())
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "TEST_ONLY_locked").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (tmp_path / "TEST_ONLY_locked").exists()
        duplicate = subprocess.run(
            [BASE, "-c", script, str(tmp_path)], env=environment(), timeout=10
        )
        assert duplicate.returncode == 23
        first.kill()
        first.wait(timeout=10)
        from alphalens_data.daily.storage import Store

        with Store(tmp_path).lock():
            pass  # The OS releases the existing lock after actual process termination.
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=10)


@pytest.mark.parametrize("contained", [False, True])
def test_real_cmd_and_venv_ancestor_loss_reproduces_gap_then_contains_it(
    tmp_path: Path, contained: bool
) -> None:
    worker_script = tmp_path / "TEST_ONLY_worker.py"
    worker_script.write_text(WORKER)
    script = worker_script
    arguments = f'"{tmp_path}" wait'
    if contained:
        script = tmp_path / "TEST_ONLY_supervisor.py"
        script.write_text(RUNNER)
        (tmp_path / "command.json").write_text(
            json.dumps([sys.executable, str(worker_script), str(tmp_path), "wait"])
        )
        arguments = f'"{tmp_path}" cmd file'
    wrapper = tmp_path / "TEST_ONLY_wrapper.cmd"
    wrapper.write_text(
        f'@echo off\n"{sys.executable}" "{script}" {arguments}\nexit /b %errorlevel%\n'
    )
    cmd = str(Path(os.environ["SYSTEMROOT"]) / "System32/cmd.exe")
    parent = subprocess.Popen([cmd, "/d", "/c", str(wrapper)], env=environment())
    worker_pid = ready(tmp_path / "worker.pid", parent)
    worker = open_process(worker_pid)
    supervisor = open_process(ready(tmp_path / "supervisor.pid", parent)) if contained else None
    try:
        parent.kill()
        parent.wait(timeout=10)
        if contained:
            ended(worker)
            worker = 0
            assert supervisor is not None
            ended(supervisor)
            supervisor = None
            assert "ANCESTOR_EXITED_WORKER_INTERRUPTED" in (tmp_path / "facts.jsonl").read_text()
        else:
            # This is the preexisting uncontained shape, not evidence of the incident initiator.
            assert _Windows().api.WaitForSingleObject(worker, 350) == 258
    finally:
        if worker:
            os.kill(worker_pid, signal.SIGTERM)
            ended(worker)
        if supervisor:
            _Windows().close(supervisor)


def test_dead_pinned_ancestor_prevents_any_worker_execution(tmp_path: Path) -> None:
    from workers.nse_market.windows_supervision import supervise

    parent = subprocess.Popen([BASE, "-c", "pass"])
    handle = open_process(parent.pid)
    parent.wait(timeout=10)
    facts = []
    try:
        result = supervise(
            [BASE, "-c", WORKER, str(tmp_path), "normal"],
            parent_handle=handle,
            record=lambda *args: facts.append(args),
        )
        assert result == PARENT_INTERRUPTED
        assert facts == [("ANCESTOR_ALREADY_EXITED", PARENT_INTERRUPTED)]
        assert not (tmp_path / "worker.pid").exists()
    finally:
        _Windows().close(handle)


def test_control_interrupt_terminates_contained_worker_before_receipt(tmp_path: Path) -> None:
    from workers.nse_market.windows_supervision import supervise

    handle = open_process(os.getpid())
    facts = []

    def record(stage: str, code: int | None) -> None:
        if stage == "CONTAINED_WORKER_STARTED":
            ready(tmp_path / "worker.pid")
            raise KeyboardInterrupt
        pid = int((tmp_path / "worker.pid").read_text())
        ended(open_process(pid))
        facts.append((stage, code))

    try:
        result = supervise(
            [BASE, "-c", WORKER, str(tmp_path), "wait"], parent_handle=handle, record=record
        )
        assert result == 130
        assert facts == [("SUPERVISOR_CONTROL_INTERRUPT", 130)]
        assert not (tmp_path / "worker.done").exists()
    finally:
        _Windows().close(handle)


def test_native_argument_roundtrip_without_shell(tmp_path: Path) -> None:
    from workers.nse_market.windows_supervision import supervise

    expected = ["", "space space", 'quote"inside', "end\\", 'slash\\"quote', "%PATH%", "$()"]
    script = tmp_path / "TEST_ONLY_argv.py"
    target = tmp_path / "TEST_ONLY_argv.json"
    script.write_text(
        "import sys,json;from pathlib import Path;"
        "Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))"
    )
    handle = open_process(os.getpid())
    try:
        assert (
            supervise(
                [BASE, str(script), str(target), *expected],
                parent_handle=handle,
                record=lambda *_: None,
            )
            == 0
        )
        assert json.loads(target.read_text()) == expected
    finally:
        _Windows().close(handle)


def test_job_attribute_failure_prevents_process_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workers.nse_market import windows_supervision as module

    windows = _Windows()
    handle = open_process(os.getpid())
    monkeypatch.setattr(module, "_Windows", lambda: windows)
    created = []
    monkeypatch.setattr(windows.api, "UpdateProcThreadAttribute", lambda *_: 0)
    monkeypatch.setattr(windows.api, "CreateProcessW", lambda *args: created.append(args))
    try:
        with pytest.raises(OSError, match="WINDOWS_SUPERVISION_API_FAILED"):
            module.supervise(
                [BASE, "-c", WORKER, str(tmp_path), "normal"],
                parent_handle=handle,
                record=lambda *_: None,
            )
        assert not created
        assert not (tmp_path / "worker.pid").exists()
    finally:
        windows.close(handle)


def test_hard_kill_immediately_after_native_creation_before_resume_has_no_orphan(
    tmp_path: Path,
) -> None:
    # Stop immediately after the native API returns, before its Python wrapper
    # returns, attribute cleanup, or any ResumeThread call can occur.
    hook = """
from workers.nse_market import windows_supervision as module
import time
import ctypes
original = windows.api.CreateProcessW
def paused_creation(*args):
    result = original(*args)
    if result:
        info = ctypes.cast(args[-1], ctypes.POINTER(module._ProcessInfo)).contents
        (folder / 'created.pid').write_text(str(info.dwProcessId))
        time.sleep(60)
    return result
windows.api.CreateProcessW = paused_creation
module._Windows = lambda: windows
"""
    runner = RUNNER.replace("try:\n    result = supervise", hook + "\ntry:\n    result = supervise")
    command = [BASE, "-c", WORKER, str(tmp_path), "normal"]
    process = subprocess.Popen(
        [BASE, "-c", runner, str(tmp_path), str(os.getpid()), json.dumps(command)],
        env=environment(),
    )
    supervisor = ready(tmp_path / "supervisor.pid", process)
    worker = open_process(ready(tmp_path / "created.pid", process))
    try:
        assert not (tmp_path / "worker.pid").exists()
        os.kill(supervisor, signal.SIGTERM)
        process.wait(timeout=15)
        ended(worker)
        worker = 0
        assert not (tmp_path / "worker.pid").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if worker:
            ended(worker)


def test_parent_loss_stops_worker_even_while_receipt_writer_is_blocked(tmp_path: Path) -> None:
    from workers.nse_market.windows_supervision import supervise

    parent = subprocess.Popen([BASE, "-c", "import time;time.sleep(60)"])
    handle = open_process(parent.pid)
    facts = []

    def blocked_receipt(stage: str, code: int | None) -> None:
        if stage == "CONTAINED_WORKER_STARTED":
            pid = ready(tmp_path / "worker.pid")
            worker = open_process(pid)
            parent.kill()
            parent.wait(timeout=10)
            # Main supervision loop is inside this callback; native watchdog must stop it.
            ended(worker)
        facts.append((stage, code))

    try:
        assert (
            supervise(
                [BASE, "-c", WORKER, str(tmp_path), "wait"],
                parent_handle=handle,
                record=blocked_receipt,
            )
            == PARENT_INTERRUPTED
        )
        assert facts[-1] == ("ANCESTOR_EXITED_WORKER_INTERRUPTED", PARENT_INTERRUPTED)
        assert not (tmp_path / "worker.done").exists()
    finally:
        _Windows().close(handle)
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=10)
