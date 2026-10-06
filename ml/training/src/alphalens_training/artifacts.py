"""Checksum-pinned local registry. No pickle/joblib or arbitrary automatic type trust."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import skops.io as sio
from pydantic import AwareDatetime
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from alphalens_data.contracts import Contract
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.contracts import TrainingConfig
from alphalens_training.engine import TrainingResult, environment, run_identity
from alphalens_training.metrics import classification_metrics, regression_metrics
from alphalens_training.split import split

# Reviewed scikit-learn 1.7 built-in histogram structures only; never accept a
# type merely because get_untrusted_types reports it or a manifest requests it.
REVIEWED_TYPES = frozenset(
    {
        "numpy.dtype",
        "sklearn.ensemble._hist_gradient_boosting.binning._BinMapper",
        "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor",
        "sklearn._loss.loss.HalfBinomialLoss",
        "sklearn._loss.loss.HalfSquaredError",
        "sklearn._loss._loss.CyHalfBinomialLoss",
        "sklearn._loss._loss.CyHalfSquaredError",
        "sklearn._loss.link.LogitLink",
        "sklearn._loss.link.IdentityLink",
        "sklearn._loss.link.Interval",
    }
)


class RegistryEntry(Contract):
    schema_version: Literal["p8.registry.v1"] = "p8.registry.v1"
    model_run_id: Hash
    model_family: str
    task: Literal["classification", "regression"]
    horizon: Literal[1, 5, 10, 20]
    status: Literal["TEST_ONLY", "VALIDATED_BASELINE"]
    classification: Literal["TEST_ONLY", "RESEARCH_FIXTURE"]
    feature_set_id: Hash
    label_set_id: Hash
    supervised_dataset_id: Hash
    training_cutoff: AwareDatetime
    validation_start: str
    validation_end: str
    artifact_path: str
    checksums: dict[str, Hash]
    metrics: dict[str, Any]
    created_at: AwareDatetime
    code_model_version: Literal["p8.baseline.v1"] = "p8.baseline.v1"
    production_claims_permitted: Literal[False] = False


class LocalRegistry:
    """Root is private ignored local storage; entries/artifacts are immutable.

    Checksums detect corruption, not authenticity. Only use artifacts created by
    this local installation. There is no remote upload, plugin or untrusted load API.
    """

    def __init__(self, root: Path):
        self.root = local_output(root)

    def entry(self, run_id: str) -> RegistryEntry:
        if len(run_id) != 64 or any(c not in "0123456789abcdef" for c in run_id):
            raise DataContractError("INVALID_MODEL_RUN_ID")
        record = RegistryEntry.model_validate_json(
            (self.root / "registry" / f"{run_id}.json").read_bytes()
        )
        if record.model_run_id != run_id or (
            record.classification == "TEST_ONLY" and record.status != "TEST_ONLY"
        ):
            raise DataContractError("REGISTRY_CLASSIFICATION_OR_ID_MISMATCH")
        return record

    def verify(self, run_id: str) -> tuple[RegistryEntry, dict[str, Any], dict[str, Any], bytes]:
        entry = self.entry(run_id)
        expected_path = f"artifacts/{run_id}"
        if entry.artifact_path != expected_path:
            raise DataContractError("REGISTRY_ARTIFACT_PATH_MISMATCH")
        base = self.root / expected_path
        if not base.resolve().is_relative_to(self.root):
            raise DataContractError("ARTIFACT_PATH_ESCAPES_REGISTRY")
        required = {"model.skops", "manifest.json", "evaluation.json"}
        if set(entry.checksums) != required:
            raise DataContractError("ARTIFACT_CHECKSUM_CONTRACT_MISMATCH")
        payloads = {name: (base / name).read_bytes() for name in sorted(required)}
        if any(checksum(payload) != entry.checksums[name] for name, payload in payloads.items()):
            raise DataContractError("ARTIFACT_CHECKSUM_MISMATCH")
        manifest, report = (json.loads(payloads[n]) for n in ("manifest.json", "evaluation.json"))
        identity = manifest["identity"]
        if (
            checksum(stable_json(identity)) != run_id
            or manifest["model_run_id"] != run_id
            or report["model_run_id"] != run_id
            or manifest["classification"] != entry.classification
            or manifest["status"] != entry.status
            or report["data_classification"] != entry.classification
            or identity["data_classification"] != entry.classification
            or identity["feature_set_id"] != entry.feature_set_id
            or identity["label_set_id"] != entry.label_set_id
            or identity["supervised_dataset_id"] != entry.supervised_dataset_id
            or report["metrics"] != entry.metrics
            or manifest["production_claims_permitted"] is not False
            or report["production_claims_permitted"] is not False
        ):
            raise DataContractError("ARTIFACT_MANIFEST_IDENTITY_MISMATCH")
        return entry, manifest, report, payloads["model.skops"]

    def save(self, result: TrainingResult) -> RegistryEntry:
        run_id = result.manifest["model_run_id"]
        if (self.root / "registry" / f"{run_id}.json").exists():
            entry, manifest, report, _ = self.verify(run_id)
            if manifest != json.loads(stable_json(result.manifest)) or report != json.loads(
                stable_json(result.report)
            ):
                raise DataContractError("IMMUTABLE_RUN_BEHAVIOR_CONFLICT")
            return entry
        identity = result.manifest["identity"]
        if checksum(stable_json(identity)) != run_id:
            raise DataContractError("MODEL_RUN_ID_MISMATCH")
        config = TrainingConfig.model_validate(identity["configuration"])
        status = (
            "TEST_ONLY"
            if identity["data_classification"] == Classification.TEST_ONLY
            else "VALIDATED_BASELINE"
        )
        base = self.root / "artifacts" / run_id
        payloads = {
            "model.skops": sio.dumps(result.model),
            "manifest.json": stable_json(result.manifest),
            "evaluation.json": stable_json(result.report),
        }
        unknown = set(sio.get_untrusted_types(data=payloads["model.skops"]))
        if not unknown <= REVIEWED_TYPES:
            raise DataContractError("UNREVIEWED_ARTIFACT_TYPES")
        for name, payload in payloads.items():
            # Serialization zip timestamps may differ on replay. Preserve first
            # completed artifact and require a registry record for reuse above.
            publish(base / name, payload)
        entry = RegistryEntry(
            model_run_id=run_id,
            model_family=config.model_family,
            task=config.task,
            horizon=config.horizon,
            status=status,
            classification=identity["data_classification"],
            feature_set_id=identity["feature_set_id"],
            label_set_id=identity["label_set_id"],
            supervised_dataset_id=identity["supervised_dataset_id"],
            training_cutoff=config.training_cutoff,
            validation_start=str(config.validation_start),
            validation_end=str(config.validation_end),
            artifact_path=f"artifacts/{run_id}",
            checksums={name: checksum(payload) for name, payload in payloads.items()},
            metrics=result.report["metrics"],
            created_at=datetime.now(UTC),
        )
        publish(
            self.root / "registry" / f"{run_id}.json", stable_json(entry.model_dump(mode="json"))
        )
        self.verify(run_id)
        return entry

    def load(self, run_id: str) -> tuple[Pipeline, dict[str, Any], dict[str, Any]]:
        _, manifest, report, payload = self.verify(run_id)
        if manifest["identity"]["environment"] != environment():
            raise DataContractError("ARTIFACT_ENVIRONMENT_MISMATCH")
        unknown = set(sio.get_untrusted_types(data=payload))
        if not unknown <= REVIEWED_TYPES:
            raise DataContractError("UNREVIEWED_ARTIFACT_TYPES")
        model = sio.loads(payload, trusted=sorted(REVIEWED_TYPES))
        if not isinstance(model, Pipeline):
            raise DataContractError("EXPECTED_TRAINED_PIPELINE")
        return model, manifest, report

    def evaluate(self, run_id: str, data: SupervisedDataset) -> dict[str, Any]:
        model, manifest, report = self.load(run_id)
        config = TrainingConfig.model_validate(manifest["identity"]["configuration"])
        holdout = split(data, config)
        if stable_json(run_identity(data, config, model)) != stable_json(manifest["identity"]):
            raise DataContractError("EVALUATION_REQUIRES_EXACT_PINNED_DATASET")
        if list(holdout.feature_columns) != manifest["feature_order"]:
            raise DataContractError("ARTIFACT_FEATURE_ORDER_MISMATCH")
        with threadpool_limits(limits=1):
            prediction = np.asarray(model.predict(holdout.x_validation), dtype="float64")
            if config.task == "classification":
                probability = np.asarray(
                    model.predict_proba(holdout.x_validation)[:, 1], dtype="float64"
                )
                metrics = classification_metrics(
                    holdout.y_validation, probability, config, prediction
                )
            else:
                metrics = regression_metrics(holdout.y_validation, prediction)
        if metrics != report["metrics"]:
            raise DataContractError("SERIALIZED_MODEL_BEHAVIOR_MISMATCH")
        return report
