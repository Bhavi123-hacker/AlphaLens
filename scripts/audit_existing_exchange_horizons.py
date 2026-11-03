"""Audit immutable settled outcomes against the registered exchange session horizon.

Read-only. Does not change stored outcomes, timestamps, forecasts or hashes.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from workers.nse_market.forward_maturation_engine import (  # noqa: E402
    registered_exchange_horizon_dates,
)


def audit_existing_horizons(db_path: Path) -> dict[str, Any]:
    if not db_path.is_file():
        return {"status": "LOCAL_MATURED_LEDGER_NOT_AVAILABLE", "path": str(db_path)}

    by_session: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "aligned": 0, "misaligned": 0, "unverifiable": 0}
    )
    mismatches: list[dict[str, str | int]] = []
    total = 0
    aligned = 0
    misaligned = 0
    unverifiable = 0
    try:
        with sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
            db.execute("PRAGMA query_only = ON")
            check = db.execute("PRAGMA integrity_check").fetchone()
            if check is None or check[0] != "ok":
                return {"status": "LEDGER_SQLITE_INTEGRITY_FAILED"}
            rows = db.execute(
                "SELECT forecast_id, forecast_session, horizon_sessions, "
                "entry_session, settlement_session FROM matured_forecasts"
            )
            for f_id, f_session, horizon, recorded_entry, recorded_exit in rows:
                total += 1
                group = by_session[str(f_session)]
                group["total"] += 1
                expected = registered_exchange_horizon_dates(str(f_session), int(horizon))
                if expected is None:
                    unverifiable += 1
                    group["unverifiable"] += 1
                elif expected[0] != recorded_entry or expected[-1] != recorded_exit:
                    misaligned += 1
                    group["misaligned"] += 1
                    if len(mismatches) < 12:
                        mismatches.append(
                            {
                                "forecast_id": str(f_id),
                                "observation_session": str(f_session),
                                "horizon": int(horizon),
                                "recorded_entry": str(recorded_entry),
                                "expected_entry": expected[0],
                                "recorded_exit": str(recorded_exit),
                                "expected_exit": expected[-1],
                            }
                        )
                else:
                    aligned += 1
                    group["aligned"] += 1
    except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
        return {"status": "READ_ONLY_AUDIT_FAILED", "error": str(exc)}
    return {
        "status": (
            "QUARANTINE_REVIEW_REQUIRED"
            if misaligned or unverifiable
            else "EXCHANGE_SESSION_WINDOWS_ALIGNED"
        ),
        "source": "READ_ONLY_LOCAL_SQLITE",
        "total": total,
        "aligned": aligned,
        "misaligned": misaligned,
        "unverifiable": unverifiable,
        "by_observation_session": dict(by_session),
        "mismatch_sample": mismatches,
        "database_mutated": False,
        "remediation": (
            "Preserve original rows; do not use misaligned outcomes for model "
            "acceptance. Reconstruct corrected outcomes only in a separate "
            "versioned research ledger with original evidence attached."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only audit of matured H horizons against NSE sessions"
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "data"
            / "forecasts"
            / "matured_outcomes_ledger.db"
        ),
    )
    args = parser.parse_args()
    print(json.dumps(audit_existing_horizons(args.ledger), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
