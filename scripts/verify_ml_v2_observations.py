"""Read real private V2 evidence; export aggregate verification, never market prices."""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse_v2 import data
from workers.experimental_nse_v2.features import build
from workers.experimental_nse_v2.pipeline import verified
from workers.experimental_nse_v2.workspace import read_workspace
from workers.personal.analytics import preference_match
from workers.personal.contracts import Profile


def check(root: Path) -> dict[str, Any]:
    base, current = data.load(root), data.load_current(root)
    workspace = read_workspace(root)
    now = datetime.now(UTC)
    primary = verified(root / "evaluation.json")
    companion = verified(root / "price-only/evaluation.json")
    features = build(
        current["rows"],
        current["sessions"],
        current["quality"]["excluded_sessions"],
        include_context=False,
    )
    latest = current["sessions"][-1]
    eligible = {r.key: r for r in features.samples if r.session == latest}
    assert len(eligible) == len(workspace["candidates"])
    for row in workspace["candidates"]:
        assert row["features"] == list(eligible[row["key"]].vector)
        assert row["symbol"] == eligible[row["key"]].symbol
        assert (
            datetime.fromisoformat(row["source_observed_at"])
            <= datetime.fromisoformat(row["inference_at"])
            <= now
        )
        assert datetime.fromisoformat(row["inference_at"]) < datetime.fromisoformat(
            row["entry_open_at"]
        )
        assert row["session"] == latest
    profile = Profile(
        maximum_drawdown_percent="100",
        maximum_daily_volatility_percent="100",
        minimum_volume=0,
        minimum_rsi="0",
        maximum_rsi="100",
    )
    matched = sum(
        preference_match(profile, row["preference_metrics"])["state"]
        == "MATCHES_SUPPORTED_CONSTRAINTS"
        for row in workspace["candidates"]
    )
    assert matched == len(eligible)
    constrained = profile.model_copy(update={"budget_inr": "0"})
    excluded = sum(
        preference_match(constrained, row["preference_metrics"])["state"]
        == "EXCLUDED_BY_SUPPORTED_CONSTRAINT"
        for row in workspace["candidates"]
    )
    assert excluded == len(eligible)
    experiments = {}
    for name, report in (("primary_20", primary), ("companion_16", companion)):
        experiments[name] = {
            key: report[key]
            for key in (
                "model_id",
                "dataset_id",
                "protocol_id",
                "feature_version",
                "actual_fit_count",
                "selected_algorithm",
                "candidate_summary",
                "baseline_summary",
                "historical_folds",
                "uncertainty",
                "selected_stability",
                "feature_audit",
                "evidence_conclusion",
                "secondary_horizons",
            )
        }
        experiments[name]["economic_reference_scenarios_25bps_plus_5bps_per_side"] = [
            s
            for s in report["hypothetical_economic_sensitivity"]["scenarios"]
            if s["round_trip_cost_bps_assumption"] == 25
            and s["slippage_bps_each_side_assumption"] == 5
        ]
        experiments[name]["economic_evidence"] = (
            "CONDITIONAL_REFERENCE_PRICES_NOT_EXECUTED_PROFIT_OR_INDEPENDENT_EDGE"
        )
    return {
        "verified_at": now.isoformat(),
        "source": "UPSTOX_OFFICIAL_AUTHENTICATED_DAILY_CANDLES",
        "permission_reference": base["permission_reference"],
        "base_dataset_id": base["dataset_id"],
        "current_dataset_id": current["dataset_id"],
        "base_observations": len(base["rows"]),
        "current_observations": len(current["rows"]),
        "securities": len(current["identities"]),
        "sessions": len(current["sessions"]),
        "start": current["sessions"][0],
        "end": latest,
        "historical_acquisition_api_calls": base["api_calls"],
        "closed_current_api_calls": current["current_api_calls"],
        "missing_cohort_slots": current["quality"]["missing_cohort_slots"],
        "cross_security_duplicate_groups": current["quality"][
            "cross_security_identical_ohlcv_groups"
        ],
        "anomaly_count": len(current["quality"]["anomalies"]),
        "action_reference_states": dict(Counter(v["state"] for v in current["actions"].values())),
        "raw_action_payloads_retained": False,
        "complete_action_coverage": False,
        "feature_exclusions": dict(Counter(r["reason"] for r in features.exclusions)),
        "historical_feature_vectors": len(features.samples),
        "matured_historical_feature_vectors": sum(r.target is not None for r in features.samples),
        "actual_model_scored_securities": len(eligible),
        "top_5_10_20": {str(n): min(n, len(eligible)) for n in (5, 10, 20)},
        "genuine_vector_price_symbol_alignment": True,
        "supported_preference_test": {
            "context": "TEST_ONLY_PREFERENCES_GENUINE_OBSERVATIONS_NO_ACCOUNT_WRITE",
            "broad_supported_matches": matched,
            "zero_budget_exclusions": excluded,
        },
        "prospective": workspace["prospective"],
        "acceptance": workspace["acceptance"],
        "experiments": experiments,
        "accepted_current_rankings": 0,
        "provider_requests_during_verification": 0,
        "market_prices_or_secrets_exported": False,
    }


if __name__ == "__main__":
    evidence = check(Path(".local-data/experimental-nse-v2"))
    output = Path("docs/development/ml-v2-observed-evidence.json")
    output.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: evidence[k]
                for k in (
                    "securities",
                    "current_observations",
                    "actual_model_scored_securities",
                    "top_5_10_20",
                    "accepted_current_rankings",
                )
            }
        )
    )
