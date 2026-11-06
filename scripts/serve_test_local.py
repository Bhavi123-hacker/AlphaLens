"""Isolated TEST_ONLY supervisor for real socket/restart integration tests."""

import argparse
import asyncio
from pathlib import Path

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.local.cli import runtime, serve
from alphalens_data.daily.storage import Store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    if not args.root.name.startswith("TEST_ONLY_"):
        raise ValueError("ISOLATED_TEST_ONLY_ROOT_REQUIRED")
    account = AuthStore(args.root / "auth").diagnostics()["account"]
    if not account or account["username"] != "test_operator":
        raise ValueError("TEST_ONLY_ACCOUNT_REQUIRED")
    settings = Settings(
        environment="test",
        auth_root=args.root / "auth",
        operations_root=args.root / "ops",
        frontend_root=args.root / "web",
        port=args.port,
        cors_origins=(f"http://127.0.0.1:{args.port}",),
    )
    control = runtime(settings)
    with Store(control).lock():
        asyncio.run(serve(settings, control))


if __name__ == "__main__":
    main()
