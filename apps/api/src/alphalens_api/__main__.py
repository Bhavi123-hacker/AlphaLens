"""Loopback startup and explicit offline discovery-index preparation."""

import argparse
import json

import uvicorn

from .catalog import build_catalog
from .core.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaLens local research read API")
    parser.add_argument("command", choices=("serve", "build-catalog"), nargs="?", default="serve")
    args = parser.parse_args()
    settings = Settings()
    if args.command == "build-catalog":
        print(json.dumps(build_catalog(settings), sort_keys=True))
    else:
        uvicorn.run(
            "alphalens_api.main:app",
            host="127.0.0.1",
            port=settings.port,
            proxy_headers=False,
            access_log=False,
        )


if __name__ == "__main__":
    main()
