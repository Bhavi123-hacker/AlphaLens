"""Private immutable process facts. Never provider bodies, arguments or exception messages."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alphalens_api.auth.permissions import restrict, verify

EVENTS = {
    "LAUNCHER_STARTED",
    "LAUNCHER_EXIT",
    "LAUNCHER_INTERRUPTED",
    "LAUNCHER_EXCEPTION",
    "WORKER_STARTED",
    "WORKER_FINISHED",
    "WORKER_INTERRUPTED",
    "STAGE",
    "COOLDOWN_WAIT",
}


def launch_id() -> str:
    candidate = os.environ.get("ALPHALENS_NSE_LAUNCH_ID", "")
    return candidate if re.fullmatch(r"[a-f0-9]{32}", candidate) else uuid.uuid4().hex


def emit(
    root: Path,
    correlation: str,
    event: str,
    *,
    run_id: str | None = None,
    stage: str | None = None,
    code: str | None = None,
    exit_code: int | None = None,
    wait_seconds: float | None = None,
) -> None:
    if (
        event not in EVENTS
        or not re.fullmatch(r"[a-f0-9]{32}", correlation)
        or (run_id is not None and not re.fullmatch(r"[a-f0-9]{32}", run_id))
        or any(s is not None and not re.fullmatch(r"[A-Z0-9_]{1,100}", s) for s in (stage, code))
    ):
        raise ValueError("NSE_DIAGNOSTIC_METADATA_REJECTED")
    verify(root)
    folder = root
    for part in ("operational", "diagnostics"):
        folder = folder / part
        if folder.is_symlink() or not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError("NSE_DIAGNOSTIC_PRIVATE_PATH_REQUIRED")
        if part == "diagnostics":
            try:
                folder.mkdir(mode=0o700)
            except FileExistsError:
                pass
            else:
                restrict(folder)
            verify(folder)
        else:
            folder.mkdir(exist_ok=True, mode=0o700)
    value = {
        "version": "nse.process-facts.v1",
        "at": datetime.now(UTC).isoformat(),
        "event": event,
        "launch_id": correlation,
        "run_id": run_id,
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "stage": stage,
        "code": code,
        "exit_code": exit_code,
        "wait_seconds": wait_seconds,
        "termination_initiator": None,
    }
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    target = folder / (uuid.uuid4().hex + ".json")
    temporary = target.with_suffix(".tmp")
    for path, data in (
        (temporary, body),
        (target.with_suffix(".json.sha256"), hashlib.sha256(body).hexdigest().encode()),
    ):
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            path.chmod(0o600)
    temporary.replace(target)


def configured_root(config: Path) -> Path:
    """Only enough protected configuration to record launch; worker still checks full approval."""
    if config.is_symlink() or config.stat().st_size > 16384:
        raise ValueError("NSE_LAUNCHER_CONFIG_REJECTED")
    verify(config, directory=False)
    root = Path(json.loads(config.read_bytes())["root"])
    if not root.is_absolute() or root.is_symlink():
        raise ValueError("NSE_DIAGNOSTIC_PRIVATE_PATH_REQUIRED")
    verify(root)
    return root
