"""Explicit bounded local operator commands; no implicit provider acquisition."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from workers.nse_market import daily, engine, operational


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=(
            "capture",
            "status",
            "score",
            "daily",
            "run",
            "normalize",
            "publish",
            "freeze-current",
        ),
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--provider-root", type=Path)
    parser.add_argument("--v2-root", type=Path)
    parser.add_argument("--max-new", type=int, default=50)
    parser.add_argument("--max-requests", type=int, default=100)
    parser.add_argument("--permission-reference")
    parser.add_argument("--session", type=date.fromisoformat)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--scheduled", action="store_true")
    args = parser.parse_args()
    if args.operation == "run":
        if args.config is None:
            parser.error("run requires protected configuration")
        try:
            result = operational.run(
                operational.configured(args.config),
                session=args.session,
                collect=args.collect,
                scheduled=args.scheduled,
            )
        except (ValueError, OSError):
            result = {"state": "FAILED", "error_code": "EXPANDED_OPERATIONAL_CONFIGURATION_INVALID"}
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        sys.exit(1 if result["state"] == "FAILED" else 0)
    if args.root is None:
        parser.error("this operation requires --root")
    if args.operation == "freeze-current":
        from workers.nse_market.forward_cohort import freeze_current

        result = freeze_current(args.root)
        engine.publish_workspace(args.root)
    elif args.operation == "publish":
        result = engine.publish_workspace(args.root)
    elif args.operation == "normalize":
        result = engine.materialize(args.root)
    elif args.operation == "capture":
        if args.provider_root is None or args.permission_reference is None:
            parser.error(
                "capture requires protected provider root and explicit permission reference"
            )
        result = engine.capture(
            args.root,
            args.provider_root,
            max_new=args.max_new,
            max_requests=args.max_requests,
            permission_reference=args.permission_reference,
        )
    elif args.operation == "daily":
        if args.v2_root is None or args.provider_root is None or args.session is None:
            parser.error("daily requires V2/provider roots and exact session date")
        if args.permission_reference is None:
            parser.error("daily requires explicit private permission reference")
        result = daily.run(
            args.root,
            args.provider_root,
            args.v2_root,
            session=args.session,
            max_stocks=args.max_new,
            max_requests=args.max_requests,
            collect=args.collect,
            permission_reference=args.permission_reference,
        )
    elif args.operation == "score":
        if args.v2_root is None:
            parser.error("score requires original verified V2 model root")
        result = engine.score(args.root, args.v2_root)
    else:
        result = engine.workspace(args.root, args.v2_root)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print(
            json.dumps(
                {
                    "state": "FAILED",
                    "error_code": "NSE_MARKET_OPERATION_FAILED",
                    "source_requests_last_run": None,
                }
            )
        )
        sys.exit(1)
