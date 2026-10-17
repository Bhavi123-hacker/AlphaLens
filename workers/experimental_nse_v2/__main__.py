"""Explicit manual V2 commands. No automatic acquisition or task registration."""

import argparse
import json
from pathlib import Path

from .data import acquire, closed_current
from .pipeline import infer, train
from .workspace import read_workspace

parser = argparse.ArgumentParser()
parser.add_argument("operation", choices=("train", "infer", "status", "acquire", "capture", "run"))
parser.add_argument("--root", type=Path)
parser.add_argument("--config", type=Path)
parser.add_argument("--collect", action="store_true")
parser.add_argument("--scheduled", action="store_true")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--price-only", action="store_true")
parser.add_argument("--provider-root", type=Path)
parser.add_argument("--v1-root", type=Path)
args = parser.parse_args()
if args.operation == "run":
    from .workflow import configured, run

    if args.config is None:
        parser.error("explicit private --config is required")
    try:
        outcome = run(
            configured(args.config),
            collect=args.collect,
            scheduled=args.scheduled,
            dry_run=args.dry_run,
        )
        print(json.dumps(outcome, allow_nan=False))
        raise SystemExit(1 if outcome["state"] == "FAILED" else 0)
    except (OSError, ValueError):
        print('{"state":"FAILED","code":"V2_OPERATIONAL_CONFIGURATION_INVALID"}')
        raise SystemExit(1) from None
if args.root is None:
    parser.error("--root is required for this operation")
if args.operation in ("capture", "acquire") and args.provider_root is None:
    parser.error("explicit private --provider-root is required for bounded acquisition")
if args.operation == "acquire" and args.v1_root is None:
    parser.error("--v1-root is required for verified immutable base reuse")
if args.operation == "train":
    result = train(args.root, price_only=args.price_only)
elif args.operation == "capture":
    result = closed_current(args.root, args.provider_root)
elif args.operation == "acquire":
    result = acquire(args.root, args.v1_root, args.provider_root)
else:
    result = {"infer": infer, "status": read_workspace}[args.operation](args.root)
print(
    json.dumps(
        {
            k: result.get(k)
            for k in (
                "model_id",
                "selected_algorithm",
                "status",
                "forecast_write",
                "prospective",
                "dataset_id",
                "current_api_calls",
                "last_collection_api_calls",
                "collection_replayed",
                "collection_pending",
            )
        },
        allow_nan=False,
    )
)
