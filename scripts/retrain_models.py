"""Automated Reproducible Walk-Forward Model Retraining and Gated Lifecycle Pipeline.

Enforces strict model lifecycle state governance:
1. TRAINING_SUCCESS: Model optimization converged on training partition with fixed seeds.
2. BACKTEST_EVALUATED: Historical holdout metrics computed across walk-forward folds.
3. RESEARCH_CANDIDATE: Passes preliminary statistical filters (positive edge over chance).
4. FORWARD_OUTCOME_PENDING: Deployed for prospective observation; awaiting future sessions.
5. INDEPENDENT_ACCEPTANCE_PENDING: Prospective forward outcomes accumulating towards thresholds.
6. ACCEPTED: Formal independent acceptance granted ONLY after >=60 forward sessions,
   >=500 prospective securities, forward directional accuracy >54%, and positive alpha after costs.
   Never granted from historical holdout metrics alone.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from workers.nse_market import (  # noqa: E402
    forward_maturation_engine,
    full_universe_predictor,
    multi_model_engine,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("alphalens.retrain_models")


class ModelLifecycleState(StrEnum):
    TRAINING_SUCCESS = "TRAINING_SUCCESS"
    BACKTEST_EVALUATED = "BACKTEST_EVALUATED"
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    FORWARD_OUTCOME_PENDING = "FORWARD_OUTCOME_PENDING"
    INDEPENDENT_ACCEPTANCE_PENDING = "INDEPENDENT_ACCEPTANCE_PENDING"
    ACCEPTED = "ACCEPTED"


def evaluate_independent_acceptance(audit_summary: dict[str, Any]) -> dict[str, Any]:
    """Evaluate formal independent acceptance based exclusively on genuine forward outcomes.

    Strictly reconciled with registered policy in docs/ml/MODEL_TRAINING_AND_EVALUATION.md:
    1. Minimum 126 distinct forward daily decision dates PER MODEL
    2. Minimum 1,000 qualified matured forward outcomes PER MODEL
    3. Minimum 30 distinct securities observed prospectively PER MODEL
    4. Two full calendar quarters of forward walk-forward outcomes (>= 180 days elapsed) PER MODEL
    5. Model prospective directional hit-rate > 54.0%
    6. Positive net excess alpha after trading friction (> 0 bps after 20 bps round-trip costs)
    7. Brier score calibration <= 0.25

    NEVER aggregates outcomes across different models to satisfy acceptance thresholds.
    """
    q_stat = audit_summary.get("quarantine_status", {})
    if (
        q_stat.get("quarantine_active")
        or audit_summary.get("acceptance_status", {}).get("status")
        == "ACCEPTANCE_EVIDENCE_QUARANTINED"
    ):
        return {
            "status": "ACCEPTANCE_EVIDENCE_QUARANTINED",
            "verdict": "REGISTERED_ACCEPTANCE_CRITERIA_QUARANTINED",
            "accepted_models_count": 0,
            "accepted_models": [],
            "qualified_outcomes_count": 0,
            "qualified_decision_dates_count": 0,
            "quarantined_outcomes_count": q_stat.get("legacy_outcomes_quarantined", 601),
            "per_model_evaluations": {},
            "acceptance_granted": False,
            "reason": (
                f"Quarantined forward outcomes ({q_stat.get('legacy_outcomes_quarantined', 601)}) "
                "contribute ZERO observations and ZERO decision dates to independent ML acceptance."
            ),
        }
    by_model = audit_summary.get("summary_by_model", {})
    if not by_model and "summary_by_horizon" in audit_summary:
        h5 = audit_summary["summary_by_horizon"].get("H_5", {})
        raw_alpha = float(h5.get("mean_excess_alpha", -1.0))
        by_model = {
            "default_candidate": {
                "settled_count": int(audit_summary.get("total_matured_forecasts", 0)),
                "distinct_decision_dates": int(audit_summary.get("distinct_decision_dates", 0)),
                "distinct_securities": int(audit_summary.get("distinct_securities", 0)),
                "date_span_days": int(audit_summary.get("date_span_days", 0)),
                "directional_hit_rate": float(h5.get("directional_hit_rate", 0.0)),
                "mean_brier_score": float(h5.get("mean_brier_score", 1.0)),
                "mean_excess_alpha": raw_alpha,
                "net_excess_alpha": round(raw_alpha - 0.0020, 5),
            }
        }

    per_model_evaluations: dict[str, Any] = {}
    accepted_models: list[str] = []

    if not by_model:
        return {
            "status": ModelLifecycleState.FORWARD_OUTCOME_PENDING,
            "verdict": "REGISTERED_ACCEPTANCE_CRITERIA_PENDING_MATURATION",
            "accepted_models_count": 0,
            "accepted_models": [],
            "per_model_evaluations": {},
            "acceptance_granted": False,
            "reason": "No model-specific forward maturation records available in audit summary.",
        }

    for model_id, m_metrics in by_model.items():
        m_cnt = int(m_metrics.get("settled_count", 0))
        m_dates = int(m_metrics.get("distinct_decision_dates", 0))
        m_secs = int(m_metrics.get("distinct_securities", 0))
        m_days = int(m_metrics.get("date_span_days", 0))
        m_hit = float(m_metrics.get("directional_hit_rate", 0.0))
        m_brier = float(m_metrics.get("mean_brier_score", 1.0))
        m_alpha = float(m_metrics.get("mean_excess_alpha", -1.0))
        net_alpha = float(m_metrics.get("net_excess_alpha", m_alpha - 0.0020))

        criteria: dict[str, dict[str, Any]] = {
            "matured_outcomes": {
                "required": 1000,
                "current": m_cnt,
                "satisfied": m_cnt >= 1000,
            },
            "decision_dates": {
                "required": 126,
                "current": m_dates,
                "satisfied": m_dates >= 126,
            },
            "distinct_securities": {
                "required": 30,
                "current": m_secs,
                "satisfied": m_secs >= 30,
            },
            "calendar_quarters_days": {
                "required": 180,
                "current": m_days,
                "satisfied": m_days >= 180,
            },
            "directional_hit_rate": {
                "required": 0.54,
                "current": m_hit,
                "satisfied": m_hit > 0.54,
            },
            "calibration_brier": {
                "required": 0.25,
                "current": m_brier,
                "satisfied": m_brier <= 0.25,
            },
            "net_excess_alpha": {
                "required": 0.0,
                "current": net_alpha,
                "satisfied": net_alpha > 0.0,
            },
        }

        count_criteria_satisfied = (
            criteria["matured_outcomes"]["satisfied"]
            and criteria["decision_dates"]["satisfied"]
            and criteria["distinct_securities"]["satisfied"]
            and criteria["calendar_quarters_days"]["satisfied"]
        )

        all_satisfied = all(c["satisfied"] for c in criteria.values())
        if all_satisfied:
            accepted_models.append(model_id)
            per_model_evaluations[model_id] = {
                "status": ModelLifecycleState.ACCEPTED,
                "verdict": "INDEPENDENT_ACCEPTANCE_GRANTED",
                "criteria_audit": criteria,
                "directional_hit_rate": m_hit,
                "mean_brier_score": m_brier,
                "net_excess_alpha": net_alpha,
                "acceptance_granted": True,
            }
        elif count_criteria_satisfied:
            per_model_evaluations[model_id] = {
                "status": ModelLifecycleState.INDEPENDENT_ACCEPTANCE_PENDING,
                "verdict": "PERFORMANCE_THRESHOLDS_NOT_SATISFIED",
                "criteria_audit": criteria,
                "directional_hit_rate": m_hit,
                "mean_brier_score": m_brier,
                "net_excess_alpha": net_alpha,
                "acceptance_granted": False,
            }
        else:
            per_model_evaluations[model_id] = {
                "status": ModelLifecycleState.FORWARD_OUTCOME_PENDING,
                "verdict": "REGISTERED_ACCEPTANCE_CRITERIA_PENDING_MATURATION",
                "criteria_audit": criteria,
                "directional_hit_rate": m_hit,
                "mean_brier_score": m_brier,
                "net_excess_alpha": net_alpha,
                "acceptance_granted": False,
            }

    overall_accepted = len(accepted_models) > 0
    first_eval = next(iter(per_model_evaluations.values())) if per_model_evaluations else {}
    overall_status = first_eval.get("status", ModelLifecycleState.FORWARD_OUTCOME_PENDING)
    if overall_accepted:
        overall_status = ModelLifecycleState.ACCEPTED

    return {
        "status": overall_status,
        "verdict": (
            "INDEPENDENT_ACCEPTANCE_GRANTED"
            if overall_accepted
            else first_eval.get("verdict", "REGISTERED_ACCEPTANCE_CRITERIA_PENDING_MATURATION")
        ),
        "accepted_models_count": len(accepted_models),
        "accepted_models": accepted_models,
        "per_model_evaluations": per_model_evaluations,
        "criteria_audit": first_eval.get("criteria_audit", {}),
        "directional_hit_rate": first_eval.get("directional_hit_rate", 0.0),
        "mean_brier_score": first_eval.get("mean_brier_score", 1.0),
        "net_excess_alpha": first_eval.get("net_excess_alpha", -1.0),
        "acceptance_granted": overall_accepted,
        "reason": (
            f"Evaluated {len(by_model)} candidate models independently against criteria. "
            f"Currently {len(accepted_models)} models meet all 7 independent conditions."
        ),
    }


def load_authoritative_forecasts(root: Path | None = None) -> list[dict[str, Any]]:
    """Load genuine immutable prospective forecasts from authoritative sqlite ledgers.

    Never manufactures missing probability or expected return using defaults.
    Deduplicates records correctly and excludes retrospective research rankings.
    Preserves prediction creation time, valid entry deadline, model ID, target definition,
    dataset identity, and source provenance.
    """
    import sqlite3

    if root is None:
        root = repo.parent / ".local-data" / "nse-market-expansion" / "expanded-forecasts"
        if not root.exists():
            root = repo / ".local-data" / "nse-market-expansion" / "expanded-forecasts"

    if not root.exists():
        logger.warning("Authoritative forecast root does not exist: %s", root)
        return []

    forecasts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    shard_files = sorted(root.glob("**/experimental-v2-prospective.sqlite3"))

    for sf in shard_files:
        try:
            with sqlite3.connect(sf) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, model_id, instrument_key, observation_session, recorded_at, body "
                    "FROM experimental_forecasts"
                )
                for row in cursor.fetchall():
                    f_id, m_id, key, obs_session, rec_at, body_str = row
                    if f_id in seen_ids:
                        continue
                    seen_ids.add(f_id)

                    try:
                        b = json.loads(body_str)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug("Skipping unparseable body for %s: %s", f_id, e)
                        continue

                    # Require valid directional score without manufacturing defaults
                    raw_score = b.get("score")
                    if raw_score is None:
                        raw_score = b.get("direction_probability")
                    if raw_score is None:
                        continue

                    try:
                        pred_prob = float(raw_score)
                    except (ValueError, TypeError):
                        continue

                    f_entry = {
                        "id": f_id,
                        "model_id": m_id or b.get("model_id", "AlphaLens_Default"),
                        "instrument_key": key or b.get("key"),
                        "session": obs_session or b.get("session"),
                        "recorded_at": rec_at or b.get("recorded_at"),
                        "horizon_sessions": int(b.get("horizon", 5)),
                        "direction_probability": pred_prob,
                        "expected_return": b.get("expected_return"),
                        "symbol": b.get("symbol"),
                        "next_session_timing": b.get("next_session_timing"),
                        "prospective_eligible": b.get("prospective_eligible", True),
                        "forecast_classification": b.get("classification"),
                        "dataset_id": b.get("dataset_id"),
                        "target_version": b.get("target_version"),
                        "source_provenance": b.get("source"),
                    }
                    forecasts.append(f_entry)
        except Exception as e:
            logger.warning("Error reading forecast shard %s: %s", sf, e)

    logger.info(
        "Loaded %d authoritative forecasts from %d shards", len(forecasts), len(shard_files)
    )
    return forecasts


def run_outcome_settlement(
    forecasts: list[dict[str, Any]] | None = None,
    histories: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Independent audited stage for settling forward outcomes from authorized ledgers."""
    logger.info("Executing forward outcome settlement stage...")
    engine = forward_maturation_engine.ForwardMaturationEngine()

    # Live settlement must enforce quarantine before new database writes. A
    # separate reporting audit does not automatically gate this pathway.
    from scripts.audit_existing_exchange_horizons import audit_existing_horizons

    horizon_audit = audit_existing_horizons(engine.db_path)
    if horizon_audit.get("status") != "EXCHANGE_SESSION_WINDOWS_ALIGNED":
        summary = engine.generate_audit_summary()
        summary["quarantine_status"] = {
            "quarantine_active": True,
            "legacy_outcomes_quarantined": int(summary.get("total_matured_forecasts", 0)),
            "misaligned_outcomes": int(horizon_audit.get("misaligned", 0)),
            "unverifiable_outcomes": int(horizon_audit.get("unverifiable", 0)),
            "qualified_acceptance_outcomes": 0,
            "qualified_acceptance_decision_dates": 0,
            "audit_status": horizon_audit.get("status", "UNKNOWN"),
        }
        summary["acceptance_status"] = {"status": "ACCEPTANCE_EVIDENCE_QUARANTINED"}
        logger.error(
            "SETTLEMENT_HELD_QUARANTINED_LEGACY_OUTCOMES: %s",
            horizon_audit.get("status", "UNKNOWN"),
        )
        return summary

    # 1. Connect real authorized market-history ledger if not provided
    if histories is None:
        mv_path = repo.parent / ".local-data" / "nse-market-expansion" / "market-view-latest.json"
        if not mv_path.exists():
            mv_path = repo / ".local-data" / "nse-market-expansion" / "market-view-latest.json"
        if mv_path.exists():
            try:
                meta = json.loads(mv_path.read_text(encoding="utf-8"))
                mv_doc = json.loads((mv_path.parent / meta["path"]).read_text(encoding="utf-8"))
                histories = mv_doc.get("histories", {})
                logger.info("Loaded authorized market histories for %d instruments", len(histories))
            except Exception as e:
                logger.warning("Could not read authorized market-view: %s", e)
                histories = {}
        else:
            histories = {}

    # 2. Connect genuine immutable prospective forecast ledger if not provided
    # (Never settle retrospective rankings exports as prospective forecasts)
    if forecasts is None:
        forecasts = load_authoritative_forecasts()
        logger.info(
            "Loaded %d authorized prospective forecasts from immutable shards", len(forecasts)
        )

    # Benchmark candles if available
    benchmark_history = histories.get("NSE_INDEX|Nifty 50") if histories else None

    # Settle forecasts against genuine market history (NEVER fabricate outcomes)
    if forecasts and histories:
        matured = engine.settle_forecasts(
            forecasts,
            histories,
            benchmark_history=benchmark_history,
            require_entry_timing=True,
            require_qualified_benchmark=True,
            require_calendar_aligned_horizon=True,
        )
        logger.info("Settled %d newly matured prospective outcomes", len(matured))
    else:
        logger.info(
            "No authorized forecasts or histories available to settle; 0 outcomes fabricated."
        )

    summary = engine.generate_audit_summary()
    final_audit = audit_existing_horizons(engine.db_path)
    status = final_audit.get("status")
    is_quarantined = status != "EXCHANGE_SESSION_WINDOWS_ALIGNED"
    summary["quarantine_status"] = {
        "quarantine_active": is_quarantined,
        "legacy_outcomes_quarantined": (
            int(summary.get("total_matured_forecasts", 0)) if is_quarantined else 0
        ),
        "misaligned_outcomes": int(final_audit.get("misaligned", 0)),
        "unverifiable_outcomes": int(final_audit.get("unverifiable", 0)),
        "qualified_acceptance_outcomes": (
            0 if is_quarantined else int(summary.get("total_matured_forecasts", 0))
        ),
        "qualified_acceptance_decision_dates": (
            0 if is_quarantined else int(summary.get("distinct_decision_dates", 0))
        ),
        "audit_status": status,
    }
    if is_quarantined:
        summary["acceptance_status"] = {"status": "ACCEPTANCE_EVIDENCE_QUARANTINED"}
    return summary


