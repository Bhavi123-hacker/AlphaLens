"""New, isolated chronological logistic pilot and constrained JSON inference.

No frozen model is loaded, no accepted ranking is written, and no broker or alert
module is called. A numerical output remains uncalibrated experimental research.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

from .features import (
    FAMILY,
    FEATURE_NAMES,
    FEATURE_VERSION,
    HORIZON,
    TARGET_VERSION,
    Sample,
    build,
)

CLASSIFICATION = "EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED"
MODEL_SCHEMA = "alphalens.experimental.logistic-json.v1"
MODEL_FIELDS = {
    "schema",
    "family",
    "feature_version",
    "target_version",
    "feature_names",
    "dataset_id",
    "trained_at",
    "training_last_session",
    "training_target_last_session",
    "algorithm",
    "parameters",
    "mean",
    "scale",
    "coefficients",
    "intercept",
    "model_id",
}


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("AWARE_EXPERIMENT_CLOCK_REQUIRED")
    return value.astimezone(UTC)


def _float(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("FINITE_NUMERIC_MODEL_VALUE_REQUIRED")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("FINITE_NUMERIC_MODEL_VALUE_REQUIRED")
    return result


def validate_model(model: Mapping[str, Any]) -> None:
    if set(model) != MODEL_FIELDS:
        raise ValueError("EXACT_CONSTRAINED_MODEL_SCHEMA_REQUIRED")
    if (
        model["schema"] != MODEL_SCHEMA
        or model["family"] != FAMILY
        or model["feature_version"] != FEATURE_VERSION
        or model["target_version"] != TARGET_VERSION
        or model["feature_names"] != list(FEATURE_NAMES)
        or model["algorithm"] != "STANDARD_SCALER_LOGISTIC_REGRESSION"
        or model["parameters"]
        != {"C": 1.0, "class_weight": "balanced", "max_iter": 1000, "random_state": 42}
    ):
        raise ValueError("EXACT_EXPERIMENTAL_CONTRACT_REQUIRED")
    for field in ("mean", "scale", "coefficients"):
        values = model[field]
        if not isinstance(values, list) or len(values) != len(FEATURE_NAMES):
            raise ValueError("EXACT_MODEL_FEATURE_COUNT_REQUIRED")
        for value in values:
            if field == "scale" and _float(value) <= 0:
                raise ValueError("POSITIVE_SCALER_REQUIRED")
            _float(value)
    _float(model["intercept"])
    _aware(datetime.fromisoformat(model["trained_at"]))
    body = {key: value for key, value in model.items() if key != "model_id"}
    if model["model_id"] != hashlib.sha256(_json(body)).hexdigest():
        raise ValueError("MODEL_ID_CHECKSUM_MISMATCH")


def save_model(path: Path, model: Mapping[str, Any]) -> str:
    """Append-only JSON artifact; equal bytes replay, changed bytes never overwrite."""
    validate_model(model)
    payload = _json(dict(model))
    if path.suffix != ".json" or path.is_symlink():
        raise ValueError("PLAIN_LOCAL_JSON_MODEL_REQUIRED")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("IMMUTABLE_MODEL_ALREADY_EXISTS")
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
    """Only checksum-pinned finite scalar JSON; no pickle/skops or executable types."""
    if path.suffix != ".json" or path.is_symlink() or path.stat().st_size > 1_000_000:
        raise ValueError("PLAIN_BOUNDED_JSON_MODEL_REQUIRED")
    payload = path.read_bytes()
    if len(expected_sha256) != 64 or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("MODEL_ARTIFACT_CHECKSUM_MISMATCH")
    model: dict[str, Any] = json.loads(payload, object_pairs_hook=_pairs)
    validate_model(model)
    return model


def predict_vector(model: Mapping[str, Any], vector: Sequence[float]) -> tuple[float, list[float]]:
    validate_model(model)
    if len(vector) != len(FEATURE_NAMES):
        raise ValueError("EXACT_ORDERED_FEATURE_VECTOR_REQUIRED")
    contribution = [
        (_float(value) - model["mean"][index])
        / model["scale"][index]
        * model["coefficients"][index]
        for index, value in enumerate(vector)
    ]
    margin = math.fsum(contribution) + model["intercept"]
    if not math.isfinite(margin):
        raise ValueError("NONFINITE_MODEL_MARGIN")
    probability = (
        1 / (1 + math.exp(-margin)) if margin >= 0 else math.exp(margin) / (1 + math.exp(margin))
    )
    return probability, contribution


def _metrics(samples: Sequence[Sample], scores: Sequence[float]) -> dict[str, Any]:
    y = [int(sample.target) for sample in samples if sample.target is not None]
    if len(y) != len(samples) or len(scores) != len(samples) or not y:
        raise ValueError("MATURED_ALIGNED_EVALUATION_REQUIRED")
    predictions = [int(value >= 0.5) for value in scores]
    rank: float | None = None
    if len(set(scores)) > 1 and len({sample.target_return for sample in samples}) > 1:
        from scipy.stats import spearmanr

        correlation = float(
            spearmanr(scores, [sample.target_return for sample in samples]).statistic
        )
        rank = correlation if math.isfinite(correlation) else None
    calibration = []
    for index in range(5):
        indices = [i for i, value in enumerate(scores) if min(int(value * 5), 4) == index]
        if indices:
            calibration.append(
                {
                    "score_lower": index / 5,
                    "score_upper": (index + 1) / 5,
                    "count": len(indices),
                    "mean_score": math.fsum(scores[i] for i in indices) / len(indices),
                    "observed_positive_fraction": sum(y[i] for i in indices) / len(indices),
                }
            )
    return {
        "sample_count": len(y),
        "security_count": len({sample.key for sample in samples}),
        "date_count": len({sample.session for sample in samples}),
        "start": min(sample.session for sample in samples),
        "end": max(sample.session for sample in samples),
        "positive_fraction": sum(y) / len(y),
        "balanced_accuracy": math.fsum(
            sum(
                truth == label and prediction == label
                for truth, prediction in zip(y, predictions, strict=True)
            )
            / y.count(label)
            for label in sorted(set(y))
        )
        / len(set(y)),
        "observed_target_classes": sorted(set(y)),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(y, scores)),
        "rank_correlation_to_future_open_close_movement": rank,
        "calibration_bins": calibration,
        "probability_calibration_established": False,
    }


def _bootstrap(
    samples: Sequence[Sample], candidate: Sequence[float], baseline: Sequence[float]
) -> dict[str, Any]:
    """Resample whole date clusters, preserving same-date cross-security dependence."""
    dates: dict[str, list[int]] = {}
    for index, sample in enumerate(samples):
        dates.setdefault(sample.session, []).append(index)
    clusters = list(dates.values())
    rng = np.random.default_rng(42)
    changes = []
    for _ in range(300):
        indices = [
            index
            for draw in rng.integers(0, len(clusters), len(clusters))
            for index in clusters[draw]
        ]
        y = [samples[index].target for index in indices]
        if len(set(y)) < 2:
            continue
        candidate_y = [int(candidate[index] >= 0.5) for index in indices]
        baseline_y = [int(baseline[index] >= 0.5) for index in indices]
        changes.append(
            float(balanced_accuracy_score(y, candidate_y) - balanced_accuracy_score(y, baseline_y))
        )
    return {
        "method": "WHOLE_DATE_CLUSTER_BOOTSTRAP_300_SEED42",
        "draws": len(changes),
        "balanced_accuracy_improvement_95_percent_interval": (
            [float(value) for value in np.quantile(changes, [0.025, 0.975])] if changes else None
        ),
        "limitation": (
            "Date clusters do not remove serial dependence or selection/survivorship bias."
        ),
    }


def _sensitivity(samples: Sequence[Sample], scores: Sequence[float]) -> dict[str, Any]:
    """Hypothetical daily-exposure arithmetic, deliberately not a tradable backtest."""
    dates = sorted({sample.session for sample in samples})
    by_date: dict[str, list[tuple[Sample, float]]] = {}
    for sample, value in zip(samples, scores, strict=True):
        by_date.setdefault(sample.session, []).append((sample, value))
    memberships = []
    for day in dates:
        cohort = sorted(by_date[day], key=lambda item: (-item[1], item[0].key))
        memberships.append({sample.key for sample, _ in cohort[:5]})
    changes = [
        len(right - left) / max(1, len(right))
        for left, right in zip(memberships, memberships[1:], strict=False)
    ]
    scenarios = []
    for cost_bps in (0, 10, 25, 50):
        movements = []
        # Nonoverlapping five-slot decision cohorts; each path assumes new daily exposure.
        for day in dates[::HORIZON]:
            cohort = sorted(by_date[day], key=lambda item: (-item[1], item[0].key))[:5]
            paths = [sample.target_path for sample, _ in cohort]
            if paths:
                for step in range(HORIZON):
                    movements.append(
                        math.fsum(path[step] for path in paths) / len(paths) - cost_bps / 10_000
                    )
        equity, peak, drawdown = 1.0, 1.0, 0.0
        for movement in movements:
            equity *= 1 + movement
            peak = max(peak, equity)
            drawdown = min(drawdown, equity / peak - 1)
        scenarios.append(
            {
                "assumed_round_trip_bps_each_daily_exposure": cost_bps,
                "daily_exposure_count": len(movements),
                "compounded_open_close_movement_after_assumed_cost": equity - 1,
                "drawdown_of_hypothetical_daily_exposures": drawdown,
            }
        )
    return {
        "classification": "DESCRIPTIVE_HYPOTHETICAL_DAILY_EXPOSURES_NOT_EXECUTABLE_PNL",
        "mean_top5_membership_turnover": math.fsum(changes) / len(changes) if changes else None,
        "cost_scenarios": scenarios,
        "limitations": [
            "Target concerns independent daily open-close movements; overnight return is excluded.",
            "No verified fills, slippage, taxes, capacity, action entitlement or cash ledger.",
            "Counterfactual daily exposure at observed opens/closes is not an execution claim.",
        ],
    }


def score(
    model: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    sessions: Sequence[str],
    decision_at: datetime,
    source_observed_at: datetime,
    completed_session_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Score only the latest complete cohort observation using a live nonbackdated clock."""
    validate_model(model)
    decision, observed = _aware(decision_at), _aware(source_observed_at)
    now = datetime.now(UTC)
    if not 0 <= (now - decision).total_seconds() <= 30:
        raise ValueError("LIVE_NONBACKDATED_INFERENCE_CLOCK_REQUIRED")
    trained = _aware(datetime.fromisoformat(model["trained_at"]))
    if observed > decision or trained > decision:
        raise ValueError("INPUT_AND_MODEL_MUST_PRECEDE_DECISION")
    latest = sessions[-1] if sessions else ""
    today = decision.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    same_day_completed = (
        latest == today
        and completed_session_end is not None
        and _aware(completed_session_end) < observed
        and completed_session_end.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat() == latest
    )
    if not latest or latest > today or (latest == today and not same_day_completed):
        raise ValueError("COMPLETED_PRIOR_SESSION_REQUIRED")
    if (decision.date() - datetime.fromisoformat(latest).date()).days > 7:
        raise ValueError("CURRENT_EXPERIMENTAL_OBSERVATIONS_STALE")
    dataset = build(rows, sessions)
    training_targets = [
        sample.target
        for sample in dataset.samples
        if sample.target is not None
        and sample.session <= model["training_last_session"]
        and str(sample.target_session) <= model["training_target_last_session"]
    ]
    if not training_targets:
        raise ValueError("ORIGINAL_TRAINING_LABELS_REQUIRED_FOR_BASELINE_COMPARISON")
    majority_baseline = sum(training_targets) / len(training_targets)
    results = []
    for sample in dataset.samples:
        if sample.session != latest:
            continue
        value, contributions = predict_vector(model, sample.vector)
        reasons = sorted(
            (
                {
                    "feature": name,
                    "log_odds_contribution": contribution,
                    "observed_value": observed_value,
                }
                for name, contribution, observed_value in zip(
                    FEATURE_NAMES, contributions, sample.vector, strict=True
                )
            ),
            key=lambda item: abs(_float(item["log_odds_contribution"])),
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
                "model_id": model["model_id"],
                "dataset_id": model["dataset_id"],
                "feature_version": FEATURE_VERSION,
                "target_version": TARGET_VERSION,
                "horizon_observed_sessions": HORIZON,
                "score": value,
                "baseline_majority_score": majority_baseline,
                "baseline_momentum_score": float(sample.vector[2] > 0),
                "score_label": "UNCALIBRATED_LOGISTIC_MODEL_SCORE",
                "feature_names": list(FEATURE_NAMES),
                "features": list(sample.vector),
                "vector": list(sample.vector),
                "feature_hash": hashlib.sha256(_json(list(sample.vector))).hexdigest(),
                "feature_contributions": reasons,
                "risk": sample.risk,
                "classification": CLASSIFICATION,
                "accepted_prediction": False,
                "missing_evidence": [
                    "Independent model acceptance and prospective matured evidence",
                    "Historical PIT identity, adjustment metadata and complete action coverage",
                    "Exchange-certified complete historical session calendar",
                ],
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), str(item["key"])))


