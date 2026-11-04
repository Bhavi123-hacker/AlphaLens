"""Reconstruct calendar-aligned research outcomes in a separate versioned research ledger.

Preserves the original immutable matured_outcomes_ledger.db byte-for-byte.
Applies the registered exchange trading calendar to evaluate true T+1 entry and T+H exit.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from scripts.audit_existing_exchange_horizons import audit_existing_horizons  # noqa: E402
from workers.nse_market.forward_maturation_engine import (  # noqa: E402
    registered_exchange_horizon_dates,
)


def reconstruct_research_ledger(
    legacy_ledger_path: Path | None = None,
    output_ledger_path: Path | None = None,
    market_view_path: Path | None = None,
) -> dict[str, Any]:
    legacy_path = legacy_ledger_path or (repo / "data" / "forecasts" / "matured_outcomes_ledger.db")
    research_path = output_ledger_path or (
        repo / "data" / "forecasts" / "matured_outcomes_calendar_aligned_research.db"
    )

    if not legacy_path.exists():
        raise FileNotFoundError(f"Legacy ledger not found: {legacy_path}")

    # 1. Read-only audit of legacy ledger
    audit_report = audit_existing_horizons(legacy_path)

    # 2. Load market histories for candle availability check
    mv_path = market_view_path or (
        repo.parent / ".local-data" / "nse-market-expansion" / "market-view-latest.json"
    )
    if not mv_path.exists():
        mv_path = repo / ".local-data" / "nse-market-expansion" / "market-view-latest.json"

    histories: dict[str, set[str]] = {}
    if mv_path.exists():
        try:
            meta = json.loads(mv_path.read_text(encoding="utf-8"))
            doc = json.loads((mv_path.parent / meta["path"]).read_text(encoding="utf-8"))
            raw_histories = doc.get("histories", {})
            histories = {
                k: {row["session"] for row in v if "session" in row}
                for k, v in raw_histories.items()
            }
        except Exception as exc:
            print(f"Warning: could not read market-view: {exc}")

    # 3. Read legacy rows from SQLite (PRAGMA query_only = ON)
    with sqlite3.connect(legacy_path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                forecast_id, model_id, instrument_key, forecast_session,
                horizon_sessions, entry_session, settlement_session,
                realized_return, benchmark_return, realized_excess_alpha,
                directional_hit, brier_score_component, record_hash
            FROM matured_forecasts
            """
        )
        legacy_rows = cursor.fetchall()

    # 4. Initialize separate versioned research database
    research_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(research_path) as out_conn:
        out_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reconstructed_research_outcomes (
                forecast_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                instrument_key TEXT NOT NULL,
                observation_session TEXT NOT NULL,
                horizon_sessions INTEGER NOT NULL,
                legacy_entry_session TEXT NOT NULL,
                legacy_settlement_session TEXT NOT NULL,
                expected_entry_session TEXT,
                expected_settlement_session TEXT,
                reconstruction_status TEXT NOT NULL,
                status_reason TEXT NOT NULL,
                missing_vendor_sessions TEXT,
                reconstructed_at TEXT NOT NULL
            )
            """
        )

        mapping: list[dict[str, Any]] = []
        counts: dict[str, int] = {
            "RECONSTRUCTED_CALENDAR_ALIGNED_RESEARCH_OUTCOME": 0,
            "RECONSTRUCTION_PENDING_AUTHENTIC_DATA": 0,
            "PROSPECTIVE_ELIGIBILITY_UNVERIFIABLE": 0,
            "INVALID_BENCHMARK_WINDOW": 0,
        }

        cal_cache: dict[str, bool | None] = {}
        horizon_cache: dict[tuple[str, int], tuple[str, ...] | None] = {}
        for row in legacy_rows:
            (
                f_id,
                m_id,
                key,
                obs_session,
                horizon,
                leg_entry,
                leg_settle,
                ret,
                b_ret,
                alpha,
                hit,
                brier,
                rec_hash,
            ) = row

            cache_key = (str(obs_session), int(horizon))
            if cache_key not in horizon_cache:
                horizon_cache[cache_key] = registered_exchange_horizon_dates(
                    str(obs_session), int(horizon), calendar_cache=cal_cache, calendar_root=repo
                )
            expected_sessions = horizon_cache[cache_key]
            if expected_sessions is None:
                status = "PROSPECTIVE_ELIGIBILITY_UNVERIFIABLE"
                reason = "Exchange calendar evidence unavailable for registered horizon."
                exp_entry = None
                exp_settle = None
                missing_str = ""
            else:
                exp_entry = expected_sessions[0]
                exp_settle = expected_sessions[-1]
                available_sessions = histories.get(str(key), set())
                missing_sessions = [
                    ses for ses in expected_sessions if ses not in available_sessions
                ]

                if missing_sessions:
                    status = "RECONSTRUCTION_PENDING_AUTHENTIC_DATA"
                    reason = f"Vendor history lacks required exchange sessions: {missing_sessions}"
                    missing_str = json.dumps(missing_sessions)
                else:
                    status = "RECONSTRUCTED_CALENDAR_ALIGNED_RESEARCH_OUTCOME"
                    reason = "All registered exchange sessions verified with authentic candle data."
                    missing_str = "[]"

            counts[status] += 1

            now_iso = datetime.now(UTC).isoformat()
            out_conn.execute(
                """
                INSERT OR REPLACE INTO reconstructed_research_outcomes (
                    forecast_id, model_id, instrument_key, observation_session,
                    horizon_sessions, legacy_entry_session, legacy_settlement_session,
                    expected_entry_session, expected_settlement_session,
                    reconstruction_status, status_reason, missing_vendor_sessions,
                    reconstructed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(f_id),
                    str(m_id),
                    str(key),
                    str(obs_session),
                    int(horizon),
                    str(leg_entry),
                    str(leg_settle),
                    exp_entry,
                    exp_settle,
                    status,
                    reason,
                    missing_str,
                    now_iso,
                ),
            )

            if len(mapping) < 15:
                mapping.append(
                    {
                        "forecast_id": str(f_id),
                        "observation_session": str(obs_session),
                        "horizon": int(horizon),
                        "legacy_window": f"{leg_entry} -> {leg_settle}",
                        "expected_exchange_window": (
                            f"{exp_entry} -> {exp_settle}" if exp_entry else "N/A"
                        ),
                        "status": status,
                        "reason": reason,
                    }
                )

        out_conn.commit()

    report = {
        "schema": "alphalens.reconstructed_research_audit.v1",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "legacy_ledger": str(legacy_path),
        "research_ledger": str(research_path),
        "total_legacy_outcomes": len(legacy_rows),
        "quarantined_outcomes": audit_report.get("misaligned", 0),
        "reconstruction_counts": counts,
        "sample_mappings": mapping,
        "independent_acceptance_contribution": {
            "qualified_observations_contributed": 0,
            "qualified_decision_dates_contributed": 0,
            "policy": "ZERO_QUARANTINED_EVIDENCE_FOR_ACCEPTANCE",
        },
        "recomputed_qualified_metrics": {
            "directional_accuracy": None,
            "mean_brier_score": None,
            "mean_rank_ic": None,
            "mean_net_alpha_bps": None,
            "note": (
                "Recomputed metrics remain None pending authentic exchange session "
                "candle delivery for registered exit sessions 2026-10-26 and 2026-10-27."
            ),
        },
    }

    # Save reconciliation report
    report_path = repo / "docs" / "ml" / "reconstructed_calendar_aligned_research_audit.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruct calendar-aligned research outcomes into versioned database"
    )
    parser.add_argument("--legacy", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = reconstruct_research_ledger(
        legacy_ledger_path=args.legacy,
        output_ledger_path=args.output,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
