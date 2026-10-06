"""Developer baseline training/evaluation on checksum-pinned P7 artifacts only."""

import argparse
from pathlib import Path

from pydantic import ValidationError

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.artifacts import LocalRegistry
from alphalens_training.contracts import TrainingConfig
from alphalens_training.engine import train


def train_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P8 development ML; no performance claims")
    parser.add_argument("command", choices=["baseline"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=Path("data/p8-models"))
    args = parser.parse_args(argv)
    try:
        data = SupervisedDataset.model_validate_json(args.input.read_bytes())
        config = TrainingConfig.model_validate_json(args.config.read_bytes())
        result = train(data, config)
        entry = LocalRegistry(args.registry).save(result)
        print(stable_json(result.report | {"artifact_checksums": entry.checksums}).decode())
        return 0
    except DataContractError as exc:
        print(stable_json(dict(status="REJECTED", reason=exc.code)).decode())
        return 2
    except (ValidationError, ValueError, KeyError, OSError):
        print(stable_json(dict(status="REJECTED", reason="BASELINE_TRAINING_FAILED")).decode())
        return 2


def model_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-evaluate a trusted locally created P8 model")
    parser.add_argument("command", choices=["evaluate"])
    parser.add_argument("model_run_id")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=Path("data/p8-models"))
    args = parser.parse_args(argv)
    try:
        data = SupervisedDataset.model_validate_json(args.input.read_bytes())
        report = LocalRegistry(args.registry).evaluate(args.model_run_id, data)
        print(stable_json(report).decode())
        return 0
    except DataContractError as exc:
        print(stable_json(dict(status="REJECTED", reason=exc.code)).decode())
        return 2
    except (ValidationError, ValueError, KeyError, OSError):
        print(stable_json(dict(status="REJECTED", reason="BASELINE_EVALUATION_FAILED")).decode())
        return 2
