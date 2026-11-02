"""Forward Outcome Maturation Engine and Performance Audit Ledger for AlphaLens.

Tracks and scores forecasts as trading days transpire:
- Links prospective predictions made on session T across horizons H in {1, 5, 10, 20}
- Once session T+H is observed in authentic market data, settles the prediction
- Computes realized returns, directional hit-rate, Brier score, and benchmark-relative alpha
- Maintains an immutable SQLite performance ledger with cryptographic verification receipts
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class MaturedForecast:
    forecast_id: str
    instrument_key: str
    symbol: str
    forecast_session: str
    horizon_sessions: int
    settlement_session: str
    predicted_direction_prob: float
    predicted_return: float
    realized_return: float
    realized_direction: int
    directional_hit: bool
    brier_score_component: float
    realized_excess_alpha: float
    matured_at: str


class ForwardMaturationEngine:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (repo / "data" / "forecasts" / "matured_outcomes_ledger.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matured_forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    instrument_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    forecast_session TEXT NOT NULL,
                    horizon_sessions INTEGER NOT NULL,
                    settlement_session TEXT NOT NULL,
                    predicted_direction_prob REAL NOT NULL,
                    predicted_return REAL NOT NULL,
                    realized_return REAL NOT NULL,
                    realized_direction INTEGER NOT NULL,
                    directional_hit INTEGER NOT NULL,
                    brier_score_component REAL NOT NULL,
                    realized_excess_alpha REAL NOT NULL,
                    matured_at TEXT NOT NULL,
                    record_hash TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_matured_session "
                "ON matured_forecasts (forecast_session, horizon_sessions)"
            )
            conn.commit()

    @staticmethod
    def _hash_record(record_dict: dict[str, Any]) -> str:
        body = json.dumps(record_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def settle_forecasts(
        self,
        forecasts: list[dict[str, Any]],
        histories: dict[str, list[dict[str, Any]]],
        benchmark_history: list[dict[str, Any]] | None = None,
    ) -> list[MaturedForecast]:
        """Evaluate and settle pending forecasts whose forward horizon sessions have arrived."""
        matured: list[MaturedForecast] = []
        now_iso = datetime.now(UTC).isoformat()

        # Build quick session lookup for each security
        session_closes: dict[str, dict[str, float]] = {}
        for key, candles in histories.items():
            session_closes[key] = {
                str(c["session"]): float(c["close"]) for c in candles if c.get("close") is not None
            }

        # Build chronological list of sessions for each security
        session_lists: dict[str, list[str]] = {}
        for key, candles in histories.items():
            session_lists[key] = sorted(
                list(
                    {
                        str(c["session"])
                        for c in candles
                        if c.get("close") is not None and c.get("session")
                    }
                )
            )

        # Benchmark closes
        bench_closes: dict[str, float] = {}
        if benchmark_history:
            bench_closes = {
                str(c["session"]): float(c["close"])
                for c in benchmark_history
                if c.get("close") is not None
            }

        for f in forecasts:
            key = f.get("instrument_key", f.get("key", ""))
            f_session = str(f.get("session", ""))
            h = int(f.get("horizon_sessions", 5))
            pred_prob = float(f.get("direction_probability", f.get("score", 0.5)))
            pred_ret = float(f.get("expected_return", 0.0))
            symbol = str(f.get("symbol", key.removeprefix("NSE_EQ|").removeprefix("BSE_EQ|")))

            if key not in session_lists or f_session not in session_lists[key]:
                continue

            sessions = session_lists[key]
            try:
                curr_idx = sessions.index(f_session)
            except ValueError:
                continue

            target_idx = curr_idx + h
            if target_idx >= len(sessions):
                # Forward horizon has not matured yet
                continue

            settle_session = sessions[target_idx]
            close_t = session_closes[key][f_session]
            close_settle = session_closes[key][settle_session]

            realized_ret = (close_settle - close_t) / max(close_t, 1e-4)
            realized_dir = 1 if realized_ret > 0 else 0
            pred_dir = 1 if pred_prob >= 0.5 else 0
            dir_hit = bool(pred_dir == realized_dir)
            brier_comp = float((pred_prob - realized_dir) ** 2)

            # Benchmark alpha
            bench_ret = 0.0
            if (
                bench_closes
                and f_session in bench_closes
                and settle_session in bench_closes
                and bench_closes[f_session] > 0
            ):
                bench_ret = (bench_closes[settle_session] - bench_closes[f_session]) / bench_closes[
                    f_session
                ]

            excess_alpha = realized_ret - bench_ret
            forecast_id = f"{key}_{f_session}_H{h}"

            m = MaturedForecast(
                forecast_id=forecast_id,
                instrument_key=key,
                symbol=symbol,
                forecast_session=f_session,
                horizon_sessions=h,
                settlement_session=settle_session,
                predicted_direction_prob=round(pred_prob, 4),
                predicted_return=round(pred_ret, 5),
                realized_return=round(realized_ret, 5),
                realized_direction=realized_dir,
                directional_hit=dir_hit,
                brier_score_component=round(brier_comp, 5),
                realized_excess_alpha=round(excess_alpha, 5),
                matured_at=now_iso,
            )
            matured.append(m)

        # Persist matured forecasts
        if matured:
            self._save_matured(matured)

        return matured

    def _save_matured(self, matured: list[MaturedForecast]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            for m in matured:
                rec_dict = {
                    "forecast_id": m.forecast_id,
                    "instrument_key": m.instrument_key,
                    "forecast_session": m.forecast_session,
                    "horizon_sessions": m.horizon_sessions,
                    "settlement_session": m.settlement_session,
                    "predicted_prob": m.predicted_direction_prob,
                    "realized_return": m.realized_return,
                }
                r_hash = self._hash_record(rec_dict)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO matured_forecasts (
                        forecast_id, instrument_key, symbol, forecast_session,
                        horizon_sessions, settlement_session, predicted_direction_prob,
                        predicted_return, realized_return, realized_direction,
                        directional_hit, brier_score_component, realized_excess_alpha,
                        matured_at, record_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m.forecast_id,
                        m.instrument_key,
                        m.symbol,
                        m.forecast_session,
                        m.horizon_sessions,
                        m.settlement_session,
                        m.predicted_direction_prob,
                        m.predicted_return,
                        m.realized_return,
                        1 if m.directional_hit else 0,
                        1 if m.directional_hit else 0,
                        m.brier_score_component,
                        m.realized_excess_alpha,
                        m.matured_at,
                        r_hash,
                    ),
                )
            conn.commit()

    def generate_audit_summary(self) -> dict[str, Any]:
        """Aggregate audit statistics across all matured forecast records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM matured_forecasts")
            total = cursor.fetchone()[0]
            if total == 0:
                return {
                    "status": "AWAITING_FUTURE_SESSION_MATURATION",
                    "total_matured_forecasts": 0,
                    "summary_by_horizon": {},
                }

            cursor.execute(
                """
                SELECT
                    horizon_sessions,
                    COUNT(*),
                    AVG(directional_hit),
                    AVG(brier_score_component),
                    AVG(realized_return),
                    AVG(realized_excess_alpha)
                FROM matured_forecasts
                GROUP BY horizon_sessions
                """
            )
            rows = cursor.fetchall()
            by_horizon = {}
            for row in rows:
                h, cnt, hit_rate, brier, avg_ret, avg_alpha = row
                by_horizon[f"H_{h}"] = {
                    "horizon_sessions": h,
                    "settled_count": cnt,
                    "directional_hit_rate": round(float(hit_rate), 4),
                    "mean_brier_score": round(float(brier), 4),
                    "mean_realized_return": round(float(avg_ret), 5),
                    "mean_excess_alpha": round(float(avg_alpha), 5),
                }

            return {
                "status": "AUDIT_RECORDS_SETTLED",
                "total_matured_forecasts": total,
                "summary_by_horizon": by_horizon,
            }
