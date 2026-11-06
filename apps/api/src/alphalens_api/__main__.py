"""Loopback startup and explicit offline discovery-index preparation."""

import argparse
import json

import uvicorn

from .catalog import build_catalog
from .core.config import Settings
from .core.logging import server_logging_config
from .hosted import serving_address, validate_state


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaLens local research read API")
    parser.add_argument("command", choices=("serve", "build-catalog"), nargs="?", default="serve")
    args = parser.parse_args()
    settings = Settings()
    if args.command == "build-catalog":
        print(json.dumps(build_catalog(settings), sort_keys=True))
    else:
        validate_state(settings)
        host, port = serving_address(settings)
        uvicorn.run(
            "alphalens_api.main:app",
            host=host,
            port=port,
            proxy_headers=False,
            forwarded_allow_ips="",
            access_log=False,
            log_config=server_logging_config(),
        )


if __name__ == "__main__":
    main()
