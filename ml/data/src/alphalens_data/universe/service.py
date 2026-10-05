"""Indexed known-revision selection and half-open historical universe reconstruction."""

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import VALIDATOR_VERSION, QualityStatus
from alphalens_data.universe.models import (
    EffectiveFact,
    SecurityType,
    SurvivorshipAudit,
    UniverseEntry,
    UniverseInput,
    UniverseSnapshot,
)


class FactIndex[Fact: EffectiveFact]:
    def __init__(self, facts: tuple[Fact, ...]) -> None:
        groups: dict[str, list[Fact]] = defaultdict(list)
        self.securities = {fact.security_id for fact in facts}
        for fact in facts:
            groups[fact.fact_id].append(fact)
        self.histories: dict[str, dict[str, tuple[tuple[datetime, ...], tuple[Fact, ...]]]] = (
            defaultdict(dict)
        )
        for fact_id, revisions in groups.items():
            by_revision = {r.revision_id: r for r in revisions}
            if len(by_revision) != len(revisions) or len({r.security_id for r in revisions}) != 1:
                raise DataContractError("CONFLICTING_FACT_REVISION")
            roots = [r for r in revisions if r.supersedes_revision_id is None]
            if len(roots) != 1:
                raise DataContractError("FACT_REQUIRES_SINGLE_REVISION_ROOT")
            successors: dict[str, Fact] = {}
            for r in revisions:
                previous_id = r.supersedes_revision_id
                if previous_id is None:
                    continue
                if previous_id not in by_revision or previous_id in successors:
                    raise DataContractError("INVALID_OR_BRANCHING_REVISION_CHAIN")
                previous = by_revision[previous_id]
                if r.provenance.ingested_at < previous.provenance.ingested_at or (
                    previous.provenance.available_at
                    and r.provenance.available_at
                    and r.provenance.available_at < previous.provenance.available_at
                ):
                    raise DataContractError("REVISION_TIME_INVERSION")
                successors[previous_id] = r
            ordered: list[Fact] = []
            current: Fact | None = roots[0]
            visited: set[str] = set()
            while current:
                if current.revision_id in visited:
                    raise DataContractError("REVISION_CYCLE")
                visited.add(current.revision_id)
                ordered.append(current)
                current = successors.get(current.revision_id)
            if len(ordered) != len(revisions):
                raise DataContractError("DISCONNECTED_REVISION_CHAIN")
            # Unknown-availability revisions never supersede known historical facts.
            known = tuple(r for r in ordered if r.provenance.available_at is not None)
            times = tuple(r.provenance.available_at for r in known)
            # The guard above narrows runtime values; keep the typed index explicit.
            known_times = tuple(t for t in times if t is not None)
            if any(a > b for a, b in zip(known_times, known_times[1:], strict=False)):
                raise DataContractError("REVISION_TIME_INVERSION")
            self.histories[roots[0].security_id][fact_id] = (known_times, known)

    def known(self, security: str, at: datetime, mode: str) -> tuple[Fact, ...]:
        selected: list[Fact] = []
        for times, history in self.histories.get(security, {}).values():
            index = bisect_right(times, at) - 1
            if mode == "live":
                while index >= 0 and history[index].provenance.ingested_at > at:
                    index -= 1
            if index >= 0:
                selected.append(history[index])
        selected.sort(key=lambda r: (r.effective_from, r.fact_id, r.revision_id))
        for left, right in zip(selected, selected[1:], strict=False):
            if left.effective_to is None or left.effective_to > right.effective_from:
                raise DataContractError("OVERLAPPING_EXCLUSIVE_EFFECTIVE_FACTS")
        return tuple(selected)

    @staticmethod
    def active(facts: tuple[Fact, ...], session: date) -> Fact | None:
        index = bisect_right(tuple(f.effective_from for f in facts), session) - 1
        if index < 0:
            return None
        fact = facts[index]
        return fact if fact.effective_to is None or session < fact.effective_to else None


