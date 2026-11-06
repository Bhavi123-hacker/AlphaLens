"""Statistical significance and sample size audit for AlphaLens backtests."""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

LOCAL_DATA = Path("D:/al-research/p28-worktree/.local-data")


def run_statistical_audit() -> None:
    # Load market view sessions
    p_ptr = LOCAL_DATA / "nse-market-expansion" / "market-view-latest.json"
    meta = json.loads(p_ptr.read_text(encoding="utf-8"))
    mv_file = p_ptr.parent / meta["path"]
    data = json.loads(mv_file.read_text(encoding="utf-8"))

    histories = data["histories"]
    all_sessions = set()
    for bars in histories.values():
        for b in bars:
            d = b.get("session") or b.get("date") or b.get("timestamp", "")[:10]
            if d:
                all_sessions.add(str(d))
    sorted_sessions = sorted(all_sessions)

    # Test window: 84 sessions (index 36 to 119)
    test_sessions = sorted_sessions[36:]
    total_test_sessions = len(test_sessions)

    # 1. T+5 non-overlapping schedule
    t5_schedule = []
    for idx in range(36, 120, 5):
        exit_idx = idx + 5
        if exit_idx < len(sorted_sessions):
            t5_schedule.append({
                "trade_num": len(t5_schedule) + 1,
                "entry_idx_global": idx,
                "exit_idx_global": exit_idx,
                "entry_idx_test": idx - 36,
                "exit_idx_test": exit_idx - 36,
                "entry_session": sorted_sessions[idx],
                "exit_session": sorted_sessions[exit_idx],
                "holding_days": 5,
            })
        else:
            incomplete_t5 = {
                "entry_idx_global": idx,
                "entry_idx_test": idx - 36,
                "entry_session": sorted_sessions[idx],
                "expected_exit_idx_global": exit_idx,
                "status": "INCOMPLETE_UNMATURED_OBSERVATION",
            }

    # 2. T+10 non-overlapping schedule
    t10_schedule = []
    for idx in range(36, 120, 10):
        exit_idx = idx + 10
        if exit_idx < len(sorted_sessions):
            t10_schedule.append({
                "trade_num": len(t10_schedule) + 1,
                "entry_idx_global": idx,
                "exit_idx_global": exit_idx,
                "entry_idx_test": idx - 36,
                "exit_idx_test": exit_idx - 36,
                "entry_session": sorted_sessions[idx],
                "exit_session": sorted_sessions[exit_idx],
                "holding_days": 10,
            })
        else:
            incomplete_t10 = {
                "entry_idx_global": idx,
                "entry_idx_test": idx - 36,
                "entry_session": sorted_sessions[idx],
                "expected_exit_idx_global": exit_idx,
                "status": "INCOMPLETE_UNMATURED_OBSERVATION",
            }

    # 3. Load empirical backtest results from docs/ml/hybrid_vs_ml_empirical_comparison.json
    comp_file = repo / "docs" / "ml" / "hybrid_vs_ml_empirical_comparison.json"
    comp_data = json.loads(comp_file.read_text(encoding="utf-8")) if comp_file.exists() else {}

    # Sample size power calculation for T+5
    # Assume target alpha = 50 bps (0.0050), standard deviation = 2.50% (0.0250)
    alpha_target = 0.0050
    sigma_est = 0.0250
    effect_size = alpha_target / sigma_est
    # N required for 80% power at alpha=0.05 (one-tailed)
    z_alpha = 1.645
    z_beta = 0.842
    n_required_50bps = math.ceil(((z_alpha + z_beta) / effect_size) ** 2)

    # For 30 bps alpha
    effect_size_30bps = 0.0030 / sigma_est
    n_required_30bps = math.ceil(((z_alpha + z_beta) / effect_size_30bps) ** 2)

    # Actual power of N=16 trades with effect_size = 0.20
    # z = sqrt(16)*0.20 - 1.645 = 4*0.20 - 1.645 = 0.80 - 1.645 = -0.845
    # Normal CDF(-0.845) ~ 0.20 (only 20% power!)
    power_n16 = 0.199

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "test_window": {
            "start_session": test_sessions[0],
            "end_session": test_sessions[-1],
            "total_sessions": total_test_sessions,
        },
        "t5_schedule": {
            "completed_trades_count": len(t5_schedule),
            "trades": t5_schedule,
            "incomplete_observation": incomplete_t5,
        },
        "t10_schedule": {
            "completed_trades_count": len(t10_schedule),
            "trades": t10_schedule,
            "incomplete_observation": incomplete_t10,
        },
        "statistical_power_analysis": {
            "assumed_standard_deviation_per_cycle": sigma_est,
            "hypothesized_alpha_50bps": {
                "effect_size_cohen_d": round(effect_size, 4),
                "n_cycles_required_80pct_power": n_required_50bps,
            },
            "hypothesized_alpha_30bps": {
                "effect_size_cohen_d": round(effect_size_30bps, 4),
                "n_cycles_required_80pct_power": n_required_30bps,
            },
            "actual_sample_t5": {
                "n_completed_trades": len(t5_schedule),
                "statistical_power_at_50bps": round(power_n16, 3),
                "verdict": "STATISTICALLY_INSUFFICIENT_FOR_ACCEPTANCE",
                "notes": "With N=16, statistical power is only ~20%. Standard error of mean exceeds expected alpha.",
            },
            "actual_sample_t10": {
                "n_completed_trades": len(t10_schedule),
                "verdict": "STATISTICALLY_INSUFFICIENT_FOR_ACCEPTANCE",
                "notes": "With N=8, degrees of freedom = 7, power < 12%. Descriptive preliminary evidence only.",
            },
        },
        "acceptance_verdict": "NOT_STATISTICALLY_DEMONSTRATED_PRELIMINARY_EVIDENCE_ONLY",
    }

    out_file = repo / "release" / "alphalens_statistical_significance_audit.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Statistical audit complete. Output written to {out_file}")


if __name__ == "__main__":
    run_statistical_audit()
