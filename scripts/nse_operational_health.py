"""Build one saved-source health report; optional derived publication, no live calls."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from workers.nse_market import operational_health


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--v2-root", required=True, type=Path)
    parser.add_argument("--universe-root", required=True, type=Path)
    parser.add_argument("--qualification", type=Path)
    parser.add_argument("--observe-windows", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    qualification = json.loads(args.qualification.read_bytes()) if args.qualification else None
    task = None
    if args.observe_windows:
        from alphalens_api.nse_monitoring import windows_observation

        task = windows_observation({}, at=datetime.now(UTC))
    data = operational_health.build(
        args.root,
        args.v2_root,
        args.universe_root,
        at=datetime.now(UTC),
        qualification=qualification,
        task_observation=task,
    )
    if args.publish:
        operational_health.publish(args.root, data, qualification=qualification)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
