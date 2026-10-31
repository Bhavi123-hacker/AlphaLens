"""Preview or explicitly import an operator-downloaded official NSE final file."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from workers.experimental_nse.acquire import encoded, initialize, write_new
from workers.nse_market import manual_eod
from workers.providers import universe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("preview")
    preview.add_argument("--source", type=Path, required=True)
    preview.add_argument("--provenance", type=Path, required=True)
    preview.add_argument("--master-root", type=Path, required=True)
    preview.add_argument("--calendar", type=Path, required=True)
    preview.add_argument("--output", type=Path, required=True)
    accept = sub.add_parser("import")
    accept.add_argument("--source", type=Path, required=True)
    accept.add_argument("--candidate", type=Path, required=True)
    accept.add_argument("--approval", type=Path, required=True)
    accept.add_argument("--approve-candidate", required=True)
    accept.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preview":
        manual_eod._safe_destination(args.output)
        result = manual_eod.review(
            args.source,
            json.loads(args.provenance.read_bytes()),
            universe.load(args.master_root),
            args.calendar,
            at=datetime.now(UTC),
        )
        initialize(args.output.parent)
        write_new(args.output, encoded(result))
        print(
            json.dumps(
                {
                    "state": "PREVIEW_ONLY_APPROVAL_REQUIRED",
                    "candidate_id": result["candidate_id"],
                    "accepted_rows": len(result["rows"]),
                    "exclusion_counts": result["exclusion_counts"],
                    "session": result["session"],
                    "model_compatible": False,
                }
            )
        )
    else:
        print(
            json.dumps(
                manual_eod.import_candidate(
                    args.root,
                    args.source,
                    json.loads(args.candidate.read_bytes()),
                    json.loads(args.approval.read_bytes()),
                    approved_candidate=args.approve_candidate,
                    at=datetime.now(UTC),
                )
            )
        )


if __name__ == "__main__":
    main()
