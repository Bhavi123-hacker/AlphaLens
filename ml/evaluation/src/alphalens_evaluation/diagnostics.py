"""Descriptive OOS stability and fixed cross-sectional groups; never trading profit."""

from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import spearmanr, t

from alphalens_evaluation.contracts import OOSPrediction, WalkForwardDefinition


def rank_diagnostics(
    rows: list[OOSPrediction], definition: WalkForwardDefinition
) -> dict[str, Any]:
    groups: dict[str, list[OOSPrediction]] = defaultdict(list)
    for row in rows:
        if row.scoring_status != "SCORABLE" or row.actual_forward_return is None:
            continue
        groups[row.session_date.isoformat()].append(row)
    summaries = []
    for session, peers in sorted(groups.items()):
        if len(peers) < definition.ranking_minimum_securities:
            continue
        ordered = sorted(
            peers,
            key=lambda r: (
                -(r.probability if r.probability is not None else r.prediction),
                r.security_id,
            ),
        )
        count = max(1, int(len(peers) * definition.ranking_quantile))
        actual = np.asarray([float(str(r.actual_forward_return)) for r in ordered])
        score = np.asarray(
            [r.probability if r.probability is not None else r.prediction for r in ordered]
        )
        ic = float(spearmanr(score, actual).statistic) if np.ptp(score) and np.ptp(actual) else None
        top, bottom = float(actual[:count].mean()), float(actual[-count:].mean())
        summaries.append(
            dict(
                session=session,
                sample_count=len(peers),
                spearman_ic=ic,
                top_quintile_target=top,
                bottom_quintile_target=bottom,
                top_minus_bottom_target=top - bottom,
            )
        )
    return dict(
        status="DESCRIPTIVE_TARGET_DIAGNOSTIC_NOT_PROFIT"
        if summaries
        else "INSUFFICIENT_CROSS_SECTIONAL_EVIDENCE",
        quantile=definition.ranking_quantile,
        minimum_securities=definition.ranking_minimum_securities,
        sessions=summaries,
    )


def stability(reports: list[dict[str, Any]], definition: WalkForwardDefinition) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for family in definition.model_families:
        folds = [
            r
            for r in reports
            if r["model_family"] == family
            and r["status"] == "EVALUATED"
            and r["metrics"].get("sample_count", 0) > 0
        ]
        metrics: dict[str, Any] = {}
        names = sorted(
            {
                k
                for r in folds
                for k, v in r["metrics"].items()
                if isinstance(v, (int, float)) and k != "sample_count"
            }
        )
        for name in names:
            values = [
                float(r["metrics"][name]) for r in folds if r["metrics"].get(name) is not None
            ]
            if not values:
                continue
            lower = name in ("brier_score", "log_loss", "mae", "rmse")
            worst = max(values) if lower else min(values)
            best = min(values) if lower else max(values)
            metrics[name] = dict(
                mean=float(np.mean(values)),
                median=float(np.median(values)),
                standard_deviation=float(np.std(values)),
                worst_fold=worst,
                best_fold=best,
                fold_count=len(values),
            )
        result[family] = dict(
            metrics=metrics,
            evaluated_fold_count=len(folds),
            requested_fold_count=len(definition.folds),
            percentage_beating_naive=100 * sum(r["beats_naive"] for r in folds) / len(folds)
            if folds
            else None,
            samples_by_fold={r["fold_id"]: r["test_rows"] for r in folds},
        )
    return result


def uncertainty(
    values: list[float], sessions: int, definition: WalkForwardDefinition
) -> dict[str, Any]:
    # Folds, rather than individual correlated securities, are the sampling unit.
    if (
        definition.data_classification.value == "TEST_ONLY"
        or len(values) < definition.uncertainty_minimum_folds
        or sessions < definition.uncertainty_minimum_sessions
    ):
        return dict(status="INSUFFICIENT_EVIDENCE", interval=None)
    margin = float(t.ppf(0.975, len(values) - 1) * np.std(values, ddof=1) / np.sqrt(len(values)))
    mean = float(np.mean(values))
    return dict(
        status="DESCRIPTIVE_FOLD_MEAN_INTERVAL_NOT_SIGNIFICANCE",
        method="95_PERCENT_STUDENT_T_FOLD_MEAN_APPROXIMATION",
        interval=[mean - margin, mean + margin],
        limitation="Expanding folds share training history; independence is approximate",
    )
