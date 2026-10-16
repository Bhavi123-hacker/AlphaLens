"""Four fixed V2 experiments, expanding-date development and scalar JSON models.

All historical outcomes were potentially observed during V1 development. None of
these folds constitutes an untouched independent test or model acceptance.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from .features import (
    FAMILY,
    FEATURE_CONTRACTS,
    FEATURE_NAMES,
    FEATURE_VERSION,
    LOCAL_FEATURE_NAMES,
    LOCAL_FEATURE_VERSION,
    TARGET_VERSION,
    Sample,
    build,
)

ALGORITHMS = ("LOGISTIC", "RIDGE", "HIST_GRADIENT_BOOSTING", "RANDOM_FOREST")
SCHEMA = "alphalens.experimental.scalar-json.v2"
PARAMETERS: dict[str, dict[str, Any]] = {
    "LOGISTIC": {"C": 1.0, "class_weight": "balanced", "max_iter": 1000, "random_state": 42},
    "RIDGE": {"alpha": 10.0},
    "HIST_GRADIENT_BOOSTING": {
        "max_iter": 100,
        "max_depth": 3,
        "min_samples_leaf": 100,
        "l2_regularization": 10.0,
        "random_state": 42,
        "early_stopping": False,
    },
    "RANDOM_FOREST": {
        "n_estimators": 100,
        "max_depth": 4,
        "min_samples_leaf": 100,
        "random_state": 42,
        "n_jobs": 4,
        "max_features": 0.7,
    },
}


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("AWARE_V2_CLOCK_REQUIRED")
    return value.astimezone(UTC)


def _finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("FINITE_SCALAR_REQUIRED")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("FINITE_SCALAR_REQUIRED")
    return number


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value)) if value >= 0 else math.exp(value) / (1 + math.exp(value))


def validate_model(model: Mapping[str, Any]) -> None:
    fields = {
        "schema",
        "family",
        "feature_version",
        "target_version",
        "feature_names",
        "dataset_id",
        "protocol_id",
        "algorithm",
        "parameters",
        "trained_at",
        "training_last_session",
        "training_target_last_session",
        "payload",
        "model_id",
    }
    if set(model) != fields or (
        model.get("schema") != SCHEMA
        or model.get("family") != FAMILY
        or model.get("feature_version") not in FEATURE_CONTRACTS
        or model.get("target_version") != TARGET_VERSION
        or model.get("feature_names")
        != list(FEATURE_CONTRACTS.get(str(model.get("feature_version")), ()))
        or model.get("algorithm") not in ALGORITHMS
        or model.get("parameters") != PARAMETERS.get(str(model.get("algorithm")))
    ):
        raise ValueError("EXACT_CONSTRAINED_V2_MODEL_REQUIRED")
    _aware(datetime.fromisoformat(model["trained_at"]))
    body = {key: value for key, value in model.items() if key != "model_id"}
    if hashlib.sha256(_json(body)).hexdigest() != model["model_id"]:
        raise ValueError("V2_MODEL_CONTENT_HASH_MISMATCH")
    payload = model["payload"]
    if not isinstance(payload, dict):
        raise ValueError("SCALAR_MODEL_PAYLOAD_REQUIRED")
    if model["algorithm"] in ("LOGISTIC", "RIDGE"):
        if set(payload) != {"mean", "scale", "coefficients", "intercept", "return_scale"}:
            raise ValueError("LINEAR_PAYLOAD_SCHEMA_REQUIRED")
        for name in ("mean", "scale", "coefficients"):
            values = payload[name]
            if not isinstance(values, list) or len(values) != len(model["feature_names"]):
                raise ValueError("EXACT_ORDERED_FEATURE_COUNT_REQUIRED")
            for value in values:
                if name == "scale" and _finite(value) <= 0:
                    raise ValueError("POSITIVE_SCALER_REQUIRED")
                _finite(value)
        _finite(payload["intercept"])
        if _finite(payload["return_scale"]) <= 0:
            raise ValueError("POSITIVE_RETURN_SCALE_REQUIRED")
    else:
        if set(payload) != {"trees", "intercept"} or not isinstance(payload["trees"], list):
            raise ValueError("TREE_PAYLOAD_SCHEMA_REQUIRED")
        _finite(payload["intercept"])
        expected = PARAMETERS[str(model["algorithm"])][
            "n_estimators" if model["algorithm"] == "RANDOM_FOREST" else "max_iter"
        ]
        if len(payload["trees"]) != expected:
            raise ValueError("EXACT_TREE_COUNT_REQUIRED")
        for tree in payload["trees"]:
            if not isinstance(tree, list) or not 1 <= len(tree) <= 127:
                raise ValueError("BOUNDED_TREE_REQUIRED")
            for index, node in enumerate(tree):
                if not isinstance(node, list) or len(node) != 5:
                    raise ValueError("EXACT_TREE_NODE_SCHEMA_REQUIRED")
                feature, threshold, left, right, value = node
                _finite(threshold)
                _finite(value)
                if any(type(item) is not int for item in (feature, left, right)):
                    raise ValueError("INTEGER_ONLY_TREE_INDICES_REQUIRED")
                if feature == -1:
                    if left != -1 or right != -1:
                        raise ValueError("LEAF_WITHOUT_CHILDREN_REQUIRED")
                elif (
                    type(feature) is not int
                    or not 0 <= feature < len(model["feature_names"])
                    or type(left) is not int
                    or type(right) is not int
                    or not index < left < len(tree)
                    or not index < right < len(tree)
                ):
                    raise ValueError("FORWARD_ONLY_BOUNDED_TREE_REQUIRED")
                if model["algorithm"] == "RANDOM_FOREST" and not 0 <= value <= 1:
                    raise ValueError("FOREST_LEAF_PROBABILITY_REQUIRED")


def save_model(path: Path, model: Mapping[str, Any]) -> str:
    validate_model(model)
    payload = _json(dict(model))
    if path.suffix != ".json" or path.is_symlink():
        raise ValueError("PLAIN_JSON_MODEL_REQUIRED")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("IMMUTABLE_V2_MODEL_ALREADY_EXISTS")
    else:
        with path.open("xb") as handle:
            handle.write(payload)
    return hashlib.sha256(payload).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("DUPLICATE_MODEL_JSON_KEY")
        result[key] = value
    return result


def load_model(path: Path, expected_sha256: str) -> dict[str, Any]:
    if path.suffix != ".json" or path.is_symlink() or path.stat().st_size > 10_000_000:
        raise ValueError("PLAIN_BOUNDED_JSON_MODEL_REQUIRED")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("V2_ARTIFACT_CHECKSUM_MISMATCH")
    model: dict[str, Any] = json.loads(payload, object_pairs_hook=_pairs)
    validate_model(model)
    return model


def _predict(model: Mapping[str, Any], vector: Sequence[float]) -> tuple[float, list[float]]:
    if len(vector) != len(model["feature_names"]):
        raise ValueError("EXACT_ORDERED_V2_VECTOR_REQUIRED")
    values = [_finite(value) for value in vector]
    payload, algorithm = model["payload"], model["algorithm"]
    contributions: list[float] = []
    if algorithm in ("LOGISTIC", "RIDGE"):
        contributions = [
            (value - payload["mean"][index])
            / payload["scale"][index]
            * payload["coefficients"][index]
            for index, value in enumerate(values)
        ]
        margin = math.fsum(contributions) + payload["intercept"]
        if algorithm == "RIDGE":
            margin /= payload["return_scale"]
        return _sigmoid(margin), contributions
    tree_values = []
    for tree in payload["trees"]:
        index = 0
        for _ in range(len(tree)):
            feature, threshold, left, right, value = tree[index]
            if feature == -1:
                tree_values.append(value)
                break
            # sklearn forests perform float32 input conversion; histogram boosting uses float64.
            item = (
                float(np.float32(values[feature]))
                if algorithm == "RANDOM_FOREST"
                else values[feature]
            )
            index = left if item <= threshold else right
        else:
            raise ValueError("TREE_TRAVERSAL_FAILED")
    return (
        math.fsum(tree_values) / len(tree_values)
        if algorithm == "RANDOM_FOREST"
        else _sigmoid(payload["intercept"] + math.fsum(tree_values))
    ), contributions


def predict_vector(model: Mapping[str, Any], vector: Sequence[float]) -> tuple[float, list[float]]:
    validate_model(model)
    return _predict(model, vector)


def _fit(algorithm: str, samples: Sequence[Sample]) -> dict[str, Any]:
    x = np.asarray([item.vector for item in samples], dtype=np.float64)
    y = np.asarray([item.target for item in samples], dtype=int)
    returns = np.asarray([item.target_return for item in samples], dtype=float)
    if len(samples) < 100 or len(set(y.tolist())) != 2:
        raise ValueError("100_MATURED_TWO_CLASS_SAMPLES_REQUIRED")
    parameters = PARAMETERS[algorithm]
    with threadpool_limits(limits=4):
        if algorithm in ("LOGISTIC", "RIDGE"):
            scaler = StandardScaler().fit(x)
            transformed = scaler.transform(x)
            if algorithm == "LOGISTIC":
                estimator: Any = LogisticRegression(**parameters).fit(transformed, y)
                if int(estimator.n_iter_[0]) >= parameters["max_iter"]:
                    raise ValueError("LOGISTIC_CONVERGENCE_NOT_ESTABLISHED")
                coefficients, intercept = estimator.coef_[0], estimator.intercept_[0]
            else:
                estimator = Ridge(**parameters).fit(transformed, returns)
                coefficients, intercept = estimator.coef_, estimator.intercept_
            return {
                "mean": scaler.mean_.tolist(),
                "scale": scaler.scale_.tolist(),
                "coefficients": coefficients.tolist(),
                "intercept": float(intercept),
                "return_scale": max(float(np.std(returns)), 1e-12),
            }
        if algorithm == "RANDOM_FOREST":
            estimator = RandomForestClassifier(**parameters).fit(x, y)
            trees = []
            for fitted in estimator.estimators_:
                tree = fitted.tree_
                nodes = []
                for index in range(tree.node_count):
                    leaf = tree.children_left[index] == -1
                    values = tree.value[index][0]
                    nodes.append(
                        [
                            -1 if leaf else int(tree.feature[index]),
                            0.0 if leaf else float(tree.threshold[index]),
                            -1 if leaf else int(tree.children_left[index]),
                            -1 if leaf else int(tree.children_right[index]),
                            float(values[1] / sum(values)),
                        ]
                    )
                trees.append(nodes)
            return {"trees": trees, "intercept": 0.0}
        estimator = HistGradientBoostingClassifier(**parameters).fit(x, y)
        trees = []
        for predictors in estimator._predictors:
            nodes = []
            for item in predictors[0].nodes:
                if item["is_categorical"]:
                    raise ValueError("NUMERICAL_ONLY_HISTOGRAM_TREE_REQUIRED")
                leaf = bool(item["is_leaf"])
                nodes.append(
                    [
                        -1 if leaf else int(item["feature_idx"]),
                        0.0 if leaf else float(item["num_threshold"]),
                        -1 if leaf else int(item["left"]),
                        -1 if leaf else int(item["right"]),
                        float(item["value"]),
                    ]
                )
            trees.append(nodes)
        return {"trees": trees, "intercept": float(estimator._baseline_prediction[0, 0])}


def _artifact(
    algorithm: str,
    samples: Sequence[Sample],
    dataset_id: str,
    protocol_id: str,
    now: datetime,
    include_context: bool = True,
) -> dict[str, Any]:
    payload = _fit(algorithm, samples)
    completed_at = datetime.now(UTC)
    if now > completed_at:
        raise ValueError("MODEL_TRAINING_CLOCK_CANNOT_BE_FUTURE")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "family": FAMILY,
        "feature_version": FEATURE_VERSION if include_context else LOCAL_FEATURE_VERSION,
        "target_version": TARGET_VERSION,
        "feature_names": list(FEATURE_NAMES if include_context else LOCAL_FEATURE_NAMES),
        "dataset_id": dataset_id,
        "protocol_id": protocol_id,
        "algorithm": algorithm,
        "parameters": PARAMETERS[algorithm],
        "trained_at": completed_at.isoformat(),
        "training_last_session": max(item.session for item in samples),
        "training_target_last_session": max(str(item.target_session) for item in samples),
        "payload": payload,
    }
    result["model_id"] = hashlib.sha256(_json(result)).hexdigest()
    validate_model(result)
    return result


def metrics(samples: Sequence[Sample], scores: Sequence[float]) -> dict[str, Any]:
    y = np.asarray([item.target for item in samples], dtype=int)
    predicted = np.asarray(scores) >= 0.5
    if len(samples) != len(scores) or not samples:
        raise ValueError("NONEMPTY_ALIGNED_SAMPLES_REQUIRED")
    by_date: dict[str, list[int]] = {}
    for index, sample in enumerate(samples):
        by_date.setdefault(sample.session, []).append(index)
    correlations, spreads = [], []
    for indices in by_date.values():
        values = [scores[index] for index in indices]
        returns = [_finite(samples[index].target_return) for index in indices]
        if len(set(values)) > 1 and len(set(returns)) > 1:
            correlation = float(spearmanr(values, returns).statistic)
            if math.isfinite(correlation):
                correlations.append(correlation)
        ranked = sorted(indices, key=lambda index: (-scores[index], samples[index].key))
        width = max(1, len(ranked) // 5)
        spreads.append(
            math.fsum(_finite(samples[index].target_return) for index in ranked[:width]) / width
            - math.fsum(_finite(samples[index].target_return) for index in ranked[-width:]) / width
        )
    bins = []
    for bucket in range(5):
        indices = [index for index, value in enumerate(scores) if min(int(value * 5), 4) == bucket]
        if indices:
            bins.append(
                {
                    "count": len(indices),
                    "mean_score": float(np.mean(np.asarray(scores)[indices])),
                    "positive_fraction": float(np.mean(y[indices])),
                }
            )
    return {
        "sample_count": len(samples),
        "date_count": len(by_date),
        "security_count": len({item.key for item in samples}),
        "start": min(by_date),
        "end": max(by_date),
        "balanced_accuracy": float(
            np.mean([np.mean(predicted[y == label] == label) for label in sorted(set(y.tolist()))])
        ),
        "observed_classes": sorted(set(y.tolist())),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, scores)) if len(set(y.tolist())) == 2 else None,
        "brier_score": float(brier_score_loss(y, scores)),
        "mean_date_rank_ic": float(np.mean(correlations)) if correlations else None,
        "mean_date_top_minus_bottom_quintile_return": float(np.mean(spreads)),
        "calibration_bins": bins,
        "probability_calibration_established": False,
    }


def _uncertainty(
    samples: Sequence[Sample], scores: Sequence[float], baseline: Sequence[float]
) -> dict[str, Any]:
    """Moving blocks of 20 whole dates preserve cross-security/shared-date dependence."""
    days = sorted({item.session for item in samples})
    counts = np.zeros((len(days), 6), dtype=float)
    positions = {day: index for index, day in enumerate(days)}
    for sample, candidate, reference in zip(samples, scores, baseline, strict=True):
        label = int(sample.target)  # type: ignore[arg-type]
        row = counts[positions[sample.session]]
        row[label] += 1
        row[2 + label] += int(int(candidate >= 0.5) == label)
        row[4 + label] += int(int(reference >= 0.5) == label)
    rng = np.random.default_rng(42)
    differences = []
    rank_differences = []
    date_rank_difference = []
    grouped_indices: dict[str, list[int]] = {day: [] for day in days}
    for index, sample in enumerate(samples):
        grouped_indices[sample.session].append(index)
    for day in days:
        date_indices = grouped_indices[day]
        returns = [_finite(samples[index].target_return) for index in date_indices]
        correlations = []
        for values in (scores, baseline):
            items = [values[index] for index in date_indices]
            correlation = (
                float(spearmanr(items, returns).statistic)
                if len(set(items)) > 1 and len(set(returns)) > 1
                else 0.0
            )
            correlations.append(correlation)
        date_rank_difference.append(correlations[0] - correlations[1])
    rank_array = np.asarray(date_rank_difference)
    block = min(20, len(days))
    for _ in range(1000):
        indices = np.concatenate(
            [
                np.arange(start, start + block)
                for start in rng.integers(0, len(days) - block + 1, math.ceil(len(days) / block))
            ]
        )[: len(days)]
        total = counts[indices].sum(axis=0)
        if min(total[:2]) > 0:
            differences.append(float(((total[2:4] - total[4:6]) / total[:2]).mean()))
            rank_differences.append(float(rank_array[indices].mean()))
    alpha = 0.05 / (len(ALGORITHMS) * 3)
    return {
        "method": "MOVING_BLOCK_20_WHOLE_DATES_1000_SEED42",
        "draws": len(differences),
        "familywise_comparisons": len(ALGORITHMS) * 3,
        "improvement_95_percent_interval": np.quantile(differences, [0.025, 0.975]).tolist(),
        "bonferroni_familywise_interval": np.quantile(
            differences, [alpha / 2, 1 - alpha / 2]
        ).tolist(),
        "independent_confirmation": False,
        "rank_ic_improvement_95_percent_interval": np.quantile(
            rank_differences, [0.025, 0.975]
        ).tolist(),
        "rank_ic_improvement_bonferroni_familywise_interval": np.quantile(
            rank_differences, [alpha / 2, 1 - alpha / 2]
        ).tolist(),
        "constant_score_rank_ic_convention": 0.0,
    }


def sensitivity(samples: Sequence[Sample], scores: Sequence[float]) -> dict[str, Any]:
    """Nonoverlapping next-open/fifth-close price references, never actual fills."""
    by_day: dict[str, list[tuple[Sample, float]]] = {}
    for sample, value in zip(samples, scores, strict=True):
        by_day.setdefault(sample.session, []).append((sample, value))
    daily: dict[str, list[float]] = {"equal_cohort": []}
    memberships: dict[int, list[set[str]]] = {5: [], 10: [], 20: []}
    for day in sorted(by_day)[::5]:
        cohort = by_day[day]
        selections = {"equal_cohort": cohort}
        for count in (5, 10, 20):
            selections[f"top{count}"] = sorted(cohort, key=lambda item: (-item[1], item[0].key))[
                :count
            ]
            selections[f"momentum_top{count}"] = sorted(
                cohort, key=lambda item: (-item[0].vector[1], item[0].key)
            )[:count]
            selections[f"mean_reversion_top{count}"] = sorted(
                cohort, key=lambda item: (item[0].vector[1], item[0].key)
            )[:count]
            selections[f"low_volatility_top{count}"] = sorted(
                cohort, key=lambda item: (item[0].risk["return_daily_sd_20"], item[0].key)
            )[:count]
            memberships[count].append({item.key for item, _ in selections[f"top{count}"]})
        for name, items in selections.items():
            daily.setdefault(name, []).append(
                math.fsum(_finite(item.target_return) for item, _ in items) / len(items)
            )
    scenarios = []
    for name, returns in daily.items():
        for bps in (10, 25, 50, 100):
            for slippage in (0, 5, 10):
                net = [value - (bps + 2 * slippage) / 10000 for value in returns]
                equity, peak, drawdown = 1.0, 1.0, 0.0
                for value in net:
                    equity *= 1 + value
                    peak = max(peak, equity)
                    drawdown = min(drawdown, equity / peak - 1)
                sd = float(np.std(net))
                scenarios.append(
                    {
                        "selection": name,
                        "round_trip_cost_bps_assumption": bps,
                        "slippage_bps_each_side_assumption": slippage,
                        "observed_exposure_dates": len(net),
                        "gross_compounded_reference_return": math.prod(
                            1 + value for value in returns
                        )
                        - 1,
                        "compounded_reference_return": equity - 1,
                        "maximum_rebalance_endpoint_reference_drawdown": drawdown,
                        "annualized_reference_volatility_252_over_5_assumption": sd
                        * math.sqrt(252 / 5),
                        "reference_sharpe_zero_cash_252_over_5_assumption": float(np.mean(net))
                        / sd
                        * math.sqrt(252 / 5)
                        if sd
                        else None,
                    }
                )
    return {
        "classification": "HYPOTHETICAL_NEXT_OPEN_FIFTH_CLOSE_PRICE_REFERENCES_NOT_EXECUTED_PNL",
        "scenarios": scenarios,
        "mean_membership_turnover": {
            str(count): float(
                np.mean(
                    [
                        len(right - left) / len(right)
                        for left, right in zip(items, items[1:], strict=False)
                    ]
                )
            )
            if len(items) > 1
            else None
            for count, items in memberships.items()
        },
        "source_compatible_holding_price_component": True,
        "full_economic_compatibility_verified": False,
        "economic_edge_accepted": False,
        "limitations": [
            "No verified fills, capacity, actual tax schedule or dividend entitlements.",
            "Split/bonus adjustment source-confirmed; complete corporate actions unverified.",
            "Costs and slippage are declared assumptions, not actual broker charges.",
            "Drawdown measured at rebalance endpoints; within-holding path drawdown unavailable.",
        ],
    }


def train(
    rows: Sequence[Mapping[str, Any]],
    sessions: Sequence[str],
    dataset_id: str,
    protocol_id: str,
    decision_at: datetime,
    source_observed_at: datetime | None = None,
    excluded_sessions: Mapping[str, Iterable[str]] | None = None,
    audit_root: Path | None = None,
    include_context: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fixed four-candidate budget; every historical fold is development evidence."""
    now = _aware(decision_at)
    if not dataset_id or len(protocol_id) != 64:
        raise ValueError("VERSIONED_DATASET_AND_REGISTERED_PROTOCOL_HASH_REQUIRED")
    if source_observed_at is not None and _aware(source_observed_at) > now:
        raise ValueError("SOURCE_MUST_PRECEDE_TRAINING")
    dataset = build(rows, sessions, excluded_sessions, include_context=include_context)
    matured = [sample for sample in dataset.samples if sample.target is not None]
    if (
        not matured
        or max(str(sample.target_session) for sample in matured) >= now.date().isoformat()
    ):
        raise ValueError("PAST_MATURED_TARGETS_REQUIRED")
    folds = [
        ("2023", "2023-01-01", "2023-12-31"),
        ("2024", "2024-01-01", "2024-12-31"),
        ("2025", "2025-01-01", "2025-12-31"),
        ("2026_KNOWN_V1_PERIOD", "2026-01-01", "2026-12-31"),
    ]
    evaluations: dict[str, Any] = {}
    pooled: dict[str, list[float]] = {algorithm: [] for algorithm in ALGORITHMS}
    baseline_pooled: dict[str, list[float]] = {
        name: [] for name in ("majority", "momentum", "mean_reversion")
    }
    pooled_samples: list[Sample] = []
    for label, start, end in folds:
        evaluation = [sample for sample in matured if start <= sample.session <= end]
        if not evaluation:
            continue
        first = min(sample.session for sample in evaluation)
        prior = sorted(day for day in sessions if day < first)
        if len(prior) < 41:
            continue
        cutoff = prior[-21]  # 20-date embargo; target maturity separately purged by 20 dates
        target_cutoff = prior[-41]
        training = [
            sample
            for sample in matured
            if str(sample.target_session) < target_cutoff and sample.session < cutoff
        ]
        if len(training) < 100:
            continue
        baselines = {
            "majority": [sum(_finite(item.target) for item in training) / len(training)]
            * len(evaluation),
            "momentum": [_sigmoid(item.vector[1] / 0.05) for item in evaluation],
            "mean_reversion": [_sigmoid(-item.vector[1] / 0.05) for item in evaluation],
        }
        entry: dict[str, Any] = {
            "classification": "RETROSPECTIVE_DEVELOPMENT_NOT_UNTOUCHED_TEST",
            "training_last_decision": max(item.session for item in training),
            "training_last_target": max(str(item.target_session) for item in training),
            "evaluation_first_decision": first,
            "models": {},
            "model_artifacts": {},
            "baselines": {name: metrics(evaluation, values) for name, values in baselines.items()},
        }
        pooled_samples.extend(evaluation)
        for name, values in baselines.items():
            baseline_pooled[name].extend(values)
        for algorithm in ALGORITHMS:
            model_path = audit_root / f"{label}-{algorithm}.json" if audit_root else None
            if model_path is not None and model_path.exists():
                model = load_model(model_path, model_path.with_suffix(".sha256").read_text())
                if (
                    model["dataset_id"] != dataset_id
                    or model["protocol_id"] != protocol_id
                    or model["algorithm"] != algorithm
                    or model["feature_version"]
                    != (FEATURE_VERSION if include_context else LOCAL_FEATURE_VERSION)
                    or model["training_last_session"] != max(item.session for item in training)
                    or model["training_target_last_session"]
                    != max(str(item.target_session) for item in training)
                ):
                    raise ValueError("V2_FIT_RESUME_LINEAGE_MISMATCH")
            else:
                model = _artifact(
                    algorithm, training, dataset_id, protocol_id, now, include_context
                )
                if model_path is not None:
                    model_path.parent.mkdir(parents=True, exist_ok=True)
                    checksum = save_model(model_path, model)
                    model_path.with_suffix(".sha256").write_text(checksum)
            entry["model_artifacts"][algorithm] = model["model_id"]
            scores = [_predict(model, sample.vector)[0] for sample in evaluation]
            pooled[algorithm].extend(scores)
            entry["models"][algorithm] = metrics(evaluation, scores)
        evaluations[label] = entry
    if not {"2023", "2024", "2025"}.issubset(evaluations):
        raise ValueError("AT_LEAST_THREE_PREDECLARED_EXPANDING_YEAR_FOLDS_REQUIRED")
    summary = {algorithm: metrics(pooled_samples, values) for algorithm, values in pooled.items()}
    selected = max(
        ALGORITHMS,
        key=lambda algorithm: (
            sum(
                (
                    entry["models"][algorithm]["mean_date_rank_ic"]
                    if entry["models"][algorithm]["mean_date_rank_ic"] is not None
                    else -1.0
                )
                for label, entry in evaluations.items()
                if label != "2026_KNOWN_V1_PERIOD"
            )
            / sum(label != "2026_KNOWN_V1_PERIOD" for label in evaluations)
        ),
    )
    report: dict[str, Any] = {
        "family": FAMILY,
        "protocol_id": protocol_id,
        "dataset_id": dataset_id,
        "feature_version": FEATURE_VERSION if include_context else LOCAL_FEATURE_VERSION,
        "feature_names": list(FEATURE_NAMES if include_context else LOCAL_FEATURE_NAMES),
        "target_version": TARGET_VERSION,
        "historical_folds": evaluations,
        "selection_rule": (
            "MAXIMUM_MEAN_2023_2025_FOLD_DATE_RANK_IC_FIXED_ORDER_TIES_2026_DIAGNOSTIC_ONLY"
        ),
        "selection_is_independent_evidence": False,
        "parameter_search_budget": 4,
        "actual_fit_count": len(evaluations) * 4 + 1,
        "selected_algorithm": selected,
        "candidate_summary": summary,
        "baseline_summary": {
            name: metrics(pooled_samples, values) for name, values in baseline_pooled.items()
        },
        "uncertainty": {
            algorithm: {
                name: _uncertainty(pooled_samples, values, baseline)
                for name, baseline in baseline_pooled.items()
            }
            for algorithm, values in pooled.items()
        },
        "hypothetical_economic_sensitivity": sensitivity(pooled_samples, pooled[selected]),
        "independent_acceptance": False,
        "accepted_current_rankings": 0,
        "evidence_conclusion": "NO_DEMONSTRATED_EDGE",
        "future_independent_confirmation_required": True,
        "purge_max_horizon_observed_dates": 20,
        "embargo_observed_dates": 20,
        "secondary_horizons": {},
    }
    report["feature_audit"] = _feature_audit(
        matured, FEATURE_NAMES if include_context else LOCAL_FEATURE_NAMES
    )
    report["selected_stability"] = _stability(pooled_samples, pooled[selected])
    for horizon in (10, 20):
        secondary = build(rows, sessions, excluded_sessions, horizon, include_context)
        eligible = [sample for sample in secondary.samples if sample.target is not None]
        report["secondary_horizons"][str(horizon)] = {
            "matured_sample_count": len(eligible),
            "model_selection_used": False,
            "target": f"NEXT_OPEN_TO_SESSION_{horizon}_CLOSE_SPLIT_BONUS_ADJUSTED_PRICE_RETURN",
        }
    final_path = audit_root / "selected-refit.json" if audit_root else None
    if final_path is not None and final_path.exists():
        final_model = load_model(final_path, final_path.with_suffix(".sha256").read_text())
        if (
            final_model["dataset_id"] != dataset_id
            or final_model["protocol_id"] != protocol_id
            or final_model["algorithm"] != selected
            or final_model["feature_version"]
            != (FEATURE_VERSION if include_context else LOCAL_FEATURE_VERSION)
        ):
            raise ValueError("V2_SELECTED_REFIT_LINEAGE_MISMATCH")
    else:
        final_model = _artifact(selected, matured, dataset_id, protocol_id, now, include_context)
        if final_path is not None:
            checksum = save_model(final_path, final_model)
            final_path.with_suffix(".sha256").write_text(checksum)
    report["model_id"] = final_model["model_id"]
    return final_model, report


