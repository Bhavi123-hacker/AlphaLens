"""Bounded subprocess inspection of one trusted frozen XGBoost artifact, no predictions."""

import argparse
import json
import multiprocessing
import os
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from alphalens_data.daily.providers import BASELINE
from alphalens_data.normalization import checksum
from workers.daily.compatibility import REPORT_SHA256
from workers.daily.inference import verify_model

MODEL_SHA256 = "e418c80ae33c8f41ba48900e312bedaffd34705d0cab1437dde93a3acaebbc03"
SCOPED_TYPES = {"xgboost.core.Booster", "xgboost.sklearn.XGBClassifier"}


def inspect(root: Path) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=probe, args=(root, writer))
    try:
        process.start()
        writer.close()
        if not reader.poll(45):
            raise ValueError
        result = reader.recv()
        process.join(2)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, OSError, EOFError):
        return {
            "state": "BLOCKED",
            "reason": "TRUSTED_MODEL_INSPECTION_FAILED",
            "predictions_generated": 0,
        }
    finally:
        if process.is_alive():
            process.terminate()  # Only this owned diagnostic child, never a shared worker.
            process.join(2)
        reader.close()
        writer.close()


def probe(root: Path, writer: Connection) -> None:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    try:
        writer.send(child(root))
    except Exception:
        writer.send(None)
    finally:
        writer.close()


def child(root: Path) -> dict[str, Any]:
    import skops.io as sio

    from alphalens_training.artifacts import REVIEWED_TYPES

    report_bytes = (root / "2026-results.json").read_bytes()
    if checksum(report_bytes) != REPORT_SHA256:
        raise ValueError("FROZEN_REPORT_MISMATCH")
    reports = [r for r in json.loads(report_bytes)["reports"] if r["horizon"] == 10]
    if len(reports) != 1 or reports[0]["model_sha256"] != MODEL_SHA256:
        raise ValueError("FIXED_XGBOOST_ARTIFACT_REQUIRED")
    path = verify_model(root / "p9", reports[0], BASELINE)
    if path.stat().st_size > 128000000:
        raise ValueError("MODEL_SIZE_LIMIT")
    types = set(sio.get_untrusted_types(file=path))
    if types - REVIEWED_TYPES != SCOPED_TYPES:
        raise ValueError("SCOPED_ARTIFACT_TYPES_MISMATCH")
    model = sio.load(path, trusted=sorted(REVIEWED_TYPES | SCOPED_TYPES))
    estimator = model.steps[-1][1]
    if (
        type(estimator).__module__ + "." + type(estimator).__name__
        != "xgboost.sklearn.XGBClassifier"
    ):
        raise ValueError("ESTIMATOR_TYPE_MISMATCH")
    config = json.loads(estimator.get_booster().save_config())
    return {
        "state": "TRUSTED_LOCAL_DESERIALIZATION_VERIFIED",
        "model_sha256": MODEL_SHA256,
        "scoped_types": sorted(SCOPED_TYPES),
        "n_features_after_stored_preprocessing": int(estimator.n_features_in_),
        "native_xgboost_config_version": config["version"],
        "predictions_generated": 0,
        "artifact_changed": checksum(path.read_bytes()) != MODEL_SHA256,
        "global_type_allowlist_changed": False,
        "model_acceptance": "NOT_PASSED",
        "current_inference": "UNAVAILABLE",
        "scope": "TRUSTED_SUBPROCESS_DIAGNOSTIC_NOT_A_SECURITY_SANDBOX",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.root)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
