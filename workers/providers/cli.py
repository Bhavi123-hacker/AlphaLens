"""Local provider diagnostics and disabled selection; no acquire/enable/trade command."""

import argparse
import json
import sqlite3
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from alphalens_data.providers.multi_adapters import DisabledAdapter
from alphalens_data.providers.multi_contracts import Instrument, ProviderName
from alphalens_data.providers.test_bundle import parse_bundle

from .readiness import PROFILES, comparison
from .store import ProviderStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P28 offline preparation; acquisition and scheduling disabled"
    )
    parser.add_argument(
        "command",
        choices=(
            "init",
            "status",
            "select",
            "comparison",
            "capabilities",
            "plan",
            "verify-fixture",
            "import-analytics",
            "catch-up-plan",
        ),
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument("--provider", choices=[p["provider"] for p in PROFILES])
    parser.add_argument("--instruments", type=Path)
    parser.add_argument("--from-date", type=date.fromisoformat)
    parser.add_argument("--to-date", type=date.fromisoformat)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--calendar", type=Path)
    args = parser.parse_args(argv)
    try:
        result: Any
        provider = cast(ProviderName, args.provider or "upstox")
        if args.command == "import-analytics":
            from .credentials import import_analytics

            if not sys.stdin.isatty():
                raise ValueError("LOCAL_INTERACTIVE_CONSOLE_REQUIRED")
            result = import_analytics()
        elif args.command == "comparison":
            # Archive session intentionally absent: CLI makes no unverified local-storage claim.
            result = comparison()
        elif args.command == "capabilities":
            result = DisabledAdapter(provider).get_provider_capabilities()
        elif args.command == "catch-up-plan":
            from alphalens_data.daily.contracts import Calendar

            from .session_plan import plan

            if not args.calendar or not args.from_date or not args.to_date:
                parser.error("--calendar, --from-date and --to-date are required")
            if args.calendar.stat().st_size > 500000:
                raise ValueError("CALENDAR_PLAN_LIMIT")
            calendar = Calendar.model_validate_json(args.calendar.read_bytes())
            result = plan(calendar, args.from_date, args.to_date, datetime.now(UTC), provider)
        elif args.command == "plan":
            if not args.instruments or not args.from_date or not args.to_date:
                parser.error("--instruments, --from-date and --to-date are required")
            if args.instruments.stat().st_size > 50000:
                raise ValueError("INSTRUMENT_PLAN_LIMIT")
            instruments = tuple(
                Instrument.model_validate(i) for i in json.loads(args.instruments.read_bytes())
            )
            result = (
                DisabledAdapter(provider)
                .plan_daily(instruments, args.from_date, args.to_date)
                .model_dump(mode="json")
            )
        elif args.command == "verify-fixture":
            if not args.fixture or not args.from_date:
                parser.error("--fixture and --from-date (expected session) are required")
            if args.fixture.stat().st_size > 5000000:
                raise ValueError("FIXTURE_SIZE_LIMIT")
            raw, rows, _, lineage = parse_bundle(
                args.fixture.read_bytes(), provider, args.from_date, datetime.now(UTC)
            )
            result = {
                "classification": "TEST_ONLY",
                "rows": len(rows),
                "native_bytes": len(raw),
                "lineage": lineage,
                "collection_enabled": False,
            }
        else:
            if not args.root:
                parser.error("--root is required")
            store = ProviderStore(args.root)
            if args.command == "init":
                store.initialize()
            elif args.command == "select":
                if not args.provider:
                    parser.error("--provider is required")
                store.select(provider, time.time())
            result = store.status(time.time())
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error):
        # No exception payload, credential, private path or provider message in console.
        print(
            json.dumps({"error": "PROVIDER_OPERATION_REJECTED", "collection_enabled": False}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
