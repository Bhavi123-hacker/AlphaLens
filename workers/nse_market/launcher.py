"""Scheduled-only in-process launcher: durable facts before heavy worker imports.

No child/group handling change. A hard-killed process may leave only its start
record; a missing exit record is incomplete evidence, never proof of an initiator.
"""

import argparse
import os
import runpy
import sys
import uuid
from pathlib import Path

from .diagnostics import configured_root, emit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--session")
    args = parser.parse_args()
    root = configured_root(args.config)
    correlation = uuid.uuid4().hex
    original_correlation = os.environ.get("ALPHALENS_NSE_LAUNCH_ID")
    os.environ["ALPHALENS_NSE_LAUNCH_ID"] = correlation
    emit(root, correlation, "LAUNCHER_STARTED")
    original = sys.argv
    sys.argv = ["workers.nse_market", "run", "--config", str(args.config), "--scheduled"]
    if args.session:
        sys.argv.extend(["--session", args.session])
    try:
        runpy.run_module("workers.nse_market", run_name="__main__", alter_sys=True)
    except SystemExit as exc:
        emit(root, correlation, "LAUNCHER_EXIT", exit_code=exc.code if type(exc.code) is int else 1)
        raise
    except KeyboardInterrupt:
        emit(root, correlation, "LAUNCHER_INTERRUPTED", code="CONTROL_INTERRUPT_OBSERVED")
        raise
    except Exception:
        emit(root, correlation, "LAUNCHER_EXCEPTION", code="UNEXPECTED_WORKER_EXCEPTION")
        raise
    else:
        emit(root, correlation, "LAUNCHER_EXIT", exit_code=0)
    finally:
        sys.argv = original
        if original_correlation is None:
            os.environ.pop("ALPHALENS_NSE_LAUNCH_ID", None)
        else:
            os.environ["ALPHALENS_NSE_LAUNCH_ID"] = original_correlation


if __name__ == "__main__":
    main()
