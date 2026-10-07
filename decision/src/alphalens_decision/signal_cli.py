"""Offline historical decision states, never orders or live recommendations."""

import argparse
import sys
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.ranking_storage import load as load_rank
from alphalens_decision.risk_storage import load as load_risk
from alphalens_decision.signal_contracts import PositionEvidence, SignalPolicy
from alphalens_decision.signal_storage import load, save
from alphalens_decision.signals import evaluate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["evaluate"])
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument("--risk", type=Path, action="append", default=[])
    parser.add_argument("--security", required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--history", type=Path, action="append", default=[])
    parser.add_argument("--position", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("data/signals"))
    args = parser.parse_args(argv)
    try:
        ranking = load_rank(args.ranking)
        policy = (
            SignalPolicy.model_validate_json(args.policy.read_bytes())
            if args.policy
            else SignalPolicy(horizon=ranking.horizon)
        )
        result = evaluate(
            ranking,
            args.security,
            tuple(load_risk(p) for p in args.risk),
            policy,
            tuple(load(p) for p in args.history),
            tuple(PositionEvidence.model_validate_json(p.read_bytes()) for p in args.position),
        )
        directory = save(result, args.output)
        sys.stdout.buffer.write(
            stable_json(dict(snapshot=result.model_dump(mode="json"), output=str(directory)))
            + b"\n"
        )
        return 0
    except (OSError, ValueError, KeyError, DataContractError):
        sys.stdout.buffer.write(
            stable_json(dict(status="REJECTED", reason="SIGNAL_EVIDENCE_INVALID")) + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
