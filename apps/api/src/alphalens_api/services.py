"""Read application services: stored evidence only, no training or financial recomputation."""

import hashlib
import json
import time
from datetime import date
from typing import Any

import pyarrow.dataset as ds
from pydantic import JsonValue

from alphalens_data.ingestion.storage import stable_json

from .artifacts import ArtifactReader, confined, read_json
from .catalog import Catalog
from .core.config import Settings
from .core.domain_errors import APIError
from .schemas import Classification, Envelope, IndicatorPoint, Page, PredictionPoint, PricePoint


def json_value(value: Any) -> JsonValue:
    """Preserve domain exact-value serialization without exposing arbitrary objects."""
    result: JsonValue = json.loads(json.dumps(value, default=str, allow_nan=False))
    return result


def response(
    data: Any,
    source: str,
    artifact_id: str | None = None,
    status: str = "AVAILABLE",
    reasons: tuple[str, ...] = (),
    page: Page | None = None,
    as_of: date | None = None,
) -> Envelope[JsonValue]:
    return Envelope(
        data=json_value(data),
        source=source,
        artifact_id=artifact_id,
        evidence_status=status,
        missing_data_reasons=reasons,
        page=page,
        as_of_session=as_of,
    )


class ResearchService:
    def __init__(self, settings: Settings) -> None:
        self.reader = ArtifactReader(settings)
        self.catalog = Catalog(self.reader)

    @property
    def classification(self) -> Classification:
        if self.reader.settings.test_only_evidence:
            return Classification(
                data_reality="TEST_ONLY",
                usage_classification="TEST_ONLY",
                final_vintage=None,
                research_profile=None,
            )
        return Classification()

    def response(self, *args: Any, **kwargs: Any) -> Envelope[JsonValue]:
        result = response(*args, **kwargs)
        return result.model_copy(
            update={"classification": self.classification, "provenance": self.reader.provenance()}
        )

    def reports(self) -> list[dict[str, Any]]:
        document = self.reader.report("ml/real-model-runs.json")
        dataset = self.reader.manifest("supervised-manifest.json")["dataset_id"]
        rows: list[dict[str, Any]] = document["reports"]
        for row in rows:
            if (
                row["dataset_id"] != dataset
                or row["data_reality"] != self.classification.data_reality
                or hashlib.sha256(stable_json(row["model_identity"])).hexdigest()
                != row["model_run_id"]
            ):
                raise APIError("MODEL_LINEAGE_INVALID", "Research model report lineage is invalid.")
        return rows

    def stocks(self, query: str, limit: int, offset: int) -> Envelope[JsonValue]:
        rows, more = self.catalog.search(query, limit, offset)
        return self.response(
            rows,
            "P5_RESEARCH_DISCOVERY_INDEX",
            page=Page(limit=limit, offset=offset, has_more=more),
        )

    def stock(self, security_id: str) -> Envelope[JsonValue]:
        return self.response(self.catalog.security(security_id), "P5_RESEARCH_OBSERVED_IDENTITY")

    def history(
        self, security_id: str, start: date | None, end: date | None, limit: int, offset: int
    ) -> Envelope[list[PricePoint]]:
        security = self.catalog.security(security_id)
        manifest = self.reader.manifest("canonical-manifest.json")
        root = self.reader.settings.research_data_root
        if root is None:
            raise APIError("DATASET_NOT_CONFIGURED", "Research dataset is not configured.")
        calendar = self.reader.calendar()
        with self.reader.budget() as deadline:
            path = self.reader.partition(manifest, security_id, deadline)
            rows, overflow = self.reader.rows(
                path,
                [
                    "security_id",
                    "session_date",
                    "symbol",
                    "isin",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "canonical_record_id",
                    "quality",
                    "quality_reasons",
                ],
                security_id,
                start,
                end,
                10000,
                0,
                deadline,
            )
        if overflow:
            raise APIError(
                "RESPONSE_LIMIT", "Security history exceeds the guarded read limit.", 422
            )
        by_session = {str(row["session_date"]): row for row in rows}
        if len(by_session) != len(rows):
            raise APIError(
                "IDENTITY_CONFLICT", "Multiple canonical prices exist for a session.", 409
            )
        first = max(str(start or security["first_observed"]), security["first_observed"])
        last = min(str(end or security["last_observed"]), security["last_observed"])
        points: list[PricePoint] = []
        for session in calendar["sessions"]:
            day = session["session_date"]
            if first <= day <= last:
                row = by_session.get(day)
                if row is None:
                    points.append(
                        PricePoint(
                            session=day,
                            quality="UNAVAILABLE",
                            observation_status="PRICE_OBSERVATION_MISSING",
                            quality_reasons=(
                                session["evidence"],
                                "OBSERVED_RANGE_NOT_LISTING_PROOF",
                            ),
                        )
                    )
                else:
                    points.append(
                        PricePoint(
                            session=row["session_date"],
                            symbol=row["symbol"],
                            isin=row["isin"],
                            open=row["open"],
                            high=row["high"],
                            low=row["low"],
                            close=row["close"],
                            volume=row["volume"],
                            canonical_record_id=row["canonical_record_id"],
                            quality=row["quality"],
                            quality_reasons=tuple(row["quality_reasons"]),
                            observation_status="OBSERVED",
                        )
                    )
        return Envelope(
            classification=self.classification,
            provenance=self.reader.provenance(),
            data=points[offset : offset + limit],
            source="P5_CANONICAL_RESEARCH_OHLCV",
            artifact_id=manifest["dataset_id"],
            as_of_session=max((row["session_date"] for row in rows), default=None),
            evidence_status="AVAILABLE" if rows else "UNAVAILABLE" if points else "EMPTY",
            page=Page(
                limit=limit, offset=offset, has_more=len(points) > offset + limit, total=len(points)
            ),
            missing_data_reasons=("FINAL_VINTAGE_REVISION_RISK", "NOT_LIVE_OR_PRODUCTION_PIT"),
        )

    def indicators(
        self,
        security_id: str,
        feature: str,
        start: date | None,
        end: date | None,
        limit: int,
        offset: int,
    ) -> Envelope[JsonValue]:
        self.catalog.security(security_id)
        manifest = self.reader.manifest("supervised-manifest.json")
        definitions = manifest["identity"]["feature_definitions"]
        definition = next((f for f in definitions if f["feature_name"] == feature), None)
        if definition is None or feature not in manifest["identity"]["feature_columns"]:
            raise APIError(
                "FEATURE_NOT_SUPPORTED", "Feature is not in the frozen P6 registry.", 422
            )
        with self.reader.budget() as deadline:
            rows, more = self.reader.rows(
                self.reader.partition(manifest, security_id, deadline),
                [
                    "security_id",
                    "session_date",
                    "quality",
                    "canonical_record_id",
                    feature,
                    feature + "__state",
                ],
                security_id,
                start,
                end,
                limit,
                offset,
                deadline,
            )
        points = [
            IndicatorPoint(
                session=r["session_date"],
                value=r[feature],
                state=r[feature + "__state"],
                quality=r["quality"],
                canonical_record_id=r["canonical_record_id"],
            ).model_dump(mode="json")
            for r in rows
        ]
        unit = "dimensionless"
        if feature.startswith(("sma_", "ema_", "macd", "atr_")):
            unit = "INR_RAW_PRICE"
        elif feature == "rsi_14":
            unit = "INDEX_0_100"
        elif feature == "volume_sma_20":
            unit = "SHARES"
        return self.response(
            {"feature": definition, "units": unit, "points": points},
            "P6_STORED_FEATURES",
            manifest["dataset_id"],
            page=Page(limit=limit, offset=offset, has_more=more),
        )

    def models(
        self,
        model_id: str | None,
        horizon: int | None,
        phase: str | None,
        limit: int,
        offset: int,
    ) -> Envelope[JsonValue]:
        reports = sorted(self.reports(), key=lambda r: r["model_run_id"])
        rows = [
            r
            for r in reports
            if (model_id is None or r["model_run_id"] == model_id)
            and (horizon is None or r["horizon"] == horizon)
            and (phase is None or r["phase"] == phase)
        ]
        if model_id and not rows:
            raise APIError("MODEL_NOT_FOUND", "Persisted research model was not found.", 404)
        exposed = [
            {k: v for k, v in row.items() if k not in {"model_file", "oos_file"}}
            for row in rows[offset : offset + limit]
        ]
        data: Any = exposed[0] if model_id else exposed
        return self.response(
            data,
            "P8_P9_VERIFIED_STORED_REPORTS",
            page=None
            if model_id
            else Page(
                limit=limit, offset=offset, has_more=len(rows) > offset + limit, total=len(rows)
            ),
        )

    def evaluation(self) -> Envelope[JsonValue]:
        return self.response(
            self.reader.report("ml/real-model-comparison.json"),
            "FROZEN_P9_DEVELOPMENT_CONFIRMATION_FINAL_HOLDOUT",
            reasons=("READ_ONLY_ALREADY_EVALUATED_HOLDOUT", "NOT_A_PRODUCTION_CHAMPION"),
        )

    def predictions(
        self,
        model_id: str,
        security_id: str,
        start: date | None,
        end: date | None,
        limit: int,
        offset: int,
    ) -> Envelope[list[PredictionPoint]]:
        self.catalog.security(security_id)
        reports = self.reports()
        report = next((r for r in reports if r["model_run_id"] == model_id), None)
        if report is None:
            raise APIError("MODEL_NOT_FOUND", "Persisted research model was not found.", 404)
        with self.reader.budget() as deadline:
            rows, more = self.reader.rows(
                self.reader.oos(report, deadline),
                [
                    "security_id",
                    "session_date",
                    "decision_time",
                    "prediction_id",
                    "score",
                    "prediction",
                    "canonical_record_id",
                ],
                security_id,
                start,
                end,
                limit,
                offset,
                deadline,
            )
        return Envelope(
            classification=self.classification,
            provenance=self.reader.provenance(),
            data=[
                PredictionPoint(
                    **r,
                    model_id=model_id,
                    task=report["task"],
                    horizon=report["horizon"],
                    fold_id=report["fold_id"],
                    phase=report["phase"],
                )
                for r in rows
            ],
            source="CHECKSUM_VERIFIED_P9_FOLD_TEST",
            artifact_id=report["oos_sha256"],
            page=Page(limit=limit, offset=offset, has_more=more),
            missing_data_reasons=("NOT_LIVE_PREDICTIONS", "MODEL_ESTIMATE_NOT_GUARANTEED"),
        )

    def backtests(
        self,
        backtest_id: str | None,
        horizon: int | None,
        phase: str | None,
        limit: int,
        offset: int,
    ) -> Envelope[JsonValue]:
        audit = self.reader.report("backtesting/real-research-economic-audit.json")
        rows = [
            r
            for r in audit["runs"]
            if (backtest_id is None or r["backtest_id"] == backtest_id)
            and (horizon is None or r["horizon"] == horizon)
            and (phase is None or r["phase"] == phase)
        ]
        rows.sort(key=lambda r: r["backtest_id"])
        if backtest_id:
            if not rows:
                raise APIError("BACKTEST_NOT_FOUND", "Persisted backtest was not found.", 404)
            root = self.reader.settings.research_run_root
            if root is None:
                raise APIError(
                    "ARTIFACTS_NOT_CONFIGURED", "Research run artifacts are not configured."
                )
            evidence = rows[0]
            with self.reader.budget() as deadline:
                path = self.reader.verify(
                    confined(root, f"p10/{backtest_id}/summary.json"),
                    evidence["stored_evidence_sha256"]["summary.json"],
                    deadline,
                )
                summary = read_json(path)
            if summary.get("backtest_id") != backtest_id or summary["status"] != evidence["status"]:
                raise APIError("BACKTEST_LINEAGE_INVALID", "Stored backtest identity is invalid.")
            return self.response(
                {"summary": summary, "economic_evidence": evidence},
                "P10_STORED_RESULTS",
                backtest_id,
                status=evidence["status"],
                reasons=("FULL_PATH_ECONOMIC_METRICS_UNAVAILABLE",)
                if evidence["status"] == "UNRESOLVED_ECONOMIC_OUTCOMES"
                else (),
            )
        return self.response(
            rows[offset : offset + limit],
            "P10_ECONOMIC_EVIDENCE_AUDIT",
            page=Page(
                limit=limit, offset=offset, has_more=len(rows) > offset + limit, total=len(rows)
            ),
        )

    def backtest_performance(
        self, backtest_id: str, limit: int, offset: int, start: date | None, end: date | None
    ) -> Envelope[JsonValue]:
        detail = self.backtests(backtest_id, None, None, 1, 0)
        if not isinstance(detail.data, dict):
            raise APIError("ARTIFACT_INVALID", "Backtest detail contract is invalid.")
        evidence = detail.data["economic_evidence"]
        if not isinstance(evidence, dict):
            raise APIError("ARTIFACT_INVALID", "Backtest evidence contract is invalid.")
        root = self.reader.settings.research_run_root
        if root is None:
            raise APIError("ARTIFACTS_NOT_CONFIGURED", "Research run artifacts are not configured.")
        audit = self.reader.report("backtesting/real-research-economic-audit.json")
        run = next(r for r in audit["runs"] if r["backtest_id"] == backtest_id)
        with self.reader.budget() as deadline:
            path = self.reader.verify(
                confined(root, f"p10/{backtest_id}/equity.parquet"),
                run["stored_evidence_sha256"]["equity.parquet"],
                deadline,
            )
            condition = None
            if start:
                condition = ds.field("session") >= start.isoformat()
            if end:
                expr = ds.field("session") <= end.isoformat()
                condition = expr if condition is None else condition & expr
            points: list[dict[str, Any]] = []
            seen = 0
            for batch in (
                ds.dataset(path, format="parquet")
                .scanner(filter=condition, batch_size=1024, use_threads=False)
                .to_batches()
            ):
                if time.monotonic() > deadline:
                    raise APIError(
                        "QUERY_TIMEOUT", "Persisted query exceeded the read budget.", 504
                    )
                for row in batch.to_pylist():
                    if seen >= offset:
                        points.append(row)
                    seen += 1
                    if len(points) > limit:
                        break
                if len(points) > limit:
                    break
        return self.response(
            {
                "summary": detail.data["summary"],
                "equity": points[:limit],
                "economic_evidence": evidence,
                "benchmark_status": "UNAVAILABLE",
            },
            "P10_PERSISTED_EQUITY_NO_INTERPOLATION",
            backtest_id,
            status=detail.evidence_status,
            reasons=detail.missing_data_reasons,
            page=Page(limit=limit, offset=offset, has_more=len(points) > limit),
        )