def _feature_audit(samples: Sequence[Sample], names: Sequence[str]) -> dict[str, Any]:
    """Descriptive development diagnostics never feed feature/model selection."""
    x = np.asarray([sample.vector for sample in samples])
    deviations = np.std(x, axis=0)
    nonconstant = deviations > 0
    correlations = np.zeros((len(names), len(names)))
    if int(nonconstant.sum()) > 1:
        correlations[np.ix_(nonconstant, nonconstant)] = np.corrcoef(
            x[:, nonconstant], rowvar=False
        )
    redundant = [
        {
            "left": names[left],
            "right": names[right],
            "absolute_correlation": abs(float(correlations[left, right])),
        }
        for left in range(len(names))
        for right in range(left + 1, len(names))
        if abs(correlations[left, right]) >= 0.95
    ]
    return {
        "complete_finite_vectors": len(samples),
        "missing_values_imputed": 0,
        "constant_features": [name for name, sd in zip(names, deviations, strict=True) if sd == 0],
        "absolute_correlation_over_095": redundant,
        "selection_used": False,
        "by_year_mean_and_sd": {
            year: {
                "mean": x[[sample.session.startswith(year) for sample in samples]]
                .mean(axis=0)
                .tolist(),
                "sd": x[[sample.session.startswith(year) for sample in samples]]
                .std(axis=0)
                .tolist(),
            }
            for year in sorted({sample.session[:4] for sample in samples})
        },
    }


