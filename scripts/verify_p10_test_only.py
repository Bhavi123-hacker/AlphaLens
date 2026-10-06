"""Fixed cost/model arenas replay genuine P9 OOS only. TEST_ONLY, no market winner."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.build_p10_test_inputs import definition, execution_evidence

from alphalens_backtesting.contracts import scenarios
from alphalens_backtesting.engine import BacktestResult, run
from alphalens_backtesting.storage import save, verify
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_evaluation.contracts import digest
from alphalens_evaluation.storage import load


def cost_comparison(results: list[BacktestResult]) -> dict[str, Any]:
    values = {r.manifest["identity"]["definition"]["costs"]["name"]: r.summary for r in results}
    zero = values["ZERO_COST_DIAGNOSTIC"]["net_total_return"]
    cost_sensitive = any(
        v["net_total_return"] is not None and v["net_total_return"] <= 0
        for name, v in values.items()
        if name != "ZERO_COST_DIAGNOSTIC"
    )
    return dict(
        scenarios={
            name: dict(
                backtest_id=value["backtest_id"],
                net_total_return=value["net_total_return"],
                maximum_drawdown=value["maximum_drawdown"],
                trade_count=value["trade_count"],
                unresolved_trades=value["open_or_unresolved_trade_count"],
            )
            for name, value in sorted(values.items())
        },
        flag="ZERO_COST_GAIN_NOT_RETAINED_UNDER_FIXED_ASSUMPTIONS"
        if zero is not None and zero > 0 and cost_sensitive
        else "NO_GENERAL_EDGE_INFERENCE",
        evidence_status="INSUFFICIENT_EVIDENCE",
        production_claims_permitted=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="TEST_ONLY — NOT A PERFORMANCE CLAIM")
    parser.add_argument("--inputs", type=Path, default=Path("data/p9-test-only"))
    parser.add_argument("--evaluations", type=Path, default=Path("data/p9-evaluations"))
    parser.add_argument("--output", type=Path, default=Path("data/p10-backtests"))
    args = parser.parse_args()
    evidence = execution_evidence(args.inputs)
    publish(
        args.output / "execution-calendar.TEST_ONLY.json",
        stable_json(evidence.calendar.model_dump(mode="json")),
    )
    summaries: list[dict[str, Any]] = []
    for manifest in sorted(args.evaluations.glob("*/walk-forward-manifest.json")):
        oos = load(manifest.parent)
        p9 = oos.verify()
        predictive = json.loads((manifest.parent / "model-comparison.json").read_bytes())["models"]
        context_id = digest(
            dict(
                evaluation_id=oos.manifest["evaluation_id"],
                cost_scenarios=[s.model_dump(mode="json") for s in scenarios()],
                families=p9.model_families,
                policy="TOP_K_2_MAX_3",
                baselines="EQUAL_COHORT_MAX_10_AND_SEEDED_RANDOM_MAX_3",
                version="p10.arena.v1",
            )
        )
        results: list[BacktestResult] = []
        for family in p9.model_families:
            for costs in scenarios():
                plan = definition(oos, evidence, family, costs, comparison_context_id=context_id)
                first, second = run(oos, evidence, plan), run(oos, evidence, plan)
                if first != second:
                    raise RuntimeError("P10 deterministic economic replay mismatch")
                results.append(first)
        for baseline in ("EQUAL_WEIGHT_ELIGIBLE_COHORT", "SEEDED_RANDOM_CONTROL"):
            for costs in scenarios():
                plan = definition(
                    oos,
                    evidence,
                    p9.model_families[0],
                    costs,
                    comparison_context_id=context_id,
                    baseline=baseline,
                    maximum_positions=10 if baseline == "EQUAL_WEIGHT_ELIGIBLE_COHORT" else 3,
                )
                first, second = run(oos, evidence, plan), run(oos, evidence, plan)
                if first != second:
                    raise RuntimeError("P10 naive/negative-control replay mismatch")
                results.append(first)
        arena = {
            family: dict(
                predictive_metrics=predictive[family],
                economics={
                    r.manifest["identity"]["definition"]["costs"]["name"]: r.summary
                    for r in results
                    if r.summary["model_family"] == family and r.summary["baseline"] == "MODEL"
                },
                winner_status="INSUFFICIENT_EVIDENCE_NO_MARKET_WINNER",
            )
            for family in p9.model_families
        }
        sensitivity = {}
        for result in results:
            baseline, family = result.summary["baseline"], result.summary["model_family"]
            key = f"{baseline}:{family}"
            if key not in sensitivity:
                sensitivity[key] = cost_comparison(
                    [
                        r
                        for r in results
                        if r.summary["baseline"] == baseline and r.summary["model_family"] == family
                    ]
                )
            path = save(result, args.output, sensitivity[key], arena)
            verify(path)
            publish(
                path / "definition.json", stable_json(result.manifest["identity"]["definition"])
            )
        summaries.append(
            dict(
                evaluation_id=oos.manifest["evaluation_id"],
                task=p9.task,
                horizon=p9.horizon,
                run_count=len(results),
                comparison_context_id=context_id,
                model_comparison=arena,
                cost_sensitivity=sensitivity,
                naive_strategy_results=[
                    r.summary for r in results if r.summary["baseline"] != "MODEL"
                ],
            )
        )
        print(
            f"TEST_ONLY — NOT A PERFORMANCE CLAIM: {p9.task} {p9.horizon}: {len(results)} backtests"
        )
    if not summaries:
        raise RuntimeError("No genuine P9 evaluations available")
    publish(
        args.output / "suite-summary.TEST_ONLY.json",
        stable_json(
            dict(
                data_classification="TEST_ONLY",
                disclaimer="TEST_ONLY — NOT A PERFORMANCE CLAIM",
                evaluations=summaries,
                deterministic_replay=True,
                production_claims_permitted=False,
            )
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
