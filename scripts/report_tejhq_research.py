"""Deterministic reports from completed research artifacts; no fitting or selection."""

import argparse
import json
from pathlib import Path
from typing import Any


def read(path: str) -> dict[str, Any]:
    return dict(json.loads(Path(path).read_bytes()))


def cell(value: Any) -> str:
    if value is None:
        return "UNAVAILABLE"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "/").replace("\n", " ")


def table(names: list[str], rows: list[list[Any]]) -> str:
    return (
        "\n".join(
            ["| " + " | ".join(names) + " |", "| " + " | ".join("---" for _ in names) + " |"]
            + ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
        )
        + "\n"
    )


def publish(path: str, text: str) -> None:
    p = Path(path)
    old = p.read_text(encoding="utf-8")
    heading = "## Historical preparation and earlier gates\n\n"
    if heading in old:
        old = old.split(heading, 1)[1]
    p.write_text(text + "\n" + heading + old, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    canonical = read("docs/data/research-canonical-summary.json")
    identity = read("docs/data/research-identity-profile.json")
    supervised = read("docs/data/research-dataset-identity.json")
    features = read("docs/ml/feature-availability.json")
    labels = read("docs/ml/label-distribution.json")
    action_impact = read("docs/data/research-corporate-action-impact.json")
    runs = read("docs/ml/real-model-runs.json")
    comparison = read("docs/ml/real-model-comparison.json")
    backtests = read("docs/backtesting/backtest-comparison.json")
    fit_diagnostics = read("docs/ml/real-model-fit-diagnostics.json")
    logistic_count = sum(r["model_family"] == "logistic" for r in runs["reports"])
    if len(fit_diagnostics["diagnostics"]) != logistic_count:
        raise ValueError("FIT_DIAGNOSTICS_INCOMPLETE")
    limit_count = sum(r["iteration_limit_reached"] for r in fit_diagnostics["diagnostics"])
    if not comparison["final_holdout_evaluated"]:
        raise ValueError("REPORT_REQUIRES_COMPLETED_LOCKED_FINAL_HOLDOUT")
    warning = (
        "REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION.\n"
        "NOT PRODUCTION PIT; historical revision timing remains unknown.\n"
        "Assumed availability is the next research session's pre-open stage, never\n"
        "verified exchange publication. Results are NOT PRODUCTION-VALIDATED.\n"
        "P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.\n"
        "Fundamentals and genuine benchmark comparison remain UNAVAILABLE.\n"
    )
    source = (
        "# D70 real NSE research ingestion\n\n" + warning + "\n"
        "Pinned TejHQ revision: `14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98`.\n"
        "35 publisher-native originals, 193,167,839 bytes; all publisher/local hashes\n"
        "matched. Price observations span 2010-01-04 through 2026-10-06. The research\n"
        "calendar contains 4,128 observed dates plus five verified missing-price\n"
        "Muhurat slots, with no price filling. The raw archive retains all 7,225,761\n"
        "observations, including historical identities absent from the latest session.\n\n"
        "P3: 5,288,138 VALID, 1,937,623 DEGRADED, zero rejected/quarantined.\n"
        "These states are preserved; research classification never upgrades them.\n\n"
        + table(
            ["Canonical classification/count", "Value"],
            [[k, v] for k, v in canonical["counts"].items()],
        )
        + "\n"
        + table(
            ["Identity coverage", "Value"],
            [
                [k, identity[k]]
                for k in (
                    "identities",
                    "stable_observed_isin_identities",
                    "source_year_provisional_identities",
                    "currently_observed_isin_identities",
                    "historical_isin_identities_absent_latest",
                    "provisional_identities_absent_latest",
                    "observed_isin_identities_with_multiple_symbols",
                    "raw_economic_action_rows",
                )
            ],
        )
        + "\n"
        "Absence at the latest session is not proof of delisting. Source-year\n"
        "provisional identities sacrifice continuity and cannot be counted as verified\n"
        "distinct companies. Candidate/excluded security counts can overlap over time.\n"
        "No authoritative COMMON_EQUITY or historical NIFTY membership is asserted.\n"
        "The analytical universe is NSE_RESEARCH_EQUITY_CANDIDATE_UNIVERSE_V1.\n"
        "ISIN is used only where observed; future ISIN/name/type evidence is not backfilled.\n"
        "Raw prices remain RAW_UNADJUSTED. Action evidence becomes research-known\n"
        "after its effective session under the assumed availability policy.\n\n"
        f"Canonical identity: `{canonical['dataset_id']}`.\n"
        f"Frozen supervised identity: `{supervised['dataset_id']}`.\n\n"
        "See research-canonical-summary.json, research-identity-profile.json and\n"
        "research-dataset-identity.json for counts, versions, calendar and file hashes.\n"
    )
    publish("docs/data/real-10y-ingestion-report.md", source)
    training = (
        "# D70 real NSE research training\n\n" + warning + "\n"
        f"Feature rows: {features['feature_rows']:,}. Model fits: {runs['models_trained']}.\n"
        "All six classification and six regression families use identical eligible\n"
        "rows/features within each horizon/fold. The fixed existing arena uses seed\n"
        "1729, one CPU thread and 32 tree/boosting iterations, with no tuning search.\n"
        "This small baseline arena is not a claim of optimal model capacity.\n"
        "2010-2014 are retained for warm-up; expanding training starts in 2015.\n"
        "2022-2024 are development OOS, 2025 confirmation, 2026 final holdout.\n"
        "All preprocessing is freshly fitted on past training rows only.\n\n"
        + table(
            ["Feature", "Available", "Unavailable", "Availability %"],
            [
                [n, v["available_count"], v["unavailable_count"], v["availability_percent"]]
                for n, v in sorted(features["availability"].items())
            ],
        )
        + "\n"
        "Benchmark-relative strength/market context and fundamentals are unavailable\n"
        "and excluded from X. Momentum percentile uses contemporaneous candidate\n"
        "peers only. Missing required slots remain null, including SMA100/SMA200\n"
        "windows crossing missing Muhurat prices. Degraded inputs retain their states\n"
        "under the explicit existing ALLOW_DEGRADED policy.\n\n"
        + table(
            [
                "Horizon",
                "Mature",
                "Unavailable",
                "Not yet mature",
                "Training eligible",
                "Candidate rows with missing required Muhurat slot",
            ],
            [
                [
                    h,
                    v.get("MATURE", 0),
                    v.get("UNAVAILABLE", 0),
                    v.get("NOT_YET_MATURE", 0),
                    v.get("TRAINING_ELIGIBLE", 0),
                    features["missing_muhurat_affected"].get(f"candidate_training_rows_{h}", 0),
                ]
                for h, v in sorted(labels["horizons"].items(), key=lambda x: int(x[0]))
            ],
        )
        + "\n"
        "Missing-slot impact counts may overlap other insufficiencies; they are not\n"
        "causal counterfactual counts. Authoritative terminal events remain unavailable,\n"
        "rather than being invented from disappearance. P7 targets preserve exact\n"
        "Decimal numerator/denominator; conversion occurs at the estimator boundary.\n\n"
        + table(
            ["Horizon", "Unadjusted-action outcome exclusions"],
            [
                [h, v]
                for h, v in sorted(
                    action_impact["label_rows_with_unadjusted_action_outcome_exclusion"].items(),
                    key=lambda item: int(item[0]),
                )
            ],
        )
        + "\nAction-affected available feature windows are quantified separately in\n"
        "../data/research-corporate-action-impact.json. Counts overlap other quality\n"
        "and missingness causes; they are not additive or adjustment factors.\n\n"
        + table(
            ["Phase", "Horizon", "Task", "Family", "Fold", "Training", "OOS", "Scored", "Run ID"],
            [
                [
                    r["phase"],
                    r["horizon"],
                    r["task"],
                    r["model_family"],
                    r["fold_id"],
                    r["training_rows"],
                    r["test_rows"],
                    r["scored_test_rows"],
                    r["model_run_id"],
                ]
                for r in runs["reports"]
            ],
        )
        + "\n"
        "real-model-runs.json pins full configurations and artifacts. Local skops bytes\n"
        "preserve the first valid checksum-pinned artifact; cross-process serialization\n"
        "byte identity is not claimed. No untrusted external model is loaded.\n"
        f"\nStored optimizer diagnostics: {limit_count}/{logistic_count} LogisticRegression\n"
        "fits reached the frozen iteration limit. Convergence is not established\n"
        "for those fits; this is a material research limitation. No iteration/solver\n"
        "or candidate-policy change follows from viewing results. See\n"
        "real-model-fit-diagnostics.json for exact model IDs and stored iteration\n"
        "counts, read only from locally created checksum-verified sklearn models.\n"
    )
    publish("docs/ml/real-data-training-report.md", training)
    evaluation = "# D70 real NSE walk-forward evaluation\n\n" + warning + "\n"
    evaluation += (
        "The pre-results research-training-plan.json locks exact fold boundaries,\n"
        "86400-second embargo, availability/maturity purge, model arena and code hashes.\n"
        "Each fold retrains independently. Only FOLD_TEST predictions enter P10.\n"
        "Family/configuration selection uses 2022-2024 only and ten equally weighted\n"
        "ordinal criteria, rather than accuracy alone. The candidate lock precedes\n"
        "2025 confirmation and one 2026 evaluation; no retuning follows. Selection is\n"
        "an analytical information scope, not an assertion that it occurred in 2025.\n"
        "Late development outcomes unavailable before 2025 are excluded from selection\n"
        "metrics. Confirmation outcomes unavailable before 2026 are likewise excluded.\n\n"
    )
    for task, names in (
        (
            "classification",
            [
                "accuracy",
                "balanced_accuracy",
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "pr_auc_average_precision",
                "log_loss",
                "brier_score",
            ],
        ),
        ("regression", ["mae", "rmse", "r2", "spearman"]),
    ):
        evaluation += "## " + task.title() + "\n\n"
        evaluation += (
            table(
                ["Phase", "Horizon", "Family", "Fold", "Scored"]
                + names
                + ["Rank IC", "Top quintile", "Bottom quintile", "Spread", "Naive", "Beats naive"],
                [
                    [
                        r["phase"],
                        r["horizon"],
                        r["model_family"],
                        r["fold_id"],
                        r["scored_test_rows"],
                    ]
                    + [r["metrics"].get(n) for n in names]
                    + [
                        r["ranking"][n]
                        for n in (
                            "mean_rank_ic",
                            "mean_top_quintile",
                            "mean_bottom_quintile",
                            "mean_top_minus_bottom",
                        )
                    ]
                    + [r["naive"][r["primary_metric"]], r["beats_naive"]]
                    for r in runs["reports"]
                    if r["task"] == task
                ],
            )
            + "\n"
        )
    evaluation += (
        "Rank IC and group targets are descriptive raw-target diagnostics, not\n"
        "investable returns. Daily ranking groups use fixed 20%/10% cutoffs, with\n"
        "deciles unavailable below ten observations. real-model-comparison.json\n"
        "contains fold mean/median/std/best/worst, naive comparisons and selection\n"
        "scores. Classification calibration bins are descriptive; no calibrator was\n"
        "fitted on OOS data. Three development years cannot establish robust significance.\n\n"
        + table(
            ["Horizon", "Selected task", "Family", "Status", "Selection score"],
            [
                [h, r["task"], r["model_family"], r["research_status"], r["selection_score"]]
                for h, r in sorted(comparison["selected"].items(), key=lambda x: int(x[0]))
            ],
        )
    )
    publish("docs/ml/real-data-walk-forward-report.md", evaluation)
    selected = comparison["selected"]
    chosen = [
        r
        for r in backtests["backtests"]
        if (r["task"], r["model_family"])
        == (selected[str(r["horizon"])]["task"], selected[str(r["horizon"])]["model_family"])
    ]
    stats = [
        "total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "sortino",
        "maximum_drawdown",
        "calmar",
        "win_rate",
        "profit_factor",
        "expectancy",
        "turnover",
        "trade_count",
        "closed_trade_count",
        "unresolved_trade_count",
        "average_holding_sessions",
        "exposure",
        "cash_utilization",
    ]
    backtest = (
        "# D70 real NSE hypothetical backtest\n\n" + warning + "\n"
        f"Backtest runs: {len(backtests['backtests'])}. Genuine OOS only, no in-sample\n"
        "predictions or target-based selection. Completed t data precedes a next-slot\n"
        "pre-open decision and evidenced open fill; exits use t+h close. No calendar\n"
        "slot is skipped. Missing opens produce no fill, with no cost. Missing exits\n"
        "and raw economic actions retain unresolved holdings; no zero terminal value,\n"
        "dividend or adjustment factor is invented. Full-path returns/annual metrics\n"
        "remain UNAVAILABLE when economic state cannot be valued. Closed-trade\n"
        "statistics describe closed trades only and never erase unresolved holdings.\n"
        "Development closes at its locked period end; no 2025 price finishes an old\n"
        "development trade. The final period stops at the latest completed EOD with\n"
        "a known assumed next-session boundary, not an invented future session.\n\n"
        "Fixed research rules: TOP_K=2, TOP_PERCENTILE=0.2, classifier threshold=0.5,\n"
        "regression threshold=0, max positions=3, initial capital=100000. Available\n"
        "cash is divided over free slots using exact rational quantities, allowing\n"
        "hypothetical fractional shares. No leverage/short selling or product-policy\n"
        "calibration. ZERO_COST_DIAGNOSTIC / LOW_COST_ASSUMPTION / HIGHER_COST_STRESS\n"
        "are existing engineered cost assumptions; the last is the requested stress\n"
        "scenario display, not verified current brokerage/tax charges. Annualization\n"
        "uses the explicit 252-session and zero risk-free assumptions only where valid.\n\n"
        + table(
            ["Phase", "Horizon", "Family", "Rule", "Cost", "Status"] + stats,
            [
                [
                    r["phase"],
                    r["horizon"],
                    r["model_family"],
                    r["selection_rule"],
                    r["cost_scenario"],
                    r["status"],
                ]
                + [r.get(n) for n in stats]
                for r in chosen
            ],
        )
        + "\nAll models/rules/scenarios, fees/slippage and skip reasons are retained in\n"
        "backtest-comparison.json. Local checksum-pinned Parquet provides actual\n"
        "OHLCV, OOS predictions, realized targets, equity/P&L/drawdown and price-linked\n"
        "trade markers. No charts are rendered and no real orders are created.\n"
    )
    publish("docs/backtesting/real-data-backtest-report.md", backtest)
    publish(
        "docs/development/real-data-readiness.md",
        "# D70 real research evidence ready for verification/review\n\n" + warning + "\n"
        f"Frozen supervised dataset `{supervised['dataset_id']}` completed P4-P10\n"
        "under the separately authorized methodology. Repository gates must be\n"
        "recorded separately before final acceptance. Review the full reports and\n"
        "machine-readable results, including weak/unavailable metrics. Final-vintage\n"
        "revision risk, incomplete calendar/type/identity/action evidence and unknown\n"
        "terminal values prevent production validation or an unbiased NSE-wide claim.\n"
        "P11-P14 weights/thresholds remain unchanged. P17 NOT_STARTED.\n",
    )
    # Preserve D69's strict-mode historical blocker while refreshing its existing
    # machine-readable path with the explicitly amended research status.
    readiness = read("docs/development/real-data-readiness.json")
    if readiness["dataset_id"] != supervised["dataset_id"]:
        raise ValueError("REPORT_READINESS_DATASET_MISMATCH")
    legacy = Path("docs/data/real-data-readiness.json")
    historical = Path("docs/data/real-data-readiness-d69.json")
    if not historical.exists():
        historical.write_bytes(legacy.read_bytes())
    legacy.write_bytes(Path("docs/development/real-data-readiness.json").read_bytes())
    print(
        json.dumps(
            dict(
                stage="reports",
                output=str(args.output),
                fits=runs["models_trained"],
                backtests=len(backtests["backtests"]),
            )
        )
    )


if __name__ == "__main__":
    main()
