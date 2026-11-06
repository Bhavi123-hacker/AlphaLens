"""Deterministic archival descriptors. No fitting, recommendations or policy promotion."""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from statistics import median, pstdev
from typing import Any

import numpy as np

VERSION = "p29.descriptive-intelligence.v1"
MIN_SAMPLES = 128
MIN_COVERAGE = 0.8
FIELDS = (
    "return_1",
    "return_20",
    "volatility_20",
    "distance_sma_20",
    "drawdown_20",
    "rsi_14",
    "volume_ratio_20",
)


def number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value):
        return float(value)
    return None


def values(rows: list[dict[str, Any]], field: str) -> list[float]:
    return [n for row in rows if (n := number(row.get(field))) is not None]


def describe(values_: list[float]) -> dict[str, Any]:
    return {
        "n": len(values_),
        "median": median(values_) if values_ else None,
        "q10": float(np.quantile(values_, 0.1)) if values_ else None,
        "q90": float(np.quantile(values_, 0.9)) if values_ else None,
        "std": pstdev(values_) if len(values_) > 1 else None,
    }


def regime(
    rows: list[dict[str, Any]],
    session: date,
    *,
    cutoff: datetime | None = None,
    strict_pit: bool = False,
) -> dict[str, Any]:
    """Fixed interpretation assumptions predeclared before viewing new results."""
    reasons: Counter[str] = Counter()
    eligible = []
    seen = set()
    for row in rows:
        if row.get("session") != session.isoformat():
            reasons["SESSION_MISMATCH_EXCLUDED"] += 1
            continue
        security = row.get("security_id")
        if not security or security in seen:
            raise ValueError("UNIQUE_OBSERVED_IDENTITIES_REQUIRED")
        seen.add(security)
        try:
            price = Decimal(str(row.get("close")))
        except InvalidOperation:
            price = Decimal("NaN")
        if row.get("quality") not in {"VALID", "DEGRADED"} or not price.is_finite() or price <= 0:
            reasons["PRICE_OR_QUALITY_UNAVAILABLE"] += 1
            continue
        if strict_pit:
            available = row.get("available_at")
            if cutoff is None or cutoff.tzinfo is None or not available:
                reasons["ACTUAL_AVAILABILITY_UNKNOWN"] += 1
                continue
            try:
                stamp = datetime.fromisoformat(available)
            except (TypeError, ValueError):
                reasons["ACTUAL_AVAILABILITY_INVALID"] += 1
                continue
            if stamp.tzinfo is None or stamp > cutoff:
                reasons["NOT_AVAILABLE_AT_CUTOFF"] += 1
                continue
        eligible.append(row)
    metrics = {field: describe(values(eligible, field)) for field in FIELDS}
    denominator = len(eligible)
    required = ("return_1", "return_20", "volatility_20", "distance_sma_20", "drawdown_20")
    coverage: dict[str, float | None] = {
        name: metrics[name]["n"] / denominator if denominator else None for name in FIELDS
    }
    sufficient = denominator >= MIN_SAMPLES and all(
        c is not None and c >= MIN_COVERAGE for c in (coverage[n] for n in required)
    )
    if denominator < MIN_SAMPLES:
        reasons["MINIMUM_OBSERVED_SAMPLE_NOT_MET"] += 1
    for name in required:
        c = coverage[name]
        if c is None or c < MIN_COVERAGE:
            reasons["MISSING_REQUIRED_METRIC_" + name.upper()] += 1
    returns = values(eligible, "return_1")
    trends = values(eligible, "distance_sma_20")
    drawdowns = values(eligible, "drawdown_20")
    breadth = (
        ((sum(v > 0 for v in returns) - sum(v < 0 for v in returns)) / len(returns))
        if returns
        else None
    )
    participation = sum(v > 0 for v in trends) / len(trends) if trends else None
    stress = sum(v < -0.1 for v in drawdowns) / len(drawdowns) if drawdowns else None
    classification = "INSUFFICIENT_EVIDENCE"
    if sufficient:
        momentum = metrics["return_20"]["median"]
        volatility = metrics["volatility_20"]["median"]
        if volatility > 0.03 and stress is not None and stress >= 0.2:
            classification = "HIGH_VOLATILITY_STRESS"
        elif momentum > 0.03 and participation is not None and participation >= 0.6:
            classification = "BROAD_OBSERVED_UPTREND"
        elif momentum < -0.03 and participation is not None and participation <= 0.4:
            classification = "BROAD_OBSERVED_DOWNTREND"
        else:
            classification = "MIXED_SIDEWAYS"
    return {
        "version": VERSION,
        "session": session.isoformat(),
        "classification": classification,
        "mode": "EVIDENCE_GATED_PIT" if strict_pit else "RETROSPECTIVE_FINAL_VINTAGE_DESCRIPTION",
        "observed_cohort": sum(r.get("session") == str(session) for r in rows),
        "eligible_observed": denominator,
        "exclusions": dict(sorted(reasons.items())),
        "metrics": metrics,
        "metric_coverage": coverage,
        "advance_decline_balance": breadth,
        "trend_participation": participation,
        "drawdown_stress_fraction": stress,
        "quality_counts": dict(
            Counter(
                str(r.get("quality", "UNKNOWN")) for r in rows if r.get("session") == str(session)
            )
        ),
        "minimum_samples": MIN_SAMPLES,
        "minimum_metric_coverage": MIN_COVERAGE,
        "interpretation": "DESCRIPTIVE_NOT_FORECAST_OR_RECOMMENDATION",
        "universe": "OBSERVED_SOURCE_COHORT_NOT_ENTIRE_NSE_OR_SURVIVORSHIP_CONTROL",
        "threshold_basis": "PREDECLARED_EXPLORATORY_ASSUMPTIONS_NOT_FITTED_TO_HOLDOUT",
    }


