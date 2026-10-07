"""Developer offline explanation cards; no model loading, network or LLM calls."""

import argparse
import sys
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.explanation_contracts import ExplanationPolicy, LocalAttribution
from alphalens_decision.explanation_storage import save
from alphalens_decision.explanations import explain
from alphalens_decision.ranking_storage import load as load_rank
from alphalens_decision.risk_storage import load as load_risk
from alphalens_decision.signal_storage import load as load_signal
from alphalens_features.models import FeatureDataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["explain"])
    parser.add_argument("--signal", type=Path, required=True)
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument("--risk", type=Path, action="append", default=[])
    parser.add_argument("--features", type=Path)
    parser.add_argument("--history", type=Path, action="append", default=[])
    parser.add_argument("--attribution", type=Path, action="append", default=[])
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/explanations"))
    args = parser.parse_args(argv)
    try:
        result = explain(
            load_signal(args.signal),
            load_rank(args.ranking),
            tuple(load_risk(p) for p in args.risk),
            FeatureDataset.model_validate_json(args.features.read_bytes())
            if args.features
            else None,
            tuple(load_signal(p) for p in args.history),
            tuple(LocalAttribution.model_validate_json(p.read_bytes()) for p in args.attribution),
            ExplanationPolicy.model_validate_json(args.policy.read_bytes())
            if args.policy
            else ExplanationPolicy(),
        )
        directory = save(result, args.output)
        sys.stdout.buffer.write(
            stable_json(
                dict(
                    snapshot=result.model_dump(mode="json"),
                    annotation=result.annotation().model_dump(mode="json"),
                    output=str(directory),
                )
            )
            + b"\n"
        )
        return 0
    except (OSError, ValueError, KeyError, DataContractError):
        sys.stdout.buffer.write(
            stable_json(dict(status="REJECTED", reason="EXPLANATION_EVIDENCE_INVALID")) + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
