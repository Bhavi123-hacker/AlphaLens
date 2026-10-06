"""Validate the canonical graph, classifications and original lineage before writes."""

from alphalens_data.canonical.models import (
    ActionRevision,
    CanonicalBatch,
    IdentityRevision,
    MembershipRevision,
    NormalizedEvidence,
    PriceRevision,
    QualityRevision,
    revision_key,
)
from alphalens_data.canonical.revisions import ordered_revisions
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification, QuarantineRecord
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.universe.models import UniverseInput
from alphalens_data.universe.service import HistoricalUniverse


def validate_batch(batch: CanonicalBatch) -> CanonicalBatch:
    n: NormalizedEvidence | None
    q: QuarantineRecord | None
    batch = CanonicalBatch.model_validate(batch.model_dump())
    if batch.classification == Classification.PRODUCTION:
        raise DataContractError("PRODUCTION_CANONICAL_NOT_CLEARED")
    classification = batch.classification
    if (
        batch.definition.classification != classification
        or any(s.classification != classification for s in batch.securities)
        or any(a.spec.classification != classification for a in batch.artifacts)
        or any(r.classification != classification for r in batch.runs)
        or any(r.provenance.classification != classification for r in batch.revisions)
        or any(q.record.classification != classification for q in batch.quarantine)
    ):
        raise DataContractError("MIXED_CANONICAL_CLASSIFICATION")
    ordered_revisions(batch.revisions)
    if any(r.kind == "FUNDAMENTAL" for r in batch.revisions):
        raise DataContractError("FUNDAMENTAL_PIT_DATA_UNAVAILABLE")
    artifacts = {a.artifact_id: a for a in batch.artifacts}
    securities = {s.security_id for s in batch.securities}
    normalized = {n.normalized_record_id: n for n in batch.normalized}
    quarantine = {q.quarantine_key: q.record for q in batch.quarantine}
    records = {revision_key(r): r for r in batch.revisions}
    if (
        len(artifacts) != len(batch.artifacts)
        or len(securities) != len(batch.securities)
        or len(normalized) != len(batch.normalized)
        or len(quarantine) != len(batch.quarantine)
    ):
        raise DataContractError("DUPLICATE_CANONICAL_EVIDENCE")
    for n in batch.normalized:
        if n.artifact_id not in artifacts:
            raise DataContractError("NORMALIZED_ARTIFACT_MISSING")
        if n.normalization_version == "p2.eod.v1":
            a = artifacts[n.artifact_id]
            p = n.payload
            expected = checksum(
                stable_json(
                    [
                        a.artifact_id,
                        p.get("source_row_number"),
                        p.get("source_row_sha256"),
                        p.get("versions"),
                    ]
                )
            )
            if (
                n.normalized_record_id != expected
                or p.get("artifact_id") != a.artifact_id
                or p.get("raw_sha256") != a.sha256
                or p.get("source") != a.spec.source
                or p.get("classification") != classification
            ):
                raise DataContractError("P2_NORMALIZED_LINEAGE_MISMATCH")
        elif n.normalized_record_id != checksum(
            stable_json(
                [
                    n.artifact_id,
                    n.normalization_version,
                    n.payload,
                ]
            )
        ):
            raise DataContractError("REFERENCE_NORMALIZATION_MISMATCH")
    for key, q in quarantine.items():
        if (
            key != checksum(stable_json(q.model_dump(mode="json")))
            or q.artifact_id not in artifacts
        ):
            raise DataContractError("QUARANTINE_LINEAGE_MISMATCH")
        if q.raw_sha256 != artifacts[q.artifact_id].sha256:
            raise DataContractError("QUARANTINE_CHECKSUM_MISMATCH")
    by_record: dict[str, list[str]] = {}
    source_records: dict[str, set[str]] = {}
    declared: set[str] = set()
    for link in batch.lineage:
        record = records.get(link.record_key)
        artifact = artifacts.get(link.artifact_id)
        if record is None or artifact is None:
            raise DataContractError("CANONICAL_LINEAGE_FOREIGN_KEY_MISSING")
        by_record.setdefault(link.record_key, []).append(link.artifact_id)
        if link.normalized_record_id:
            n = normalized.get(link.normalized_record_id)
            if n is None or n.artifact_id != artifact.artifact_id:
                raise DataContractError("NORMALIZED_LINEAGE_FOREIGN_KEY_MISSING")
            if n.normalization_version == "p5.reference.v1" and n.payload == record.model_dump(
                mode="json"
            ):
                declared.add(link.record_key)
            if link.source_record_id and link.source_record_id != checksum(
                stable_json(
                    [
                        link.normalized_record_id,
                        "canonical",
                    ]
                )
            ):
                raise DataContractError("P2_SOURCE_RECORD_ID_MISMATCH")
            if isinstance(record, PriceRevision) and n.normalization_version == "p2.eod.v1":
                if link.source_record_id is None:
                    raise DataContractError("P2_CANONICAL_SOURCE_RECORD_ID_REQUIRED")
                source_records.setdefault(link.record_key, set()).add(link.source_record_id)
                p = n.payload
                if (
                    p.get("source") != record.provenance.source
                    or p.get("session_date") != record.session_date.isoformat()
                    or p.get("currency") != record.currency
                ):
                    raise DataContractError("PRICE_SOURCE_SCOPE_MISMATCH")
                if not any(
                    isinstance(identity, IdentityRevision)
                    and identity.security_id == record.security_id
                    and identity.fact.source_security_id == p.get("security_id")
                    and identity.provenance.source == record.provenance.source
                    for identity in batch.revisions
                ):
                    raise DataContractError("PRICE_DURABLE_IDENTITY_MAPPING_MISSING")
                if record.price_basis != "ADJUSTED" and record.values:
                    from alphalens_data.canonical.models import EODValues

                    expected_values = EODValues.model_validate(
                        {name: p[name] for name in ("open", "high", "low", "close", "volume")}
                    )
                    if any(
                        getattr(record.values, name) != getattr(expected_values, name)
                        for name in ("open", "high", "low", "close", "volume")
                    ):
                        raise DataContractError("PRICE_NORMALIZED_VALUES_MISMATCH")
        if link.quarantine_key:
            q = quarantine.get(link.quarantine_key)
            if q is None or q.artifact_id != artifact.artifact_id:
                raise DataContractError("QUARANTINE_LINEAGE_FOREIGN_KEY_MISSING")
            if isinstance(record, PriceRevision) and record.values is not None:
                raise DataContractError("QUARANTINE_CANNOT_BECOME_USABLE_VALUES")
    for key, record in records.items():
        if record.security_id and record.security_id not in securities:
            raise DataContractError("CANONICAL_SECURITY_FOREIGN_KEY_MISSING")
        linked = by_record.get(key, [])
        if not linked or not any(
            artifacts[a].sha256 == record.provenance.artifact_sha256 for a in linked
        ):
            raise DataContractError("CANONICAL_PROVENANCE_CHECKSUM_MISMATCH")
        if key not in declared:
            raise DataContractError("CANONICAL_RECORD_DECLARATION_MISMATCH")
        if isinstance(record, PriceRevision):
            if (
                record.values is not None
                and record.price_basis != "ADJUSTED"
                and key not in source_records
            ):
                raise DataContractError("OBSERVED_PRICE_NORMALIZATION_REQUIRED")
            if record.quality_key:
                quality = records.get(record.quality_key)
                if (
                    not isinstance(quality, QualityRevision)
                    or quality.provenance.source != record.provenance.source
                    or quality.evidence.session_date != record.session_date
                ):
                    raise DataContractError("PRICE_QUALITY_FOREIGN_KEY_MISMATCH")
                if (
                    record.values is not None
                    and record.price_basis != "ADJUSTED"
                    and not quality.evidence.report.dataset_blocked
                ):
                    assessed = {
                        record_id
                        for session in quality.evidence.report.sessions
                        for record_id in session.record_ids
                    }
                    if not source_records.get(key, set()) <= assessed:
                        raise DataContractError("PRICE_QUALITY_RECORD_LINEAGE_MISMATCH")
            if record.adjustment:
                action = records.get(record.adjustment.corporate_action_key)
                original = records.get(record.adjustment.original_price_key)
                if (
                    not isinstance(action, ActionRevision)
                    or not isinstance(original, PriceRevision)
                    or action.security_id != record.security_id
                    or original.security_id != record.security_id
                    or original.session_date != record.session_date
                    or original.price_basis != "RAW_UNADJUSTED"
                    or action.provenance.available_at is None
                    or record.provenance.available_at is None
                    or action.provenance.available_at > record.provenance.available_at
                ):
                    raise DataContractError("ADJUSTMENT_EVIDENCE_MISMATCH")
    # Reuse P4's revision and current-snapshot protections; no competing identity engine.
    HistoricalUniverse(
        UniverseInput(
            definition=batch.definition,
            identities=tuple(r.fact for r in batch.revisions if isinstance(r, IdentityRevision)),
            memberships=tuple(r.fact for r in batch.revisions if isinstance(r, MembershipRevision)),
        )
    )
    return batch
