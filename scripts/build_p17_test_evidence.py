"""Small TEST_ONLY stored evidence for API tests; no model fitting or real-market claims."""

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_api.artifacts import sha256
from alphalens_api.catalog import REPORTS, bucket_for, build_catalog
from alphalens_api.core.config import Settings
from alphalens_data.ingestion.storage import stable_json

SECURITY = "TEST_ONLY:STABLE_ID_A"
OTHER = "TEST_ONLY:STABLE_ID_B"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(data))


def identity(data: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json(data)).hexdigest()


def build(root: Path) -> Settings:
    data, runs, reports = root / "data", root / "runs", root / "reports"
    source_inputs = {
        "source": "TEST_ONLY_SOURCE_NO_REAL_DATA",
        "revision": "TEST_ONLY_REVISION",
        "files": [],
    }
    calendar = {
        "completeness": "TEST_ONLY_OBSERVED_AND_MISSING_SESSION",
        "sessions": [
            {
                "session_date": day,
                "evidence": "TEST_ONLY_SESSION",
                "price_status": "PRICE_OBSERVATION_MISSING"
                if day == "2013-11-03"
                else "SOURCE_ROWS_PRESENT",
                "status": "SESSION_EXISTS",
            }
            for day in ("2013-11-01", "2013-11-03", "2013-11-04", "2013-11-05")
        ],
    }
    write_json(data / "research-calendar.json", calendar)
    schema = pa.schema(
        [
            ("security_id", pa.string()),
            ("session_date", pa.date32()),
            ("symbol", pa.string()),
            ("isin", pa.string()),
            ("name", pa.string()),
            ("analytical_type", pa.string()),
            ("type_reason", pa.string()),
            ("identity_basis", pa.string()),
            ("open", pa.decimal128(38, 18)),
            ("high", pa.decimal128(38, 18)),
            ("low", pa.decimal128(38, 18)),
            ("close", pa.decimal128(38, 18)),
            ("volume", pa.int64()),
            ("canonical_record_id", pa.string()),
            ("quality", pa.string()),
            ("quality_reasons", pa.list_(pa.string())),
        ]
    )
    observations: list[dict[str, Any]] = []
    for security in (SECURITY, OTHER):
        for day in (1, 4, 5):
            observations.append(
                {
                    "security_id": security,
                    "session_date": date(2013, 11, day),
                    "symbol": "TESTOLD" if day == 1 else "TESTNEW",
                    "isin": None
                    if day == 1
                    else "TESTISIN_A"
                    if security == SECURITY
                    else "TESTISIN_B",
                    "name": "TEST ONLY COMPANY",
                    "analytical_type": "RESEARCH_EQUITY_CANDIDATE",
                    "type_reason": "TEST_ONLY_NOT_AUTHORITATIVE",
                    "identity_basis": "TEST_ONLY_SOURCE_ID",
                    "open": Decimal("10.123456789012345678"),
                    "high": Decimal("12"),
                    "low": Decimal("9"),
                    "close": Decimal("11"),
                    "volume": 100,
                    "canonical_record_id": identity({"security": security, "day": day}),
                    "quality": "VALID",
                    "quality_reasons": [],
                }
            )
    files = []
    for bucket in range(64):
        path = data / "canonical" / f"bucket-{bucket:02d}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [r for r in observations if bucket_for(r["security_id"]) == bucket]
        rows.sort(key=lambda r: (r["security_id"], r["session_date"]))
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
        files.append(
            {"path": path.relative_to(data).as_posix(), "sha256": sha256(path), "rows": len(rows)}
        )
    canonical_identity = {
        "data_reality": "TEST_ONLY",
        "usage_classification": "TEST_ONLY",
        "final_vintage": None,
        "source_identity": identity(source_inputs),
        "calendar_id": identity(calendar),
        "files": files,
    }
    write_json(
        data / "canonical-manifest.json",
        {"identity": canonical_identity, "dataset_id": identity(canonical_identity)},
    )
    feature_schema = pa.schema(
        [
            ("security_id", pa.string()),
            ("session_date", pa.date32()),
            ("quality", pa.string()),
            ("canonical_record_id", pa.string()),
            ("sma_200", pa.float64()),
            ("sma_200__state", pa.string()),
            ("target_return_1", pa.string()),
        ]
    )
    features = [
        {
            **r,
            "sma_200": None if r["session_date"].day == 1 else 10.5,
            "sma_200__state": "UNAVAILABLE" if r["session_date"].day == 1 else "AVAILABLE",
            "target_return_1": "TEST_ONLY_TARGET_MUST_NOT_LEAK",
        }
        for r in observations
    ]
    files = []
    for bucket in range(64):
        path = data / "features-labels" / f"bucket-{bucket:02d}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [r for r in features if bucket_for(r["security_id"]) == bucket]
        rows.sort(key=lambda r: (r["security_id"], r["session_date"]))
        pq.write_table(pa.Table.from_pylist(rows, schema=feature_schema), path)
        files.append(
            {"path": path.relative_to(data).as_posix(), "sha256": sha256(path), "rows": len(rows)}
        )
    supervised_identity = {
        "data_reality": "TEST_ONLY",
        "usage_classification": "TEST_ONLY",
        "final_vintage": None,
        "files": files,
        "feature_columns": ["sma_200"],
        "feature_definitions": [
            {
                "feature_name": "sma_200",
                "feature_version": "p6.features.v1",
                "formula": "MEAN_LAST_200_EVIDENCED_CLOSES",
            }
        ],
    }
    supervised_id = identity(supervised_identity)
    write_json(
        data / "supervised-manifest.json",
        {"identity": supervised_identity, "dataset_id": supervised_id},
    )
    model_identity = {
        "dataset_id": supervised_id,
        "data_reality": "TEST_ONLY",
        "configuration": {"family": "TEST_ONLY_NO_ESTIMATOR"},
    }
    model_id = identity(model_identity)
    oos = runs / "p9/oos/test-only.parquet"
    oos.parent.mkdir(parents=True)
    predictions = [
        {
            "security_id": SECURITY,
            "session_date": date(2013, 11, 4),
            "decision_time": datetime(2013, 11, 5, tzinfo=UTC),
            "prediction_id": identity({"TEST_ONLY_PREDICTION": 1}),
            "score": 0.5,
            "prediction": 0.0,
            "canonical_record_id": observations[1]["canonical_record_id"],
            "target_return_1": "TEST_ONLY_TARGET_MUST_NOT_LEAK",
        }
    ]
    table = pa.Table.from_pylist(predictions).replace_schema_metadata(
        {
            b"role": b"FOLD_TEST",
            b"model_run_id": model_id.encode(),
            b"dataset_id": supervised_id.encode(),
            b"model_identity": stable_json(model_identity),
        }
    )
    pq.write_table(table, oos)
    report = {
        "model_run_id": model_id,
        "model_identity": model_identity,
        "dataset_id": supervised_id,
        "data_reality": "TEST_ONLY",
        "task": "classification",
        "horizon": 1,
        "phase": "2026",
        "fold_id": "2026",
        "oos_file": "oos/test-only.parquet",
        "oos_sha256": sha256(oos),
        "model_file": "models/TEST_ONLY_NOT_CREATED.skops",
        "metrics": {"accuracy": 0.5, "brier_score": 0.25},
        "training_rows": 0,
    }
    bid = identity({"TEST_ONLY_BACKTEST": 1})
    summary = {
        "backtest_id": bid,
        "status": "UNRESOLVED_ECONOMIC_OUTCOMES",
        "total_return": None,
        "cagr": None,
        "sharpe": None,
        "trade_statistics_scope": "CLOSED_ONLY_NOT_FULL_STRATEGY_RETURN",
        "closed_trade_count": 0,
        "benchmark_status": "UNAVAILABLE",
    }
    bp = runs / "p10" / bid
    write_json(bp / "summary.json", summary)
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "session": "2013-11-04",
                    "portfolio_value": None,
                    "drawdown": None,
                    "quality": "UNRESOLVED",
                    "freshness": "UNAVAILABLE",
                }
            ]
        ),
        bp / "equity.parquet",
    )
    audit_run = {
        "backtest_id": bid,
        "horizon": 1,
        "phase": "development",
        "status": summary["status"],
        "cause_counts": {"TEST_ONLY_MISSING_PRICE": 1},
        "stored_evidence_sha256": {
            "summary.json": sha256(bp / "summary.json"),
            "equity.parquet": sha256(bp / "equity.parquet"),
        },
    }
    documents: dict[str, dict[str, Any]] = {
        REPORTS[0]: {"reports": [report]},
        REPORTS[1]: {"folds": [report]},
        REPORTS[2]: {
            "selected": {"1": {"research_status": "REAL_RESEARCH_INSUFFICIENT_EVIDENCE"}},
            "final_holdout": [report],
            "final_holdout_evaluated": True,
        },
        REPORTS[3]: {"backtests": [summary]},
        REPORTS[4]: {"runs": [audit_run]},
        REPORTS[5]: {
            "source_dataset_identity": identity(source_inputs),
            "identity_inputs": source_inputs,
        },
    }
    for reference, document in documents.items():
        write_json(reports / reference, document)
    settings = Settings(
        environment="test",
        test_only_evidence=True,
        research_data_root=data,
        research_run_root=runs,
        research_report_root=reports,
        catalog_path=root / "index/discovery.sqlite",
    )
    build_catalog(settings)
    return settings
