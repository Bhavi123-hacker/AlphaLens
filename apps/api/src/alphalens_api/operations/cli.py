"""Explicit finite operator commands; no background jobs or outbound delivery."""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from workers.alerts.store import AlertStore
from workers.observability import completed

from alphalens_api.core.config import Settings

from .health import inspect
from .recovery import backup, restore
from .store import OperationsStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("init", "check", "history", "process-alerts", "backup", "restore")
    )
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args(argv)
    settings = Settings()
    started = time.perf_counter()
    succeeded = False
    result: dict[str, Any]
    try:
        if args.command == "backup":
            if args.destination is None:
                raise ValueError("BACKUP_DESTINATION_REQUIRED")
            result = backup(settings, args.destination)
        elif args.command == "restore":
            if args.source is None or args.destination is None:
                raise ValueError("RESTORE_PATHS_REQUIRED")
            result = restore(args.source, args.destination)
        else:
            if settings.operations_root is None:
                raise ValueError("OPERATIONS_ROOT_REQUIRED")
            store = OperationsStore(settings.operations_root)
            if args.command == "init":
                store.initialize()
                result = {"initialized": True, "scheduling": "DISABLED"}
            elif args.command == "check":
                report = inspect(settings)
                result = {
                    "probe_id": store.record(report, test_only=settings.test_only_evidence),
                    "report": report,
                }
            elif args.command == "history":
                result = store.history()
            else:
                if settings.alerts_root is None:
                    raise ValueError("ALERTS_ROOT_REQUIRED")
                alerts = AlertStore(settings.alerts_root)
                result = {"processing": store.process(alerts), "delivery": alerts.deliver()}
        print(json.dumps(result, sort_keys=True))
        succeeded = True
        return 0
    except (OSError, ValueError, sqlite3.Error, KeyError, StopIteration):
        print('{"status":"FAILED","reason":"CHECK_PRIVATE_CONFIGURATION_AND_INTEGRITY"}')
        return 2
    finally:
        completed("operations", args.command, started, 200 if succeeded else 500)


if __name__ == "__main__":
    raise SystemExit(main())
