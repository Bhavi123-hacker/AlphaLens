"""Read-only private deployment manifest/config validation, with no live probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != 1
        or value.get("mode") != "PRIVATE_EXPERIMENTAL_RESEARCH"
        or value.get("backend_host") != "127.0.0.1"
        or value.get("database_host") != "127.0.0.1"
        or type(value.get("backend_port")) is not int
        or value["backend_port"] != 8041
        or any(
            value.get(key) is not False
            for key in (
                "public_ingress_enabled",
                "public_market_data_authorized",
                "trading_enabled",
            )
        )
        or value.get("collector_candidate_activation") != "BLOCKED_APPROVAL"
    ):
        raise ValueError("PRIVATE_NETWORK_AND_ACTIVATION_BOUNDARY_REQUIRED")
    expected = {
        "configured_securities": 500,
        "max_stocks_per_run": 250,
        "reserved_gets_per_run": 600,
        "reserved_gets_per_day": 1800,
        "cooldown_minutes": 60,
        "cadence_ist": ["20:30", "21:30", "22:30"],
    }
    if any(value.get(key) != required for key, required in expected.items()):
        raise ValueError("ORIGINAL_COLLECTION_POLICY_REQUIRED")
    for key in (
        "backend_python",
        "backend_config",
        "collector_candidate_python",
        "collector_candidate_wrapper",
        "collector_candidate_config",
        "rollback_backend_config",
    ):
        item = value.get(key)
        if not isinstance(item, str) or "\\" in item or ":" in item:
            raise ValueError("WORKSPACE_RELATIVE_RELEASE_PATH_REQUIRED")
        path = Path(item)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("WORKSPACE_RELATIVE_RELEASE_PATH_REQUIRED")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("infra/release/alphalens-private.json")
    )
    args = parser.parse_args()
    value = json.loads(args.manifest.read_bytes())
    validate(value)
    repo = Path(__file__).resolve().parents[1]
    # Explicitly parse, never start the application or acquire provider data.
    from alphalens_api.auth.permissions import verify
    from alphalens_api.core.config import Settings
    from alphalens_api.frontend import validate as validate_frontend

    config = repo / value["backend_config"]
    verify(config)
    raw = json.loads(config.read_bytes())
    if "database_url" in raw:
        raise ValueError("DATABASE_SECRET_MUST_STAY_IN_CREDENTIAL_MANAGER")
    settings = Settings(**raw)
    # The native supervisor hardcodes its listener to 127.0.0.1; Settings has no
    # configurable bind host. Its validated Origin must agree with this port.
    if settings.port != value["backend_port"] or (
        f"http://127.0.0.1:{settings.port}" not in settings.cors_origins
    ):
        raise ValueError("PRIVATE_CONFIG_MANIFEST_MISMATCH")
    if settings.upstox_private_view is not False:
        raise ValueError("WEB_PROVIDER_ACQUISITION_MUST_STAY_DISABLED")
    validate_frontend(settings)
    for key in ("backend_python", "collector_candidate_python", "collector_candidate_wrapper"):
        if not (repo / value[key]).is_file():
            raise ValueError("PREPARED_RUNTIME_REQUIRED")
    print(
        json.dumps(
            {
                "state": "VERIFIED_COMPLETE",
                "scope": "MANIFEST_CONFIG_AND_COMPILED_BUILD_ONLY",
                "provider_requests": 0,
                "tasks_modified": False,
                "public_ingress": False,
            }
        )
    )


if __name__ == "__main__":
    main()
