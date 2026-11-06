"""Explicit one-shot operations; no scheduler, outbound messages or automatic acquisition."""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from alphalens_data.errors import DataContractError
from workers.observability import completed

from .contracts import Preferences
from .producer import (
    check_freshness,
    inspect_lock,
    process_daily,
    process_paper,
    process_valuation,
    source_check,
)
from .store import AlertError, AlertStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    process = commands.add_parser("process")
    process.add_argument("--daily-root", type=Path, required=True)
    source = commands.add_parser("check-source")
    source.add_argument(
        "--network", action="store_true", help="Fixed public metadata only; no prices"
    )
    paper = commands.add_parser("import-paper")
    paper.add_argument("--state", type=Path, required=True)
    paper.add_argument("--test-only", action="store_true")
    valuation = commands.add_parser("import-valuation")
    valuation.add_argument("--snapshot", type=Path, required=True)
    valuation.add_argument("--test-only", action="store_true")
    freshness = commands.add_parser("freshness")
    freshness.add_argument("--evidence", type=Path, required=True)
    freshness.add_argument("--daily-root", type=Path, required=True)
    freshness.add_argument("--test-only", action="store_true")
    models = commands.add_parser(
        "inspect-models", help="Checksum frozen candidate metadata without loading estimators"
    )
    models.add_argument("--run-root", type=Path, required=True)
    lock = commands.add_parser("inspect-lock")
    lock.add_argument("--daily-root", type=Path, required=True)
    history = commands.add_parser("list")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--offset", type=int, default=0)
    history.add_argument("--category")
    history.add_argument("--severity")
    history.add_argument("--lifecycle")
    history.add_argument("--delivery")
    history.add_argument("--search", default="")
    history.add_argument("--test-only", action="store_true")
    detail = commands.add_parser("get")
    detail.add_argument("alert_id")
    detail.add_argument("--test-only", action="store_true")
    state = commands.add_parser("state")
    state.add_argument("alert_id")
    state.add_argument("target", choices=["READ", "ACKNOWLEDGED", "RESOLVED"])
    prefs = commands.add_parser("preferences")
    prefs.add_argument("--file", type=Path)
    commands.add_parser("deliver")
    commands.add_parser(
        "retry", help="Retry only due pending in-app deliveries; exhausted failures stay failed"
    )
    commands.add_parser(
        "prune", help="Explicitly prune old resolved INFO/WARNING; retain dedup tombstones"
    )
    args = parser.parse_args(argv)
    started = time.perf_counter()
    succeeded = False
    store = AlertStore(args.root)
    result: Any
    try:
        if args.command == "init":
            store.initialize()
            result = {
                "initialized": True,
                "channels": {
                    "IN_APP": "AVAILABLE",
                    "EMAIL": "UNAVAILABLE",
                    "DESKTOP": "UNAVAILABLE",
                },
                "scheduling": "DISABLED",
            }
        elif args.command == "process":
            result = process_daily(store, args.daily_root)
            result["delivery"] = store.deliver()
        elif args.command == "check-source":
            result = source_check(store, network=args.network)
            result["delivery"] = store.deliver()
        elif args.command == "import-paper":
            result = {
                "published": process_paper(store, args.state, test_only=args.test_only),
                "delivery": store.deliver(),
            }
        elif args.command == "list":
            rows, count = store.listing(
                category=args.category,
                severity=args.severity,
                lifecycle=args.lifecycle,
                delivery=args.delivery,
                search=args.search,
                limit=args.limit,
                offset=args.offset,
                test_only=args.test_only,
            )
            result = {"alerts": rows, "total": count}
        elif args.command == "import-valuation":
            result = {
                "published": process_valuation(store, args.snapshot, test_only=args.test_only),
                "delivery": store.deliver(),
            }
        elif args.command == "freshness":
            result = check_freshness(
                store, args.evidence, args.daily_root, test_only=args.test_only
            )
            result["delivery"] = store.deliver()
        elif args.command == "inspect-models":
            from .model_checks import inspect_models

            result = inspect_models(store, args.run_root)
            result["delivery"] = store.deliver()
        elif args.command == "inspect-lock":
            result = inspect_lock(store, args.daily_root)
            result["delivery"] = store.deliver()
        elif args.command == "get":
            result = store.get(args.alert_id, test_only=args.test_only)
        elif args.command == "state":
            store.transition(args.alert_id, args.target)
            result = {"state": args.target}
        elif args.command == "preferences":
            if args.file:
                if args.file.stat().st_size > 8192:
                    raise AlertError("PREFERENCE_FILE_SIZE_LIMIT")
                store.set_preferences(Preferences.model_validate_json(args.file.read_bytes()))
            result = store.preferences().model_dump(mode="json")
        elif args.command in {"deliver", "retry"}:
            result = store.deliver()
        else:
            result = {"pruned": store.prune()}
        print(json.dumps(result, indent=2, ensure_ascii=True))
        succeeded = True
        return 0
    except (AlertError, DataContractError, OSError, ValueError, KeyError, sqlite3.Error):
        # Never print raw provider exceptions, personal data, credentials or file paths.
        print(
            json.dumps(
                {
                    "error": "ALERT_OPERATION_REJECTED",
                    "details": "Review configured local evidence and operation limits.",
                }
            )
        )
        return 2
    finally:
        completed("alerts", args.command, started, 200 if succeeded else 500)


if __name__ == "__main__":
    raise SystemExit(main())
