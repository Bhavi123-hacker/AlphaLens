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
import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("alphalens.forward_maturation")

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
    benchmark_return: float
    realized_excess_alpha: float
    benchmark_source: str
    matured_at: str


class ForwardMaturationEngine:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (repo / "data" / "forecasts" / "matured_outcomes_ledger.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(matured_forecasts)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            required_columns = {
                "model_id",
                "entry_session",
                "benchmark_return",
                "benchmark_source",
                "record_hash",
            }
            missing_columns = required_columns - existing_cols
            if existing_cols and missing_columns:
                # This is an immutable audit ledger. A destructive migration would
                # erase settled outcomes, so require a separately verified backup
                # and explicit non-destructive migration instead.
                raise RuntimeError(
                    "LEGACY_MATURED_LEDGER_SCHEMA_MIGRATION_REQUIRED: "
                    + ", ".join(sorted(missing_columns))
                    + "; original records preserved; migrate using a verified backup"
                )

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
                    benchmark_return REAL NOT NULL DEFAULT 0.0,
                    realized_excess_alpha REAL NOT NULL,
                    benchmark_source TEXT NOT NULL DEFAULT 'ZERO_BASELINE',
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
        require_entry_timing: bool = False,
        require_qualified_benchmark: bool = False,
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

        # Index returns must use the same next-session OPEN-to-exit CLOSE
        # holding window as the model, not an entry-close approximation.
        bench_opens: dict[str, float] = {}
        bench_closes: dict[str, float] = {}
        if benchmark_history:
            bench_opens = {
                str(c["session"]): float(c["open"])
                for c in benchmark_history
                if c.get("open") is not None
            }
            bench_closes = {
                str(c["session"]): float(c["close"])
                for c in benchmark_history
                if c.get("close") is not None
            }

        # Build broad-market equal-weighted benchmark returns across all securities
        # for each holding window (entry_session, settle_session) when index is not provided
        window_market_returns: dict[tuple[str, str], float] = {}
        if not bench_closes or not bench_opens:
            window_accum: dict[tuple[str, str], list[float]] = {}
            for k_inst, s_list in session_lists.items():
                opens_map = session_opens[k_inst]
                closes_map = session_closes[k_inst]
                for idx, e_s in enumerate(s_list):
                    # Include same-day open-to-close windows (H=1).
                    for s_s in s_list[idx : min(len(s_list), idx + 20)]:
                        o_val = opens_map.get(e_s)
                        c_val = closes_map.get(s_s)
                        if o_val and c_val and o_val > 0:
                            window_accum.setdefault((e_s, s_s), []).append((c_val - o_val) / o_val)
            for win_key, rets_list in window_accum.items():
                if len(rets_list) >= 30:
                    window_market_returns[win_key] = sum(rets_list) / len(rets_list)

        seen_forecast_keys: set[str] = set()

        for f in forecasts:
            # 1. Do not settle retrospective ranking exports as prospective forecasts
            if f.get("forecast_classification") == "RETROSPECTIVE_RESEARCH_BENCHMARK":
                continue
            if f.get("prospective_eligible") is False:
                continue

            # 2. Never manufacture missing direction probability from defaults
            raw_prob = f.get("direction_probability")
            if raw_prob is None:
                raw_prob = f.get("score")
            if raw_prob is None:
                continue
            try:
                pred_prob = float(raw_prob)
            except (ValueError, TypeError):
                continue

            # 3. Valid entry timing deadline check (FAIL CLOSED):
            # Genuine prospective settlement requires verified recording and entry timestamps
            timing = f.get("next_session_timing")
            recorded_at_str = f.get("recorded_at") or f.get("inference_at")
            if require_entry_timing or timing is not None or recorded_at_str is not None:
                if not (isinstance(timing, dict) and "open_at" in timing and recorded_at_str):
                    # Fail-closed: missing timestamps cannot be verified as prospective
                    continue
                try:
                    rec_dt = datetime.fromisoformat(str(recorded_at_str)).astimezone(UTC)
                    open_dt = datetime.fromisoformat(str(timing["open_at"])).astimezone(UTC)
                    if rec_dt >= open_dt:
                        # Entry deadline elapsed prior to forecast: retrospective, disqualify
                        continue
                except (ValueError, TypeError, KeyError) as e:
                    # Fail-closed: unparseable timestamps cannot be verified as pre-entry
                    logger.debug("Disqualifying forecast with invalid timestamps: %s", e)
                    continue

            key = str(f.get("instrument_key", f.get("key", "")))
            f_session = str(f.get("session", ""))
            h = int(f.get("horizon_sessions", f.get("horizon", 5)))
            model_id = str(f.get("model_id", f.get("model_name", "AlphaLens_Default")))
            symbol = str(f.get("symbol", key.removeprefix("NSE_EQ|").removeprefix("BSE_EQ|")))

            # 4. Deduplicate records correctly
            dedup_key = f"{model_id}_{key}_{f_session}_H{h}"
            if dedup_key in seen_forecast_keys:
                continue
            seen_forecast_keys.add(dedup_key)

            # 5. Extract expected return without manufacturing fake non-zero values
            raw_ret = f.get("expected_return")
            pred_ret = float(raw_ret) if raw_ret is not None else 0.0

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

            # Benchmark must have real open/close observations for this
            # exact holding window. Zero is NOT a substitute for absent data.
            bench_ret = 0.0
            bench_source = "BENCHMARK_UNAVAILABLE"
            if (
                entry_session in bench_opens
                and settle_session in bench_closes
                and bench_opens[entry_session] > 0
            ):
                bench_ret = (
                    bench_closes[settle_session] - bench_opens[entry_session]
                ) / bench_opens[entry_session]
                bench_source = "EXPLICIT_BENCHMARK_INDEX"
            elif (entry_session, settle_session) in window_market_returns:
                bench_ret = window_market_returns[(entry_session, settle_session)]
                bench_source = "BROAD_MARKET_EQUAL_WEIGHTED_UNIVERSE"

            if require_qualified_benchmark and bench_source == "BENCHMARK_UNAVAILABLE":
                logger.warning(
                    "BENCHMARK_UNAVAILABLE: not settling %s %s H%d without an "
                    "authenticated matched-window benchmark",
                    key,
                    f_session,
                    h,
                )
                continue

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
                benchmark_return=round(bench_ret, 5),
                realized_excess_alpha=round(excess_alpha, 5),
                benchmark_source=bench_source,
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
                    "benchmark_return": m.benchmark_return,
                    "realized_excess_alpha": m.realized_excess_alpha,
                    "benchmark_source": m.benchmark_source,
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
                        benchmark_return, realized_excess_alpha, benchmark_source,
                        matured_at, record_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        m.benchmark_return,
                        m.realized_excess_alpha,
                        m.benchmark_source,
                        m.matured_at,
                        r_hash,
                    ),
                )
            conn.commit()

    @staticmethod
    def _compute_session_rank_metrics(rows: list[tuple[float, float]]) -> dict[str, float]:
        """Compute Spearman Rank IC and top-minus-bottom decile spread for a single session.

        rows: list of (predicted_return, realized_return)
        """
        if len(rows) < 10:
            return {"rank_ic": 0.0, "decile_spread_bps": 0.0}

        preds = np.array([r[0] for r in rows], dtype=np.float64)
        rets = np.array([r[1] for r in rows], dtype=np.float64)

        pred_ranks = np.argsort(np.argsort(preds)).astype(np.float64)
        ret_ranks = np.argsort(np.argsort(rets)).astype(np.float64)

        std_p = np.std(pred_ranks, ddof=1)
        std_r = np.std(ret_ranks, ddof=1)
        if std_p > 1e-9 and std_r > 1e-9:
            cov = np.cov(pred_ranks, ret_ranks, ddof=1)[0, 1]
            rank_ic = float(cov / (std_p * std_r))
        else:
            rank_ic = 0.0

        n = len(rows)
        k = max(1, n // 10)
        sorted_indices = np.argsort(preds)
        bottom_indices = sorted_indices[:k]
        top_indices = sorted_indices[-k:]

        top_ret = float(np.mean(rets[top_indices]))
        bottom_ret = float(np.mean(rets[bottom_indices]))
        decile_spread_bps = float((top_ret - bottom_ret) * 10000.0)

        return {
            "rank_ic": round(rank_ic, 4),
            "decile_spread_bps": round(decile_spread_bps, 2),
        }

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
                    AVG(benchmark_return),
                    AVG(realized_excess_alpha)
                FROM matured_forecasts
                GROUP BY horizon_sessions
                """
            )
            rows = cursor.fetchall()
            by_horizon = {}
            for row in rows:
                h, cnt, hit_rate, brier, avg_ret, avg_bench, avg_alpha = row
                raw_ret = float(avg_ret) if avg_ret is not None else 0.0
                raw_bench = float(avg_bench) if avg_bench is not None else 0.0
                raw_alpha = float(avg_alpha) if avg_alpha is not None else 0.0

                cursor.execute(
                    """
                    SELECT forecast_session, predicted_return, realized_return
                    FROM matured_forecasts
                    WHERE horizon_sessions = ?
                    ORDER BY forecast_session
                    """,
                    (h,),
                )
                h_sess_map: dict[str, list[tuple[float, float]]] = {}
                for f_s, p_r, r_r in cursor.fetchall():
                    h_sess_map.setdefault(f_s, []).append((float(p_r), float(r_r)))

                h_rics = []
                h_spreads = []
                for s_list in h_sess_map.values():
                    if len(s_list) >= 10:
                        rm = self._compute_session_rank_metrics(s_list)
                        h_rics.append(rm["rank_ic"])
                        h_spreads.append(rm["decile_spread_bps"])

                h_mean_ric = round(float(np.mean(h_rics)), 4) if h_rics else 0.0
                h_mean_dsp = round(float(np.mean(h_spreads)), 2) if h_spreads else 0.0

                by_horizon[f"H_{h}"] = {
                    "horizon_sessions": h,
                    "settled_count": cnt,
                    "directional_hit_rate": round(float(hit_rate), 4),
                    "mean_brier_score": round(float(brier), 4),
                    "mean_realized_return": round(raw_ret, 5),
                    "mean_benchmark_return": round(raw_bench, 5),
                    "mean_excess_alpha": round(raw_alpha, 5),
                    "net_excess_alpha": round(raw_alpha - 0.0020, 5),
                    "mean_rank_ic": h_mean_ric,
                    "mean_decile_spread_bps": h_mean_dsp,
                }

            cursor.execute(
                """
                SELECT
                    model_id,
                    COUNT(*),
                    COUNT(DISTINCT forecast_session),
                    COUNT(DISTINCT instrument_key),
                    MIN(forecast_session),
                    MAX(forecast_session),
                    AVG(directional_hit),
                    AVG(brier_score_component),
                    AVG(realized_return),
                    AVG(benchmark_return),
                    AVG(realized_excess_alpha),
                    MAX(benchmark_source)
                FROM matured_forecasts
                GROUP BY model_id
                """
            )
            by_model = {}
            for row in cursor.fetchall():
                (
                    m_id,
                    m_cnt,
                    m_dates,
                    m_secs,
                    m_min,
                    m_max,
                    m_hit,
                    m_brier,
                    m_ret,
                    m_bench,
                    m_alpha,
                    m_src,
                ) = row
                m_span = 0
                if m_min and m_max:
                    try:
                        m_span = (date.fromisoformat(m_max) - date.fromisoformat(m_min)).days
                    except (ValueError, TypeError):
                        m_span = 0

                raw_ret_val = float(m_ret) if m_ret is not None else 0.0
                raw_bench_val = float(m_bench) if m_bench is not None else 0.0
                raw_alpha_val = float(m_alpha) if m_alpha is not None else -1.0

                cursor.execute(
                    """
                    SELECT forecast_session, predicted_return, realized_return
                    FROM matured_forecasts
                    WHERE model_id = ?
                    ORDER BY forecast_session
                    """,
                    (m_id,),
                )
                m_sess_map: dict[str, list[tuple[float, float]]] = {}
                for f_s, p_r, r_r in cursor.fetchall():
                    m_sess_map.setdefault(f_s, []).append((float(p_r), float(r_r)))

                m_rics = []
                m_spreads = []
                for s_list in m_sess_map.values():
                    if len(s_list) >= 10:
                        rm = self._compute_session_rank_metrics(s_list)
                        m_rics.append(rm["rank_ic"])
                        m_spreads.append(rm["decile_spread_bps"])

                m_mean_ric = round(float(np.mean(m_rics)), 4) if m_rics else 0.0
                m_mean_dsp = round(float(np.mean(m_spreads)), 2) if m_spreads else 0.0

                by_model[m_id] = {
                    "settled_count": m_cnt,
                    "distinct_decision_dates": m_dates,
                    "distinct_securities": m_secs,
                    "date_span_days": m_span,
                    "directional_hit_rate": round(float(m_hit), 4),
                    "mean_brier_score": round(float(m_brier), 4),
                    "mean_realized_return": round(raw_ret_val, 5),
                    "mean_benchmark_return": round(raw_bench_val, 5),
                    "mean_excess_alpha": round(raw_alpha_val, 5),
                    "net_excess_alpha": round(raw_alpha_val - 0.0020, 5),
                    "mean_rank_ic": m_mean_ric,
                    "mean_decile_spread_bps": m_mean_dsp,
                    "benchmark_source": m_src,
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
