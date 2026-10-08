"""Locked research P8-P10 orchestration; never broker, API or live execution."""

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_backtesting.contracts import scenarios
from alphalens_backtesting.research import ResearchPrices, run_research
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchCalendar, lineage
from alphalens_evaluation.research import (
    development,
    evaluate_fold,
    file_hash,
    load_matrix,
    locked_folds,
)

CRITERIA = (
    "mean_rank_ic",
    "mean_top_minus_bottom",
    "folds_beating_naive",
    "worst_fold_rank_ic",
    "naive_relative_improvement",
    "low_cost_return",
    "low_cost_sharpe",
    "negative_drawdown",
    "negative_turnover",
    "stress_return",
)


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(value))


def freeze_plan(root: Path, output: Path) -> dict[str, Any]:
    dataset = json.loads((root / "supervised-manifest.json").read_bytes())
    sessions = ResearchCalendar.model_validate_json((root / "research-calendar.json").read_bytes())
    plan = dict(
        **lineage(sessions.profile),
        dataset_id=dataset["dataset_id"],
        evaluation_periods=dict(
            early_warmup=[2010, 2014],
            development_training=[2015, 2021],
            development_oos=[2022, 2023, 2024],
            confirmation=2025,
            final_holdout=2026,
        ),
        development_folds=[
            f.model_dump(mode="json") for f in locked_folds(sessions, (2022, 2023, 2024))
        ],
        confirmation_fold=locked_folds(sessions, (2025,))[0].model_dump(mode="json"),
        final_holdout_fold=locked_folds(sessions, (2026,))[0].model_dump(mode="json"),
        embargo_seconds=86400,
        training_start="2015-01-01",
        availability_purge="LABEL_AVAILABLE_BY_CUTOFF_STRICTLY_BEFORE_TEST_DATE",
        arena="EXISTING_P9_32_TREES_ONE_THREAD_SEED_1729_NO_SEARCH",
        family_selection="EQUAL_WEIGHT_ORDINAL_MULTI_METRIC_DEVELOPMENT_ONLY_V1",
        selection_criteria=list(CRITERIA),
        missing_metric_rank=0,
        execution_policies=["TOP_K", "TOP_PERCENTILE", "PREDICTION_THRESHOLD"],
        cost_scenarios=[s.model_dump(mode="json") for s in scenarios()],
        stress_display_alias="STRESS_COST_ASSUMPTION = existing HIGHER_COST_STRESS",
        code_hashes={
            p: file_hash(Path(p))
            for p in (
                "scripts/run_tejhq_research.py",
                "ml/evaluation/src/alphalens_evaluation/research.py",
                "ml/evaluation/src/alphalens_evaluation/models.py",
                "backtesting/src/alphalens_backtesting/research.py",
            )
        },
        policy_scope="ENGINEERED_RESEARCH_COMPARISON_NOT_CALIBRATED_PRODUCT_POLICY",
        final_holdout_performance_inspected_at_lock=False,
    )
    path = output / "training-plan.json"
    if path.exists() and json.loads(path.read_bytes()) != plan:
        raise ValueError("FROZEN_TRAINING_PLAN_CHANGED_NEW_EXPLICIT_RUN_REQUIRED")
    save(path, plan)
    save(Path("docs/ml/research-training-plan.json"), plan)
    return plan


def compact_report(report: dict[str, Any]) -> dict[str, Any]:
    payload = {k: v for k, v in report.items() if k != "ranking"}
    payload["ranking"] = {k: v for k, v in report["ranking"].items() if k != "sessions"}
    return payload


