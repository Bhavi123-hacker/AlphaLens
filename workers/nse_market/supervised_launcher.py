"""Candidate-only Windows scheduled launcher; no task registration or activation."""

import argparse
import sys
import uuid
from pathlib import Path

from .diagnostics import configured_root, emit
from .windows_supervision import _Windows, supervise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    root = configured_root(args.config)
    correlation = uuid.uuid4().hex

    def record(stage: str, code: int | None) -> None:
        emit(root, correlation, "STAGE", stage=stage, exit_code=code)

    windows = _Windows()
    ancestor = windows.cmd_parent()
    try:
        try:
            return supervise(
                [sys.executable, "-m", "workers.nse_market.launcher", "--config", str(args.config)],
                parent_handle=ancestor,
                record=record,
            )
        except Exception:
            record("SUPERVISOR_FAILED", 1)
            return 1
    finally:
        windows.close(ancestor)


if __name__ == "__main__":
    raise SystemExit(main())