def train(
    rows: Sequence[Mapping[str, Any]],
    sessions: Sequence[str],
    dataset_id: str,
    decision_at: datetime,
    source_observed_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """One predeclared fit, shared-date 60/20/20 split, five-slot purge and embargo."""
    decision = _aware(decision_at)
    if not dataset_id or (source_observed_at is not None and _aware(source_observed_at) > decision):
        raise ValueError("DATED_VERSIONED_SOURCE_REQUIRED")
    dataset = build(rows, sessions)
    if sessions[-1] >= decision.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat():
        raise ValueError("FUTURE_OR_UNCOMPLETED_DATASET_SESSION")
    matured = [sample for sample in dataset.samples if sample.target is not None]
    dates = sorted({sample.session for sample in matured})
    if len(dates) < 100:
        raise ValueError("AT_LEAST_100_MATURED_DECISION_DATES_REQUIRED")
    first, second = int(len(dates) * 0.6), int(len(dates) * 0.8)
    periods = {
        "train": dates[: first - HORIZON],
        "validation": dates[first + HORIZON : second - HORIZON],
        "final": dates[second + HORIZON :],
    }
    selected = {
        period: [sample for sample in matured if sample.session in set(period_dates)]
        for period, period_dates in periods.items()
    }
    if any(not samples for samples in selected.values()):
        raise ValueError("NONEMPTY_CHRONOLOGICAL_SPLITS_REQUIRED")
    training = selected["train"]
    training_targets = [int(sample.target) for sample in training if sample.target is not None]
    if len(set(training_targets)) < 2 or len(training_targets) < 40:
        raise ValueError("TWO_CLASSES_AND_40_TRAINING_EXAMPLES_REQUIRED")
    if max(str(sample.target_session) for sample in training) >= periods["validation"][0]:
        raise ValueError("TRAIN_TARGET_CROSSES_VALIDATION_BOUNDARY")
    if max(str(sample.target_session) for sample in selected["validation"]) >= periods["final"][0]:
        raise ValueError("VALIDATION_TARGET_CROSSES_FINAL_BOUNDARY")
    scaler = StandardScaler()
    train_x = scaler.fit_transform(
        np.asarray([sample.vector for sample in training], dtype=np.float64)
    )
    estimator = LogisticRegression(C=1.0, class_weight="balanced", random_state=42, max_iter=1000)
    estimator.fit(train_x, training_targets)
    if int(estimator.n_iter_[0]) >= 1000:
        raise ValueError("EXPERIMENTAL_LOGISTIC_DID_NOT_CONVERGE")
    model: dict[str, Any] = {
        "schema": MODEL_SCHEMA,
        "family": FAMILY,
        "feature_version": FEATURE_VERSION,
        "target_version": TARGET_VERSION,
        "feature_names": list(FEATURE_NAMES),
        "dataset_id": dataset_id,
        "trained_at": decision.isoformat(),
        "training_last_session": max(sample.session for sample in training),
        "training_target_last_session": max(str(sample.target_session) for sample in training),
        "algorithm": "STANDARD_SCALER_LOGISTIC_REGRESSION",
        "parameters": {"C": 1.0, "class_weight": "balanced", "max_iter": 1000, "random_state": 42},
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coefficients": estimator.coef_[0].tolist(),
        "intercept": float(estimator.intercept_[0]),
    }
    model["model_id"] = hashlib.sha256(_json(model)).hexdigest()
    validate_model(model)
    majority_score = sum(training_targets) / len(training_targets)
    evaluations: dict[str, Any] = {}
    for period in ("validation", "final"):
        samples = selected[period]
        candidate = [predict_vector(model, sample.vector)[0] for sample in samples]
        majority = [majority_score] * len(samples)
        momentum = [float(sample.vector[2] > 0) for sample in samples]
        by_time = {}
        for quarter in sorted(
            {
                sample.session[:4] + "Q" + str((int(sample.session[5:7]) - 1) // 3 + 1)
                for sample in samples
            }
        ):
            indices = [
                index
                for index, sample in enumerate(samples)
                if sample.session[:4] + "Q" + str((int(sample.session[5:7]) - 1) // 3 + 1)
                == quarter
            ]
            by_time[quarter] = _metrics(
                [samples[index] for index in indices], [candidate[index] for index in indices]
            )
        evaluations[period] = {
            "candidate": _metrics(samples, candidate),
            "baseline_train_majority": _metrics(samples, majority),
            "baseline_trailing5_open_close_direction": _metrics(samples, momentum),
            "candidate_by_quarter": by_time,
            "candidate_minus_momentum_uncertainty": _bootstrap(samples, candidate, momentum),
            "candidate_minus_majority_uncertainty": _bootstrap(samples, candidate, majority),
            "descriptive_sensitivity": _sensitivity(samples, candidate),
        }
    final = evaluations["final"]
    report: dict[str, Any] = {
        "family": FAMILY,
        "classification": CLASSIFICATION,
        "dataset_id": dataset_id,
        "model_id": model["model_id"],
        "feature_version": FEATURE_VERSION,
        "feature_names": list(FEATURE_NAMES),
        "target_version": TARGET_VERSION,
        "horizon_observed_sessions": HORIZON,
        "target_description": (
            "Compound next five independent daily open-close movements; "
            "not shareholder return or tradable profit."
        ),
        "methodology": (
            "Fixed current cohort, final-vintage retrospective; shared-date60/20/20; "
            "purge5 and embargo5; train-only scaling; no hyperparameter tuning."
        ),
        "historical_point_in_time": False,
        "complete_official_calendar": False,
        "action_or_adjustment_metadata_verified": False,
        "feature_scale_invariance": (
            "Same-session ratios only; no overnight raw-price or cross-date volume features."
        ),
        "observation_count": dataset.observation_count,
        "security_count": dataset.security_count,
        "feature_vector_count": len(dataset.samples),
        "matured_target_count": len(matured),
        "exclusion_counts": dict(Counter(item["reason"] for item in dataset.exclusions)),
        "splits": {
            period: {
                "start": min(period_dates),
                "end": max(period_dates),
                "date_count": len(period_dates),
                "sample_count": len(selected[period]),
                "last_target_session": max(
                    str(sample.target_session) for sample in selected[period]
                ),
            }
            for period, period_dates in periods.items()
        },
        "logistic_iterations": int(estimator.n_iter_[0]),
        "evaluation": evaluations,
        "final_beats_both_baselines_on_balanced_accuracy": final["candidate"]["balanced_accuracy"]
        > max(
            final["baseline_train_majority"]["balanced_accuracy"],
            final["baseline_trailing5_open_close_direction"]["balanced_accuracy"],
        ),
        "final_evaluation_used_for_selection": False,
        "independent_model_accepted": False,
        "accepted_rankings": False,
        "limitations": [
            "Fixed current cohort has survivorship/selection bias; not NSE-wide performance.",
            "Retrospective candles retrieved now; historical publication/revision clocks unknown.",
            "Adjustment basis/action coverage unknown; same-session scale invariance "
            "does not verify source correctness.",
            "Observed-cohort session union cannot establish sessions absent from every instrument.",
            "Scores are uncalibrated and evidence has not received independent acceptance.",
        ],
    }
    # Actual forecasts require a separately captured actual retrieval timestamp.
    current = (
        score(model, rows, sessions, decision, source_observed_at) if source_observed_at else []
    )
    return model, report, current
