"""Immutable deterministic local backtest outputs with explicit schemas/checksums."""

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_backtesting.engine import BacktestResult
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_evaluation.contracts import digest
from alphalens_evaluation.storage import parquet_bytes


def strings(names: str) -> Any:
    return pa.schema([(name, pa.string()) for name in names.split()])


SCHEMAS = {
    "equity-curve.parquet": strings(
        "session_date portfolio_value cash market_value normalized_wealth "
        "value_rational state benchmark_wealth"
    ),
    "drawdown.parquet": pa.schema(
        [("session_date", pa.string()), ("drawdown", pa.float64()), ("status", pa.string())]
    ),
    "positions.parquet": strings(
        "session_date trade_id security_id fold_id quantity quantity_rational "
        "market_value state planned_exit classification"
    ),
    "session-pnl.parquet": pa.schema(
        [
            (
                name,
                pa.int32()
                if name == "open_positions"
                else pa.float64()
                if name in ("occupied_fraction", "cash_utilization")
                else pa.string(),
            )
            for name in [
                "session_date",
                "portfolio_value",
                "cash",
                "market_value",
                "realized_pnl",
                "unrealized_pnl",
                "total_pnl",
                "session_pnl",
                "cumulative_fees",
                "cumulative_slippage",
                "gross_pnl",
                "open_positions",
                "occupied_fraction",
                "cash_utilization",
                "state",
                "classification",
            ]
        ]
    ),
    "trade-ledger.parquet": pa.schema(
        [
            (name, pa.int32() if name in ("holding_sessions", "horizon") else pa.string())
            for name in [
                "trade_id",
                "backtest_id",
                "selection_decision_id",
                "security_id",
                "prediction_id",
                "model_run_id",
                "fold_id",
                "decision_session",
                "prediction_available_at",
                "entry_session",
                "entry_time",
                "entry_time_policy",
                "entry_price",
                "entry_effective_price",
                "entry_price_available_at",
                "quantity",
                "quantity_rational",
                "capital_allocation",
                "capital_allocation_rational",
                "entry_costs",
                "exit_costs",
                "total_costs",
                "slippage_cost",
                "planned_exit",
                "exit_session",
                "exit_time",
                "exit_price",
                "exit_effective_price",
                "gross_return",
                "net_return",
                "net_pnl",
                "net_pnl_rational",
                "holding_sessions",
                "exit_reason",
                "data_quality_state",
                "corporate_action_state",
                "classification",
                "audit_chain",
                "entry_revision_key",
                "exit_revision_key",
                "cost_scenario",
                "horizon",
            ]
        ]
    ),
}


def save(
    result: BacktestResult,
    root: Path,
    cost_sensitivity: dict[str, Any] | None = None,
    model_comparison: dict[str, Any] | None = None,
) -> Path:
    has_context = result.manifest["identity"]["definition"]["comparison_context_id"] is not None
    if has_context != (cost_sensitivity is not None and model_comparison is not None) or (
        cost_sensitivity is None
    ) != (model_comparison is None):
        raise DataContractError("P10_PINNED_COMPARISON_CONTEXT_REQUIRED")
    directory = local_output(root) / str(result.manifest["backtest_id"])
    common = {
        k: result.manifest[k]
        for k in (
            "backtest_id",
            "version",
            "classification",
            "disclaimer",
            "production_claims_permitted",
        )
    }
    trades = [r | {"audit_chain": stable_json(r["audit_chain"]).decode()} for r in result.trades]
    tables = {
        "equity-curve.parquet": result.equity,
        "drawdown.parquet": result.drawdown,
        "trade-ledger.parquet": trades,
        "positions.parquet": result.positions,
        "session-pnl.parquet": result.session_pnl,
    }
    files = {name: parquet_bytes(rows, SCHEMAS[name]) for name, rows in tables.items()}
    files.update(
        {
            "definition.json": stable_json(result.manifest["identity"]["definition"]),
            "summary.json": stable_json(result.summary),
            "selection-decisions.json": stable_json(dict(**common, decisions=result.decisions)),
            "cost-sensitivity.json": stable_json(
                dict(
                    **common,
                    comparison=cost_sensitivity
                    or {
                        "status": "UNAVAILABLE_SINGLE_SCENARIO_RUN_EXPLICIT_SCENARIO_IN_DEFINITION"
                    },
                )
            ),
            "model-comparison.json": stable_json(
                dict(
                    **common,
                    comparison=model_comparison
                    or {"status": "UNAVAILABLE_SINGLE_MODEL_RUN_NOT_A_MODEL_SELECTION"},
                )
            ),
        }
    )
    for name, data in files.items():
        publish(directory / name, data)
    publish(
        directory / "backtest-manifest.json",
        stable_json(
            dict(
                **result.manifest,
                checksums={name: checksum(data) for name, data in files.items()},
                artifact_boundary="TRUSTED_LOCAL_RESEARCH_ONLY_INTEGRITY_NOT_AUTHENTICATION",
            )
        ),
    )
    return directory


def verify(root: Path) -> dict[str, Any]:
    root = local_output(root)
    manifest: dict[str, Any] = json.loads((root / "backtest-manifest.json").read_bytes())
    if (
        digest(manifest["identity"]) != manifest["backtest_id"]
        or manifest["classification"] not in ("TEST_ONLY", "RESEARCH_FIXTURE", "RESEARCH_ONLY")
        or manifest["production_claims_permitted"] is not False
    ):
        raise DataContractError("P10_ARTIFACT_IDENTITY_OR_CLASSIFICATION_MISMATCH")
    required = set(SCHEMAS) | {
        "definition.json",
        "summary.json",
        "selection-decisions.json",
        "cost-sensitivity.json",
        "model-comparison.json",
    }
    if set(manifest["checksums"]) != required:
        raise DataContractError("P10_ARTIFACT_REQUIRED_OUTPUT_MISMATCH")
    for name, expected in manifest["checksums"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or checksum(path.read_bytes()) != expected:
            raise DataContractError("P10_ARTIFACT_CHECKSUM_OR_PATH_MISMATCH")
        if name in SCHEMAS and pq.read_table(path).schema != SCHEMAS[name]:
            raise DataContractError("P10_ARTIFACT_SCHEMA_MISMATCH")
    if json.loads((root / "definition.json").read_bytes()) != manifest["identity"]["definition"]:
        raise DataContractError("P10_ARTIFACT_DEFINITION_MISMATCH")
    for name in (
        "summary.json",
        "selection-decisions.json",
        "cost-sensitivity.json",
        "model-comparison.json",
    ):
        document = json.loads((root / name).read_bytes())
        if any(
            document[key] != manifest[key]
            for key in ("backtest_id", "classification", "production_claims_permitted")
        ):
            raise DataContractError("P10_ARTIFACT_REPORT_IDENTITY_MISMATCH")
    return manifest
