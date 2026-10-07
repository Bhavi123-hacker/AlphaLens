"""Developer offline CLI; explicit JSON inputs and immutable ledger outputs."""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.contracts import Contract
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.quality.files import local_output

from .accounting import append, reconstruct
from .contracts import Ledger, Portfolio, Transaction
from .history import build_history
from .storage import load, save
from .valuation import value


def canonical(path: Path) -> CanonicalReader:
    data = json.loads(path.read_bytes())
    return CanonicalReader(
        verify_local_batch(CanonicalBatch.model_validate(data["batch"]), data["artifact_roots"])
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["create", "add-transaction", "import-position", "positions", "value", "history"],
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Portfolio/transaction JSON or immutable ledger path",
    )
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--canonical", type=Path)
    parser.add_argument("--session", type=date.fromisoformat)
    parser.add_argument("--cutoff", type=datetime.fromisoformat)
    parser.add_argument(
        "--observations", type=Path, help="Explicit session/cutoff pairs; no invented calendar"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result: Contract
    if args.command == "create":
        ledger = Ledger(portfolio=Portfolio.model_validate_json(args.input.read_bytes()))
        if not args.output:
            parser.error("create requires --output")
        print(save(local_output(args.output), ledger))
    elif args.command in {"add-transaction", "import-position"}:
        if not args.ledger or not args.output:
            parser.error("ledger mutation requires --ledger and --output")
        transaction = Transaction.model_validate_json(args.input.read_bytes())
        if args.command == "import-position" and transaction.kind != "OPENING_POSITION":
            parser.error("import-position requires declared OPENING_POSITION")
        print(save(local_output(args.output), append(load(args.ledger), transaction)))
    else:
        ledger = load(args.input)
        if args.command == "history":
            if not args.canonical or not args.observations:
                parser.error("history requires --canonical and --observations")
            observations = tuple(
                (date.fromisoformat(s), datetime.fromisoformat(c))
                for s, c in json.loads(args.observations.read_bytes())
            )
            result = build_history(ledger, canonical(args.canonical), observations)
            for disclaimer in sorted({v.disclaimer for v in result.valuations}):
                print(disclaimer)
        else:
            if not args.session or not args.cutoff:
                parser.error("positions/value requires --session and --cutoff")
            if args.command == "value":
                if not args.canonical:
                    parser.error("value requires --canonical")
                result = value(ledger, canonical(args.canonical), args.session, args.cutoff)
                print(result.disclaimer)
            else:
                result = reconstruct(ledger, args.session, args.cutoff)
                print("Execution provenance is user-recorded or simulated; never broker verified")
        print(stable_json(result.model_dump(mode="json")).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