class HistoricalUniverse:
    def __init__(self, data: UniverseInput) -> None:
        self.data = UniverseInput.model_validate(data.model_dump())
        data = self.data
        if data.definition.evidence_scope == "CURRENT_SNAPSHOT_ONLY":
            raise DataContractError("CURRENT_SNAPSHOT_CANNOT_DEFINE_HISTORICAL_MEMBERSHIP")
        classification = data.definition.classification
        if any(
            f.provenance.classification != classification
            for f in (*data.identities, *data.memberships)
        ):
            raise DataContractError("MIXED_UNIVERSE_CLASSIFICATION")
        if any(q.report.classification != classification for q in data.quality):
            raise DataContractError("MIXED_QUALITY_CLASSIFICATION")
        validator_versions = {q.report.validator_version for q in data.quality}
        if len(validator_versions) > 1:
            raise DataContractError("QUALITY_VALIDATOR_VERSION_MISMATCH")
        self.validator_version = next(iter(validator_versions), VALIDATOR_VERSION)
        self.identities = FactIndex(data.identities)
        self.memberships = FactIndex(data.memberships)
        self.securities = tuple(sorted(self.identities.securities | self.memberships.securities))
        self.quality = {q.session_date: q for q in data.quality}
        if len(self.quality) != len(data.quality):
            raise DataContractError("AMBIGUOUS_SESSION_QUALITY_REPORTS")
        self.quality_sessions = {
            session: {(s.security_id, s.session_date): s for s in q.report.sessions}
            for session, q in self.quality.items()
        }
        canonical_input = data.model_dump(mode="json")
        for family in ("identities", "memberships"):
            canonical_input[family].sort(
                key=lambda f: (f["security_id"], f["fact_id"], f["revision_id"])
            )
        canonical_input["quality"].sort(key=lambda q: q["session_date"])
        self.input_sha256 = checksum(stable_json(canonical_input))

    def as_of(
        self,
        session_date: date,
        decision_time: datetime,
        *,
        mode: Literal["historical", "live"] = "historical",
    ) -> UniverseSnapshot:
        if decision_time.tzinfo is None or decision_time.utcoffset() is None:
            raise DataContractError("NAIVE_DECISION_TIMESTAMP")
        if mode not in {"historical", "live"}:
            raise DataContractError("INVALID_KNOWLEDGE_MODE")
        decision_time = decision_time.astimezone(UTC)
        if session_date > decision_time.astimezone(ZoneInfo("Asia/Kolkata")).date():
            raise DataContractError("FUTURE_SESSION_QUERY")
        quality = self.quality.get(session_date)
        if quality and (
            quality.available_at is None
            or quality.available_at > decision_time
            or (mode == "live" and quality.ingested_at > decision_time)
        ):
            quality = None
        entries: list[UniverseEntry] = []
        known_facts: list[EffectiveFact] = []
        identity_keys: dict[tuple[str, str, str], str] = {}
        for security in self.securities:
            known_identity = self.identities.known(security, decision_time, mode)
            known_membership = self.memberships.known(security, decision_time, mode)
            known_facts.extend((*known_identity, *known_membership))
            identity = self.identities.active(known_identity, session_date)
            membership = self.memberships.active(known_membership, session_date)
            reason = "INCLUDED_LISTED_CASH_EQUITY"
            included = False
            if not membership:
                future_listing = any(
                    f.effective_from > session_date and f.listing_status == "LISTED"
                    for f in known_membership
                )
                reason = (
                    "EXCLUDED_NOT_YET_LISTED"
                    if future_listing
                    else (
                        "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE"
                        if known_membership
                        else "EXCLUDED_INFORMATION_NOT_AVAILABLE"
                    )
                )
            elif membership.listing_status == "DELISTED":
                reason = "EXCLUDED_DELISTED"
            elif membership.listing_status == "NOT_YET_LISTED":
                reason = "EXCLUDED_NOT_YET_LISTED"
            elif membership.listing_status == "UNKNOWN":
                reason = "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE"
            elif membership.security_type == SecurityType.UNKNOWN:
                reason = "EXCLUDED_UNKNOWN_CLASSIFICATION"
            elif membership.security_type != SecurityType.COMMON_EQUITY:
                reason = "EXCLUDED_SECURITY_TYPE"
            elif identity is None:
                reason = "EXCLUDED_INFORMATION_NOT_AVAILABLE"
            else:
                included = True
            if identity:
                for attribute in ("source_security_id", "symbol", "isin"):
                    value = getattr(identity, attribute)
                    if not value:
                        continue
                    key = (identity.provenance.source, attribute, value)
                    if key in identity_keys and identity_keys[key] != security:
                        raise DataContractError("SIMULTANEOUS_IDENTITY_CONFLICT")
                    identity_keys[key] = security
            quality_status: QualityStatus | Literal["UNAVAILABLE"] = "UNAVAILABLE"
            quality_reasons: tuple[str, ...] = ("SESSION_QUALITY_UNAVAILABLE",)
            if quality and identity and quality.source == identity.provenance.source:
                assessment = self.quality_sessions[session_date].get(
                    (identity.source_security_id, session_date)
                )
                if quality.report.dataset_blocked:
                    quality_status = QualityStatus.REJECTED
                    quality_reasons = tuple(
                        sorted(
                            {
                                i.rule_id
                                for i in quality.report.issues
                                if i.security_id is None and i.severity in {"ERROR", "FATAL"}
                            }
                        )
                    )
                elif assessment:
                    quality_status = (
                        QualityStatus.REJECTED
                        if quality.report.dataset_blocked
                        else assessment.status
                    )
                    quality_reasons = assessment.reason_codes
            analysis = included and quality_status in {QualityStatus.VALID, QualityStatus.DEGRADED}
            analysis_reason = (
                "ANALYSIS_ELIGIBLE"
                if analysis
                else (
                    "DATA_QUALITY_REJECTED"
                    if included and quality_status == QualityStatus.REJECTED
                    else "DATA_QUALITY_UNAVAILABLE"
                    if included
                    else reason
                )
            )
            entries.append(
                UniverseEntry(
                    security_id=security,
                    universe_membership=included,
                    membership_reason=reason,
                    identity=identity,
                    membership_evidence=membership,
                    evidence_status="VERIFIED" if identity and membership else "UNKNOWN",
                    data_quality_status=quality_status,
                    data_quality_reasons=quality_reasons,
                    analysis_eligible=analysis,
                    analysis_reason=analysis_reason,
                )
            )
        eligible = tuple(e for e in entries if e.universe_membership)
        excluded = tuple(e for e in entries if not e.universe_membership)
        unknown = any(
            e.membership_reason
            in {
                "EXCLUDED_INFORMATION_NOT_AVAILABLE",
                "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE",
                "EXCLUDED_UNKNOWN_CLASSIFICATION",
            }
            for e in entries
        )
        status = (
            "UNAVAILABLE"
            if self.data.definition.coverage_status in {"UNKNOWN", "NOT_SUPPORTED"}
            else "DEGRADED"
            if unknown or self.data.definition.coverage_status != "VERIFIED"
            else "AVAILABLE"
        )
        known_payload = {
            "facts": [
                f.model_dump(mode="json")
                for f in sorted(
                    known_facts,
                    key=lambda f: (f.security_id, type(f).__name__, f.fact_id, f.revision_id),
                )
            ],
            "quality": quality.model_dump(mode="json") if quality else None,
        }
        references = {f.provenance.artifact_reference for f in known_facts}
        if quality:
            references.add(quality.evidence_reference)
        payload = {
            "session_date": session_date.isoformat(),
            "decision_time": decision_time.isoformat(),
            "knowledge_mode": mode,
            "universe_definition": self.data.definition.model_dump(mode="json"),
            "identity_version": "p4.identity.v1",
            "membership_version": "p4.membership.v1",
            "validator_version": self.validator_version,
            "input_sha256": self.input_sha256,
            "known_evidence_sha256": checksum(stable_json(known_payload)),
            "historical_universe_status": status,
            "eligible_securities": [e.model_dump(mode="json") for e in eligible],
            "excluded_securities": [e.model_dump(mode="json") for e in excluded],
            "input_artifact_references": sorted(references),
            "production_claims_permitted": False,
        }
        provisional = UniverseSnapshot.model_validate({"snapshot_id": "0" * 64, **payload})
        return provisional.model_copy(
            update={
                "snapshot_id": checksum(
                    stable_json(provisional.model_dump(mode="json", exclude={"snapshot_id"}))
                )
            }
        )

    def replay(self, snapshot: UniverseSnapshot) -> bool:
        rebuilt = self.as_of(
            snapshot.session_date, snapshot.decision_time, mode=snapshot.knowledge_mode
        )
        if rebuilt.to_bytes() != snapshot.to_bytes():
            raise DataContractError("UNIVERSE_REPLAY_INPUT_OR_OUTPUT_MISMATCH")
        return True


