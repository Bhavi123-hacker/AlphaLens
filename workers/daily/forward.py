"""Immutable prospective records; genuine P19 provenance and independent gates required."""

import json
import os
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal, Self, cast
from zoneinfo import ZoneInfo

import numpy as np
from pydantic import AwareDatetime, Field, model_validator
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, roc_auc_score

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.contracts import Contract
from alphalens_data.daily.contracts import Calendar
from alphalens_data.daily.providers import assessment
from alphalens_data.daily.storage import Store, identifier
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchCalendar
from alphalens_labels.research import indexed_targets
from workers.alerts.contracts import Event
from workers.alerts.store import AlertStore

Safe = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.: -]{1,200}$")]


class Forecast(Contract):
    version: Literal["p19.prospective.v1"] = "p19.prospective.v1"
    classification: Literal["TEST_ONLY", "RESEARCH_ONLY"]
    source_run_id: Hash
    source_receipt_sha256: Hash
    source_revision: Safe
    feature_registry_id: Hash
    feature_product_sha256: Hash
    model_sha256: Hash
    model_run_id: Hash
    model_family: Literal["hist_gradient_boosting", "xgboost"]
    security_id: Safe
    symbol: Safe
    session: date
    horizon: Literal[1, 5, 10, 20]
    predicted_direction: Literal[0, 1]
    model_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    decision_at: AwareDatetime
    training_cutoff: AwareDatetime
    received_at: AwareDatetime
    ranking_position: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def chronology(self) -> Self:
        if (
            self.training_cutoff >= self.decision_at
            or self.received_at > self.decision_at
            or self.session <= date(2026, 10, 6)
            or self.decision_at.astimezone(ZoneInfo("Asia/Kolkata")).date() <= self.session
            or self.ranking_position is not None  # Ranking gates have not been accepted.
            or self.model_family != ("xgboost" if self.horizon == 10 else "hist_gradient_boosting")
        ):
            raise ValueError("FORECAST_CHRONOLOGY_OR_RANKING_GATE_REJECTED")
        return self


