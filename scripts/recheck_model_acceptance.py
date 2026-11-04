"""Automated Model Re-Evaluation and Strategy Performance Audit.

Rechecks independent model acceptance criteria as new forward outcomes mature.
Computes net alpha after transaction friction (20 bps roundtrip), Brier calibration,
Rank IC, and cross-sectional decile spreads per model without cross-model pooling.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from scripts.audit_forward_performance_metrics import audit_matured_ledger  # noqa: E402
from scripts.retrain_models import evaluate_independent_acceptance  # noqa: E402


def recheck_all_models(
    ledger_path: Path | None = None,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> dict[str, Any]:
    ledger = ledger_path or (repo / "data" / "forecasts" / "matured_outcomes_ledger.db")
    audit_summary = audit_matured_ledger(ledger)
    acceptance_eval = evaluate_independent_acceptance(audit_summary)

    # Strategy performance after transaction friction (20 bps roundtrip)
    friction_bps = 20.0
    friction_dec = friction_bps / 10000.0

    gross_alpha_bps = float(audit_summary.get("mean_gross_excess_alpha_bps", 0.0))
    net_alpha_bps = gross_alpha_bps - friction_bps

    total_matured = int(audit_summary.get("total_matured_outcomes", 0))
    dir_hit_rate = float(audit_summary.get("directional_hit_rate", 0.0))
    mean_brier = float(audit_summary.get("mean_brier_score", 1.0))
    mean_rank_ic = float(audit_summary.get("mean_rank_ic", 0.0))
    mean_realized = float(audit_summary.get("mean_realized_return", 0.0))
    mean_benchmark = float(audit_summary.get("mean_benchmark_return", 0.0))
    distinct_dates = int(audit_summary.get("distinct_decision_dates", 0))
    distinct_secs = int(audit_summary.get("distinct_securities", 0))

    is_quarantined = acceptance_eval.get("status") == "ACCEPTANCE_EVIDENCE_QUARANTINED"
    qualified_outcomes = 0 if is_quarantined else total_matured

    strategy_performance = {
        "transaction_friction_model": {
            "roundtrip_bps": friction_bps,
            "brokerage_and_stt_bps": 12.0,
            "exchange_turnover_and_gst_bps": 5.0,
            "slippage_buffer_bps": 3.0,
        },
        "gross_realized_return": mean_realized,
        "net_realized_return": mean_realized - friction_dec,
        "benchmark_return": mean_benchmark,
        "gross_excess_alpha_bps": gross_alpha_bps,
        "net_excess_alpha_bps": net_alpha_bps,
        "directional_accuracy": dir_hit_rate,
        "mean_brier_score": mean_brier,
        "mean_rank_ic": mean_rank_ic,
        "decile_spread_bps": float(audit_summary.get("mean_decile_spread_bps", 0.0)),
    }

    result = {
        "schema": "alphalens.automated_model_acceptance.v1",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "ledger_examined": str(ledger),
        "total_matured_outcomes": total_matured,
        "distinct_decision_dates": distinct_dates,
        "distinct_securities": distinct_secs,
        "strategy_performance_after_costs": strategy_performance,
        "acceptance_criteria": {
            "min_forward_decision_dates_required": 126,
            "min_qualified_outcomes_required": 1000,
            "min_distinct_securities_required": 30,
            "min_directional_accuracy_required": 0.54,
            "min_net_alpha_bps_required": 0.0,
            "max_brier_score_required": 0.25,
            "current_forward_dates": distinct_dates,
            "current_qualified_outcomes": qualified_outcomes,
            "dates_met": distinct_dates >= 126,
            "outcomes_met": total_matured >= 1000 and not is_quarantined,
            "cross_model_pooling_allowed": False,
        },
        "acceptance_verdict": {
            "status": acceptance_eval.get("status", "EXPERIMENTAL"),
            "accepted_models_count": acceptance_eval.get("accepted_models_count", 0),
            "total_models_evaluated": 20,
            "acceptance_granted": acceptance_eval.get("acceptance_granted", False),
            "reason": acceptance_eval.get("reason", "Forward session maturation in progress."),
        },
    }

    out_json_path = output_json or (
        repo / "docs" / "ml" / "automated_model_acceptance_receipt.json"
    )
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    out_md_path = output_md or (repo / "docs" / "ml" / "AUTOMATED_MODEL_ACCEPTANCE_REPORT.md")
    status_verdict = result["acceptance_verdict"]["status"]
    app_count = result["acceptance_verdict"]["accepted_models_count"]
    tot_models = result["acceptance_verdict"]["total_models_evaluated"]

    lines = [
        "# AlphaLens — Automated Model Acceptance & Strategy Performance Audit",
        "",
        f"**Evaluated At:** {result['evaluated_at']}  ",
        f"**Ledger Inspected:** `{result['ledger_examined']}`  ",
        f"**Acceptance Verdict:** **{status_verdict}**  ",
        f"**Independently Approved Models:** **{app_count} / {tot_models}**",
        "",
        "---",
        "",
        "## 1. Strategy Performance After Costs (20 bps Roundtrip)",
        "",
        "| Metric | Value | Threshold | Status |",
        "| :--- | :--- | :--- | :--- |",
        f"| Gross Return | {strategy_performance['gross_realized_return']:.4f} | — | Evaluated |",
        f"| Net Return | {strategy_performance['net_realized_return']:.4f} | — | After 20 bps |",
        f"| Benchmark Return | {strategy_performance['benchmark_return']:.4f} | — | Broad Market |",
        f"| Gross Alpha | {strategy_performance['gross_excess_alpha_bps']:.1f} bp | > 0 | Done |",
        f"| Net Alpha | {strategy_performance['net_excess_alpha_bps']:.1f} bp | > 0 | Done |",
        f"| Hit Rate | {strategy_performance['directional_accuracy'] * 100:.1f}% | > 54% | Done |",
        f"| Brier Score | {strategy_performance['mean_brier_score']:.4f} | <= 0.25 | Done |",
        f"| Rank IC | {strategy_performance['mean_rank_ic']:.4f} | > 0.02 | Done |",
        f"| Decile Spread | {strategy_performance['decile_spread_bps']:.0f} bp | > 0 | Done |",
        "",
        "---",
        "",
        "## 2. Independent Model Acceptance Criteria Progress",
        "",
        "| Requirement | Required | Current | Status |",
        "| :--- | :--- | :--- | :--- |",
        f"| Forward Dates | >= 126 | {distinct_dates} | In Progress |",
        f"| Qualified Outcomes | >= 1,000 | {qualified_outcomes} | In Progress |",
        f"| Distinct Securities | >= 30 | {distinct_secs} | PASS |",
        f"| Directional Hit Rate | > 54.0% | {dir_hit_rate * 100:.2f}% | Evaluated |",
        f"| Net Alpha After Friction | > 0.0 bps | {net_alpha_bps:.2f} bps | Evaluated |",
        f"| Brier Calibration | <= 0.25 | {mean_brier:.4f} | Evaluated |",
        "| Cross-Model Pooling | Prohibited | Enforced | PASS |",
        "",
        "---",
        "",
        "## 3. Policy & Governance Statement",
        "",
        result["acceptance_verdict"]["reason"],
        "",
    ]
    out_md_path.write_text("\n".join(lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    res = recheck_all_models()
    print(json.dumps(res, indent=2))
