"""Inspect saved prospective maturity, or explicitly retry offline append-only reconciliation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workers.nse_market import outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--append-qualified",
        action="store_true",
        help="Append qualified references under existing daily lock; no acquisition",
    )
    args = parser.parse_args()
    print(
        json.dumps(outcomes.run(args.root, append=args.append_qualified), indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    main()
