"""Immutable local JSON/Parquet evidence. Checksums are integrity, not authentication."""

import io
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import skops.io as sio

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_evaluation.contracts import OOSPrediction, WalkForwardDefinition, digest
from alphalens_evaluation.engine import EvaluationResult
from alphalens_training.contracts import boundary

OOS_SCHEMA = pa.schema(
    [
        (
            name,
            pa.list_(pa.field("element", pa.string()))
            if name == "outcome_reason_codes"
            else pa.float64()
            if name in ("prediction", "probability", "actual_target")
            else pa.int32()
            if name == "horizon"
            else pa.bool_()
            if name == "production_claims_permitted"
            else pa.string(),
        )
        for name in OOSPrediction.model_fields
    ]
)


def parquet_bytes(rows: list[dict[str, Any]], schema: Any) -> bytes:
    stream = io.BytesIO()
    pq.write_table(
        pa.Table.from_pylist(rows, schema=schema),
        stream,
        compression="zstd",
        version="2.6",
        use_dictionary=False,
    )
    return stream.getvalue()


def save(result: EvaluationResult, root: Path) -> Path:
    directory = local_output(root) / str(result.manifest["evaluation_id"])
    common = {
        k: result.manifest[k]
        for k in (
            "evaluation_id",
            "data_classification",
            "disclaimer",
            "production_claims_permitted",
        )
    }
    files = {
        "fold-metrics.json": stable_json(dict(**common, folds=result.fold_metrics)),
        "model-comparison.json": stable_json(dict(**common, models=result.model_comparison)),
        "stability-report.json": stable_json(dict(**common, models=result.stability_report)),
        "negative-control-report.json": stable_json(
            dict(**common, **{k: v for k, v in result.negative_control.items() if k not in common})
        ),
        "oos-predictions.parquet": parquet_bytes(
            [r.model_dump(mode="json") for r in result.predictions], OOS_SCHEMA
        ),
    }
    for run_id, model in result.fold_models.items():
        # Stored only for engineering audit. No loader automatically trusts their types.
        files[f"models/{run_id}.skops"] = sio.dumps(model)
    checksums = {name: checksum(content) for name, content in files.items()}
    for name, content in files.items():
        path = directory / name
        if path.exists() and name.startswith("models/"):
            # Serialized bytes are not claimed deterministic; preserve first valid artifact.
            checksums[name] = checksum(path.read_bytes())
        else:
            publish(path, content)
    publish(
        directory / "walk-forward-manifest.json",
        stable_json(
            dict(
                **result.manifest,
                checksums=checksums,
                artifact_boundary="TRUSTED_LOCAL_ONLY_NO_ARBITRARY_TYPE_LOADING",
            )
        ),
    )
    return directory


@dataclass(frozen=True)
class OOSDataset:
    manifest: dict[str, Any]
    predictions: tuple[OOSPrediction, ...]

    def verify(self) -> WalkForwardDefinition:
        manifest = self.manifest
        identity = manifest["identity"]
        definition = WalkForwardDefinition.model_validate(identity["definition"])
        if (
            digest(identity) != manifest["evaluation_id"]
            or manifest["prediction_role"] != "FOLD_TEST"
            or manifest["data_classification"] != definition.data_classification.value
            or manifest["production_claims_permitted"] is not False
            or digest([r.model_dump(mode="json") for r in self.predictions])
            != manifest["oos_prediction_dataset_id"]
            or len(self.predictions) != manifest["prediction_count"]
        ):
            raise DataContractError("P9_OOS_MANIFEST_MISMATCH")
        keys = [(r.session_date, r.security_id, r.model_family) for r in self.predictions]
        if keys != sorted(set(keys)):
            raise DataContractError("P9_OOS_ORDER_OR_DUPLICATE")
        folds = {f.fold_id: f for f in definition.folds}
        for row in self.predictions:
            OOSPrediction.model_validate(row.model_dump())
            fold = folds.get(row.fold_id)
            model = manifest["fold_models"].get(row.model_run_id)
            if (
                fold is None
                or model is None
                or digest(model) != row.model_run_id
                or model["evaluation_id"] != manifest["evaluation_id"]
                or model["fold"] != fold.model_dump(mode="json")
                or model["model_family"] != row.model_family
                or model["training_supervised_dataset_id"]
                != definition.training_dataset_ids[row.fold_id]
                or datetime.fromisoformat(model["effective_training_cutoff"])
                != fold.training_cutoff - timedelta(seconds=definition.embargo_seconds)
                or not fold.test_start <= row.session_date <= fold.test_end
                or row.decision_time <= fold.training_cutoff
                or fold.training_cutoff >= boundary(fold.test_start)
                or row.evaluation_id != manifest["evaluation_id"]
                or row.feature_set_id != definition.feature_set_id
                or row.label_set_id != definition.label_set_id
                or row.supervised_dataset_id != definition.supervised_dataset_id
                or row.canonical_input_id != identity["canonical_input_id"]
                or row.task != definition.task
                or row.horizon != definition.horizon
                or row.model_family not in definition.model_families
                or row.classification != definition.data_classification
            ):
                raise DataContractError("P9_GENUINE_FOLD_TEST_REQUIRED")
        return definition


def load(root: Path) -> OOSDataset:
    root = local_output(root)
    manifest = json.loads((root / "walk-forward-manifest.json").read_bytes())
    for name, expected in manifest["checksums"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or checksum(path.read_bytes()) != expected:
            raise DataContractError("P9_ARTIFACT_CHECKSUM_OR_PATH_MISMATCH")
    table = pq.read_table(root / "oos-predictions.parquet")
    if table.schema != OOS_SCHEMA:
        raise DataContractError("P9_OOS_SCHEMA_MISMATCH")
    result = OOSDataset(manifest, tuple(OOSPrediction.model_validate(r) for r in table.to_pylist()))
    result.verify()
    return result