def _stability(samples: Sequence[Sample], scores: Sequence[float]) -> dict[str, Any]:
    groups: dict[str, list[int]] = {}
    for index, sample in enumerate(samples):
        quarter = sample.session[:4] + "Q" + str((int(sample.session[5:7]) - 1) // 3 + 1)
        # Regime is based exclusively on contemporaneously observed fixed-cohort momentum.
        regime_value = sample.vector[17] if len(sample.vector) == 20 else sample.vector[2]
        regime_scope = "COHORT" if len(sample.vector) == 20 else "SINGLE_SECURITY"
        regime = regime_scope + ("_UPTREND" if regime_value > 0 else "_NONPOSITIVE_TREND")
        for group in (quarter, "security:" + sample.key, regime):
            groups.setdefault(group, []).append(index)
    return {
        name: metrics([samples[index] for index in indices], [scores[index] for index in indices])
        for name, indices in groups.items()
    }


def score(
    model: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    sessions: Sequence[str],
    decision_at: datetime,
    source_observed_at: datetime,
    entry_open_at: datetime,
    entry_session: str,
    excluded_sessions: Mapping[str, Iterable[str]] | None = None,
    completed_session_end: datetime | None = None,
    require_future_entry: bool = True,
) -> list[dict[str, Any]]:
    """Actual live forecast; the independently evidenced entry must still be future.

    The caller supplies the independently verified next-session open, never a
    weekday guess. Historical published EOD values cannot become executable closes.
    """
    validate_model(model)
    decision = _aware(decision_at)
    observed = _aware(source_observed_at)
    entry = _aware(entry_open_at)
    if not 0 <= (datetime.now(UTC) - decision).total_seconds() <= 30:
        raise ValueError("LIVE_NONBACKDATED_V2_DECISION_REQUIRED")
    if observed > decision or _aware(datetime.fromisoformat(model["trained_at"])) > decision:
        raise ValueError("SOURCE_AND_MODEL_MUST_PRECEDE_V2_DECISION")
    timing_eligible = entry > decision
    if (require_future_entry and not timing_eligible) or entry.astimezone(
        ZoneInfo("Asia/Kolkata")
    ).date().isoformat() != entry_session:
        raise ValueError("INDEPENDENT_FUTURE_ENTRY_OPEN_REQUIRED")
    latest = sessions[-1] if sessions else ""
    local_day = decision.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    same_day_complete = (
        latest == local_day
        and completed_session_end is not None
        and _aware(completed_session_end) < observed
        and completed_session_end.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat() == latest
    )
    if (
        not latest
        or latest >= entry_session
        or latest > local_day
        or (latest == local_day and not same_day_complete)
    ):
        raise ValueError("COMPLETED_PRIOR_OBSERVATION_BEFORE_FUTURE_ENTRY_REQUIRED")
    if (decision.date() - datetime.fromisoformat(latest).date()).days > 7:
        raise ValueError("V2_CURRENT_OBSERVATIONS_STALE")
    include_context = model["feature_version"] == FEATURE_VERSION
    dataset = build(rows, sessions, excluded_sessions, include_context=include_context)
    training_labels = [
        sample.target
        for sample in dataset.samples
        if sample.target is not None
        and str(sample.target_session) <= model["training_target_last_session"]
        and sample.session <= model["training_last_session"]
    ]
    if not training_labels:
        raise ValueError("ORIGINAL_TRAINING_LABELS_REQUIRED_FOR_BASELINE")
    majority = sum(training_labels) / len(training_labels)
    results = []
    for sample in dataset.samples:
        if sample.session != latest:
            continue
        value, contributions = _predict(model, sample.vector)
        reasons = sorted(
            [
                {
                    "feature": name,
                    "observed_value": observed_value,
                    "linear_contribution": contribution,
                }
                for name, observed_value, contribution in zip(
                    FEATURE_NAMES, sample.vector, contributions, strict=False
                )
            ],
            key=lambda item: abs(_finite(item["linear_contribution"])),
            reverse=True,
        )
        results.append(
            {
                "key": sample.key,
                "symbol": sample.symbol,
                "session": sample.session,
                "observed_price": sample.price,
                "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
                "source_observed_at": observed.isoformat(),
                "inference_at": decision.isoformat(),
                "entry_session": entry_session,
                "entry_open_at": entry.isoformat(),
                "model_id": model["model_id"],
                "dataset_id": model["dataset_id"],
                "protocol_id": model["protocol_id"],
                "feature_version": FEATURE_VERSION if include_context else LOCAL_FEATURE_VERSION,
                "target_version": TARGET_VERSION,
                "horizon_observed_sessions": 5,
                "score": value,
                "baseline_majority_score": majority,
                "baseline_momentum_score": _sigmoid(sample.vector[1] / 0.05),
                "baseline_mean_reversion_score": _sigmoid(-sample.vector[1] / 0.05),
                "baseline_risk_score": 1 / (1 + sample.vector[4]),
                "score_label": (
                    "MONOTONIC_TRANSFORM_UNCALIBRATED_RETURN_SCORE"
                    if model["algorithm"] == "RIDGE"
                    else "UNCALIBRATED_CLASSIFIER_MODEL_SCORE"
                ),
                "algorithm": model["algorithm"],
                "calibration_status": "NOT_ESTABLISHED",
                "features": list(sample.vector),
                "vector": list(sample.vector),
                "feature_names": list(FEATURE_NAMES if include_context else LOCAL_FEATURE_NAMES),
                "feature_hash": hashlib.sha256(_json(list(sample.vector))).hexdigest(),
                "feature_contributions": reasons,
                "risk": sample.risk,
                "classification": (
                    "BACKTESTED_NOT_PROSPECTIVELY_ACCEPTED"
                    if timing_eligible
                    else "TIMING_INELIGIBLE_RESEARCH_SCORES"
                ),
                "eligible_for_prospective": timing_eligible,
                "accepted_prediction": False,
                "missing_evidence": [
                    "Genuinely future matured outcomes and independent review",
                    "Complete corporate-action and historical point-in-time availability evidence",
                    "Verified executable fills and actual cost/capacity evidence",
                ],
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), str(item["key"])))
