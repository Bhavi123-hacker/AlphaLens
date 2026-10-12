"""Explicit isolated TEST_ONLY local demo, no source acquisition or model fitting."""

import argparse
import getpass
import json
from pathlib import Path

from scripts.build_p17_test_evidence import build
from workers.alerts.store import AlertStore
from workers.providers.store import ProviderStore

from alphalens_api.auth.permissions import restrict
from alphalens_api.auth.store import AuthStore
from alphalens_api.operations.store import OperationsStore


def prepare(root: Path, frontend: Path, username: str, password: str) -> Path:
    if not root.name.startswith("TEST_ONLY_demo") or root.exists():
        raise ValueError("NEW_ISOLATED_TEST_ONLY_DEMO_LOCATION_REQUIRED")
    if not (frontend / "index.html").is_file():
        raise ValueError("COMPILED_FRONTEND_REQUIRED")
    root.mkdir(parents=True)
    restrict(root)
    settings = build(root)
    auth = AuthStore(root / "auth")
    auth.initialize()
    auth.bootstrap(username, password)
    alerts = root / "alerts"
    alerts.mkdir()
    restrict(alerts)
    AlertStore(alerts).initialize()
    OperationsStore(root / "operations").initialize()
    ProviderStore(root / "providers").initialize()
    settings = settings.model_copy(
        update={
            "auth_root": auth.root,
            "alerts_root": alerts,
            "operations_root": root / "operations",
            "providers_root": root / "providers",
            "frontend_root": frontend.resolve(),
            "port": 8029,
            "cors_origins": ("http://127.0.0.1:8029",),
        }
    )
    config = root / "config.json"
    config.write_text(
        json.dumps(settings.model_dump(mode="json", exclude={"database_url"}), indent=2),
        encoding="utf-8",
    )
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--frontend", type=Path, required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = getpass.getpass("New local TEST_ONLY demo password (hidden): ")
    if password != getpass.getpass("Confirm (hidden): "):
        raise SystemExit("PASSWORD_CONFIRMATION_MISMATCH")
    config = prepare(args.root, args.frontend, args.username, password)
    print(f"TEST_ONLY_DEMO_PREPARED: {config}; loopback only; all market acquisition disabled")


if __name__ == "__main__":
    main()
