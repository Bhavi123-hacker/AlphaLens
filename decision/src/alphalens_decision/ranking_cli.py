"""Developer historical rankings; no ENTRY/HOLD/EXIT or live recommendations."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.comparison import load_comparisons
from alphalens_decision.evidence import load_models
from alphalens_decision.ranking import RankingEngine
from alphalens_decision.ranking_contracts import RankingPolicy
from alphalens_decision.ranking_storage import load, save
from alphalens_decision.risk import RiskEngine
from alphalens_decision.risk_storage import load as load_risk
from alphalens_features.models import FeatureDataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P12 historical opportunity diagnostics, no signals"
    )
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--horizon", type=int, choices=[1, 5, 10, 20], required=True)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--evaluation", type=Path, action="append", default=[])
    parser.add_argument("--backtest", type=Path, action="append", default=[])
    parser.add_argument("--risk", type=Path, action="append")
    parser.add_argument("--history", type=Path, action="append", default=[])
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/ranking"))
    args = parser.parse_args(argv)
    try:
        envelope = json.loads(args.canonical.read_bytes())
        batch = verify_local_batch(
            CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
        )
        features = FeatureDataset.model_validate_json(args.features.read_bytes())
        policy = (
            RankingPolicy.model_validate_json(args.policy.read_bytes())
            if args.policy
            else RankingPolicy.model_validate(dict(horizon=args.horizon))
        )
        if policy.horizon != args.horizon:
            raise ValueError("CLI and policy horizons differ")
        engine = RankingEngine(
            RiskEngine(CanonicalReader(batch), features, load_models(args.evaluation)),
            load_comparisons(args.evaluation, args.backtest),
        )
        result = engine.evaluate(
            args.date,
            policy,
            tuple(load_risk(p) for p in args.risk) if args.risk is not None else None,
            tuple(load(p) for p in args.history),
        )
        top = result.top(args.top)
        directory = save(result, args.output)
        sys.stdout.buffer.write(
            stable_json(
                dict(
                    rank_snapshot_id=result.rank_snapshot_id,
                    classification=result.classification.value,
                    disclaimer=result.disclaimer,
                    production_claims_permitted=False,
                    horizon=result.horizon,
                    session=result.session_date.isoformat(),
                    model_selection_status=result.model_selection_status,
                    ranked_count=len(result.ranked),
                    top=[r.model_dump(mode="json") for r in top],
                    excluded=[r.model_dump(mode="json") for r in result.excluded],
                    output=str(directory),
                )
            )
            + b"\n"
        )
        return 0
    except (OSError, ValueError, KeyError, DataContractError):
        sys.stdout.buffer.write(
            stable_json(dict(status="REJECTED", reason="RANKING_EVIDENCE_INVALID")) + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
