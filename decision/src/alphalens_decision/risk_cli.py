"""Developer risk evidence; no actions, model fitting or live recommendation."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.evidence import load_models
from alphalens_decision.risk import RiskEngine
from alphalens_decision.risk_contracts import RiskPolicy
from alphalens_decision.risk_storage import save
from alphalens_features.models import FeatureDataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P11 historical risk evidence, no trading actions")
    parser.add_argument("command", choices=["evaluate"])
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--session", type=date.fromisoformat, required=True)
    parser.add_argument("--security", required=True)
    parser.add_argument("--horizon", type=int, choices=[1, 5, 10, 20], required=True)
    parser.add_argument("--evaluation", type=Path, action="append", default=[])
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/risk"))
    args = parser.parse_args(argv)
    try:
        envelope = json.loads(args.canonical.read_bytes())
        batch = verify_local_batch(
            CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
        )
        features = FeatureDataset.model_validate_json(args.features.read_bytes())
        policy = (
            RiskPolicy.model_validate_json(args.policy.read_bytes())
            if args.policy
            else RiskPolicy()
        )
        engine = RiskEngine(CanonicalReader(batch), features, load_models(args.evaluation))
        result = engine.evaluate(args.security, args.session, args.horizon, policy)
        directory = save(result, args.output)
        sys.stdout.buffer.write(
            stable_json(dict(**result.model_dump(mode="json"), output=str(directory))) + b"\n"
        )
        return 0
    except (OSError, ValueError, KeyError, DataContractError, ValidationError):
        sys.stdout.buffer.write(
            stable_json(dict(status="REJECTED", reason="RISK_EVIDENCE_INVALID")) + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