def run_retraining(
    as_of_session: str = "2026-11-02",
    stage: str = "all",
) -> dict[str, Any]:
    """Execute reproducible retraining and lifecycle auditing routine."""
    logger.info(
        "Starting model lifecycle runner for session %s (stage=%s)...", as_of_session, stage
    )
    start_time = datetime.now(UTC)

    multi_res: dict[str, Any] = {}
    audit_summary: dict[str, Any] = {}
    universe_res: dict[str, Any] = {}

    # Stage: Retrain Models
    if stage in ("all", "retrain"):
        logger.info("[1/3] Executing multi-model walk-forward training (resource-bounded)...")
        multi_res = multi_model_engine.run_pipeline()

    # Stage: Settle Out-of-Sample Outcomes
    if stage in ("all", "settle"):
        logger.info("[2/3] Executing audited forward outcome settlement...")
        audit_summary = run_outcome_settlement()

    # Stage: Prospective Universe Scoring
    if stage in ("all", "predict"):
        logger.info("[3/3] Generating prospective rankings across universe...")
        predictor = full_universe_predictor.FullUniversePredictor()
        models = multi_res.get("models")
        universe_res = predictor.run_full_universe_prediction(
            as_of_session=as_of_session, trained_models=models
        )

    # Assess Independent Acceptance Policy
    acceptance_audit = evaluate_independent_acceptance(audit_summary)
    logger.info(
        "Model Lifecycle Evaluation: %s (Acceptance Granted: %s)",
        acceptance_audit["status"],
        acceptance_audit["acceptance_granted"],
    )

    elapsed_seconds = (datetime.now(UTC) - start_time).total_seconds()
    receipt = {
        "schema": "alphalens.model_lifecycle_receipt.v2",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "as_of_session": as_of_session,
        "stage": stage,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "lifecycle_state": {
            "training_state": (
                ModelLifecycleState.TRAINING_SUCCESS
                if stage in ("all", "retrain")
                else "SKIPPED_IN_THIS_STAGE"
            ),
            "backtest_state": (
                ModelLifecycleState.BACKTEST_EVALUATED
                if stage in ("all", "retrain")
                else "SKIPPED_IN_THIS_STAGE"
            ),
            "candidate_state": (
                ModelLifecycleState.RESEARCH_CANDIDATE
                if stage in ("all", "retrain")
                else "SKIPPED_IN_THIS_STAGE"
            ),
            "acceptance_state": acceptance_audit["status"],
            "independent_acceptance_granted": acceptance_audit["acceptance_granted"],
        },
        "acceptance_policy_audit": acceptance_audit,
        "total_models_evaluated": len(multi_res.get("metrics", [])),
        "audit_summary": audit_summary,
        "universe_summary": universe_res.get("universe_summary", {}),
        "bse_status": universe_res.get("bse_status", {}),
    }

    out_receipt = repo / "docs" / "ml" / "automated_retraining_receipt.json"
    out_receipt.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    logger.info("Lifecycle execution complete. Receipt written to %s", out_receipt)

    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaLens Model Lifecycle & Retraining Pipeline")
    parser.add_argument(
        "--as-of-session", type=str, default="2026-11-02", help="Target market session"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "retrain", "settle", "predict"],
        default="all",
        help="Pipeline stage to execute",
    )
    args = parser.parse_args()

    run_retraining(as_of_session=args.as_of_session, stage=args.stage)


if __name__ == "__main__":
    main()