class FuturePrice(Contract):
    session: date
    source_run_id: Hash
    source_revision: Safe
    open: Decimal = Field(gt=0, allow_inf_nan=False)
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    received_at: AwareDatetime
    eligible: bool
    action_status: Literal["VERIFIED_NO_ACTION", "VERIFIED_ACTION", "UNKNOWN"]

    @model_validator(mode="after")
    def observed(self) -> Self:
        if self.session > self.received_at.astimezone(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("FUTURE_SESSION_NOT_OBSERVED")
        return self


class ObservedSlots:
    """P7 numerical target adapter with actual receipts, never assumed availability."""

    def __init__(self, dates: tuple[date, ...], rows: dict[date, FuturePrice]) -> None:
        self.dates = dates
        self.rows = rows

    def availability(self, session: date) -> datetime | None:
        return self.rows[session].received_at if session in self.rows else None


def outcome(
    forecast: Forecast,
    calendar: Calendar,
    prices: list[FuturePrice],
    at: datetime,
    recorded_at: datetime,
) -> dict[str, Any]:
    if at.tzinfo is None or recorded_at.tzinfo is None:
        raise DataContractError("AWARE_EVALUATION_CLOCK_REQUIRED")
    if at < max(recorded_at, forecast.decision_at):
        raise DataContractError("EVALUATION_PRECEDES_FORECAST")
    if calendar.completeness != "VERIFIED_TRADING_SESSION_SEQUENCE":
        return dict(maturity="UNAVAILABLE", reasons=["SESSION_SEQUENCE_NOT_VERIFIED"])
    required = [
        s for s in calendar.sessions if s.status == "TRADING" and s.session >= forecast.session
    ]
    dates = tuple(s.session for s in required)
    if not dates or dates[0] != forecast.session or len(dates) <= forecast.horizon:
        return dict(maturity="NOT_YET_MATURE", reasons=["REQUIRED_FUTURE_SESSIONS_NOT_KNOWN"])
    dates = dates[: forecast.horizon + 1]
    if any(s.known_at > at for s in required[: forecast.horizon + 1]):
        return dict(maturity="NOT_YET_MATURE", reasons=["REQUIRED_SESSION_EVIDENCE_NOT_YET_KNOWN"])
    entry_start = datetime.combine(dates[1], time.min, ZoneInfo("Asia/Kolkata"))
    if max(recorded_at, forecast.decision_at) >= entry_start:
        return dict(maturity="UNAVAILABLE", reasons=["FORECAST_NOT_RECORDED_BEFORE_ENTRY_DATE"])
    rows: dict[date, FuturePrice] = {}
    for row in prices:
        if row.session in rows:
            raise DataContractError("AMBIGUOUS_FUTURE_REVISION")
        if row.received_at <= at:
            rows[row.session] = row
    if any(day in rows and rows[day].action_status != "VERIFIED_NO_ACTION" for day in dates[1:]):
        return dict(maturity="UNAVAILABLE", reasons=["CORPORATE_ACTION_ECONOMICS_NOT_VERIFIED"])
    slots = ObservedSlots(dates, rows)
    result = indexed_targets(
        cast(ResearchCalendar, slots),
        [rows[d].open if d in rows else None for d in dates],
        [rows[d].close if d in rows else None for d in dates],
        np.array([d in rows and rows[d].eligible for d in dates], dtype=bool),
        np.zeros(len(dates), dtype=bool),
        forecast.horizon,
        [0],
    )[0]
    result["reasons"] = result.pop("outcome_reasons")
    result["economic_validation"] = "UNAVAILABLE_NO_EXECUTION_COST_OR_BENCHMARK_EVIDENCE"
    for key, value in result.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
    return result


class ForwardStore:
    def __init__(
        self,
        daily_root: Path,
        *,
        test_only: bool = False,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.daily = Store(daily_root)
        self.root = daily_root.resolve() / "prospective"
        self.path = self.root / "prospective.sqlite3"
        if test_only and not any("TEST_ONLY" in p for p in daily_root.parts):
            raise DataContractError("ISOLATED_TEST_NAMESPACE_REQUIRED")
        self.test_only = test_only
        if clock is not None and not test_only:
            raise DataContractError("REAL_CLOCK_OVERRIDE_FORBIDDEN")
        self.clock = clock or (lambda: datetime.now(UTC))

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        restrict(self.root)
        verify(self.root)
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(fd)
        verify(self.path, directory=False)
        with sqlite3.connect(self.path, timeout=10) as conn:
            if conn.execute("PRAGMA user_version").fetchone()[0] not in {0, 1}:
                raise DataContractError("PROSPECTIVE_SCHEMA_UNSUPPORTED")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            schema = Path(__file__).resolve().parents[2] / "db/prospective/schema.sql"
            conn.executescript("BEGIN IMMEDIATE;\n" + schema.read_text() + "\nCOMMIT;")

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise DataContractError("PROSPECTIVE_STORE_NOT_INITIALIZED")
        verify(self.root)
        verify(self.path, directory=False)
        conn = sqlite3.connect(
            self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=10
        )
        conn.row_factory = sqlite3.Row
        try:
            if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise DataContractError("PROSPECTIVE_SCHEMA_UNSUPPORTED")
            if write:
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA synchronous=FULL")
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record(self, forecast: Forecast) -> str:
        receipt = self.daily.receipt(forecast.source_run_id)
        if receipt["state"] not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
            raise DataContractError("SOURCE_RUN_NOT_ACCEPTED")
        if self.test_only:
            if forecast.classification != "TEST_ONLY" or receipt["mode"] != "TEST_ONLY":
                raise DataContractError("TEST_ONLY_FORECAST_REQUIRED")
        elif (
            forecast.classification != "RESEARCH_ONLY"
            or receipt["mode"] != "DAILY"
            or not assessment().allowed("DAILY")
            or receipt["inference_status"] != "AVAILABLE"
        ):
            raise DataContractError("FRESH_INFERENCE_ACCEPTANCE_NOT_PASSED")
        if (
            forecast.source_receipt_sha256 != receipt["receipt_sha256"]
            or forecast.session.isoformat() != receipt["session"]
            or forecast.source_revision != receipt["identity"]["provider"]["revision"]
            or forecast.feature_registry_id != receipt["identity"]["feature_registry_id"]
            or forecast.feature_product_sha256 != receipt["products"]["features"]["sha256"]
            or forecast.received_at != datetime.fromisoformat(receipt["source_received_at"])
        ):
            raise DataContractError("FORECAST_SOURCE_LINEAGE_MISMATCH")
        rows = self.daily.product(forecast.source_run_id, "canonical")["rows"]
        if not any(
            r["security_id"] == forecast.security_id and r["symbol"] == forecast.symbol
            for r in rows
        ):
            raise DataContractError("FORECAST_SECURITY_NOT_IN_SOURCE")
        now = self.clock()
        if now.tzinfo is None or forecast.decision_at > now:
            raise DataContractError("FORECAST_NOT_YET_DECIDED")
        payload = stable_json(forecast.model_dump(mode="json"))
        sha = checksum(payload)
        key = checksum(
            stable_json(
                [
                    forecast.source_run_id,
                    forecast.security_id,
                    forecast.model_sha256,
                    forecast.horizon,
                ]
            )
        )
        with self.connection(write=True) as conn:
            old = conn.execute("SELECT sha256 FROM forecasts WHERE identity=?", (key,)).fetchone()
            if old and old[0] != sha:
                raise DataContractError("FORECAST_REWRITE_FORBIDDEN")
            if not old and conn.execute("SELECT count(*) FROM forecasts").fetchone()[0] >= 50000:
                raise DataContractError("PROSPECTIVE_CAPACITY_ARCHIVE_REQUIRED")
            conn.execute(
                "INSERT OR IGNORE INTO forecasts VALUES (?,?,?,?,?)",
                (sha, key, payload.decode(), sha, now.isoformat()),
            )
        return sha

    def forecasts(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        if not 1 <= limit <= 100 or not 0 <= offset <= 50000:
            raise DataContractError("PROSPECTIVE_PAGINATION_INVALID")
        with self.connection() as conn:
            count = conn.execute("SELECT count(*) FROM forecasts").fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM forecasts ORDER BY recorded_at,id LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        output = []
        for row in rows:
            if checksum(row["payload"].encode()) != row["sha256"]:
                raise DataContractError("FORECAST_CHECKSUM_MISMATCH")
            value = Forecast.model_validate_json(row["payload"])
            if not self.test_only and value.classification == "TEST_ONLY":
                raise DataContractError("TEST_ONLY_FORECAST_BLOCKED")
            output.append(
                dict(id=row["id"], recorded_at=row["recorded_at"], **value.model_dump(mode="json"))
            )
        return dict(rows=output, total=count, limit=limit, offset=offset)

    def evaluate(self, forecast_id: str, calendar: Calendar, prices: list[FuturePrice]) -> str:
        if not self.test_only:
            # No approved real future observation adapter exists; arbitrary prices cannot pass.
            raise DataContractError("VERIFIED_FUTURE_OBSERVATION_ADAPTER_NOT_AVAILABLE")
        with self.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM forecasts WHERE id=?", (identifier(forecast_id),)
            ).fetchone()
            if row is None or checksum(row["payload"].encode()) != row["sha256"]:
                raise DataContractError("FORECAST_NOT_FOUND_OR_CORRUPT")
            forecast = Forecast.model_validate_json(row["payload"])
            if any(s.evidence_type != "TEST_ONLY" for s in calendar.sessions):
                raise DataContractError("TEST_ONLY_CALENDAR_REQUIRED")
            value = outcome(
                forecast, calendar, prices, self.clock(), datetime.fromisoformat(row["recorded_at"])
            )
            # Preserve evidence and corrections; never mutate the original forecast/outcome.
            value = dict(
                forecast_id=forecast_id,
                result=value,
                evidence=[r.model_dump(mode="json") for r in prices],
                calendar=calendar.model_dump(mode="json"),
                classification="TEST_ONLY",
            )
            payload = stable_json(value)
            sha = checksum(payload)
            existing = conn.execute("SELECT id FROM outcomes WHERE id=?", (sha,)).fetchone()
            if (
                not existing
                and conn.execute("SELECT count(*) FROM outcomes").fetchone()[0] >= 100000
            ):
                raise DataContractError("PROSPECTIVE_OUTCOME_CAPACITY_ARCHIVE_REQUIRED")
            conn.execute(
                "INSERT OR IGNORE INTO outcomes VALUES (?,?,?,?,?)",
                (sha, forecast_id, payload.decode(), sha, self.clock().isoformat()),
            )
        return sha

    def process_alerts(self, alerts: AlertStore) -> dict[str, int]:
        """Ack only after durable P20 publication; stable IDs make interrupted replay safe."""
        if self.test_only and not any("TEST_ONLY" in p for p in alerts.root.parts):
            raise DataContractError("ISOLATED_TEST_ALERT_NAMESPACE_REQUIRED")
        with self.connection() as conn:
            position = conn.execute(
                "SELECT position FROM notification_cursor WHERE singleton=1"
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT o.*,o.rowid AS sequence,f.payload AS forecast_payload,"
                "f.sha256 AS forecast_sha "
                "FROM outcomes o JOIN forecasts f ON f.id=o.forecast_id WHERE o.rowid>? "
                "ORDER BY o.rowid LIMIT 100",
                (position,),
            ).fetchall()
        published = 0
        for row in rows:
            if (
                checksum(row["payload"].encode()) != row["sha256"]
                or checksum(row["forecast_payload"].encode()) != row["forecast_sha"]
            ):
                raise DataContractError("PROSPECTIVE_EVENT_CHECKSUM_MISMATCH")
            f = Forecast.model_validate_json(row["forecast_payload"])
            result = json.loads(row["payload"])
            if (
                result["forecast_id"] != row["forecast_id"]
                or result["classification"] != f.classification
            ):
                raise DataContractError("PROSPECTIVE_EVENT_LINEAGE_MISMATCH")
            if not self.test_only and f.classification == "TEST_ONLY":
                raise DataContractError("TEST_ONLY_FORECAST_BLOCKED")
            if result["result"]["maturity"] == "MATURE":
                event = Event(
                    component="P19",
                    code="PROSPECTIVE_EVALUATED",
                    evidence_ref="prospective:" + row["id"],
                    evidence_sha256=row["sha256"],
                    event_at=datetime.fromisoformat(row["recorded_at"]),
                    time_basis="PERSISTED_EVENT_TIME",
                    run_id=f.source_run_id,
                    security_id=f.security_id,
                    session=f.session,
                    classification=f.classification,
                    mode="TEST_ONLY" if self.test_only else "DAILY",
                    group="P19:PROSPECTIVE_EVALUATED",
                    identity=row["id"],
                    reasons=("ECONOMIC_VALIDATION_UNAVAILABLE",),
                )
                published += alerts.publish("prospective:" + row["id"], row["sha256"], [event])
            with self.connection(write=True) as conn:
                conn.execute(
                    "UPDATE notification_cursor SET position=max(position,?) WHERE singleton=1",
                    (row["sequence"],),
                )
        return dict(scanned=len(rows), published=published, continuation=int(len(rows) == 100))

    def summary(self) -> dict[str, Any]:
        """Use latest immutable resolution per forecast; never show zero as missing metrics."""
        groups: dict[int, list[tuple[int, int, float]]] = {h: [] for h in (1, 5, 10, 20)}
        models: dict[int, set[str]] = {h: set() for h in groups}
        pending = unresolved = count = 0
        with self.connection() as conn:
            # Stream one forecast/latest resolution at a time, including full hash checks.
            rows = conn.execute(
                "SELECT f.*, o.payload AS outcome_payload, o.sha256 AS outcome_sha "
                "FROM forecasts f LEFT JOIN outcomes o ON o.rowid="
                "(SELECT max(rowid) FROM outcomes WHERE forecast_id=f.id) "
                "ORDER BY f.id"
            )
            for row in rows:
                count += 1
                if checksum(row["payload"].encode()) != row["sha256"]:
                    raise DataContractError("FORECAST_CHECKSUM_MISMATCH")
                f = Forecast.model_validate_json(row["payload"])
                if not self.test_only and f.classification == "TEST_ONLY":
                    raise DataContractError("TEST_ONLY_FORECAST_BLOCKED")
                result = {}
                if row["outcome_payload"] is not None:
                    if checksum(row["outcome_payload"].encode()) != row["outcome_sha"]:
                        raise DataContractError("OUTCOME_CHECKSUM_MISMATCH")
                    resolved = json.loads(row["outcome_payload"])
                    if resolved["forecast_id"] != row["id"]:
                        raise DataContractError("OUTCOME_FORECAST_LINEAGE_MISMATCH")
                    result = resolved["result"]
                if result.get("maturity") == "MATURE":
                    models[f.horizon].add(f.model_sha256)
                    groups[f.horizon].append(
                        (result["direction_value"], f.predicted_direction, f.model_probability)
                    )
                elif result.get("maturity") == "UNAVAILABLE":
                    unresolved += 1
                else:
                    pending += 1
        metrics = []
        for horizon, data in groups.items():
            resolved_count = len(data)
            if len(models[horizon]) > 1:
                data = []  # Distinct models must not be pooled into a performance claim.
            y, predicted, probabilities = zip(*data, strict=True) if data else ((), (), ())
            both = len(set(y)) == 2
            metrics.append(
                dict(
                    horizon=horizon,
                    resolved=resolved_count,
                    model_sha256=next(iter(models[horizon])) if len(models[horizon]) == 1 else None,
                    directional_accuracy=float(np.mean(np.array(y) == predicted)) if data else None,
                    balanced_accuracy=float(balanced_accuracy_score(y, predicted))
                    if both
                    else None,
                    roc_auc=float(roc_auc_score(y, probabilities)) if both else None,
                    brier=float(brier_score_loss(y, probabilities)) if data else None,
                    always_up_accuracy=float(np.mean(y)) if data else None,
                    evidence="INCOMPARABLE_MODEL_VERSIONS"
                    if len(models[horizon]) > 1
                    else "INSUFFICIENT_FOR_MODEL_ACCEPTANCE",
                )
            )
        return dict(
            version="p19.prospective.v1",
            classification="TEST_ONLY" if self.test_only else "RESEARCH_ONLY",
            forecasts=count,
            pending=pending,
            unresolved=unresolved,
            resolved=sum(len(g) for g in groups.values()),
            horizons=metrics,
            ranking_ic=None,
            ranking="UNAVAILABLE_UNCHANGED_POLICY",
            economic_validation="UNAVAILABLE_NO_EXECUTION_COST_OR_BENCHMARK_EVIDENCE",
            performance_claim="NOT_A_PERFORMANCE_CLAIM",
        )
