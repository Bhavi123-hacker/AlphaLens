"""Replay approved P12/P11 TEST_ONLY evidence without creating fictitious entries."""

import argparse
from collections import Counter
from pathlib import Path

from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_decision.ranking_storage import load as load_rank
from alphalens_decision.risk_storage import load as load_risk
from alphalens_decision.signal_contracts import SignalPolicy, SignalSnapshot
from alphalens_decision.signal_storage import load, save
from alphalens_decision.signals import evaluate
from alphalens_evaluation.contracts import disclaimer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rankings", type=Path, required=True)
    parser.add_argument("--risks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rankings = [load_rank(p.parent) for p in args.rankings.glob("*/rank-manifest.json")]
    risks = tuple(load_risk(p.parent) for p in args.risks.glob("*/risk-manifest.json"))
    if not rankings or any(r.classification != Classification.TEST_ONLY for r in rankings):
        raise ValueError("Authored TEST_ONLY rankings required")
    snapshots: list[SignalSnapshot] = []
    for ranking in sorted(rankings, key=lambda r: (r.session_date, r.horizon)):
        for security in sorted(r.security_id for r in (*ranking.ranked, *ranking.excluded)):
            policy = SignalPolicy(horizon=ranking.horizon)
            first = evaluate(ranking, security, risks, policy, tuple(snapshots))
            if first != evaluate(ranking, security, risks, policy, tuple(snapshots)):
                raise ValueError("Signal replay mismatch")
            if load(save(first, args.output)) != first:
                raise ValueError("Signal artifact replay mismatch")
            snapshots.append(first)
    report = dict(
        classification="TEST_ONLY",
        disclaimer=disclaimer(Classification.TEST_ONLY),
        production_claims_permitted=False,
        deterministic_replay=True,
        snapshot_count=len(snapshots),
        horizons=[1, 5, 10, 20],
        states=dict(Counter(s.state for s in snapshots)),
        freshness=dict(Counter(s.data_freshness for s in snapshots)),
        signal_snapshot_ids=[s.signal_snapshot_id for s in snapshots],
        threshold_status="DEVELOPMENT_ASSUMPTION",
        position_contexts=0,
        test_only_state_demonstration=False,
        limitations=[
            "Insufficient model selection evidence blocks entry",
            "Unknown corporate-action coverage blocks entry",
            "No portfolio ownership or exits inferred",
        ],
    )
    publish(args.output / "signal-suite.TEST_ONLY.json", stable_json(report))
    print(stable_json(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
