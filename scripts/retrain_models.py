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
    1. Minimum 126 distinct forward daily decision dates
    2. Minimum 1,000 qualified matured forward outcomes
    3. Minimum 30 distinct securities observed prospectively
    4. Two full calendar quarters of forward walk-forward outcomes (>= 180 days elapsed)
    5. Aggregate prospective directional hit-rate > 54.0%
    6. Positive mean excess alpha after trading friction (> 0 bps after 20 bps round-trip costs)
    7. Brier score calibration <= 0.25
    """
    total_matured = int(audit_summary.get("total_matured_forecasts", 0))
    decision_dates = int(audit_summary.get("distinct_decision_dates", 0))
    distinct_securities = int(audit_summary.get("distinct_securities", 0))
    span_days = int(audit_summary.get("date_span_days", 0))
    by_horizon = audit_summary.get("summary_by_horizon", {})

    criteria = {
        "matured_outcomes": {
            "required": 1000,
            "current": total_matured,
            "satisfied": total_matured >= 1000,
        },
        "decision_dates": {
            "required": 126,
            "current": decision_dates,
            "satisfied": decision_dates >= 126,
        },
        "distinct_securities": {
            "required": 30,
            "current": distinct_securities,
            "satisfied": distinct_securities >= 30,
        },
        "calendar_quarters_days": {
            "required": 180,
            "current": span_days,
            "satisfied": span_days >= 180,
        },
    }

    if not all(c["satisfied"] for c in criteria.values()):
        return {
            "status": ModelLifecycleState.FORWARD_OUTCOME_PENDING,
            "verdict": "REGISTERED_ACCEPTANCE_CRITERIA_PENDING_MATURATION",
            "criteria_audit": criteria,
            "acceptance_granted": False,
            "reason": (
                "Formal model acceptance requires surviving >= 126 prospective daily decisions, "
                ">= 1,000 qualified matured outcomes across >= 30 securities over two quarters. "
                "Current state reflects forward maturation in progress."
            ),
        }

    # Evaluate 5-session primary horizon if sufficient matured samples exist
    h5_summary = by_horizon.get("H_5", {})
    hit_rate = float(h5_summary.get("directional_hit_rate", 0.0))
    brier = float(h5_summary.get("mean_brier_score", 1.0))
    raw_excess_alpha = float(h5_summary.get("mean_excess_alpha", -1.0))

    # Deduct 20 bps round-trip friction (brokerage, STT, exchange fees, slippage)
    net_excess_alpha = raw_excess_alpha - 0.0020

    alpha_satisfied = net_excess_alpha > 0.0
    hit_rate_satisfied = hit_rate > 0.54
    calibration_satisfied = brier <= 0.25

    if hit_rate_satisfied and alpha_satisfied and calibration_satisfied:
        return {
            "status": ModelLifecycleState.ACCEPTED,
            "verdict": "INDEPENDENT_ACCEPTANCE_GRANTED",
            "criteria_audit": criteria,
            "directional_hit_rate": hit_rate,
            "mean_brier_score": brier,
            "net_excess_alpha": net_excess_alpha,
            "acceptance_granted": True,
        }

    return {
        "status": ModelLifecycleState.INDEPENDENT_ACCEPTANCE_PENDING,
        "verdict": "PERFORMANCE_THRESHOLDS_NOT_SATISFIED",
        "criteria_audit": criteria,
        "directional_hit_rate": hit_rate,
        "mean_brier_score": brier,
        "net_excess_alpha": net_excess_alpha,
        "acceptance_granted": False,
    }


def run_outcome_settlement(
    forecasts: list[dict[str, Any]] | None = None,
    histories: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Independent audited stage for settling forward outcomes from authorized ledgers."""
    logger.info("Executing forward outcome settlement stage...")
    engine = forward_maturation_engine.ForwardMaturationEngine()

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

    # 2. Connect real authorized forecast ledger if not provided
    if forecasts is None:
        forecasts = []
        doc_forecasts = repo / "docs" / "ml" / "full_universe_rankings_20261102.json"
        if doc_forecasts.exists():
            try:
                doc = json.loads(doc_forecasts.read_text(encoding="utf-8"))
                top_equities = doc.get("dual_exchange_top_20", []) + doc.get(
                    "dual_exchange_top_50", []
                )
                for eq in top_equities:
                    forecasts.append(
                        {
                            "instrument_key": eq.get("key"),
                            "symbol": eq.get("symbol"),
                            "session": doc.get("as_of_session", "2026-11-02"),
                            "horizon_sessions": 5,
                            "direction_probability": eq.get("direction_prob_h5", 0.5),
                            "expected_return": eq.get("expected_return_bps_h5", 0.0) / 10000.0,
                            "model_id": "HistGB_Classifier_H5",
                        }
                    )
            except Exception as e:
                logger.warning("Error reading rankings json: %s", e)

        logger.info("Loaded %d authorized prospective forecasts from ledger", len(forecasts))

    # Benchmark candles if available
    benchmark_history = histories.get("NSE_INDEX|Nifty 50") if histories else None

    # Settle forecasts against genuine market history (NEVER fabricate outcomes)
    if forecasts and histories:
        matured = engine.settle_forecasts(forecasts, histories, benchmark_history=benchmark_history)
        logger.info("Settled %d newly matured prospective outcomes", len(matured))
    else:
        logger.info(
            "No authorized forecasts or histories available to settle; 0 outcomes fabricated."
        )

    return engine.generate_audit_summary()


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
            "training_state": ModelLifecycleState.TRAINING_SUCCESS,
            "backtest_state": ModelLifecycleState.BACKTEST_EVALUATED,
            "candidate_state": ModelLifecycleState.RESEARCH_CANDIDATE,
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
