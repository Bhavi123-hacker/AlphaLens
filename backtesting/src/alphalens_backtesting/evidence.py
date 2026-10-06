"""P5 PIT execution facts plus separately evidenced calendar conventions; no model fitting."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_backtesting.contracts import BacktestDefinition, CalendarDay, ExecutionCalendar
from alphalens_data.canonical.models import PriceView, QualityRevision, ReadContext, revision_key
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_evaluation.contracts import OOSPrediction, digest
from alphalens_evaluation.storage import OOSDataset
from alphalens_features.models import FeatureDataset


def date_end(session: date) -> datetime:
    return datetime.combine(session, time.max, ZoneInfo("Asia/Kolkata"))


@dataclass
class ExecutionEvidence:
    reader: CanonicalReader
    features: FeatureDataset
    calendar: ExecutionCalendar
    _views: dict[date, dict[str, PriceView]] = field(default_factory=dict)
    _actions: dict[datetime, tuple[Any, ...]] = field(default_factory=dict)
    _confirmed: dict[date, bool] = field(default_factory=dict)
    _membership: dict[tuple[date, datetime], frozenset[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            self.reader.batch.input_id != self.features.canonical_input_id
            or self.calendar.canonical_input_id != self.reader.batch.input_id
            or self.calendar.classification != self.features.classification
            or self.reader.batch.classification != self.features.classification
            or digest(self.features.model_dump(mode="json", exclude={"feature_set_id"}))
            != self.features.feature_set_id
        ):
            raise DataContractError("P10_EXECUTION_INPUT_MISMATCH")
        ExecutionCalendar.model_validate(self.calendar.model_dump())

    def verify(self, oos: OOSDataset, definition: BacktestDefinition) -> None:
        p9 = oos.verify()
        if (
            definition.evaluation_id != oos.manifest["evaluation_id"]
            or definition.oos_prediction_dataset_id != oos.manifest["oos_prediction_dataset_id"]
            or definition.canonical_input_id != self.reader.batch.input_id
            or definition.feature_set_id != self.features.feature_set_id
            or definition.feature_set_id != p9.feature_set_id
            or definition.execution_calendar_id != self.calendar.calendar_id
            or definition.universe_definition_id != self.reader.batch.definition.universe_id
            or definition.data_classification != p9.data_classification
            or definition.horizon != p9.horizon
            or definition.model_family not in p9.model_families
            or oos.manifest["identity"]["canonical_input_id"] != self.reader.batch.input_id
        ):
            raise DataContractError("P10_P9_ONLY_PINNED_INPUT_REQUIRED")
        keyed = {(r.session_date, r.security_id): r for r in self.features.rows}
        for row in oos.predictions:
            source = keyed.get((row.session_date, row.security_id))
            if source is None or (
                row.feature_canonical_dataset_id != source.canonical_dataset_id
                or row.universe_snapshot_id != source.universe_snapshot_id
                or row.decision_time != source.decision_time
                or not source.analytical_eligible
            ):
                raise DataContractError("P10_P6_P4_TRACE_MISMATCH")

    def views(self, session: date) -> dict[str, PriceView]:
        if session not in self._views:
            read = self.reader.prices_as_of(
                session, session, ReadContext(knowledge_cutoff=date_end(session))
            )
            records = [r for r in read.records if r.observation.price_basis == "RAW_UNADJUSTED"]
            if len({r.observation.security_id for r in records}) != len(records):
                raise DataContractError("P10_AMBIGUOUS_PRICE_SLOT")
            self._views[session] = {str(r.observation.security_id): r for r in records}
        return self._views[session]

    def price(self, security: str, session: date) -> PriceView | None:
        view = self.views(session).get(security)
        if (
            view is None
            or view.observation.values is None
            or view.quality not in ("VALID", "DEGRADED")
        ):
            return None
        if (
            view.observation.session_close_at is None
            or view.observation.provenance.available_at is None
        ):
            return None
        return view

    def confirmed(self, day: CalendarDay) -> bool:
        if day.session_date in self._confirmed:
            return self._confirmed[day.session_date]
        sessions = self.reader.sessions_as_of(
            day.session_date,
            day.session_date,
            ReadContext(knowledge_cutoff=date_end(day.session_date)),
        ).records
        result = len(sessions) == 1 and sessions[0].status == day.status
        self._confirmed[day.session_date] = result
        return result

    def plan(
        self, row: OOSPrediction, horizon: int
    ) -> tuple[CalendarDay | None, CalendarDay | None, str | None]:
        days = {d.session_date: d for d in self.calendar.days}
        cursor = row.session_date + timedelta(days=1)
        future: list[CalendarDay] = []
        while len(future) < horizon:
            day = days.get(cursor)
            if (
                day is None
                or day.status == "UNKNOWN_SESSION_STATUS"
                or day.available_at > row.decision_time
            ):
                return None, None, "NO_FILL_CALENDAR_NOT_KNOWABLE"
            if day.status == "VERIFIED_TRADING_SESSION":
                future.append(day)
            cursor += timedelta(days=1)
        return future[0], future[-1], None

    def member_at_open(self, security: str, session: date, cutoff: datetime) -> bool:
        key = (session, cutoff)
        if key not in self._membership:
            universe = self.reader.universe_as_of(session, ReadContext(knowledge_cutoff=cutoff))
            self._membership[key] = frozenset(
                u.security_id for u in universe.eligible_securities if u.universe_membership
            )
        return security in self._membership[key]

    def economic_actions(
        self, security: str, start: date, session: date, cutoff: datetime
    ) -> tuple[str, ...]:
        if cutoff not in self._actions:
            self._actions[cutoff] = self.reader.corporate_actions_as_of(
                ReadContext(knowledge_cutoff=cutoff)
            ).records
        return tuple(
            sorted(
                revision_key(a)
                for a in self._actions[cutoff]
                if a.security_id == security
                and a.event_type != "SYMBOL_CHANGE"
                and (a.ex_date is None or start <= a.ex_date <= session)
            )
        )

    def audit(self, row: OOSPrediction, oos: OOSDataset, view: PriceView) -> dict[str, Any]:
        feature = next(
            r
            for r in self.features.rows
            if (r.security_id, r.session_date) == (row.security_id, row.session_date)
        )
        keys = set(feature.input_revision_keys) | {revision_key(view.observation)}
        if view.observation.quality_key:
            keys.add(view.observation.quality_key)
        quality = [
            r
            for r in self.reader.batch.revisions
            if isinstance(r, QualityRevision) and revision_key(r) in keys
        ]
        links = [link for link in self.reader.batch.lineage if link.record_key in keys]
        artifacts = {a.artifact_id: a for a in self.reader.batch.artifacts}
        return dict(
            evaluation_id=row.evaluation_id,
            prediction_id=row.prediction_id,
            model_run_id=row.model_run_id,
            fold_id=row.fold_id,
            model_identity=oos.manifest["fold_models"][row.model_run_id],
            p7_label_set_id=row.label_set_id,
            p7_supervised_dataset_id=row.supervised_dataset_id,
            p6_feature_set_id=row.feature_set_id,
            p5_canonical_input_id=row.canonical_input_id,
            p5_feature_dataset_id=row.feature_canonical_dataset_id,
            p4_universe_snapshot_id=row.universe_snapshot_id,
            p4_universe_definition=self.reader.batch.definition.model_dump(mode="json"),
            revision_keys=sorted(keys),
            p3_quality_keys=[revision_key(q) for q in quality],
            p3_report_ids=[q.evidence.report_sha256 for q in quality],
            p2_source_artifacts=[
                dict(artifact_id=k, sha256=artifacts[k].sha256, source=artifacts[k].spec.source)
                for k in sorted({link.artifact_id for link in links})
            ],
            classification=row.classification.value,
        )
