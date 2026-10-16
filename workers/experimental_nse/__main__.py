"""Explicit manual private study operations. No market requests from dashboard reads."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .acquire import FAMILY, PERMISSION, capture, digest, encoded, initialize, replay, write_new


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("capture", "replay", "train", "infer", "refresh", "status", "reconcile")
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--provider-root", type=Path)
    parser.add_argument("--permission-reference")
    parser.add_argument("--retry-pending", action="store_true")
    parser.add_argument("--include-completed-today", action="store_true")
    args = parser.parse_args()
    root = args.root
    if args.command == "capture":
        if args.provider_root is None or args.permission_reference != PERMISSION:
            parser.error("Explicit private permission reference and shared provider root required")
        result = capture(root, args.provider_root, permission_reference=args.permission_reference)
        print(
            json.dumps(
                {
                    "dataset_id": result["dataset_id"],
                    "observations": len(result["rows"]),
                    "securities": len(result["manifest"]["instruments"]),
                    "replay_api_calls": result["replay_api_calls"],
                }
            )
        )
    elif args.command == "replay":
        result = replay(root)
        print(
            json.dumps(
                {
                    "dataset_id": result["dataset_id"],
                    "observations": len(result["rows"]),
                    "replay_api_calls": result["replay_api_calls"],
                }
            )
        )
    elif args.command == "train":
        from .models import load_model, save_model, score, train
        from .prospective import append_forecasts

        initialize(root)
        if (root / "latest.json").exists():
            parser.error("Existing experiment is immutable; use infer for score-only updates")
        dataset = replay(root)
        observed = datetime.fromisoformat(dataset["source_observed_at"])
        model, evaluation, _ = train(
            dataset["rows"], dataset["sessions"], dataset["dataset_id"], datetime.now(UTC)
        )
        run_id = uuid4().hex
        run = root / "runs" / run_id
        run.mkdir(parents=True)
        model_sha = save_model(run / "model.json", model)
        loaded = load_model(run / "model.json", model_sha)
        inference_at = datetime.now(UTC)
        scores = score(loaded, dataset["rows"], dataset["sessions"], inference_at, observed)
        source = dataset["manifest"]
        info = {
            "id": dataset["dataset_id"],
            "securities": len(source["instruments"]),
            "observations": len(dataset["rows"]),
            "start": dataset["sessions"][0],
            "end": dataset["sessions"][-1],
            "observed_session_dates": len(dataset["sessions"]),
            "source": source["source"],
            "source_observed_at": dataset["source_observed_at"],
            "permission_reference": source["permission_reference"],
            "price_basis": "UNKNOWN",
            "corporate_action_coverage": source["corporate_action_coverage"],
            "api_calls": source["api_calls"],
            "zero_request_replay": True,
            "calendar": "OBSERVED_COHORT_UNION_NOT_EXCHANGE_CERTIFIED_COMPLETE",
            "missing_cohort_slots": sum(
                len(dataset["sessions"]) - entry["observations"] for entry in source["instruments"]
            ),
            "exclusions": source["exclusions"],
            "limitations": evaluation["limitations"],
        }
        files = {"model": model_sha}
        for name, value in (("evaluation", evaluation), ("scores", scores), ("dataset", info)):
            body = encoded(value)
            write_new(run / (name + ".json"), body)
            files[name] = digest(body)
        forecasts = append_forecasts(
            root, model["model_id"], dataset["dataset_id"], scores, observed
        )
        receipt = {
            "family": FAMILY,
            "run_id": run_id,
            "files": files,
            "inference_at": inference_at.isoformat(),
            "forecasts": forecasts,
        }
        receipt_body = encoded(receipt)
        write_new(run / "receipt.json", receipt_body)
        temporary = root / ("latest-" + uuid4().hex + ".json")
        write_new(temporary, encoded({"run_id": run_id, "receipt_sha256": digest(receipt_body)}))
        os.replace(temporary, root / "latest.json")
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "model_id": model["model_id"],
                    "scores": len(scores),
                    "final": evaluation["evaluation"]["final"],
                    "forecasts": forecasts,
                },
                allow_nan=False,
            )
        )
    elif args.command == "infer":
        from .inference import infer

        print(json.dumps(infer(root)))
    elif args.command == "refresh":
        from .refresh import refresh

        if args.provider_root is None or args.permission_reference != PERMISSION:
            parser.error("Explicit private permission reference and shared provider root required")
        updated = refresh(
            root,
            args.provider_root,
            permission_reference=args.permission_reference,
            retry_pending=args.retry_pending,
            include_completed_today=args.include_completed_today,
        )
        print(
            json.dumps(
                {
                    "dataset_id": updated["dataset_id"],
                    "observations": len(updated["rows"]),
                    "latest": updated["sessions"][-1],
                    "state": updated["refresh_state"],
                }
            )
        )
    elif args.command == "reconcile":
        from .prospective import reconcile
        from .refresh import current_dataset

        dataset = current_dataset(root)
        print(
            json.dumps(
                reconcile(
                    root,
                    dataset["rows"],
                    dataset["sessions"],
                    datetime.fromisoformat(dataset["source_observed_at"]),
                )
            )
        )
    else:
        from .workspace import read_workspace

        data = read_workspace(root)
        print(
            json.dumps(
                {
                    "available": data["available"],
                    "scored": len(data["candidates"]),
                    "prospective": data["prospective"],
                }
            )
        )


if __name__ == "__main__":
    main()
