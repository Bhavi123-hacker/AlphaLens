"""Real loopback process, duplicate denial, cooperative stop and session-preserving restart."""

import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import read, stop
from alphalens_api.operations.store import OperationsStore


def test_real_supervisor_restart_and_private_api(tmp_path: Path) -> None:
    root = tmp_path / "TEST_ONLY_deployment"
    auth = AuthStore(root / "auth")
    auth.initialize()
    secret = secrets.token_urlsafe(32)
    auth.bootstrap("test_operator", secret)
    OperationsStore(root / "ops").initialize()
    (root / "web/assets").mkdir(parents=True)
    (root / "web/index.html").write_text('<script src="/assets/app.js"></script>')
    (root / "web/assets/app.js").write_text("/* TEST_ONLY */")
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    control = root / "ops/local"
    repo = Path(__file__).resolve().parents[2]
    args = [
        sys.executable,
        "-m",
        "scripts.serve_test_local",
        "--root",
        str(root),
        "--port",
        str(port),
    ]
    with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
        for attempt in range(2):
            with (root / f"server-{attempt}.log").open("w") as log:
                process = subprocess.Popen(args, cwd=repo, stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise AssertionError("TEST_ONLY_SERVER_START_FAILED")
                        if (control / "instance.json").exists() and read(
                            control / "instance.json"
                        ).get("state") == "RUNNING":
                            break
                        time.sleep(0.1)
                    else:
                        raise AssertionError("TEST_ONLY_SERVER_READY_TIMEOUT")
                    assert client.get("/login").status_code == 200
                    if attempt == 0:
                        assert client.get("/api/v1/auth/session").status_code == 401
                        login = client.post(
                            "/api/v1/auth/login",
                            json={"username": "test_operator", "password": secret},
                            headers={
                                "Origin": str(client.base_url).rstrip("/"),
                                "X-AlphaLens-Local": "p21",
                            },
                        )
                        assert login.status_code == 200
                        duplicate = subprocess.run(
                            args, cwd=repo, stdout=log, stderr=log, timeout=20
                        )
                        assert duplicate.returncode != 0
                    session = client.get("/api/v1/auth/session")
                    assert session.status_code == 200  # Same cookie remains valid across restart.
                    if attempt == 1:
                        reply = client.post(
                            "/api/v1/auth/logout",
                            json={},
                            headers={
                                "Origin": str(client.base_url).rstrip("/"),
                                "X-CSRF-Token": session.json()["csrf_token"],
                            },
                        )
                        assert reply.status_code == 200
                        assert client.get("/api/v1/auth/session").status_code == 401
                    assert stop(control)["status"] == "OWNED_INSTANCE_STOPPED"
                    assert process.wait(timeout=10) == 0
                finally:
                    if process.poll() is None:
                        # Only this newly spawned isolated test child; never an adopted PID.
                        process.terminate()
                        process.wait(timeout=10)