def drift(
    reference: list[dict[str, Any]],
    current: list[dict[str, Any]],
    reference_session: date,
    session: date,
) -> dict[str, Any]:
    if reference_session >= session:
        raise ValueError("PAST_ONLY_REFERENCE_SESSION_REQUIRED")
    for rows, day in ((reference, reference_session), (current, session)):
        if len({r["security_id"] for r in rows}) != len(rows) or any(
            r["session"] != str(day) for r in rows
        ):
            raise ValueError("UNIQUE_MATCHING_SESSION_ROWS_REQUIRED")
    before = {r["security_id"]: r for r in reference}
    after = {r["security_id"]: r for r in current}
    common = sorted(set(before) & set(after))
    columns = []
    for field in FIELDS:
        a, b = values(reference, field), values(current, field)
        paired: list[tuple[float, float]] = []
        for s in common:
            x, y = number(before[s].get(field)), number(after[s].get(field))
            if x is not None and y is not None:
                paired.append((x, y))
        sufficient = min(len(a), len(b)) >= MIN_SAMPLES
        distance = None
        if sufficient:
            from scipy.stats import wasserstein_distance

            distance = float(wasserstein_distance(a, b))
        columns.append(
            {
                "feature": field,
                "reference": describe(a),
                "current": describe(b),
                "wasserstein_1": distance,
                "distance_units": "ORIGINAL_FEATURE_UNITS_NOT_P_VALUE",
                "state": "DESCRIPTIVE_DISTANCE_AVAILABLE" if sufficient else "INSUFFICIENT_SAMPLES",
                "paired_count": len(paired),
                "paired_median_change": median([y - x for x, y in paired])
                if len(paired) >= MIN_SAMPLES
                else None,
                "missingness_reference": 1 - len(a) / len(reference) if reference else None,
                "missingness_current": 1 - len(b) / len(current) if current else None,
            }
        )
    return {
        "version": VERSION,
        "reference_session": str(reference_session),
        "session": str(session),
        "observed_reference": len(before),
        "observed_current": len(after),
        "common": len(common),
        "entered_observed": len(set(after) - set(before)),
        "departed_observed": len(set(before) - set(after)),
        "cohort_jaccard": len(common) / len(set(before) | set(after)) if before or after else None,
        "features": columns,
        "statistical_significance": "NOT_TESTED",
        "automatic_model_action": "DISABLED",
        "interpretation": "EMPIRICAL_SOURCE_COHORT_DIFFERENCE_NOT_MODEL_DECAY_PROOF",
    }


def reliability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = []
    folds: dict[tuple[str, str, int], list[float]] = {}
    for row in rows:
        metrics = row.get("metrics") or {}
        count = int(row.get("scored_test_rows") or 0)
        balanced = number(metrics.get("balanced_accuracy"))
        baseline = number((row.get("naive") or {}).get("balanced_accuracy"))
        calibration = metrics.get("calibration") or {}
        matrix.append(
            {
                "model_run_id": row["model_run_id"],
                "family": row.get("model_family", "UNAVAILABLE"),
                "task": row["task"],
                "horizon": row["horizon"],
                "phase": row["phase"],
                "fold": row.get("fold_id"),
                "samples": count,
                "sample_status": "RECORDED_SAMPLE_AVAILABLE"
                if count >= MIN_SAMPLES
                else "INSUFFICIENT_SAMPLES",
                "balanced_accuracy": balanced,
                "baseline_balanced_accuracy": baseline,
                "baseline_delta": balanced - baseline
                if balanced is not None and baseline is not None
                else None,
                "metric_evidence": "RECORDED_METRIC_AVAILABLE" if metrics else "UNAVAILABLE",
                "calibration": "RECORDED_BINS_AVAILABLE"
                if calibration.get("bins")
                else "CALIBRATION_UNAVAILABLE",
                "metrics": metrics,
                "naive_metrics": row.get("naive") or {},
                "class_distribution": metrics.get("class_distribution"),
                "economics": "FULL_PATH_ECONOMIC_ACCEPTANCE_NOT_ESTABLISHED",
                "current_inference": "NOT_ELIGIBLE",
                "holdout_use": "DISPLAY_ONLY_NO_SELECTION_OR_RETUNING"
                if row["phase"] == "2026"
                else "RECORDED_CHRONOLOGICAL_RESEARCH",
            }
        )
        # Stability summarizes development folds only; 2025/2026 never become tuning evidence.
        if balanced is not None and row["phase"] == "development":
            key = row.get("model_family", "UNAVAILABLE"), row["task"], int(row["horizon"])
            folds.setdefault(key, []).append(balanced)
    return {
        "version": VERSION,
        "matrix": matrix,
        "development_stability": [
            {
                "family": k[0],
                "task": k[1],
                "horizon": k[2],
                "fold_count": len(v),
                "mean": float(np.mean(v)),
                "std": pstdev(v) if len(v) > 1 else None,
            }
            for k, v in sorted(folds.items())
        ],
        "acceptance": "UNCHANGED_INSUFFICIENT_INDEPENDENT_EVIDENCE",
        "sample_guard": "128_IS_DESCRIPTIVE_DISPLAY_GUARD_NOT_STATISTICAL_POWER_GUARANTEE",
        "probabilities": "UNCALIBRATED_ESTIMATES_NOT_REALIZED_SUCCESS_RATES",
        "model_disagreement": "UNAVAILABLE_WITHOUT_ALIGNED_COMMON_OOS_EVIDENCE",
    }
