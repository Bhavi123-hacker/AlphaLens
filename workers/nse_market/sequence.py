"""Registered CPU sequence experiment; optional training, numeric-only inference.

No provider calls, arbitrary pickle loading, old-model fits or accepted publishing.
Historical report outcomes are explicitly known-period development evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from workers.experimental_nse.acquire import digest, encoded, initialize
from workers.experimental_nse_v2 import models
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES, Sample, build
from workers.nse_market import engine
from workers.providers.daily_clock import guard

FAMILY = "ALPHALENS_SEQUENCE_BENCHMARK_V1"
VERSION = "nse.price-state.sequence20x8.v1"
NAMES = (
    "price_return_1",
    "price_return_5",
    "price_return_20",
    "return_sd_20",
    "ma_distance_20",
    "rsi_14",
    "atr_14_over_close",
    "open_close_return",
)
LENGTH = 20
SEED = 1729
PROTOCOL = Path("docs/development/ml-sequence-v1-registered-protocol.md")


@dataclass(frozen=True)
class Sequence:
    sample: Sample
    values: tuple[tuple[float, ...], ...]


def sequences(samples: tuple[Sample, ...], sessions: list[str]) -> list[Sequence]:
    """Only complete trailing states; targets never enter sequence inputs."""
    lookup = {(sample.key, sample.session): sample for sample in samples}
    locations = {day: index for index, day in enumerate(sessions)}
    indices = [LOCAL_FEATURE_NAMES.index(name) for name in NAMES]
    output = []
    for sample in samples:
        index = locations[sample.session]
        if index < LENGTH - 1:
            continue
        days = sessions[index - LENGTH + 1 : index + 1]
        if any((sample.key, day) not in lookup for day in days):
            continue
        values = tuple(tuple(lookup[sample.key, day].vector[i] for i in indices) for day in days)
        if not np.isfinite(values).all():
            raise ValueError("SEQUENCE_NONFINITE_INPUT")
        output.append(Sequence(sample, values))
    return sorted(output, key=lambda item: (item.sample.session, item.sample.key))


def partitions(items: list[Sequence], sessions: list[str]) -> dict[str, list[Sequence]]:
    """Shared-date target purge and 20-date boundary embargo, no random split."""
    embargo24 = set([day for day in sessions if day >= "2024-01-01"][:20])
    embargo25 = set([day for day in sessions if day >= "2025-01-01"][:20])
    return {
        "training": [
            x
            for x in items
            if x.sample.session < "2024-01-01"
            and x.sample.target_session is not None
            and x.sample.target_session < "2024-01-01"
        ],
        "validation": [
            x
            for x in items
            if "2024-01-01" <= x.sample.session < "2025-01-01"
            and x.sample.session not in embargo24
            and x.sample.target_session is not None
            and x.sample.target_session < "2025-01-01"
        ],
        "development_report": [
            x
            for x in items
            if x.sample.session >= "2025-01-01"
            and x.sample.session not in embargo25
            and x.sample.target is not None
        ],
    }


def _sigmoid(values: Any) -> Any:
    return 1 / (1 + np.exp(-np.clip(values, -60, 60)))


def predict(model: dict[str, Any], values: Any) -> np.ndarray[Any, Any]:
    """Reviewed fixed PyTorch gate equations, no serialized executable objects."""
    if (
        model["family"] != FAMILY
        or model["feature_version"] != VERSION
        or model["feature_names"] != list(NAMES)
        or model["sequence_length"] != LENGTH
    ):
        raise ValueError("REGISTERED_SEQUENCE_MODEL_REQUIRED")
    matrix = np.asarray(values, dtype=np.float64)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (LENGTH, len(NAMES))
        or not np.isfinite(matrix).all()
    ):
        raise ValueError("COMPLETE_FINITE_ORDERED_SEQUENCE_REQUIRED")
    mean, scale = np.asarray(model["mean"]), np.asarray(model["scale"])
    if (
        mean.shape != (8,)
        or scale.shape != (8,)
        or not np.isfinite(mean).all()
        or not np.isfinite(scale).all()
        or np.any(scale <= 0)
    ):
        raise ValueError("TRAINING_ONLY_SEQUENCE_SCALING_REQUIRED")
    matrix = (matrix - mean) / scale
    state = {key: np.asarray(value, dtype=np.float64) for key, value in model["state"].items()}
    required = {
        "0.weight_ih_l0": (64, 8),
        "0.weight_hh_l0": (64, 16),
        "0.bias_ih_l0": (64,),
        "0.bias_hh_l0": (64,),
        "2.weight": (1, 16),
        "2.bias": (1,),
    }
    if set(state) != set(required) or any(
        state[key].shape != shape or not np.isfinite(state[key]).all()
        for key, shape in required.items()
    ):
        raise ValueError("FIXED_NUMERIC_LSTM_STATE_REQUIRED")
    hidden = np.zeros((len(matrix), 16))
    cell = hidden.copy()
    for step in range(LENGTH):
        gates = (
            matrix[:, step] @ state["0.weight_ih_l0"].T
            + hidden @ state["0.weight_hh_l0"].T
            + state["0.bias_ih_l0"]
            + state["0.bias_hh_l0"]
        )
        ingate, forget, candidate, outgate = np.split(gates, 4, axis=1)
        cell = _sigmoid(forget) * cell + _sigmoid(ingate) * np.tanh(candidate)
        hidden = _sigmoid(outgate) * np.tanh(cell)
    return np.asarray(_sigmoid(hidden @ state["2.weight"].T + state["2.bias"])[:, 0])


def _array(items: list[Sequence]) -> np.ndarray[Any, Any]:
    return np.asarray([item.values for item in items], dtype=np.float32)


def _return(sample: Sample) -> float:
    if sample.target_return is None:
        raise ValueError("MATURED_RETURN_REQUIRED")
    return sample.target_return


def current_timing(frame: dict[str, Any]) -> dict[str, Any]:
    """Future executions may score current inputs only before a proved future open.

    A missing operational clock does not invalidate completed historical research;
    it makes the optional current score cohort unavailable instead.
    """
    try:
        clock = guard()
        lower, upper = (datetime.fromisoformat(clock[name]) for name in ("lower_at", "upper_at"))
        latest = frame["sessions"][-1]
        timing, following = frame["session_timing"], frame["next_session_timing"]
        close, entry, observed = (
            datetime.fromisoformat(value)
            for value in (timing["close_at"], following["open_at"], frame["source_observed_at"])
        )
        age = (date.fromisoformat(clock["session_date"]) - date.fromisoformat(latest)).days
        if (
            any(value.utcoffset() is None for value in (lower, upper, close, entry, observed))
            or not lower <= upper < entry
            or not close < observed <= lower
            or timing["session"] != latest
            or following["session"] <= latest
            or not 0 <= age <= 7
        ):
            raise ValueError("CURRENT_SEQUENCE_FUTURE_ENTRY_OR_SOURCE_TIMING_UNPROVEN")
        return {"eligible": True, "clock": clock, "next_session_timing": following}
    except (ValueError, OSError, KeyError, TypeError):
        return {"eligible": False, "reason": "CURRENT_SEQUENCE_FUTURE_ENTRY_OR_SOURCE_UNAVAILABLE"}


def uncertainty(
    samples: list[Sample], predictions: list[float], baseline: list[float]
) -> dict[str, Any]:
    """Predeclared moving blocks of whole market dates, paired against reversal."""
    days = sorted({item.session for item in samples})
    counts = np.zeros((len(days), 6))
    positions = {day: index for index, day in enumerate(days)}
    for sample, value, reference in zip(samples, predictions, baseline, strict=True):
        if sample.target is None:
            raise ValueError("MATURED_CLASSIFICATION_REQUIRED")
        row = counts[positions[sample.session]]
        row[sample.target] += 1
        row[2 + sample.target] += int((value >= 0.5) == bool(sample.target))
        row[4 + sample.target] += int((reference >= 0.5) == bool(sample.target))
    rng = np.random.default_rng(SEED)
    block = min(20, len(days))
    values = []
    for _ in range(500):
        indices = np.concatenate(
            [
                np.arange(start, start + block)
                for start in rng.integers(0, len(days) - block + 1, math.ceil(len(days) / block))
            ]
        )[: len(days)]
        total = counts[indices].sum(axis=0)
        if min(total[:2]) > 0:
            values.append(float(((total[2:4] - total[4:6]) / total[:2]).mean()))
    return {
        "method": "PAIRED_MOVING_BLOCK20_WHOLE_DATES_500_SEED1729",
        "draws": len(values),
        "balanced_accuracy_difference_95_interval": np.quantile(values, [0.025, 0.975]).tolist(),
        "independent_confirmation": False,
        "multiple_comparison_risk": "EXPLORATORY_NINE_COMPARISONS_NO_PROMOTION",
    }


def economics(samples: list[Sample], predictions: list[float]) -> dict[str, Any]:
    """Fixed nonoverlapping price references with predeclared costs, never fills."""
    by_day: dict[str, list[tuple[Sample, float]]] = {}
    for sample, score in zip(samples, predictions, strict=True):
        by_day.setdefault(sample.session, []).append((sample, score))
    paths: dict[str, list[dict[str, Any]]] = {
        name: []
        for name in (
            "equal_cohort",
            "top5",
            "top10",
            "top20",
            "momentum5",
            "reversal5",
            "low_volatility5",
        )
    }
    prior: dict[str, set[str]] = {}
    for day in sorted(by_day)[::5]:
        cohort = by_day[day]
        selections = {
            "equal_cohort": cohort,
            **{
                f"top{n}": sorted(cohort, key=lambda item: (-item[1], item[0].key))[:n]
                for n in (5, 10, 20)
            },
            "momentum5": sorted(cohort, key=lambda item: (-item[0].vector[1], item[0].key))[:5],
            "reversal5": sorted(cohort, key=lambda item: (item[0].vector[1], item[0].key))[:5],
            "low_volatility5": sorted(
                cohort, key=lambda item: (item[0].risk["return_daily_sd_20"], item[0].key)
            )[:5],
        }
        for name, selected in selections.items():
            keys = {item.key for item, _ in selected}
            movement = math.fsum(_return(item) for item, _ in selected) / len(selected)
            paths[name].append(
                {
                    "decision_session": day,
                    "exit_session": selected[0][0].target_session,
                    "selected_count": len(selected),
                    "gross_return": movement,
                    "membership_turnover": len(keys - prior.get(name, set())) / len(keys),
                    "keys": sorted(keys),
                }
            )
            prior[name] = keys
    reports = {}
    for name, path in paths.items():
        scenarios = []
        for cost in (25, 50, 100):
            gross, net, peak, drawdown = 1.0, 1.0, 1.0, 0.0
            curve, movements = [], []
            for point in path:
                movement = point["gross_return"] - (cost + 10) / 10000
                movements.append(movement)
                gross *= 1 + point["gross_return"]
                net *= 1 + movement
                peak = max(peak, net)
                drawdown = min(drawdown, net / peak - 1)
                curve.append(
                    {
                        "session": point["exit_session"],
                        "gross_equity": gross,
                        "net_equity": net,
                        "drawdown": net / peak - 1,
                    }
                )
            sd = float(np.std(movements))
            scenarios.append(
                {
                    "round_trip_cost_bps": cost,
                    "slippage_bps_each_side": 5,
                    "gross_compounded_reference_return": gross - 1,
                    "net_compounded_reference_return": net - 1,
                    "maximum_endpoint_drawdown": drawdown,
                    "annualized_volatility_252_over5_assumption": sd * math.sqrt(252 / 5),
                    "reference_sharpe_zero_cash": float(np.mean(movements))
                    / sd
                    * math.sqrt(252 / 5)
                    if sd
                    else None,
                    "curve": curve,
                }
            )
        reports[name] = {
            "decision_count": len(path),
            "mean_membership_turnover": float(
                np.mean([point["membership_turnover"] for point in path])
            ),
            "scenarios": scenarios,
            "decisions": path,
        }
    return {
        "classification": "HYPOTHETICAL_PRICE_REFERENCES_NOT_EXECUTED_OR_TOTAL_RETURN",
        "strategies": reports,
        "benchmark": "OBSERVED_EQUAL_COHORT_NOT_NSE_INDEX",
        "full_path_economic_compatibility_verified": False,
        "limitations": [
            "Current fixed cohort, no historical membership reconstruction",
            "Historical publication and complete actions unknown",
            "No actual spreads, fills, tax schedule, liquidity capacity or dividends",
            "Nonoverlapping endpoint references; intervening mark-to-market path unavailable",
            "Full allocations assumed; membership turnover diagnostic; all round trips charged",
        ],
    }


def train(root: Path, source: Path, plan_id: str) -> dict[str, Any]:
    """One immutable predeclared run. No tuning or use of report outcomes in fit."""
    initialize(root)
    if (root / "report.json").exists() or (root / "attempt.json").exists():
        raise ValueError("SEQUENCE_ATTEMPT_ALREADY_RECORDED_NEW_PROTOCOL_REQUIRED")
    protocol = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    engine._checked(
        root / "attempt.json",
        {
            "family": FAMILY,
            "started_at": datetime.now(UTC).isoformat(),
            "protocol_sha256": protocol,
            "plan_id": plan_id,
            "search_budget": 1,
        },
    )
    start = time.monotonic()
    frame = engine.snapshot(source)
    plan = engine._read(source / "plans" / (plan_id + ".json"))
    if plan["target_count"] != 100:
        raise ValueError("PREDECLARED_ORIGINAL_100_STOCK_PLAN_REQUIRED")
    keys = {item["provider_key"] for item in plan["identities"]}
    rows = [row for row in frame["rows"] if row["key"] in keys]
    selected_source_at = max(row["received_at"] for row in rows)
    source_by_key = {
        key: max(row["received_at"] for row in rows if row["key"] == key) for key in keys
    }
    training_dataset_id = digest(
        encoded(
            {
                "rows": rows,
                "excluded_sessions": {
                    key: frame["quality"]["excluded_sessions"].get(key, []) for key in sorted(keys)
                },
                "price_basis": frame["price_basis"],
                "protocol_sha256": protocol,
            }
        )
    )
    engine._checked(
        root / "dataset-manifest.json",
        {
            "dataset_id": training_dataset_id,
            "parent_dataset_id": frame["dataset_id"],
            "plan_id": plan_id,
            "selected_keys": sorted(keys),
            "observations": len(rows),
            "source_observed_at": selected_source_at,
            "source_hashes": sorted({row["raw_sha256"] for row in rows}),
            "source_receipts_by_key": source_by_key,
            "price_basis": frame["price_basis"],
            "protocol_sha256": protocol,
        },
    )
    features = build(
        rows, frame["sessions"], frame["quality"]["excluded_sessions"], include_context=False
    )
    all_sequences = sequences(features.samples, frame["sessions"])
    parts = partitions(all_sequences, frame["sessions"])
    if any(len(values) < 100 for values in parts.values()):
        raise ValueError("INSUFFICIENT_CHRONOLOGICAL_SEQUENCE_DATA")
    xtrain, xvalid, xtest = (
        _array(parts[name]) for name in ("training", "validation", "development_report")
    )
    ytrain, yvalid = (
        np.asarray([item.sample.target for item in parts[name]], dtype=np.float32)
        for name in ("training", "validation")
    )
    mean = xtrain.mean(axis=(0, 1), dtype=np.float64)
    scale = xtrain.std(axis=(0, 1), dtype=np.float64)
    if np.any(scale == 0):
        raise ValueError("CONSTANT_TRAINING_SEQUENCE_FEATURE")
    torch = importlib.import_module("torch")
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)
    network = torch.nn.Sequential(
        torch.nn.LSTM(8, 16, batch_first=True), torch.nn.Dropout(0.1), torch.nn.Linear(16, 1)
    )

    def logits(value: Any) -> Any:
        output, _ = network[0](value)
        return network[2](network[1](output[:, -1]))[:, 0]

    tensors = [
        torch.tensor((values - mean) / scale, dtype=torch.float32) for values in (xtrain, xvalid)
    ]
    labels = [torch.tensor(value) for value in (ytrain, yvalid)]
    loss_function = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(network.parameters(), lr=0.001)
    best_loss, best_state, stale = math.inf, None, 0
    epochs = []
    for epoch in range(20):
        network.train()
        losses = []
        for offset in range(0, len(xtrain), 512):
            optimizer.zero_grad()
            loss = loss_function(
                logits(tensors[0][offset : offset + 512]), labels[0][offset : offset + 512]
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), 1)
            optimizer.step()
            losses.append(float(loss.detach()))
        network.eval()
        with torch.no_grad():
            validation_loss = float(loss_function(logits(tensors[1]), labels[1]))
        epochs.append(
            {
                "epoch": epoch + 1,
                "training_bce": float(np.mean(losses)),
                "validation_bce": validation_loss,
            }
        )
        print(json.dumps({"stage": "LSTM_EPOCH", **epochs[-1]}), flush=True)
        if validation_loss < best_loss:
            best_loss, best_state, stale = validation_loss, copy.deepcopy(network.state_dict()), 0
        else:
            stale += 1
        if stale >= 3:
            break
    if best_state is None:
        raise ValueError("NO_FINITE_TRAINED_LSTM_STATE")
    network.load_state_dict(best_state)
    network.eval()
    model = {
        "family": FAMILY,
        "feature_version": VERSION,
        "feature_names": list(NAMES),
        "sequence_length": LENGTH,
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "state": {key: value.tolist() for key, value in best_state.items()},
        "protocol_sha256": protocol,
        "dataset_id": training_dataset_id,
        "training_cohort": sorted(keys),
        "architecture": "LSTM8x16_ONE_LAYER_DROPOUT0.1_DENSE1",
        "calibration_status": "NOT_ESTABLISHED",
        "trained_at": datetime.now(UTC).isoformat(),
    }
    model_sha = engine._checked(root / "model.json", model)
    reloaded = engine._read(root / "model.json")
    with torch.no_grad():
        reference = torch.sigmoid(
            logits(torch.tensor((xtest[:100] - mean) / scale, dtype=torch.float32))
        ).numpy()
    parity = float(np.max(np.abs(reference - predict(reloaded, xtest[:100]))))
    if parity > 1e-6:
        raise ValueError("NUMERIC_MODEL_RELOAD_PARITY_FAILED")
    evaluations: dict[str, Any] = {}
    scores: dict[str, Any] = {"LSTM": predict(reloaded, xtest)}
    last = [item.sample for item in parts["development_report"]]
    samples = [item.sample for item in parts["training"]]
    scores["majority"] = np.full(len(last), float(ytrain.mean()))
    scores["momentum"] = np.asarray([models._sigmoid(item.vector[1] / 0.05) for item in last])
    scores["mean_reversion"] = np.asarray(
        [models._sigmoid(-item.vector[1] / 0.05) for item in last]
    )
    trainflat = ((xtrain - mean) / scale).reshape(len(xtrain), -1)
    testflat = ((xtest - mean) / scale).reshape(len(xtest), -1)
    classifiers: dict[str, Any] = {
        "LOGISTIC": LogisticRegression(
            C=1, max_iter=1000, class_weight="balanced", random_state=SEED
        ),
        "RANDOM_FOREST": RandomForestClassifier(
            n_estimators=100, max_depth=6, min_samples_leaf=30, random_state=SEED, n_jobs=2
        ),
        "HIST_GRADIENT_BOOSTING": HistGradientBoostingClassifier(
            max_iter=100,
            max_leaf_nodes=15,
            l2_regularization=1,
            random_state=SEED,
            early_stopping=False,
        ),
    }
    try:
        xgb = importlib.import_module("xgboost")
        classifiers["XGBOOST"] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            subsample=1,
            colsample_bytree=1,
            random_state=SEED,
            n_jobs=2,
        )
    except ImportError:
        evaluations["XGBOOST"] = {"state": "UNAVAILABLE_NOT_INSTALLED"}
    for name, estimator in classifiers.items():
        print(
            json.dumps({"stage": "COMPARATOR_FIT", "algorithm": name, "samples": len(ytrain)}),
            flush=True,
        )
        estimator.fit(trainflat, ytrain)
        scores[name] = estimator.predict_proba(testflat)[:, 1]
        engine._checked(
            root / ("candidate-scores-" + name + ".json"),
            {
                "algorithm": name,
                "protocol_sha256": protocol,
                "dataset_id": training_dataset_id,
                "scores": scores[name].tolist(),
            },
        )
    ridge = Ridge(alpha=10).fit(trainflat, [_return(item) for item in samples])
    ridge_returns = ridge.predict(testflat)
    scores["RIDGE"] = _sigmoid(ridge_returns / 0.05)
    for name, predictions in scores.items():
        evaluations[name] = {
            "metrics": models.metrics(last, predictions.tolist()),
            "uncertainty_vs_reversal": uncertainty(
                last, predictions.tolist(), scores["mean_reversion"].tolist()
            ),
            "economic_sensitivity": economics(last, predictions.tolist()),
        }
    evaluations["RIDGE"]["return_errors"] = {
        "mae": mean_absolute_error([_return(item) for item in last], ridge_returns),
        "rmse": math.sqrt(mean_squared_error([_return(item) for item in last], ridge_returns)),
        "brier_not_calibrated_probability": True,
    }
    # A bounded transform of a return estimate is not a probability forecast.
    for field in ("brier_score", "calibration_bins", "probability_calibration_established"):
        evaluations["RIDGE"]["metrics"].pop(field, None)
    predictions = [
        {
            "key": item.key,
            "symbol": item.symbol,
            "decision_session": item.session,
            "target_session": item.target_session,
            "actual_price_component_return": item.target_return,
            "actual_positive": item.target,
            "ridge_return_estimate": float(ridge_returns[i]),
            "scores": {name: float(values[i]) for name, values in scores.items()},
            "classification": "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE",
            "hypothetical_decision_availability": (
                "FINAL_VINTAGE_PRIOR_EOD_ASSUMPTION_NOT_VERIFIED_HISTORICAL_PUBLICATION"
            ),
        }
        for i, item in enumerate(last)
    ]
    engine._checked(
        root / "historical-predictions.json",
        {"rows": predictions, "dataset_id": training_dataset_id, "model_sha256": model_sha},
    )
    timing = current_timing(frame)
    latest = (
        [item for item in all_sequences if item.sample.session == frame["sessions"][-1]]
        if timing["eligible"]
        else []
    )
    current_scores: Any = predict(reloaded, _array(latest)) if latest else []
    current = [
        {
            "key": item.sample.key,
            "symbol": item.sample.symbol,
            "session": item.sample.session,
            "observed_price": item.sample.price,
            "score": float(value),
            "model_sha256": model_sha,
            "inference_at": datetime.now(UTC).isoformat(),
            "source_observed_at": source_by_key[item.sample.key],
            "classification": "EXPERIMENTAL_ML",
            "calibration_status": "NOT_ESTABLISHED",
            "forecast_created": False,
            "risk": item.sample.risk,
        }
        for item, value in zip(latest, current_scores, strict=True)
    ]
    report = {
        "family": FAMILY,
        "state": "EXPERIMENTAL_UNVALIDATED",
        "protocol_sha256": protocol,
        "model_sha256": model_sha,
        "dataset_id": training_dataset_id,
        "source": "UPSTOX_OFFICIAL_PRIVATE_RESEARCH",
        "feature_version": VERSION,
        "sequence_length": LENGTH,
        "feature_names": list(NAMES),
        "architecture": model["architecture"],
        "torch_version": torch.__version__,
        "training_seed": SEED,
        "search_budget": 1,
        "attempts": 1,
        "cohort": len(keys),
        "observations": len(rows),
        "sequence_exclusions": len(features.samples) - len(all_sequences),
        "periods": {
            name: {
                "samples": len(values),
                "first": values[0].sample.session,
                "last": values[-1].sample.session,
                "securities": len({item.sample.key for item in values}),
            }
            for name, values in parts.items()
        },
        "epochs": epochs,
        "reload_max_absolute_difference": parity,
        "comparisons": evaluations,
        "current_scores": sorted(current, key=lambda item: (-item["score"], item["key"])),
        "current_score_timing": timing,
        "historical_prediction_count": len(predictions),
        "prospective_forecasts": 0,
        "matured_prospective_outcomes": 0,
        "accepted_rankings": 0,
        "independent_test": False,
        "edge_status": "NO_INDEPENDENTLY_DEMONSTRATED_EDGE",
        "cost_policy": "25/50/100bps_round_trip_plus_5bps_each_side_predeclared",
        "economic_full_path_verified": False,
        "historical_membership": "CURRENT_FIXED_COHORT_RETROSPECTIVE",
        "completed_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.monotonic() - start,
    }
    engine._checked(root / "report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--plan-id", required=True)
    arguments = parser.parse_args()
    result = train(arguments.root, arguments.source, arguments.plan_id)
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"comparisons", "current_scores"}
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
