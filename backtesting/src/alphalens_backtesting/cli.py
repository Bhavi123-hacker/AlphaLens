"""Developer hypothetical replay; inputs are genuine P9 OOS and trusted P5/P6 evidence."""

import argparse
import json
import sys
from pathlib import Path

from alphalens_backtesting.contracts import BacktestDefinition, ExecutionCalendar
from alphalens_backtesting.engine import run
from alphalens_backtesting.evidence import ExecutionEvidence
from alphalens_backtesting.storage import save
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.storage import stable_json
from alphalens_evaluation.storage import load
from alphalens_features.models import FeatureDataset


def main() -> int:
    parser = argparse.ArgumentParser(description="P10 hypothetical backtest, never trading advice")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    batch = CanonicalBatch.model_validate(json.loads(args.canonical.read_bytes())["batch"])
    evidence = ExecutionEvidence(
        CanonicalReader(batch),
        FeatureDataset.model_validate_json(args.features.read_bytes()),
        ExecutionCalendar.model_validate_json(args.calendar.read_bytes()),
    )
    result = run(
        load(args.oos),
        evidence,
        BacktestDefinition.model_validate_json(args.definition.read_bytes()),
    )
    path = save(result, args.output)
    sys.stdout.buffer.write(stable_json(result.summary | {"output": str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
