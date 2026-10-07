"""Checked local contributions from trusted fitted pipelines, never global importance."""

from datetime import datetime
from typing import Any

import numpy as np
from catboost import Pool
from scipy.special import expit
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits
from xgboost import DMatrix

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.explanation_contracts import (
    ExplanationPolicy,
    FeatureContribution,
    LocalAttribution,
)
from alphalens_decision.models import PredictionEvidence
from alphalens_evaluation.contracts import digest, disclaimer
from alphalens_features.models import FeatureDataset, FeatureRow


def verified_row(
    features: FeatureDataset, security: str, session: Any, cutoff: datetime
) -> FeatureRow | None:
    FeatureDataset.model_validate(features.model_dump())
    if features.feature_set_id != digest(
        features.model_dump(mode="json", exclude={"feature_set_id"})
    ):
        raise DataContractError("EXPLANATION_FEATURE_CHECKSUM_MISMATCH")
    rows = [r for r in features.rows if r.security_id == security and r.session_date == session]
    row = rows[0] if rows else None
    if row and row.knowledge_cutoff != cutoff:
        raise DataContractError("EXPLANATION_FEATURE_CUTOFF_MISMATCH")
    return row


def local_attribution(
    model: Pipeline,
    model_identity: dict[str, Any],
    prediction: PredictionEvidence,
    features: FeatureDataset,
    policy: ExplanationPolicy | None = None,
) -> LocalAttribution:
    """Caller supplies an in-memory fitted model from verified trusted local training.

    This API does not deserialize arbitrary files. The P9 identity and reproduced
    output must match. The fitted-evidence ID additionally pins learned statistics
    and the computed attribution; model run IDs alone are not model authentication.
    """
    policy = policy or ExplanationPolicy()
    prediction = PredictionEvidence.model_validate(prediction.model_dump())
    columns = tuple(model_identity.get("feature_order", ()))
    configuration = model_identity.get("configuration", {})
    row = verified_row(
        features, prediction.security_id, prediction.session_date, prediction.decision_time
    )
    if (
        row is None
        or digest(model_identity) != prediction.model_run_id
        or model_identity.get("evaluation_id") != prediction.evaluation_id
        or model_identity.get("model_family") != prediction.family
        or datetime.fromisoformat(model_identity["effective_training_cutoff"])
        != prediction.training_cutoff
        or configuration.get("task") != prediction.task
        or configuration.get("horizon") != prediction.horizon
        or not columns
        or len(columns) != len(set(columns))
        or not set(columns) <= set(row.values)
        or features.feature_set_id != prediction.feature_set_id
        or features.classification != prediction.classification
        or row.classification != prediction.classification
        or row.canonical_dataset_id != prediction.canonical_dataset_id
        or row.universe_snapshot_id != prediction.universe_snapshot_id
        or not row.analytical_eligible
        or tuple(model.named_steps)
        not in (("imputer", "estimator"), ("imputer", "scaler", "estimator"))
    ):
        raise DataContractError("LOCAL_ATTRIBUTION_PIT_LINEAGE_MISMATCH")
    raw = np.asarray(
        [[row.values[n].value if row.values[n].value is not None else np.nan for n in columns]],
        dtype="float64",
    )
    imputer = model.named_steps["imputer"]
    statistics = np.asarray(imputer.statistics_, dtype="float64")
    if statistics.shape != (len(columns),) or not np.isfinite(statistics).all():
        raise DataContractError("ATTRIBUTION_REMOVED_OR_UNAVAILABLE_FEATURE")
    estimator = model.named_steps["estimator"]
    family = prediction.family
    classifier = prediction.task == "classification"
    limitations = ["ASSOCIATION_NOT_CAUSATION", "TRUSTED_LOCAL_FITTED_MODEL_ONLY"]
    with threadpool_limits(limits=1):
        effective = imputer.transform(raw)
        transformed = model[:-1].transform(raw)
        prediction_value = (
            float(model.predict_proba(raw)[0, 1]) if classifier else float(model.predict(raw)[0])
        )
        if family in ("logistic", "ridge"):
            coefficients = np.asarray(estimator.coef_, dtype="float64").reshape(-1)
            contributions = coefficients * np.asarray(transformed).reshape(-1)
            base = float(np.asarray(estimator.intercept_).reshape(-1)[0])
            output = base + float(contributions.sum())
            method, space = "LINEAR_COEFFICIENT", "LOG_ODDS" if classifier else "RETURN"
            reference = np.asarray(model.named_steps["scaler"].mean_, dtype="float64")
            limitations.append("COEFFICIENT_TIMES_TRAIN_STANDARDIZED_VALUE_NOT_PROBABILITY_POINTS")
        elif family in ("lightgbm", "catboost", "xgboost"):
            if family == "lightgbm":
                values = estimator.booster_.predict(transformed, pred_contrib=True, num_threads=1)
                output = float(
                    estimator.booster_.predict(transformed, raw_score=True, num_threads=1)[0]
                )
            elif family == "catboost":
                native = estimator.model_
                values = native.get_feature_importance(
                    Pool(transformed), type="ShapValues", thread_count=1
                )
                output = float(
                    np.asarray(
                        native.predict(transformed, prediction_type="RawFormulaVal")
                    ).reshape(-1)[0]
                )
            else:
                booster = estimator.get_booster()
                matrix = DMatrix(transformed)
                values = booster.predict(
                    matrix, pred_contribs=True, approx_contribs=False, strict_shape=True
                )
                output = float(booster.predict(matrix, output_margin=True).reshape(-1)[0])
            values = np.asarray(values, dtype="float64").reshape(-1)
            if values.shape != (len(columns) + 1,):
                raise DataContractError("NATIVE_ATTRIBUTION_OUTPUT_SHAPE_UNSUPPORTED")
            contributions, base = values[:-1], float(values[-1])
            method, space = "NATIVE_TREE_SHAP", "LOG_ODDS" if classifier else "RETURN"
            reference = None
            limitations.append("NATIVE_TRAINING_TREE_REFERENCE_NOT_INTERVENTIONAL_OR_CAUSAL")
        elif family in ("random_forest", "hist_gradient_boosting"):
            # An additive, explicitly order-dependent path, not Shapley attribution.
            reference = statistics
            current = statistics.reshape(1, -1).copy()

            def value(x: Any) -> float:
                return (
                    float(model.predict_proba(x)[0, 1])
                    if classifier
                    else float(model.predict(x)[0])
                )

            base = previous = value(current)
            contributions = np.empty(len(columns), dtype="float64")
            for i in range(len(columns)):
                current[0, i] = raw[0, i]
                next_value = value(current)
                contributions[i] = next_value - previous
                previous = next_value
            output = previous
            method, space = "ORDERED_TRAIN_MEDIAN_PATH", "PROBABILITY" if classifier else "RETURN"
            limitations.extend(
                (
                    "ORDER_DEPENDENT_INTERACTIONS_ASSIGNED_TO_LATER_FEATURES",
                    "NOT_SHAP_OR_CAUSAL_COUNTERFACTUAL",
                    "TRAIN_MEDIAN_REFERENCE_MAY_BE_OFF_MANIFOLD",
                )
            )
        else:
            raise DataContractError("MODEL_LOCAL_ATTRIBUTION_UNSUPPORTED")
    expected = prediction.probability if classifier else prediction.prediction
    linked = float(expit(output)) if space == "LOG_ODDS" else output
    if (
        expected is None
        or not np.isclose(
            prediction_value, expected, atol=policy.numeric_tolerance, rtol=policy.numeric_tolerance
        )
        or not np.isclose(
            linked, prediction_value, atol=policy.numeric_tolerance, rtol=policy.numeric_tolerance
        )
    ):
        raise DataContractError("ATTRIBUTION_PREDICTION_REPLAY_MISMATCH")
    measured = tuple(
        FeatureContribution(
            feature_name=name,
            actual_value=row.values[name].value,
            effective_value=float(np.asarray(effective).reshape(-1)[i]),
            transformed_value=float(np.asarray(transformed).reshape(-1)[i]),
            training_reference=float(reference[i]) if reference is not None else None,
            contribution=float(contributions[i]),
            direction="POSITIVE"
            if contributions[i] > 0
            else "NEGATIVE"
            if contributions[i] < 0
            else "ZERO",
            raw_availability=row.values[name].state.value,
            imputed=row.values[name].value is None,
        )
        for i, name in enumerate(columns)
    )
    payload: dict[str, Any] = dict(
        policy=policy.model_dump(mode="json"),
        prediction=prediction.model_dump(mode="json"),
        feature_row_id=digest(row.model_dump(mode="json")),
        model_identity_json=stable_json(model_identity).decode("utf-8"),
        fitted_evidence_id=digest(
            dict(
                training_medians=statistics.tolist(),
                contributions=[c.model_dump(mode="json") for c in measured],
                base=base,
                output=output,
            )
        ),
        method=method,
        output_space=space,
        base_value=base,
        explained_output=output,
        prediction_value=expected,
        contributions=[c.model_dump(mode="json") for c in measured],
        limitations=tuple(sorted(limitations)),
        classification=prediction.classification.value,
        disclaimer=disclaimer(prediction.classification),
    )
    draft = LocalAttribution.model_construct(
        attribution_id="0" * 64,
        **dict(
            payload,
            policy=policy,
            prediction=prediction,
            contributions=measured,
            classification=prediction.classification,
        ),
    )
    content = draft.model_dump(mode="json", exclude={"attribution_id"})
    return LocalAttribution.model_validate(dict(attribution_id=digest(content), **content))
