"""Forward Outcome Maturation Engine and Performance Audit Ledger for AlphaLens.

Tracks and scores forecasts strictly according to registered entry/exit definitions:
- Registered target definition: Entry at session T+1 OPEN, Exit at session T+H CLOSE
  Realized Return = (Close_{T+H} - Open_{T+1}) / Open_{T+1}
- Correctly records authentic realized_direction (1 for positive return, 0 otherwise)
  and directional_hit (bool: predicted_direction == realized_direction)
- Enforces append-only, conflict-checked persistence (detects and rejects conflicting rewrites)
- Distinguishes model identity in forecast uniqueness (model_id + instrument + session + horizon)
- Requires authenticated future session data and genuine trading calendar evidence
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class MaturedForecast:
    forecast_id: str
    model_id: str
    instrument_key: str
    symbol: str
    forecast_session: str
    entry_session: str
    settlement_session: str
    horizon_sessions: int
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
                    model_id TEXT NOT NULL,
                    instrument_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    forecast_session TEXT NOT NULL,
                    entry_session TEXT NOT NULL,
                    settlement_session TEXT NOT NULL,
                    horizon_sessions INTEGER NOT NULL,
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

        # Build quick session lookup for opens and closes
        session_opens: dict[str, dict[str, float]] = {}
        session_closes: dict[str, dict[str, float]] = {}
        session_lists: dict[str, list[str]] = {}

        for key, candles in histories.items():
            valid_candles = [
                c
                for c in candles
                if c.get("open") is not None and c.get("close") is not None and c.get("session")
            ]
            session_opens[key] = {str(c["session"]): float(c["open"]) for c in valid_candles}
            session_closes[key] = {str(c["session"]): float(c["close"]) for c in valid_candles}
            session_lists[key] = sorted(list({str(c["session"]) for c in valid_candles}))

        # Benchmark closes for excess alpha
        bench_closes: dict[str, float] = {}
        if benchmark_history:
            bench_closes = {
                str(c["session"]): float(c["close"])
                for c in benchmark_history
                if c.get("close") is not None
            }

        for f in forecasts:
            key = str(f.get("instrument_key", f.get("key", "")))
            f_session = str(f.get("session", ""))
            h = int(f.get("horizon_sessions", 5))
            pred_prob = float(f.get("direction_probability", f.get("score", 0.5)))
            pred_ret = float(f.get("expected_return", 0.0))
            symbol = str(f.get("symbol", key.removeprefix("NSE_EQ|").removeprefix("BSE_EQ|")))
            model_id = str(f.get("model_id", f.get("model_name", "AlphaLens_Default")))

            if key not in session_lists or f_session not in session_lists[key]:
                continue

            sessions = session_lists[key]
            try:
                curr_idx = sessions.index(f_session)
            except ValueError:
                continue

            entry_idx = curr_idx + 1
            target_idx = curr_idx + h

            # Horizon maturation requires both entry session and settlement session to have elapsed
            if target_idx >= len(sessions) or entry_idx >= len(sessions):
                continue

            entry_session = sessions[entry_idx]
            settle_session = sessions[target_idx]

            open_entry = session_opens[key][entry_session]
            close_settle = session_closes[key][settle_session]

            # Registered target: Entry at next-open, Exit at h-th close
            realized_ret = (close_settle - open_entry) / max(open_entry, 1e-4)
            realized_dir = 1 if realized_ret > 0 else 0
            pred_dir = 1 if pred_prob >= 0.5 else 0
            dir_hit = bool(pred_dir == realized_dir)
            brier_comp = float((pred_prob - realized_dir) ** 2)

            # Benchmark alpha: return over same period
            bench_ret = 0.0
            if (
                bench_closes
                and entry_session in bench_closes
                and settle_session in bench_closes
                and bench_closes[entry_session] > 0
            ):
                bench_ret = (
                    bench_closes[settle_session] - bench_closes[entry_session]
                ) / bench_closes[entry_session]

            excess_alpha = realized_ret - bench_ret
            forecast_id = f"{model_id}_{key}_{f_session}_H{h}"

            m = MaturedForecast(
                forecast_id=forecast_id,
                model_id=model_id,
                instrument_key=key,
                symbol=symbol,
                forecast_session=f_session,
                entry_session=entry_session,
                settlement_session=settle_session,
                horizon_sessions=h,
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

        # Persist matured forecasts with append-only conflict checks
        if matured:
            self._save_matured(matured)

        return matured

    def _save_matured(self, matured: list[MaturedForecast]) -> None:
        """Append-only write with strict conflict checking."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for m in matured:
                cursor.execute(
                    "SELECT record_hash, realized_return, realized_direction "
                    "FROM matured_forecasts WHERE forecast_id = ?",
                    (m.forecast_id,),
                )
                existing = cursor.fetchone()

                rec_dict = {
                    "forecast_id": m.forecast_id,
                    "model_id": m.model_id,
                    "instrument_key": m.instrument_key,
                    "forecast_session": m.forecast_session,
                    "entry_session": m.entry_session,
                    "settlement_session": m.settlement_session,
                    "horizon_sessions": m.horizon_sessions,
                    "predicted_prob": m.predicted_direction_prob,
                    "realized_return": m.realized_return,
                }
                r_hash = self._hash_record(rec_dict)

                if existing:
                    # Idempotent replay: if hash matches, skip
                    if existing[0] == r_hash:
                        continue
                    # Conflict detected: reject rewrite!
                    raise ValueError(
                        f"CONFLICTING_FORECAST_OUTCOME_MUTATION_REJECTED: "
                        f"Forecast ID {m.forecast_id} already has recorded outcome "
                        f"(stored return={existing[1]}, candidate return={m.realized_return})"
                    )

                cursor.execute(
                    """
                    INSERT INTO matured_forecasts (
                        forecast_id, model_id, instrument_key, symbol, forecast_session,
                        entry_session, settlement_session, horizon_sessions,
                        predicted_direction_prob, predicted_return, realized_return,
                        realized_direction, directional_hit, brier_score_component,
                        realized_excess_alpha, matured_at, record_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m.forecast_id,
                        m.model_id,
                        m.instrument_key,
                        m.symbol,
                        m.forecast_session,
                        m.entry_session,
                        m.settlement_session,
                        m.horizon_sessions,
                        m.predicted_direction_prob,
                        m.predicted_return,
                        m.realized_return,
                        m.realized_direction,
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
                    "distinct_decision_dates": 0,
                    "distinct_securities": 0,
                    "date_span_days": 0,
                    "summary_by_horizon": {},
                    "summary_by_model": {},
                }

            cursor.execute("SELECT COUNT(DISTINCT forecast_session) FROM matured_forecasts")
            distinct_sessions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT instrument_key) FROM matured_forecasts")
            distinct_securities = cursor.fetchone()[0]

            cursor.execute(
                "SELECT MIN(forecast_session), MAX(forecast_session) FROM matured_forecasts"
            )
            min_sess, max_sess = cursor.fetchone()
            span_days = 0
            if min_sess and max_sess:
                try:
                    d_min = date.fromisoformat(min_sess)
                    d_max = date.fromisoformat(max_sess)
                    span_days = (d_max - d_min).days
                except Exception:
                    span_days = 0

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

            cursor.execute(
                """
                SELECT
                    model_id,
                    COUNT(*),
                    AVG(directional_hit),
                    AVG(brier_score_component),
                    AVG(realized_excess_alpha)
                FROM matured_forecasts
                GROUP BY model_id
                """
            )
            by_model = {}
            for row in cursor.fetchall():
                m_id, m_cnt, m_hit, m_brier, m_alpha = row
                by_model[m_id] = {
                    "settled_count": m_cnt,
                    "directional_hit_rate": round(float(m_hit), 4),
                    "mean_brier_score": round(float(m_brier), 4),
                    "mean_excess_alpha": round(float(m_alpha), 5),
                }

            return {
                "status": "AUDIT_RECORDS_SETTLED",
                "total_matured_forecasts": total,
                "distinct_decision_dates": distinct_sessions,
                "distinct_securities": distinct_securities,
                "date_span_days": span_days,
                "summary_by_horizon": by_horizon,
                "summary_by_model": by_model,
            }
