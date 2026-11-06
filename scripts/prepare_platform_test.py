"""Create isolated TEST_ONLY operator state; retain genuine market/alert evidence read-only."""

import argparse
import json
import secrets
from pathlib import Path

from alphalens_api.auth.permissions import restrict
from alphalens_api.auth.store import AuthStore
from alphalens_api.operations.recovery import copy_database
from alphalens_api.operations.store import OperationsStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--alerts-source", type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=False)
    restrict(args.root)
    store = AuthStore(args.root / "auth")
    store.initialize()
    secret = secrets.token_urlsafe(32)
    store.bootstrap("test_operator", secret)
    credentials = args.root / "credentials.json"
    credentials.write_text(json.dumps({"username": "test_operator", "password": secret}))
    if __import__("os").name != "nt":
        credentials.chmod(0o600)
    OperationsStore(args.root / "operations").initialize()
    alerts = args.root / "alerts"
    alerts.mkdir()
    restrict(alerts)
    copy_database(args.alerts_source / "alerts.sqlite3", alerts / "alerts.sqlite3")
    print("ISOLATED_TEST_ONLY_PLATFORM_STATE_INITIALIZED")


if __name__ == "__main__":
    main()
