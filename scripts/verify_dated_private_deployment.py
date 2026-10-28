"""Read-only dated deployment wiring checks; never activate a task or contact a provider."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def relative(value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or ":" in value
    ):
        raise ValueError("WORKSPACE_RELATIVE_PATH_REQUIRED")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("WORKSPACE_RELATIVE_PATH_REQUIRED")
    return path


def validate(value: dict[str, Any]) -> None:
    expected = {
        "schema": 1,
        "recorded_date": "2026-10-28",
        "mode": "PRIVATE_EXPERIMENTAL_RESEARCH",
        "backend_host": "127.0.0.1",
        "backend_port": 8041,
        "database_host": "127.0.0.1",
        "public_ingress_enabled": False,
        "public_market_data_authorized": False,
        "trading_enabled": False,
        "configured_securities": 500,
        "max_stocks_per_run": 250,
        "reserved_gets_per_run": 600,
        "reserved_gets_per_day": 1800,
        "cadence_ist": ["20:30", "21:30", "22:30"],
        "cooldown_minutes": 60,
        "model_status": "EXPERIMENTAL_RESEARCH",
        "collector_task": "AlphaLens-Private-NSE-Market-Research",
        "collector_state": "PATCHED_RUNTIME_ACTIVE_AWAITING_CANDLE_DELIVERY",
    }
    if any(
        type(value.get(key)) is not type(required) or value[key] != required
        for key, required in expected.items()
    ):
        raise ValueError("PRIVATE_DEPLOYMENT_POLICY_MISMATCH")
    flags = value.get("collector_battery_policy")
    if (
        not isinstance(flags, dict)
        or set(flags) != {"DisallowStartIfOnBatteries", "StopIfGoingOnBatteries"}
        or any(flag is not False for flag in flags.values())
    ):
        raise ValueError("REVIEWED_BATTERY_FLAGS_REQUIRED")
    for key in (
        "backend_python",
        "backend_config",
        "frontend_root",
        "frontend_entry",
        "collector_python",
        "collector_config",
        "rollback_backend_config",
    ):
        relative(value.get(key))
    for key in ("backend_config_sha256", "frontend_index_sha256", "collector_runtime_fingerprint"):
        checksum = value.get(key)
        if (
            not isinstance(checksum, str)
            or len(checksum) != 64
            or any(char not in "0123456789abcdef" for char in checksum)
        ):
            raise ValueError("SHA256_REQUIRED")


def verify(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    validate(value)
    root = root.resolve(strict=True)

    def target(key: str) -> Path:
        result = (root / relative(value[key])).resolve(strict=True)
        if not result.is_relative_to(root):
            raise ValueError("DEPLOYMENT_PATH_ESCAPES_WORKSPACE")
        return result

    config_path, frontend = target("backend_config"), target("frontend_root")
    raw = config_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != value["backend_config_sha256"]:
        raise ValueError("CONFIG_HASH_MISMATCH")
    config = json.loads(raw)
    if (
        config.get("port") != 8041
        or config.get("upstox_private_view") is not False
        or config.get("cors_origins") != ["http://127.0.0.1:8041"]
        or "database_url" in config
        or Path(config.get("frontend_root", "")).resolve() != frontend
    ):
        raise ValueError("PRIVATE_CONFIG_BOUNDARY_MISMATCH")
    for key in (
        "backend_python",
        "collector_python",
        "collector_config",
        "rollback_backend_config",
    ):
        if not target(key).is_file():
            raise ValueError("DEPLOYMENT_FILE_REQUIRED")
    index = (frontend / "index.html").read_bytes()
    if hashlib.sha256(index).hexdigest() != value["frontend_index_sha256"]:
        raise ValueError("FRONTEND_INDEX_HASH_MISMATCH")
    entry = (frontend / relative(value["frontend_entry"])).resolve(strict=True)
    if not entry.is_relative_to(frontend) or not entry.is_file():
        raise ValueError("FRONTEND_ENTRY_REQUIRED")
    if ("/" + value["frontend_entry"]) not in index.decode("utf-8"):
        raise ValueError("FRONTEND_ENTRY_MISMATCH")
    return {
        "state": "VERIFIED_COMPLETE",
        "scope": "OFFLINE_DEPLOYMENT_WIRING_ONLY",
        "provider_requests": 0,
        "tasks_modified": False,
        "network_ports_opened": False,
        "app_restarted": False,
        "runtime_or_security_recertified": False,
        "live_candle_delivery_verified": False,
        "public_market_data_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path, default=Path("infra/release/alphalens-private-2026-10-28.json")
    )
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace, json.loads(args.manifest.read_bytes()))))


if __name__ == "__main__":
    main()
