"""Developer CLI for offline forward paper simulation; never real orders."""

import argparse
import json
import os
from datetime import date, datetime
from fractions import Fraction
from pathlib import Path

import psycopg

from alphalens_backtesting.contracts import ExecutionCalendar
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.quality.files import local_output

from .cli import canonical
from .contracts import Portfolio
from .paper import create, order_states, process_session
from .paper_contracts import ManualPaperOrder, PaperPolicy, paper_disclaimer
from .paper_performance import chart_series, performance
from .paper_storage import PostgresPaper, load, save
from .valuation import DecisionHistory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["create", "process-session", "orders", "positions", "performance", "history"],
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Create definition JSON or checksum paper checkpoint",
    )
    parser.add_argument("--canonical", type=Path)
    parser.add_argument("--calendar", type=Path)
    parser.add_argument("--session", type=date.fromisoformat)
    parser.add_argument("--cutoff", type=datetime.fromisoformat)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--manual-orders", type=Path)
    parser.add_argument("--decision-history", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Persist atomically via ALPHALENS_DATABASE_URL, never a CLI credential",
    )
    args = parser.parse_args()
    if args.command == "create":
        definition = json.loads(args.input.read_bytes())
        if not isinstance(definition["starting_cash"], (str, int)):
            parser.error("Starting cash requires exact decimal/fraction text or integer")
        state = create(
            Portfolio.model_validate(definition["portfolio"]), Fraction(definition["starting_cash"])
        )
    else:
        state = load(args.input)
        if args.command == "process-session":
            if not args.canonical or not args.calendar or not args.session or not args.cutoff:
                parser.error("process-session requires canonical/calendar/session/cutoff")
            policy = (
                PaperPolicy.model_validate_json(args.policy.read_bytes())
                if args.policy
                else PaperPolicy()
            )
            manual = (
                tuple(
                    ManualPaperOrder.model_validate(r)
                    for r in json.loads(args.manual_orders.read_bytes())
                )
                if args.manual_orders
                else ()
            )
            history = (
                DecisionHistory.model_validate_json(args.decision_history.read_bytes())
                if args.decision_history
                else None
            )
            state = process_session(
                state,
                canonical(args.canonical),
                ExecutionCalendar.model_validate_json(args.calendar.read_bytes()),
                args.session,
                args.cutoff,
                policy,
                manual,
                history,
            )
    print(paper_disclaimer(state.classification))
    if args.command in {"create", "process-session"}:
        if not args.output:
            parser.error("create/process-session requires --output")
        if args.postgres:
            url = os.environ.get("ALPHALENS_DATABASE_URL")
            if not url:
                parser.error("Database configuration unavailable")
            try:
                with psycopg.connect(url, connect_timeout=3) as connection:
                    PostgresPaper(connection).save(state)
            except psycopg.Error:
                raise ValueError("POSTGRES_PAPER_STORAGE_FAILED_DETAILS_REDACTED") from None
        path = save(local_output(args.output), state)
        print(
            stable_json(
                {
                    "state_id": state.state_id,
                    "checkpoint": str(path),
                    "report": state.reports[-1].model_dump(mode="json") if state.reports else None,
                }
            ).decode()
        )
    elif args.command == "orders":
        print(
            stable_json(
                {
                    "orders": [o.model_dump(mode="json") for o in state.orders],
                    "states": order_states(state),
                }
            ).decode()
        )
    elif args.command == "positions":
        print(
            stable_json(
                state.reports[-1].valuation.model_dump(mode="json")
                if state.reports
                else {"positions": []}
            ).decode()
        )
    elif args.command == "performance":
        print(stable_json(performance(state).model_dump(mode="json")).decode())
    else:
        print(stable_json(chart_series(state)).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
