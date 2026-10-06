"""Replay historical TEST_ONLY opportunity snapshots; no fitting or investment claim."""

import argparse
import json
from collections import Counter
from pathlib import Path

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_decision.comparison import load_comparisons
from alphalens_decision.evidence import load_models
from alphalens_decision.ranking import RankingEngine
from alphalens_decision.ranking_contracts import RankingPolicy, RankSnapshot
from alphalens_decision.ranking_storage import load, save
from alphalens_decision.risk import RiskEngine
from alphalens_decision.risk_storage import load as load_risk
from alphalens_evaluation.contracts import disclaimer
from alphalens_features.models import FeatureDataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--evaluations", type=Path, required=True)
    parser.add_argument("--risks", type=Path, required=True)
    parser.add_argument("--backtests", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    envelope = json.loads((args.inputs / "canonical/canonical-input.json").read_bytes())
    batch = verify_local_batch(
        CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
    )
    if batch.classification != Classification.TEST_ONLY:
        raise ValueError("This replay accepts authored TEST_ONLY inputs only")
    features = FeatureDataset.model_validate_json((args.inputs / "features.json").read_bytes())
    evaluations = sorted(p.parent for p in args.evaluations.glob("*/walk-forward-manifest.json"))
    models = load_models(evaluations)
    if models is None:
        raise ValueError("Verified P9 predictions required")
    backtests = []
    if args.backtests:
        for path in sorted(args.backtests.glob("*/backtest-manifest.json")):
            manifest = json.loads(path.read_bytes())
            if manifest["identity"]["definition"]["baseline"] == "MODEL":
                backtests.append(path.parent)
    comparisons = load_comparisons(evaluations, backtests)
    risks = tuple(load_risk(p.parent) for p in sorted(args.risks.glob("*/risk-manifest.json")))
    engine = RankingEngine(RiskEngine(CanonicalReader(batch), features, models), comparisons)
    snapshots: list[RankSnapshot] = []
    for session in sorted({p.session_date for p in models.predictions}):
        for horizon in (1, 5, 10, 20):
            policy = RankingPolicy.model_validate(dict(horizon=horizon))
            history = tuple(snapshots)
            first = engine.evaluate(session, policy, risks, history)
            if first != engine.evaluate(session, policy, risks, history):
                raise ValueError("Ranking replay mismatch")
            directory = save(first, args.output)
            if load(directory) != first or first.top(5) != first.ranked[:5]:
                raise ValueError("Ranking artifact/presentation mismatch")
            snapshots.append(first)
    report = dict(
        classification="TEST_ONLY",
        disclaimer=disclaimer(Classification.TEST_ONLY),
        production_claims_permitted=False,
        deterministic_replay=True,
        snapshot_count=len(snapshots),
        horizons=[1, 5, 10, 20],
        ranked_count=sum(len(s.ranked) for s in snapshots),
        excluded_count=sum(len(s.excluded) for s in snapshots),
        exclusion_reasons=dict(
            Counter(reason for s in snapshots for r in s.excluded for reason in r.reasons)
        ),
        model_selection_status=dict(Counter(s.model_selection_status for s in snapshots)),
        insufficient_selection_evidence=True,
        real_market_winner=None,
        configured_classifier="logistic",
        configured_regressor="ridge",
        feature_set_id=features.feature_set_id,
        canonical_input_id=batch.input_id,
        risk_snapshot_ids=sorted({r for s in snapshots for r in s.risk_snapshot_ids}),
        rank_snapshot_ids=[s.rank_snapshot_id for s in snapshots],
        verified_economic_inputs=len(comparisons.economics),
        visible_economic_inputs=sum(
            len(row["economics"]) for s in snapshots for row in s.model_comparison.values()
        ),
        limitations=[
            "Constructed fixtures only",
            "Insufficient model selection/calibration evidence",
            "Corporate-action and benchmark coverage not established",
        ],
    )
    publish(args.output / "ranking-suite.TEST_ONLY.json", stable_json(report))
    print(stable_json(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