def audit(snapshots: tuple[UniverseSnapshot, ...]) -> SurvivorshipAudit:
    if not snapshots:
        raise DataContractError("EMPTY_UNIVERSE_AUDIT")
    if any(
        a.session_date >= b.session_date for a, b in zip(snapshots, snapshots[1:], strict=False)
    ):
        raise DataContractError("AUDIT_REQUIRES_UNIQUE_CHRONOLOGICAL_SESSIONS")
    first = snapshots[0]
    if any(
        s.input_sha256 != first.input_sha256
        or s.universe_definition != first.universe_definition
        or s.knowledge_mode != first.knowledge_mode
        for s in snapshots
    ):
        raise DataContractError("AUDIT_REQUIRES_PINNED_INPUT_AND_DEFINITION")
    historic: set[str] = set()
    previous: set[str] = set()
    symbols: dict[str, str] = {}
    changes = entries = exits = quality_exclusions = 0
    exclusions: Counter[str] = Counter()
    unknown = unavailable = 0
    for snapshot in snapshots:
        current = {e.security_id for e in snapshot.eligible_securities}
        historic.update(current)
        entries += len(current - previous)
        exits += len(previous - current)
        for entry in (*snapshot.eligible_securities, *snapshot.excluded_securities):
            if not entry.universe_membership:
                exclusions[entry.membership_reason] += 1
            unknown += entry.membership_reason == "EXCLUDED_UNKNOWN_CLASSIFICATION"
            unavailable += entry.membership_reason in {
                "EXCLUDED_INFORMATION_NOT_AVAILABLE",
                "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE",
            }
            quality_exclusions += entry.universe_membership and not entry.analysis_eligible
            if entry.universe_membership and entry.identity:
                symbol = entry.identity.symbol
                if entry.security_id in symbols and symbols[entry.security_id] != symbol:
                    changes += 1
                symbols[entry.security_id] = symbol
        previous = current
    return SurvivorshipAudit(
        classification=first.universe_definition.classification,
        snapshot_ids=tuple(s.snapshot_id for s in snapshots),
        unique_historical_security_count=len(historic),
        entries=entries,
        exits=exits,
        symbol_changes=changes,
        exclusions_by_reason=dict(sorted(exclusions.items())),
        unknown_classification_count=unknown,
        unavailable_membership_evidence_count=unavailable,
        historically_present_absent_at_end=tuple(sorted(historic - previous)),
        data_quality_exclusion_count=quality_exclusions,
    )
