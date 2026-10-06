"""Verified historical model comparisons; no winner optimization or target inputs."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Literal, Self

from pydantic import AwareDatetime, model_validator

from alphalens_backtesting.storage import verify
from alphalens_data.contracts import Contract
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_decision.evidence import project
from alphalens_decision.models import Horizon, ModelDiagnostic, Number
from alphalens_evaluation.contracts import Family, digest
from alphalens_evaluation.storage import load
from alphalens_training.contracts import Task, boundary

METRICS = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "pr_auc_average_precision",
    "log_loss",
    "brier_score",
    "mae",
    "rmse",
    "r2",
)


def average_metric(groups: list[dict[str, Any]], name: str) -> float | None:
    values = [float(g[name]) for g in groups if g[name] is not None]
    return mean(values) if values else None


class FoldMetrics(Contract):
    diagnostic_id: Hash
    metrics: dict[str, Number | None]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if not set(self.metrics) <= set(METRICS):
            raise ValueError("Only declared descriptive metrics, never targets")
        return self


class EconomicEvidence(Contract):
    origin: Literal["P10_VERIFIED", "TEST_ONLY_AUTHORED"]
    backtest_id: Hash
    evaluation_id: Hash
    oos_prediction_dataset_id: Hash
    canonical_input_id: Hash
    feature_set_id: Hash
    family: Family
    task: Task
    horizon: Horizon
    period_end: date
    available_at: AwareDatetime
    cost_scenario: str
    source_checksum: Hash
    net_return: Number | None
    maximum_drawdown: Number | None
    turnover: Number | None
    trade_count: int
    unresolved_count: int
    classification: Classification

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.classification == Classification.PRODUCTION
            or self.origin == "TEST_ONLY_AUTHORED"
            and self.classification != Classification.TEST_ONLY
            or self.available_at < boundary(self.period_end + timedelta(days=1))
            or self.trade_count < 0
            or self.unresolved_count < 0
            or self.unresolved_count
            and self.net_return is not None
        ):
            raise ValueError("Invalid economic availability/classification/completeness")
        return self

    @property
    def evidence_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class ComparisonEvidence(Contract):
    fold_metrics: tuple[FoldMetrics, ...] = ()
    economics: tuple[EconomicEvidence, ...] = ()
    ranking: tuple[RankingEvidence, ...] = ()

    @model_validator(mode="after")
    def unique(self) -> Self:
        if (
            len({r.diagnostic_id for r in self.fold_metrics}) != len(self.fold_metrics)
            or len({r.backtest_id for r in self.economics}) != len(self.economics)
            or len({(r.evaluation_id, r.family) for r in self.ranking}) != len(self.ranking)
        ):
            raise ValueError("Ambiguous comparison evidence")
        return self


class RankingEvidence(Contract):
    evaluation_id: Hash
    family: Family
    task: Task
    horizon: Horizon
    available_at: AwareDatetime
    source_checksum: Hash
    classification: Classification
    status: str
    mean_spearman_ic: Number | None
    mean_top_target: Number | None
    mean_bottom_target: Number | None
    mean_top_minus_bottom: Number | None

    @model_validator(mode="after")
    def safe(self) -> Self:
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production ranking evidence is not cleared")
        return self


def load_comparisons(evaluations: list[Path], backtests: list[Path]) -> ComparisonEvidence:
    folds, economics, ranking = [], [], []
    sources = {}
    for path in evaluations:
        oos = load(path)
        sources[oos.manifest["evaluation_id"]] = oos
        reports = json.loads((path / "fold-metrics.json").read_bytes())["folds"]
        diagnostics = project(oos, reports).diagnostics
        for diagnostic in diagnostics:
            report = next(r for r in reports if digest(r) == diagnostic.report_checksum)
            folds.append(
                FoldMetrics(
                    diagnostic_id=diagnostic.evidence_id,
                    metrics={
                        name: report["metrics"][name]
                        for name in METRICS
                        if name in report["metrics"]
                    },
                )
            )
        definition = oos.verify()
        comparison = json.loads((path / "model-comparison.json").read_bytes())["models"]
        for family, entry in comparison.items():
            scored = [
                r
                for r in oos.predictions
                if r.model_family == family and r.scoring_status == "SCORABLE"
            ]
            times = [r.target_available_at for r in scored if r.target_available_at is not None]
            if not times or len(times) != len(scored):
                continue
            groups = entry["ranking"]["sessions"]

            ranking.append(
                RankingEvidence(
                    evaluation_id=oos.manifest["evaluation_id"],
                    family=family,
                    task=definition.task,
                    horizon=definition.horizon,
                    available_at=max(times),
                    source_checksum=digest(entry),
                    classification=definition.data_classification,
                    status=entry["ranking"]["status"],
                    mean_spearman_ic=average_metric(groups, "spearman_ic"),
                    mean_top_target=average_metric(groups, "top_quintile_target"),
                    mean_bottom_target=average_metric(groups, "bottom_quintile_target"),
                    mean_top_minus_bottom=average_metric(groups, "top_minus_bottom_target"),
                )
            )
    for path in backtests:
        manifest = verify(path)
        definition = manifest["identity"]["definition"]
        source = sources.get(definition["evaluation_id"])
        if (
            source is None
            or definition["oos_prediction_dataset_id"]
            != source.manifest["oos_prediction_dataset_id"]
        ):
            raise DataContractError("RANKING_ECONOMIC_OOS_REFERENCE_MISMATCH")
        if definition["baseline"] != "MODEL":
            raise DataContractError("RANKING_COMPARISON_REQUIRES_MODEL_NOT_RANDOM_BASELINE")
        summary = json.loads((path / "summary.json").read_bytes())
        economics.append(
            EconomicEvidence(
                origin="P10_VERIFIED",
                backtest_id=manifest["backtest_id"],
                evaluation_id=definition["evaluation_id"],
                oos_prediction_dataset_id=definition["oos_prediction_dataset_id"],
                canonical_input_id=definition["canonical_input_id"],
                feature_set_id=definition["feature_set_id"],
                family=definition["model_family"],
                task=source.verify().task,
                horizon=definition["horizon"],
                period_end=definition["end_session"],
                available_at=boundary(
                    date.fromisoformat(definition["end_session"]) + timedelta(days=1)
                ),
                cost_scenario=definition["costs"]["name"],
                source_checksum=manifest["checksums"]["summary.json"],
                net_return=summary["net_total_return"],
                maximum_drawdown=summary["maximum_drawdown"],
                turnover=summary["turnover"],
                trade_count=summary["trade_count"],
                unresolved_count=summary["open_or_unresolved_trade_count"],
                classification=manifest["classification"],
            )
        )
    return ComparisonEvidence(
        fold_metrics=tuple(folds), economics=tuple(economics), ranking=tuple(ranking)
    )


def summarize(
    diagnostics: list[ModelDiagnostic],
    extras: ComparisonEvidence,
    economic_rows: list[EconomicEvidence],
    ranking_rows: list[RankingEvidence],
) -> dict[str, Any]:
    result = {}
    metric_map = {r.diagnostic_id: r.metrics for r in extras.fold_metrics}
    for task, families in (
        (
            "classification",
            (
                "logistic",
                "random_forest",
                "hist_gradient_boosting",
                "lightgbm",
                "catboost",
                "xgboost",
            ),
        ),
        (
            "regression",
            ("ridge", "random_forest", "hist_gradient_boosting", "lightgbm", "catboost", "xgboost"),
        ),
    ):
        for family in families:
            ds = sorted(
                (d for d in diagnostics if d.task == task and d.family == family),
                key=lambda d: d.fold_id,
            )
            metrics = {}
            for name in METRICS:
                values = [
                    metric_map[d.evidence_id][name]
                    for d in ds
                    if metric_map.get(d.evidence_id, {}).get(name) is not None
                ]
                numeric = [float(v) for v in values if v is not None]
                if numeric:
                    metrics[name] = dict(
                        mean=mean(numeric),
                        std=pstdev(numeric),
                        minimum=min(numeric),
                        maximum=max(numeric),
                    )
            primary_values = [v for d in ds if (v := d.primary_metric) is not None]
            improvements = [v for d in ds if (v := d.naive_improvement) is not None]
            economics = sorted(
                (e for e in economic_rows if e.family == family and e.task == task),
                key=lambda e: e.backtest_id,
            )
            result[f"{task}:{family}"] = dict(
                status="DESCRIPTIVE_ONLY" if ds else "UNAVAILABLE_AT_CUTOFF",
                evidence_status="INSUFFICIENT_EVIDENCE",
                fold_count=len(ds),
                sample_count=sum(d.sample_count for d in ds),
                primary_metric="brier_score" if task == "classification" else "mae",
                primary_mean=mean(primary_values) if primary_values else None,
                primary_std=pstdev(primary_values) if primary_values else None,
                worst_fold=max(primary_values) if primary_values else None,
                naive_improvement_mean=mean(improvements) if improvements else None,
                fraction_folds_beating_naive=sum(v > 0 for v in improvements) / len(improvements)
                if improvements
                else None,
                calibration_available=bool(ds) and all(d.calibration_available for d in ds),
                metrics=metrics,
                diagnostic_ids=[d.evidence_id for d in ds],
                ranking=[
                    r.model_dump(mode="json")
                    for r in ranking_rows
                    if r.task == task and r.family == family
                ],
                ranking_status="DESCRIPTIVE_ONLY"
                if any(r.task == task and r.family == family for r in ranking_rows)
                else "UNAVAILABLE_AT_CUTOFF",
                economic_status="DESCRIPTIVE_ONLY" if economics else "UNAVAILABLE_AT_CUTOFF",
                economics=[e.model_dump(mode="json") for e in economics],
                automatic_winner=False,
            )
    return result
