"""One foreground loopback process and private, cooperative stop requests."""

import argparse
import asyncio
import json
import os
import secrets
import socket
import sqlite3
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn

from alphalens_api.auth.permissions import restrict, verify
from alphalens_api.core.config import Settings
from alphalens_api.core.logging import server_logging_config
from alphalens_api.operations.store import OperationsStore
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError


def configured(path: Path) -> Settings:
    if path.stat().st_size > 16384:
        raise ValueError("LOCAL_CONFIG_SIZE_INVALID")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict) or "database_url" in value:
        raise ValueError("SECRETS_MUST_STAY_OUTSIDE_LOCAL_CONFIG")
    settings = Settings(**value)
    if settings.database_credential_target and settings.database_url is None:
        from pydantic import SecretStr

        from .postgres import reader_url

        settings = settings.model_copy(update={"database_url": SecretStr(reader_url())})
    expected = f"http://127.0.0.1:{settings.port}"
    if expected not in settings.cors_origins:
        raise ValueError("SAME_ORIGIN_NOT_CONFIGURED")
    return settings


def runtime(settings: Settings) -> Path:
    if settings.operations_root is None:
        raise ValueError("OPERATIONS_NOT_CONFIGURED")
    verify(settings.operations_root)
    root = settings.operations_root / "local"
    root.mkdir(exist_ok=True, mode=0o700)
    restrict(root)
    return root


def atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".writing")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 8192:
        raise ValueError("LOCAL_STATE_INVALID")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("LOCAL_STATE_INVALID")
    return value


def check(settings: Settings) -> dict[str, Any]:
    from alphalens_api.frontend import validate
    from alphalens_api.operations.health import inspect, probe_api

    validate(settings)
    alive = probe_api(settings.port)
    health = inspect(settings, api_responding=alive)
    # CLI artifact checks do not prove that an HTTP service is running.
    required = (
        "authentication",
        "catalog",
        "research_data",
        "research_runs",
        "research_reports",
        "notifications",
        "operations",
    )
    ready = all(
        health["components"].get(k, {}).get("status") in {"HEALTHY", "DEGRADED"} for k in required
    )
    return {
        "local_setup": "PASSED" if ready else "BLOCKED",
        "api_running": alive,
        "python": sys.version.split()[0],
        "frontend": "COMPILED",
        "url": f"http://127.0.0.1:{settings.port}/login",
        "health": health,
        "automatic_acquisition": "DISABLED",
        "public_deployment": "BLOCKED",
    }


async def serve(settings: Settings, root: Path) -> None:
    from alphalens_api.main import create_app

    # Bind before publishing ownership; never adopt or stop another listener.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform == "win32":
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", settings.port))
        listener.listen(128)
    except BaseException:
        listener.close()
        raise
    nonce = secrets.token_urlsafe(32)
    state = {
        "version": "p24.local.v1",
        "pid": os.getpid(),
        "nonce": nonce,
        "started_at": datetime.now(UTC).isoformat(),
        "port": settings.port,
        "state": "STARTING",
    }
    atomic(root / "instance.json", state)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings),
            host="127.0.0.1",
            port=settings.port,
            proxy_headers=False,
            access_log=False,
            log_config=server_logging_config(),
            timeout_graceful_shutdown=15,
        )
    )

    async def watch() -> None:
        announced = False
        while not server.should_exit:
            if server.started and not announced:
                announced = True
                state["state"] = "RUNNING"
                atomic(root / "instance.json", state)
                print(
                    json.dumps(
                        {
                            "status": "LOCAL_PROCESS_READY",
                            "url": f"http://127.0.0.1:{settings.port}/login",
                        }
                    ),
                    flush=True,
                )
            stop = root / "shutdown.json"
            if stop.is_file():
                with suppress(OSError, ValueError):
                    if secrets.compare_digest(str(read(stop).get("nonce", "")), nonce):
                        server.should_exit = True
            await asyncio.sleep(0.25)

    watcher = asyncio.create_task(watch())
    try:
        await server.serve(sockets=[listener])
    finally:
        watcher.cancel()
        with suppress(asyncio.CancelledError):
            await watcher
        listener.close()
        state["state"] = "STOPPED"
        atomic(root / "instance.json", state)


def stop(root: Path) -> dict[str, str]:
    value = read(root / "instance.json")
    if value.get("state") != "RUNNING":
        raise ValueError("LOCAL_INSTANCE_NOT_RUNNING")
    # Only the private matching supervisor observes this request. No PID kill,
    # socket mutation, process enumeration or external HTTP stop endpoint.
    atomic(root / "shutdown.json", {"nonce": value["nonce"]})
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        current = read(root / "instance.json")
        if current.get("nonce") != value["nonce"]:
            raise ValueError("LOCAL_INSTANCE_CHANGED")
        if current.get("state") == "STOPPED":
            return {"status": "OWNED_INSTANCE_STOPPED"}
        time.sleep(0.2)
    raise ValueError("LOCAL_SHUTDOWN_NOT_CONFIRMED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("setup", "check", "start", "stop"):
        commands.add_parser(command)
    backup_parser = commands.add_parser("backup")
    backup_parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        settings = configured(args.config)
        if args.command == "setup":
            # Explicit operations initialization only; auth/bootstrap is separate.
            if settings.operations_root is None:
                raise ValueError("OPERATIONS_NOT_CONFIGURED")
            OperationsStore(settings.operations_root).initialize()
        if args.command in {"setup", "check", "start"}:
            result = check(settings)
            print(json.dumps(result, sort_keys=True), flush=True)
            if result["local_setup"] != "PASSED":
                return 2
        if args.command == "start":
            root = runtime(settings)
            with Store(root).lock():
                asyncio.run(serve(settings, root))
        elif args.command == "stop":
            print(json.dumps(stop(runtime(settings))))
        elif args.command == "backup":
            from alphalens_api.operations.recovery import backup

            print(json.dumps(backup(settings, args.destination)))
        return 0
    except (OSError, ValueError, sqlite3.Error, DataContractError):
        print(
            json.dumps(
                {
                    "status": "LOCAL_OPERATION_REJECTED",
                    "guidance": (
                        "Check setup, private configuration, port conflicts "
                        "and owned instance state."
                    ),
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
