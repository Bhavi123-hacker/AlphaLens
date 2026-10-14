"""Additive private UI configuration and isolated browser account; originals preserved."""

import json
import secrets
from pathlib import Path

from alphalens_api.auth.permissions import restrict
from alphalens_api.auth.store import AuthStore
from alphalens_api.operations.store import OperationsStore


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    root = repo / ".local-data/p31-runtime"
    root.mkdir(exist_ok=False)
    restrict(root)
    config = json.loads((repo / ".local-data/p30-runtime/operator-config.json").read_bytes())
    if "database_url" in config:
        raise ValueError("SECRET_CONFIG_REJECTED")
    config["frontend_root"] = str(repo / ".local-data/p31-web-build")
    (root / "operator-config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    browser = repo / ".local-data/p31-browser-runtime"
    browser.mkdir(exist_ok=False)
    restrict(browser)
    isolated = json.loads(
        (repo / ".local-data/p30-browser-runtime/operator-config.json").read_bytes()
    )
    isolated.update(
        port=8029,
        auth_root=str(browser / "auth"),
        operations_root=str(browser / "operations"),
        frontend_root=config["frontend_root"],
        cors_origins=["http://127.0.0.1:8029"],
    )
    store = AuthStore(browser / "auth")
    store.initialize()
    password = secrets.token_urlsafe(32)
    store.bootstrap("test_operator", password)
    OperationsStore(browser / "operations").initialize()
    (browser / "credentials.json").write_text(
        json.dumps({"username": "test_operator", "password": password}), encoding="utf-8"
    )
    (browser / "operator-config.json").write_text(json.dumps(isolated, indent=2), encoding="utf-8")
    print("P31_ADDITIVE_CONFIG_READY_ORIGINAL_OPERATOR_AND_DATABASE_PRESERVED")


if __name__ == "__main__":
    main()
