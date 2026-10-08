"""Partitioned P9 execution for frozen P7 final-vintage research datasets.

Uses the existing fixed P8/P9 model arena and metric helpers. The larger matrix
contract is separate from verified-PIT snapshots and carries D70 assumptions.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, timedelta
from pathlib import Path
from typing import Any, TypedDict

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import skops.io as sio
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchCalendar, ResearchProfile, lineage
from alphalens_evaluation.contracts import Family, Fold
from alphalens_evaluation.models import build_model, versions
from alphalens_training.contracts import Task, TrainingConfig, boundary, feature_families
from alphalens_training.metrics import classification_metrics, regression_metrics


class FitResourcePolicy(TypedDict):
    version: str
    forest_fit_threads: int
    native_inner_threads: int
    prediction_threads: int
    scope: str


FIT_RESOURCE_POLICY: FitResourcePolicy = {
    "version": "research.fit_resources.v1",
    "forest_fit_threads": 4,
    "native_inner_threads": 1,
    "prediction_threads": 1,
    "scope": "RESOURCE_ALLOCATION_ONLY_STATISTICAL_PARAMETERS_UNCHANGED",
}


def fit_with_resources(
    model: Pipeline,
    x: np.ndarray[Any, Any],
    y: np.ndarray[Any, Any],
    forest_fit_threads: int = 4,
) -> None:
    """Parallel independent seeded trees; restore serial prediction/aggregation.

    Each tree keeps its existing independently assigned seed and training samples.
    No parameters governing splits/capacity/preprocessing change. Predictions stay
    serial to preserve floating-point aggregation order. The normal P9 arena is
    untouched; this is the separately recorded research execution allocation.
    """
    if not 1 <= forest_fit_threads <= 4:
        raise ValueError("RESEARCH_FOREST_FIT_THREAD_BUDGET_OUT_OF_RANGE")
    estimator = model.named_steps["estimator"]
    forest = isinstance(estimator, (RandomForestClassifier, RandomForestRegressor))
    original_jobs = estimator.n_jobs if forest else None
    with threadpool_limits(limits=1):
        try:
            if forest:
                estimator.set_params(n_jobs=forest_fit_threads)
            model.fit(x, y)
        finally:
            if forest:
                estimator.set_params(n_jobs=original_jobs)


def file_hash(path: Path) -> str:
    import hashlib

    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(value))


@dataclass(frozen=True)
class ResearchMatrix:
    features: np.ndarray[Any, Any]
    metadata: pa.Table
    columns: tuple[str, ...]
    identity: str
    horizon: int
    sessions: ResearchCalendar


def load_matrix(root: Path, horizon: int) -> ResearchMatrix:
    manifest = json.loads((root / "supervised-manifest.json").read_bytes())
    identity = manifest["identity"]
    profile = ResearchProfile.model_validate(identity["research_profile"])
    if checksum(stable_json(identity)) != manifest["dataset_id"]:
        raise ValueError("FROZEN_RESEARCH_DATASET_ID_MISMATCH")
    sessions = ResearchCalendar.model_validate_json((root / "research-calendar.json").read_bytes())
    if sessions.calendar_id != identity["calendar_id"] or profile != sessions.profile:
        raise ValueError("RESEARCH_CALENDAR_OR_PROFILE_MISMATCH")
    columns = tuple(identity["feature_columns"])
    registered = feature_families(
        TrainingConfig(
            task="classification",
            horizon=horizon,
            model_family="logistic",
            training_cutoff=boundary(sessions.dates[0]) - timedelta(seconds=1),
            validation_start=sessions.dates[0],
            validation_end=sessions.dates[0],
        )
    )
    if not columns or not set(columns) <= set(registered):
        raise ValueError("ONLY_FROZEN_P6_REGISTRY_COLUMNS_ALLOWED")
    if any(n.startswith(("target", "label", "metadata")) for n in columns):
        raise ValueError("RESEARCH_FEATURE_TARGET_BOUNDARY_VIOLATION")
    # The only matrix inputs are the P7 manifest's frozen P6 feature columns.
    shape = (sum(f["rows"] for f in identity["files"]), len(columns))
    path = root / "matrix" / f"features-{horizon}.npy"
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.lib.format.open_memmap(path, mode="w+", dtype="float64", shape=shape)
    metadata = []
    offset = 0
    names = [
        "security_id",
        "session_date",
        "decision_time",
        "canonical_record_id",
        f"target_return_{horizon}",
        f"target_direction_{horizon}",
        f"label_available_at_{horizon}",
        f"training_eligible_{horizon}",
        f"outcome_reasons_{horizon}",
    ]
    for f in identity["files"]:
        source = root / f["path"]
        if file_hash(source) != f["sha256"]:
            raise ValueError("RESEARCH_SUPERVISED_PARTITION_CHECKSUM_MISMATCH")
        parquet = pq.ParquetFile(source)
        stored = json.loads(parquet.schema_arrow.metadata[b"research_lineage"])
        if stored != lineage(profile):
            raise ValueError("RESEARCH_LINEAGE_PROPAGATION_MISMATCH")
        for batch in parquet.iter_batches(batch_size=32768, columns=list(columns) + names):
            table = pa.Table.from_batches([batch])
            values = np.column_stack(
                [table.column(n).to_numpy(zero_copy_only=False) for n in columns]
            )
            matrix[offset : offset + len(table)] = values
            offset += len(table)
            metadata.append(table.select(names))
    matrix.flush()
    save(
        path.with_suffix(".manifest.json"),
        dict(
            **lineage(profile),
            dataset_id=manifest["dataset_id"],
            horizon=horizon,
            shape=list(shape),
            dtype="float64",
            feature_columns=list(columns),
            role="DERIVED_LOCAL_MATRIX_CACHE_NOT_INDEPENDENT_TRAINING_DATA",
        ),
    )
    return ResearchMatrix(
        matrix, pa.concat_tables(metadata), columns, manifest["dataset_id"], horizon, sessions
    )


def masks(
    matrix: ResearchMatrix,
    fold: Fold,
    embargo_seconds: int = 86400,
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
    table = matrix.metadata
    h = matrix.horizon
    days = table.column("session_date").to_numpy().astype("datetime64[D]")
    decision = table.column("decision_time").to_numpy().astype("datetime64[us]")
    available = table.column(f"label_available_at_{h}").to_numpy().astype("datetime64[us]")
    cutoff = np.datetime64(
        (fold.training_cutoff - timedelta(seconds=embargo_seconds)).replace(tzinfo=None), "us"
    )
    eligible = table.column(f"training_eligible_{h}").to_numpy()
    finite = np.isfinite(matrix.features).all(axis=1)
    train = (
        (days >= np.datetime64("2015-01-01"))
        & (days < np.datetime64(fold.test_start))
        & finite
        & eligible
    )
    train &= ~np.isnat(available) & (available <= cutoff) & (decision <= cutoff)
    train &= available < np.datetime64(boundary(fold.test_start).replace(tzinfo=None), "us")
    # Later outcome exclusions never decide whether an OOS prediction is issued.
    test = (
        (days >= np.datetime64(fold.test_start)) & (days <= np.datetime64(fold.test_end)) & finite
    )
    test &= ~np.isnat(decision) & (decision > cutoff)

    def ordered(mask: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        indices = np.flatnonzero(mask)
        keys = table.select(["session_date", "security_id"]).take(pa.array(indices))
        order = pc.sort_indices(
            keys, sort_keys=[("session_date", "ascending"), ("security_id", "ascending")]
        ).to_numpy()
        return np.asarray(indices[order], dtype="int64")

    return ordered(train), ordered(test)


def rank_metrics(
    days: np.ndarray[Any, Any],
    security: list[str],
    scores: np.ndarray[Any, Any],
    returns: np.ndarray[Any, Any],
    accepted: np.ndarray[Any, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for day in sorted(np.unique(days)):
        indices = np.flatnonzero((days == day) & accepted & np.isfinite(returns))
        if len(indices) < 5:
            continue
        ordered = sorted(indices, key=lambda i: (-scores[i], security[i]))
        actual = returns[ordered]
        score = scores[ordered]
        n = max(1, int(len(indices) * 0.2))
        ic = float(spearmanr(score, actual).statistic) if np.ptp(score) and np.ptp(actual) else None
        top = float(actual[:n].mean())
        bottom = float(actual[-n:].mean())
        decile = max(1, int(len(indices) * 0.1))
        records.append(
            dict(
                session=str(day),
                samples=len(indices),
                spearman_ic=ic,
                top_quintile=top,
                bottom_quintile=bottom,
                spread=top - bottom,
                top_decile=float(actual[:decile].mean()) if len(indices) >= 10 else None,
                bottom_decile=float(actual[-decile:].mean()) if len(indices) >= 10 else None,
            )
        )
    valid = [r["spearman_ic"] for r in records if r["spearman_ic"] is not None]
    return dict(
        mean_rank_ic=float(np.mean(valid)) if valid else None,
        mean_top_quintile=float(np.mean([r["top_quintile"] for r in records])) if records else None,
        mean_bottom_quintile=float(np.mean([r["bottom_quintile"] for r in records]))
        if records
        else None,
        mean_top_minus_bottom=float(np.mean([r["spread"] for r in records])) if records else None,
        worst_session_ic=min(valid) if valid else None,
        sessions=records,
        status="DESCRIPTIVE_RAW_TARGET_RANKING_NOT_INVESTMENT_RETURN",
    )


def evaluate_fold(
    matrix: ResearchMatrix,
    fold: Fold,
    task: Task,
    family: Family,
    output: Path,
) -> dict[str, Any]:
    report_path = output / f"{task}-{matrix.horizon}-{family}-{fold.fold_id}.json"
    if report_path.exists():
        existing: dict[str, Any] = json.loads(report_path.read_bytes())
        if existing["dataset_id"] != matrix.identity or existing["fold"] != fold.model_dump(
            mode="json"
        ):
            raise ValueError("RESEARCH_RESTART_REPORT_IDENTITY_MISMATCH")
        if file_hash(output / existing["oos_file"]) != existing["oos_sha256"]:
            raise ValueError("RESEARCH_RESTART_OOS_CHECKSUM_MISMATCH")
        if file_hash(output / existing["model_file"]) != existing["model_sha256"]:
            raise ValueError("RESEARCH_RESTART_MODEL_CHECKSUM_MISMATCH")
        return existing
    # A completed final run can be read again, but an interrupted final fit is
    # not silently repeated. Its locked attempt must be reviewed explicitly.
    attempt = report_path.with_suffix(".attempt.json")
    if fold.test_start.year == 2026:
        if attempt.exists():
            raise ValueError("FINAL_HOLDOUT_ATTEMPT_INCOMPLETE_REVIEW_REQUIRED")
        save(
            attempt,
            dict(
                **lineage(matrix.sessions.profile),
                dataset_id=matrix.identity,
                fold=fold.model_dump(mode="json"),
                task=task,
                family=family,
                horizon=matrix.horizon,
                policy="ONCE_NO_RETUNING",
            ),
        )
    train, test = masks(matrix, fold)
    if len(train) < 100 or len(test) < 100:
        raise ValueError("INSUFFICIENT_MATURE_REAL_RESEARCH_SAMPLES")
    table = matrix.metadata
    h = matrix.horizon
    config = TrainingConfig(
        task=task,
        horizon=h,
        model_family="logistic" if task == "classification" else "ridge",
        training_cutoff=fold.training_cutoff - timedelta(seconds=86400),
        validation_start=fold.test_start,
        validation_end=fold.test_end,
    )
    xtrain = np.asarray(matrix.features[train])
    xtest = np.asarray(matrix.features[test])
    keep = np.ptp(xtrain, axis=0) != 0
    if not keep.all():
        xtrain = xtrain[:, keep]
        xtest = xtest[:, keep]
    selected = table.take(pa.array(test))
    actual_text = selected.column(f"target_return_{h}").to_pylist()
    returns = np.asarray([float(v) if v is not None else np.nan for v in actual_text])
    accepted = selected.column(f"training_eligible_{h}").to_numpy().copy()
    available = selected.column(f"label_available_at_{h}").to_numpy().astype("datetime64[us]")
    accepted &= ~np.isnat(available)
    # Candidate evidence is locked before confirmation; late development labels
    # cannot import 2025 outcomes into family selection. Likewise for 2026.
    if fold.test_start.year <= 2024:
        outcome_cutoff = boundary(date(2025, 1, 1)) - timedelta(microseconds=1)
    elif fold.test_start.year == 2025:
        outcome_cutoff = boundary(date(2026, 1, 1)) - timedelta(microseconds=1)
    else:
        outcome_cutoff = boundary(matrix.sessions.dates[-1])
    outcome_bound = np.datetime64(outcome_cutoff.astimezone(UTC).replace(tzinfo=None), "us")
    accepted &= available <= outcome_bound
    if task == "classification":
        ytrain = (
            table.column(f"target_direction_{h}").take(pa.array(train)).to_numpy().astype("float64")
        )
        actual = (
            selected.column(f"target_direction_{h}")
            .to_numpy(zero_copy_only=False)
            .astype("float64")
        )
        if len(np.unique(ytrain)) != 2:
            raise ValueError("INSUFFICIENT_REAL_RESEARCH_TRAINING_CLASSES")
    else:
        train_targets = table.column(f"target_return_{h}").take(pa.array(train)).to_pylist()
        ytrain = np.asarray([float(v) for v in train_targets])
        actual = returns
    model = build_model(family, config)
    # The selected X rows are owned advanced-index copies and entirely finite.
    # Avoid duplicating a multi-million-row matrix merely to fill zero nulls.
    # Scaler defaults stay unchanged, so prediction calls cannot double-scale X.
    model.named_steps["imputer"].set_params(copy=False)
    parameters = {
        name: "NaN_ESTIMATOR_SENTINEL" if isinstance(value, float) and np.isnan(value) else value
        for name, value in model.named_steps["estimator"].get_params(deep=False).items()
    }
    identity = dict(
        **lineage(matrix.sessions.profile),
        dataset_id=matrix.identity,
        fold=fold.model_dump(mode="json"),
        task=task,
        horizon=h,
        family=family,
        configuration=config.model_dump(mode="json"),
        feature_columns=[n for n, k in zip(matrix.columns, keep, strict=True) if k],
        training_mask_sha256=checksum(train.tobytes()),
        test_mask_sha256=checksum(test.tobytes()),
        hyperparameters=parameters,
        parameter_encoding="NaN_ESTIMATOR_SENTINEL_IS_METADATA_NOT_A_FEATURE_VALUE",
        preprocessing="FRESH_TRAIN_ONLY_MEDIAN_LINEAR_SCALER_CONSTANT_REMOVAL",
        imputer_copy=False,
        execution_resources=FIT_RESOURCE_POLICY,
        environment=versions(),
        outcome_knowledge_cutoff=outcome_cutoff.isoformat(),
        training_start="2015-01-01_EARLIER_RETAINED_FOR_WARMUP",
        code_contract="p9.research.partitioned.v2",
    )
    run_id = checksum(stable_json(identity))
    fit_with_resources(model, xtrain, ytrain, FIT_RESOURCE_POLICY["forest_fit_threads"])
    with threadpool_limits(limits=1):
        predicted = np.asarray(model.predict(xtest), dtype="float64").ravel()
        probabilities = (
            np.asarray(model.predict_proba(xtest)[:, 1], dtype="float64")
            if task == "classification"
            else None
        )
    mask = accepted & np.isfinite(actual)
    if not mask.any():
        raise ValueError("INSUFFICIENT_SCORABLE_REAL_RESEARCH_OUTCOMES")
    if task == "classification":
        if probabilities is None:
            raise ValueError("RESEARCH_CLASSIFICATION_PROBABILITY_REQUIRED")
        metrics = classification_metrics(actual[mask], probabilities[mask], config, predicted[mask])
        naive = classification_metrics(
            actual[mask], np.full(mask.sum(), float(ytrain.mean())), config
        )
        majority = classification_metrics(
            actual[mask], np.full(mask.sum(), float(ytrain.mean() > 0.5)), config
        )
        primary = "brier_score"
    else:
        metrics = regression_metrics(actual[mask], predicted[mask])
        metrics["spearman"] = (
            float(spearmanr(actual[mask], predicted[mask]).statistic)
            if np.ptp(predicted[mask]) and np.ptp(actual[mask])
            else None
        )
        naive = regression_metrics(actual[mask], np.full(mask.sum(), float(ytrain.mean())))
        majority = regression_metrics(actual[mask], np.zeros(mask.sum()))
        primary = "mae"
    security = selected.column("security_id").to_pylist()
    days = selected.column("session_date").to_numpy().astype("datetime64[D]")
    scores = probabilities if probabilities is not None else predicted
    ranking = rank_metrics(days, security, scores, returns, mask)
    metrics.update(
        {
            n: ranking[n]
            for n in (
                "mean_rank_ic",
                "mean_top_quintile",
                "mean_bottom_quintile",
                "mean_top_minus_bottom",
            )
        }
    )
    record_ids = selected.column("canonical_record_id").to_pylist()
    prediction_ids = [checksum(f"{run_id}:{r}".encode()) for r in record_ids]
    oos = selected.append_column("prediction_id", pa.array(prediction_ids)).append_column(
        "score", pa.array(scores)
    )
    oos = oos.append_column("prediction", pa.array(predicted)).append_column(
        "scorable", pa.array(mask)
    )
    oos = oos.replace_schema_metadata(
        {
            b"research_lineage": stable_json(lineage(matrix.sessions.profile)),
            b"role": b"FOLD_TEST",
            b"model_run_id": run_id.encode(),
            b"model_identity": stable_json(identity),
            b"dataset_id": matrix.identity.encode(),
        }
    )
    oos_name = f"oos/{task}-{h}-{family}-{fold.fold_id}.parquet"
    (output / "oos").mkdir(parents=True, exist_ok=True)
    pq.write_table(oos, output / oos_name, compression="zstd")
    (output / "models").mkdir(parents=True, exist_ok=True)
    sio.dump(model, output / "models" / f"{run_id}.skops")
    report = dict(
        **lineage(matrix.sessions.profile),
        dataset_id=matrix.identity,
        model_run_id=run_id,
        model_family=family,
        task=task,
        horizon=h,
        fold_id=fold.fold_id,
        fold=fold.model_dump(mode="json"),
        status="EVALUATED",
        training_rows=len(train),
        test_rows=len(test),
        scored_test_rows=int(mask.sum()),
        training_target_mean=float(ytrain.mean()),
        metrics=metrics,
        naive=naive,
        secondary_naive=majority,
        primary_metric=primary,
        beats_naive=bool(metrics[primary] < naive[primary]),
        naive_relative_improvement=float((naive[primary] - metrics[primary]) / naive[primary])
        if naive[primary]
        else None,
        ranking=ranking,
        oos_file=oos_name,
        oos_sha256=file_hash(output / oos_name),
        model_identity=identity,
        model_file=f"models/{run_id}.skops",
        model_sha256=file_hash(output / "models" / f"{run_id}.skops"),
        serialization="FIRST_VALID_LOCAL_SKOPS_BYTES_PINNED_NOT_BYTE_DETERMINISM_CLAIM",
    )
    save(report_path, report)
    print(
        json.dumps(
            dict(
                stage="p9",
                task=task,
                horizon=h,
                family=family,
                fold=fold.fold_id,
                training=len(train),
                test=len(test),
            )
        ),
        flush=True,
    )
    return report


def locked_folds(sessions: ResearchCalendar, years: tuple[int, ...]) -> tuple[Fold, ...]:
    output = []
    for year in years:
        dates = [d for d in sessions.dates if d.year == year]
        if not dates:
            raise ValueError("LOCKED_YEAR_HAS_NO_RESEARCH_SESSION")
        output.append(
            Fold(
                fold_id=str(year),
                test_start=dates[0],
                test_end=dates[-1],
                training_cutoff=boundary(dates[0]) - timedelta(microseconds=1),
            )
        )
    return tuple(output)


def development(root: Path, output: Path) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for h in (1, 5, 10, 20):
        matrix = load_matrix(root, h)
        folds = locked_folds(matrix.sessions, (2022, 2023, 2024))
        for task in ("classification", "regression"):
            families: tuple[Family, ...] = (
                "logistic" if task == "classification" else "ridge",
                "random_forest",
                "hist_gradient_boosting",
                "lightgbm",
                "catboost",
                "xgboost",
            )
            for fold in folds:
                for family in families:
                    reports.append(evaluate_fold(matrix, fold, task, family, output))
                    save(
                        output / "development-results.json",
                        dict(
                            **lineage(matrix.sessions.profile),
                            reports=reports,
                            final_holdout_evaluated=False,
                            confirmation_evaluated=False,
                        ),
                    )
        del matrix
    return reports
