"""Bounded P9 local model loading; unchanged reviewed P8 types, never automatic trust."""

from pathlib import Path

import skops.io as sio
from sklearn.pipeline import Pipeline

from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_decision.attribution import local_attribution
from alphalens_decision.explanation_contracts import ExplanationPolicy, LocalAttribution
from alphalens_decision.models import PredictionEvidence
from alphalens_evaluation.storage import load
from alphalens_features.models import FeatureDataset
from alphalens_training.artifacts import REVIEWED_TYPES


def from_p9(
    directory: Path,
    prediction: PredictionEvidence,
    features: FeatureDataset,
    policy: ExplanationPolicy | None = None,
) -> LocalAttribution:
    """Verify P9 checksum/schema/identity first, then a fixed reviewed type allowlist.

    Third-party boosted serialized types remain unsupported at this loader boundary.
    They can use native attribution with a trusted in-memory fitted pipeline. No
    prediction is refit, and scoring outcomes never contribute to the attribution.
    """
    directory = local_output(directory)
    oos = load(directory)
    identity = oos.manifest["fold_models"].get(prediction.model_run_id)
    if (
        identity is None
        or prediction.origin != "P9_FOLD_TEST"
        or oos.manifest["evaluation_id"] != prediction.evaluation_id
        or prediction.family not in {"logistic", "ridge", "random_forest", "hist_gradient_boosting"}
    ):
        raise DataContractError("P14_MODEL_ARTIFACT_UNSUPPORTED_OR_MISMATCHED")
    content = (directory / "models" / f"{prediction.model_run_id}.skops").read_bytes()
    if checksum(content) != oos.manifest["checksums"].get(
        f"models/{prediction.model_run_id}.skops"
    ):
        raise DataContractError("P14_MODEL_ARTIFACT_CHECKSUM_REQUIRED")
    reported = set(sio.get_untrusted_types(data=content))
    if not reported <= REVIEWED_TYPES:
        raise DataContractError("P14_UNREVIEWED_MODEL_TYPES")
    model = sio.loads(content, trusted=sorted(reported))
    if not isinstance(model, Pipeline):
        raise DataContractError("P14_FITTED_PIPELINE_REQUIRED")
    return local_attribution(model, identity, prediction, features, policy)
