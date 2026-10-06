"""Pinned canonical reads; identity and membership resolution belongs to P4."""

from datetime import date

from alphalens_data.canonical.models import (
    ActionRevision,
    Availability,
    CanonicalBatch,
    CanonicalDataset,
    CanonicalRead,
    FundamentalRevision,
    IdentityRevision,
    MembershipRevision,
    PriceRevision,
    PriceView,
    QualityRevision,
    ReadContext,
    SessionRevision,
    revision_key,
)
from alphalens_data.canonical.repositories import DatasetRepository
from alphalens_data.canonical.revisions import known, select_known
from alphalens_data.canonical.validation import validate_batch
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import QualityStatus
from alphalens_data.universe.models import UniverseInput, UniverseSnapshot
from alphalens_data.universe.service import HistoricalUniverse


class CanonicalReader:
    def __init__(self, batch: CanonicalBatch) -> None:
        self.batch = validate_batch(batch)
        self._universes: dict[ReadContext, HistoricalUniverse] = {}

    def universe_as_of(self, session: date, context: ReadContext) -> UniverseSnapshot:
        if context in self._universes:
            return self._universes[context].as_of(
                session, context.knowledge_cutoff, mode=context.mode
            )
        # Retain P4's complete chains. Resolve only quality revisions before delegating.
        quality = tuple(
            r.evidence
            for r in select_known(self.batch.revisions, context)
            if isinstance(r, QualityRevision)
        )
        service = HistoricalUniverse(
            UniverseInput(
                definition=self.batch.definition,
                identities=tuple(
                    r.fact for r in self.batch.revisions if isinstance(r, IdentityRevision)
                ),
                memberships=tuple(
                    r.fact for r in self.batch.revisions if isinstance(r, MembershipRevision)
                ),
                quality=quality,
            )
        )
        self._universes[context] = service
        return service.as_of(session, context.knowledge_cutoff, mode=context.mode)

    def security_metadata_as_of(
        self, session: date, context: ReadContext
    ) -> CanonicalRead[IdentityRevision]:
        snapshot = self.universe_as_of(session, context)
        selected = {
            (e.identity.fact_id, e.identity.revision_id)
            for e in (*snapshot.eligible_securities, *snapshot.excluded_securities)
            if e.identity
        }
        records = tuple(
            r
            for r in select_known(self.batch.revisions, context)
            if isinstance(r, IdentityRevision) and (r.fact.fact_id, r.revision_id) in selected
        )
        return CanonicalRead(
            availability=Availability.AVAILABLE if records else Availability.UNAVAILABLE,
            records=records,
            reason_codes=() if records else ("IDENTITY_UNAVAILABLE",),
        )

    def corporate_actions_as_of(self, context: ReadContext) -> CanonicalRead[ActionRevision]:
        records = tuple(
            r for r in select_known(self.batch.revisions, context) if isinstance(r, ActionRevision)
        )
        return CanonicalRead(
            availability=Availability.AVAILABLE if records else Availability.UNAVAILABLE,
            records=records,
            reason_codes=() if records else ("ACTION_DATA_UNAVAILABLE",),
        )

    def fundamentals_as_of(self, context: ReadContext) -> CanonicalRead[FundamentalRevision]:
        return CanonicalRead(
            availability=Availability.UNAVAILABLE,
            records=(),
            reason_codes=("FUNDAMENTAL_PIT_DATA_UNAVAILABLE",),
        )

    def sessions_as_of(
        self, start: date, end: date, context: ReadContext
    ) -> CanonicalRead[SessionRevision]:
        if end < start:
            raise DataContractError("INVALID_CANONICAL_SESSION_RANGE")
        records = tuple(
            r
            for r in select_known(self.batch.revisions, context)
            if isinstance(r, SessionRevision) and start <= r.session_date <= end
        )
        return CanonicalRead(
            availability=Availability.AVAILABLE if records else Availability.UNAVAILABLE,
            records=records,
            reason_codes=() if records else ("SESSION_EVIDENCE_UNAVAILABLE",),
        )

    def _price_views(self, start: date, end: date, context: ReadContext) -> tuple[PriceView, ...]:
        if end < start:
            raise DataContractError("INVALID_CANONICAL_SESSION_RANGE")
        selected = select_known(self.batch.revisions, context)
        all_records = {revision_key(r): r for r in self.batch.revisions}
        snapshots: dict[date, UniverseSnapshot] = {}
        result: list[PriceView] = []
        for record in sorted(
            (
                r
                for r in selected
                if isinstance(r, PriceRevision) and start <= r.session_date <= end
            ),
            key=lambda r: (r.session_date, r.security_id or "", r.price_basis, revision_key(r)),
        ):
            if record.session_date not in snapshots:
                snapshots[record.session_date] = self.universe_as_of(record.session_date, context)
            snapshot = snapshots[record.session_date]
            entry = next(
                (
                    e
                    for e in (*snapshot.eligible_securities, *snapshot.excluded_securities)
                    if e.security_id == record.security_id
                ),
                None,
            )
            quality = all_records.get(record.quality_key or "")
            status: QualityStatus | str = "UNAVAILABLE"
            reasons: set[str] = set(record.rejection_reason_codes)
            if isinstance(quality, QualityRevision) and known(quality, context):
                assessment = next(
                    (
                        s
                        for s in quality.evidence.report.sessions
                        if entry
                        and entry.identity
                        and s.security_id == entry.identity.source_security_id
                        and s.session_date == record.session_date
                    ),
                    None,
                )
                if quality.evidence.report.dataset_blocked or record.values is None:
                    status = QualityStatus.REJECTED
                elif assessment:
                    status = assessment.status
                    reasons.update(assessment.reason_codes)
            if status == "UNAVAILABLE":
                reasons.add("DATA_QUALITY_UNAVAILABLE")
            if status == QualityStatus.REJECTED or record.values is None:
                reasons.add("DATA_QUALITY_REJECTED")
            membership = bool(entry and entry.universe_membership)
            if not membership:
                reasons.add(entry.membership_reason if entry else "SECURITY_EVIDENCE_UNAVAILABLE")
            availability = (
                Availability.UNAVAILABLE
                if record.values is None
                else Availability.DEGRADED
                if status != QualityStatus.VALID
                else Availability.AVAILABLE
            )
            if (
                record.values is not None
                and context.earliest_acceptable_availability
                and record.provenance.available_at
                and record.provenance.available_at < context.earliest_acceptable_availability
            ):
                availability = Availability.STALE
                reasons.add("EXPLICIT_FRESHNESS_POLICY_FAILED")
            result.append(
                PriceView(
                    observation=record,
                    quality=status,
                    availability=availability,
                    universe_membership=membership,
                    analysis_eligible=membership
                    and bool(entry and entry.analysis_eligible)
                    and status in {QualityStatus.VALID, QualityStatus.DEGRADED}
                    and record.values is not None
                    and availability != Availability.STALE,
                    reason_codes=tuple(sorted(reasons)),
                )
            )
        return tuple(result)

    def prices_as_of(
        self, start: date, end: date, context: ReadContext
    ) -> CanonicalRead[PriceView]:
        records = self._price_views(start, end, context)
        availability = (
            Availability.UNAVAILABLE
            if not records or all(r.availability == Availability.UNAVAILABLE for r in records)
            else Availability.STALE
            if all(r.availability == Availability.STALE for r in records)
            else Availability.DEGRADED
            if any(r.availability != Availability.AVAILABLE for r in records)
            else Availability.AVAILABLE
        )
        return CanonicalRead(
            availability=availability,
            records=records,
            reason_codes=("NO_KNOWN_PRICE_EVIDENCE",) if not records else (),
        )

    def build(self, start: date, end: date, context: ReadContext) -> CanonicalDataset:
        price_read = self.prices_as_of(start, end, context)
        prices = price_read.records
        selected = select_known(self.batch.revisions, context)
        sessions = tuple(
            r for r in selected if isinstance(r, SessionRevision) and start <= r.session_date <= end
        )
        dates = sorted(
            {p.observation.session_date for p in prices} | {s.session_date for s in sessions}
        )
        if not dates:
            raise DataContractError("CANONICAL_SNAPSHOT_HAS_NO_KNOWN_SESSIONS")
        identities = tuple(r for r in selected if isinstance(r, IdentityRevision))
        quality = tuple(
            r
            for r in selected
            if isinstance(r, QualityRevision) and start <= r.evidence.session_date <= end
        )
        linked_keys = {revision_key(r) for r in selected}
        artifact_ids = {
            link.artifact_id for link in self.batch.lineage if link.record_key in linked_keys
        }
        provisional = CanonicalDataset(
            dataset_id="0" * 64,
            input_id=self.batch.input_id,
            classification=self.batch.classification,
            context=context,
            start_session=start,
            end_session=end,
            normalization_versions=tuple(
                sorted({n.normalization_version for n in self.batch.normalized})
            ),
            validation_versions=tuple(
                sorted({q.evidence.report.validator_version for q in quality})
            ),
            universe_definition=self.batch.definition,
            artifact_hashes=tuple(
                sorted({a.sha256 for a in self.batch.artifacts if a.artifact_id in artifact_ids})
            ),
            prices=prices,
            identities=identities,
            sessions=sessions,
            corporate_actions=self.corporate_actions_as_of(context).records,
            quality=quality,
            universe_snapshots=tuple(self.universe_as_of(d, context) for d in dates),
            family_states={
                "prices": price_read.availability,
                "security_metadata": Availability.AVAILABLE
                if identities
                else Availability.UNAVAILABLE,
                "corporate_actions": self.corporate_actions_as_of(context).availability,
                "fundamentals": Availability.UNAVAILABLE,
            },
        )
        return provisional.model_copy(
            update={
                "dataset_id": checksum(
                    stable_json(provisional.model_dump(mode="json", exclude={"dataset_id"}))
                )
            }
        )


def validate_snapshot(snapshot: CanonicalDataset, batch: CanonicalBatch) -> None:
    rebuilt = CanonicalReader(batch).build(
        snapshot.start_session, snapshot.end_session, snapshot.context
    )
    if rebuilt.to_bytes() != snapshot.to_bytes():
        raise DataContractError("CANONICAL_SNAPSHOT_REPLAY_MISMATCH")


def load_reader(repository: DatasetRepository, input_id: str) -> CanonicalReader:
    batch = repository.get_input(input_id)
    if batch is None:
        raise DataContractError("CANONICAL_INPUT_UNAVAILABLE")
    return CanonicalReader(batch)
