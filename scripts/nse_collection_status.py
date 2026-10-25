"""Read saved collection health; optional separate local alert publication only."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from workers.nse_market import engine, reliability


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--provider-root", type=Path)
    parser.add_argument("--observe-windows", action="store_true", help="Read-only local task query")
    parser.add_argument(
        "--publish-local-alerts",
        action="store_true",
        help="Publish derived monitoring to its fixed separate local store; never deliver outbound",
    )
    args = parser.parse_args()
    task = None
    at = datetime.now(UTC)
    if args.observe_windows:
        from alphalens_api.nse_monitoring import windows_observation

        saved = engine._pointed(args.root, "task-observation-latest.json")
        task = windows_observation(saved, at=at)
        at = datetime.now(UTC)
    result = reliability.report(
        args.root, at=at, provider_root=args.provider_root, task_observation=task
    )
    if args.publish_local_alerts:
        from workers.nse_market.collection_alerts import publish

        result["derived_alert_publication"] = publish(args.root, result, at=datetime.now(UTC))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