def summarize_models(
    reports: list[dict[str, Any]], backtests: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in reports:
        grouped[(r["task"], r["horizon"], r["model_family"])].append(r)
    output = []
    for (task, h, family), folds in sorted(grouped.items()):
        names = sorted(
            {
                n
                for r in folds
                for n, v in r["metrics"].items()
                if isinstance(v, (float, int)) and n != "sample_count"
            }
        )
        metrics = {}
        for n in names:
            values = [float(r["metrics"][n]) for r in folds if r["metrics"].get(n) is not None]
            if values:
                lower = n in {"mae", "rmse", "brier_score", "log_loss"}
                metrics[n] = dict(
                    mean=float(np.mean(values)),
                    median=float(np.median(values)),
                    std=float(np.std(values)),
                    best=min(values) if lower else max(values),
                    worst=max(values) if lower else min(values),
                )
        chosen = [
            b
            for b in backtests
            if (b["task"], b["horizon"], b["model_family"], b["selection_rule"])
            == (task, h, family, "TOP_K")
        ]
        low = next((b for b in chosen if b["cost_scenario"] == "LOW_COST_ASSUMPTION"), None)
        stress = next((b for b in chosen if b["cost_scenario"] == "HIGHER_COST_STRESS"), None)
        ic = [
            r["ranking"]["mean_rank_ic"] for r in folds if r["ranking"]["mean_rank_ic"] is not None
        ]
        spreads = [
            r["ranking"]["mean_top_minus_bottom"]
            for r in folds
            if r["ranking"]["mean_top_minus_bottom"] is not None
        ]
        improvements = [
            r["naive_relative_improvement"]
            for r in folds
            if r["naive_relative_improvement"] is not None
        ]
        row = dict(
            task=task,
            horizon=h,
            model_family=family,
            fold_metrics=metrics,
            requested_folds=3,
            evaluated_folds=len(folds),
            training_samples=[r["training_rows"] for r in folds],
            oos_samples=sum(r["scored_test_rows"] for r in folds),
            folds_beating_naive=sum(r["beats_naive"] for r in folds) / len(folds),
            mean_rank_ic=float(np.mean(ic)) if ic else None,
            worst_fold_rank_ic=min(ic) if ic else None,
            mean_top_minus_bottom=float(np.mean(spreads)) if spreads else None,
            naive_relative_improvement=float(np.mean(improvements)) if improvements else None,
            low_cost_return=low["total_return"] if low else None,
            low_cost_sharpe=low["sharpe"] if low else None,
            negative_drawdown=-low["maximum_drawdown"]
            if low and low["maximum_drawdown"] is not None
            else None,
            negative_turnover=-low["turnover"] if low and low["turnover"] is not None else None,
            stress_return=stress["total_return"] if stress else None,
            cost_metrics_status=low["status"] if low else "NOT_RUN",
            uncertainty="INSUFFICIENT_FOLDS_FOR_STRONG_SIGNIFICANCE_CLAIM",
        )
        row["research_status"] = (
            "REAL_RESEARCH_INSUFFICIENT_EVIDENCE"
            if not low or low["total_return"] is None
            else (
                "REAL_RESEARCH_CANDIDATE"
                if row["folds_beating_naive"] >= 2 / 3
                and row["mean_rank_ic"] is not None
                and row["mean_rank_ic"] > 0
                else "REAL_RESEARCH_DOES_NOT_BEAT_NAIVE"
            )
        )
        output.append(row)
    return output


def candidate_lock(
    root: Path, output: Path, reports: list[dict[str, Any]], backtests: list[dict[str, Any]]
) -> dict[str, Any]:
    plan = freeze_plan(root, output)
    models = summarize_models(reports, backtests)
    chosen = {}
    for h in (1, 5, 10, 20):
        peers = [r for r in models if r["horizon"] == h]
        for r in peers:
            r["selection_scores"] = {}
        for criterion in CRITERIA:
            values = [r[criterion] for r in peers if r[criterion] is not None]
            for r in peers:
                value = r[criterion]
                score = (
                    0.0
                    if value is None or len(values) < 2
                    else (
                        sum(v < value for v in values) + (sum(v == value for v in values) - 1) / 2
                    )
                    / (len(values) - 1)
                )
                r["selection_scores"][criterion] = score
        for r in peers:
            r["selection_score"] = float(np.mean(list(r["selection_scores"].values())))
        winner = sorted(peers, key=lambda r: (-r["selection_score"], r["task"], r["model_family"]))[
            0
        ]
        chosen[str(h)] = {
            k: winner[k]
            for k in (
                "task",
                "model_family",
                "research_status",
                "selection_score",
                "selection_scores",
            )
        }
    profile = ResearchCalendar.model_validate_json(
        (root / "research-calendar.json").read_bytes()
    ).profile
    payload = dict(
        **lineage(profile),
        dataset_id=plan["dataset_id"],
        plan_sha256=checksum(stable_json(plan)),
        selected=chosen,
        selection_source="2022_2024_DEVELOPMENT_OOS_AND_P10_ONLY",
        confirmation_used_for_selection=False,
        final_holdout_used_for_selection=False,
        final_holdout_evaluation_policy="ONCE_NO_RETUNING",
        analytical_selection_time="DEVELOPMENT_INFORMATION_SCOPE_NOT_ACTUAL_2025_SELECTION_CLAIM",
    )
    result = dict(identity=payload, candidate_lock_id=checksum(stable_json(payload)))
    path = output / "candidate-lock.json"
    if path.exists() and json.loads(path.read_bytes()) != result:
        raise ValueError("RESEARCH_CANDIDATE_LOCK_CHANGED")
    save(path, result)
    save(Path("docs/ml/research-candidate-lock.json"), result)
    save(
        output / "candidate-lock-audit.json",
        dict(
            **lineage(profile),
            recorded_at=datetime.now(UTC).isoformat(),
            candidate_lock_id=result["candidate_lock_id"],
        ),
    )
    save(
        Path("docs/ml/real-model-comparison.json"),
        dict(
            **lineage(profile),
            models=models,
            selected=chosen,
            final_holdout_evaluated=False,
            selection_policy=list(CRITERIA),
        ),
    )
    return result


def evaluate_selected(root: Path, output: Path, year: int) -> list[dict[str, Any]]:
    # Do not even load final-period targets without a validated pre-holdout lock.
    path = output / "candidate-lock.json"
    if not path.exists():
        raise ValueError("FINAL_OR_CONFIRMATION_EVALUATION_REQUIRES_CANDIDATE_LOCK")
    lock = json.loads(path.read_bytes())
    plan = freeze_plan(root, output)
    if checksum(stable_json(lock["identity"])) != lock["candidate_lock_id"] or lock["identity"][
        "plan_sha256"
    ] != checksum(stable_json(plan)):
        raise ValueError("PRE_HOLDOUT_LOCK_IDENTITY_MISMATCH")
    marker = output / f"{year}-evaluation-lock.json"
    profile = ResearchCalendar.model_validate_json(
        (root / "research-calendar.json").read_bytes()
    ).profile
    event = dict(
        **lineage(profile),
        candidate_lock_id=lock["candidate_lock_id"],
        year=year,
        policy="ONCE_NO_RETUNING",
    )
    if marker.exists() and json.loads(marker.read_bytes()) != event:
        raise ValueError("HOLDOUT_REEVALUATION_CONFIGURATION_CHANGED")
    save(marker, event)
    reports = []
    for h in (1, 5, 10, 20):
        chosen = lock["identity"]["selected"][str(h)]
        matrix = load_matrix(root, h)
        fold = locked_folds(matrix.sessions, (year,))[0]
        reports.append(
            evaluate_fold(matrix, fold, chosen["task"], chosen["model_family"], output / "p9")
        )
        del matrix
    save(
        output / f"{year}-results.json",
        dict(**lineage(profile), reports=reports, candidate_lock_id=lock["candidate_lock_id"]),
    )
    return reports


def backtest_reports(
    root: Path, output: Path, reports: list[dict[str, Any]], phase: str
) -> list[dict[str, Any]]:
    prices = ResearchPrices(root)
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in reports:
        grouped[(r["task"], r["horizon"], r["model_family"])].append(r)
    summaries = []
    for key, folds in sorted(grouped.items()):
        for rule in ("TOP_K", "TOP_PERCENTILE", "PREDICTION_THRESHOLD"):
            for cost in scenarios():
                result = run_research(folds, output / "p9", prices, cost, rule, output / "p10")
                result["phase"] = phase
                summaries.append(result)
        print(json.dumps(dict(stage="p10", phase=phase, model=list(key))), flush=True)
        save(output / f"{phase}-backtests.json", dict(backtests=summaries))
    return summaries


def export_series(
    output: Path, reports: list[dict[str, Any]], backtests: list[dict[str, Any]], profile: Any
) -> dict[str, Any]:
    """Stream existing immutable observations into UI-ready local contracts."""
    directory = output / "series"
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {b"research_lineage": stable_json(lineage(profile))}
    oos_schema = pa.schema(
        [
            ("phase", pa.string()),
            ("task", pa.string()),
            ("horizon", pa.int8()),
            ("model_family", pa.string()),
            ("model_run_id", pa.string()),
            ("fold_id", pa.string()),
            ("security_id", pa.string()),
            ("session_date", pa.date32()),
            ("decision_time", pa.timestamp("us", tz="UTC")),
            ("prediction_id", pa.string()),
            ("canonical_record_id", pa.string()),
            ("score", pa.float64()),
            ("prediction", pa.float64()),
            ("realized_forward_target", pa.string()),
            ("realized_direction", pa.int8()),
            ("label_available_at", pa.timestamp("us", tz="UTC")),
            ("scorable", pa.bool_()),
        ],
        metadata={**metadata, b"role": b"FOLD_TEST"},
    )
    oos_path = directory / "walk-forward-oos-predictions.parquet"
    oos_count = 0
    with pq.ParquetWriter(oos_path, oos_schema, compression="zstd") as writer:
        for r in reports:
            path = output / "p9" / r["oos_file"]
            if file_hash(path) != r["oos_sha256"]:
                raise ValueError("EXPORT_OOS_CHECKSUM_MISMATCH")
            h = r["horizon"]
            mapping = dict(
                realized_forward_target=f"target_return_{h}",
                realized_direction=f"target_direction_{h}",
                label_available_at=f"label_available_at_{h}",
            )
            constants = dict(
                phase=r["phase"],
                task=r["task"],
                horizon=h,
                model_family=r["model_family"],
                model_run_id=r["model_run_id"],
                fold_id=r["fold_id"],
            )
            reader = pq.ParquetFile(path)
            for batch in reader.iter_batches(batch_size=32768):
                table = pa.Table.from_batches([batch])
                arrays = [
                    pa.array([constants[f.name]] * len(table), type=f.type)
                    if f.name in constants
                    else table.column(mapping.get(f.name, f.name)).cast(f.type)
                    for f in oos_schema
                ]
                writer.write_table(pa.Table.from_arrays(arrays, schema=oos_schema))
                oos_count += len(table)
    equity_schema = pa.schema(
        [
            ("phase", pa.string()),
            ("backtest_id", pa.string()),
            ("task", pa.string()),
            ("horizon", pa.int8()),
            ("model_family", pa.string()),
            ("selection_rule", pa.string()),
            ("cost_scenario", pa.string()),
            ("session", pa.string()),
            ("cash", pa.string()),
            ("market_value", pa.string()),
            ("portfolio_value", pa.string()),
            ("realized_pnl", pa.string()),
            ("unrealized_pnl", pa.string()),
            ("total_pnl", pa.string()),
            ("session_pnl", pa.string()),
            ("drawdown", pa.float64()),
            ("open_positions", pa.int64()),
            ("cash_utilization", pa.float64()),
            ("freshness", pa.string()),
            ("quality", pa.string()),
            ("knowledge_cutoff", pa.string()),
        ],
        metadata=metadata,
    )
    equity_path = directory / "backtest-equity-curves.parquet"
    equity_count = 0
    with pq.ParquetWriter(equity_path, equity_schema, compression="zstd") as writer:
        for r in backtests:
            path = output / "p10" / r["backtest_id"] / "equity.parquet"
            constants = {
                n: r[n]
                for n in (
                    "phase",
                    "backtest_id",
                    "task",
                    "horizon",
                    "model_family",
                    "selection_rule",
                    "cost_scenario",
                )
            }
            for batch in pq.ParquetFile(path).iter_batches(batch_size=32768):
                table = pa.Table.from_batches([batch])
                arrays = [
                    pa.array([constants[f.name]] * len(table), type=f.type)
                    if f.name in constants
                    else table.column(f.name).cast(f.type)
                    for f in equity_schema
                ]
                writer.write_table(pa.Table.from_arrays(arrays, schema=equity_schema))
                equity_count += len(table)
    return dict(
        **lineage(profile),
        files=[
            dict(
                path=str(p.relative_to(output)),
                rows=count,
                sha256=file_hash(p),
                bytes=p.stat().st_size,
            )
            for p, count in ((oos_path, oos_count), (equity_path, equity_count))
        ],
        price_history="CHECKSUM_PINNED_P5_CANONICAL_OHLCV_PARTITIONS",
        trade_markers="P10_PER_RUN_TRADES_PARQUET_PRICE_RECORD_REFERENCES",
        benchmark="UNAVAILABLE",
    )


def summaries(root: Path, output: Path) -> None:
    profile = ResearchCalendar.model_validate_json(
        (root / "research-calendar.json").read_bytes()
    ).profile
    reports = []
    backtests = []
    for phase, name in (
        ("development", "p9/development-results.json"),
        ("2025", "2025-results.json"),
        ("2026", "2026-results.json"),
    ):
        for r in json.loads((output / name).read_bytes())["reports"]:
            reports.append(dict(r, phase=phase))
        backtests.extend(json.loads((output / f"{phase}-backtests.json").read_bytes())["backtests"])
    exports = export_series(output, reports, backtests, profile)
    save(output / "series-manifest.json", exports)
    save(Path("docs/data/research-chart-series.json"), exports)
    plan = freeze_plan(root, output)
    save(
        Path("docs/ml/real-model-runs.json"),
        dict(
            **lineage(profile),
            plan=plan,
            models_trained=len(reports),
            reports=[compact_report(r) for r in reports],
        ),
    )
    save(
        Path("docs/ml/walk-forward-results.json"),
        dict(
            **lineage(profile),
            plan=plan,
            folds=[compact_report(r) for r in reports],
            final_holdout_evaluated=True,
            final_holdout_retuned=False,
        ),
    )
    comparison = json.loads(Path("docs/ml/real-model-comparison.json").read_bytes())
    comparison.update(
        final_holdout_evaluated=True,
        confirmation=[compact_report(r) for r in reports if r["phase"] == "2025"],
        final_holdout=[compact_report(r) for r in reports if r["phase"] == "2026"],
    )
    save(Path("docs/ml/real-model-comparison.json"), comparison)
    save(
        Path("docs/backtesting/backtest-comparison.json"),
        dict(
            **lineage(profile),
            backtests=[{k: v for k, v in r.items() if k != "identity"} for r in backtests],
            final_holdout_evaluated=True,
            benchmark="UNAVAILABLE",
            costs="ENGINEERED_DEVELOPMENT_ASSUMPTIONS",
        ),
    )
    readiness = dict(
        **lineage(profile),
        dataset_id=plan["dataset_id"],
        pipeline="REAL_RESEARCH_P4_P10_COMPLETED_PENDING_REPOSITORY_GATES",
        model_fits=len(reports),
        backtest_runs=len(backtests),
        final_holdout="EVALUATED_ONCE_AFTER_CANDIDATE_LOCK_NO_RETUNING",
        benchmark="UNAVAILABLE",
        fundamentals="UNAVAILABLE",
        p1_production_data_clearance="OPEN",
        production_market_data_use="NOT_CLEARED",
        p17="NOT_STARTED",
        p11_p14_calibration="NOT_CHANGED_REQUIRES_USER_REVIEW",
        software_verification="PENDING_FINAL_FULL_GATES",
    )
    save(Path("docs/development/real-data-readiness.json"), readiness)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("development", "backtest-selection", "confirmation", "final", "summaries"),
        required=True,
    )
    args = parser.parse_args()
    root = args.data_root
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    if args.stage == "development":
        plan = freeze_plan(root, output)
        reports = development(root, output / "p9")
        save(
            Path("docs/ml/real-model-runs.json"),
            dict(
                plan=plan, models_trained=len(reports), reports=[compact_report(r) for r in reports]
            ),
        )
        save(
            Path("docs/ml/walk-forward-results.json"),
            dict(
                plan=plan, folds=[compact_report(r) for r in reports], final_holdout_evaluated=False
            ),
        )
    elif args.stage == "backtest-selection":
        reports = json.loads((output / "p9/development-results.json").read_bytes())["reports"]
        b = backtest_reports(root, output, reports, "development")
        candidate_lock(root, output, reports, b)
        save(
            Path("docs/backtesting/backtest-comparison.json"),
            dict(
                backtests=[{k: v for k, v in x.items() if k != "identity"} for x in b],
                final_holdout_evaluated=False,
            ),
        )
    elif args.stage in ("confirmation", "final"):
        year = 2025 if args.stage == "confirmation" else 2026
        if year == 2026 and not (output / "2025-results.json").exists():
            raise ValueError("CONFIRMATION_MUST_PRECEDE_FINAL_HOLDOUT")
        reports = evaluate_selected(root, output, year)
        backtest_reports(root, output, reports, str(year))
    else:
        summaries(root, output)


if __name__ == "__main__":
    main()
