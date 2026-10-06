"""Shared immutable revision-chain checks; chronological knowledge, not last-write wins."""

from collections import defaultdict

from alphalens_data.canonical.models import (
    ActionRevision,
    FundamentalRevision,
    IdentityRevision,
    MembershipRevision,
    PriceRevision,
    QualityRevision,
    ReadContext,
    Revision,
    SessionRevision,
    revision_key,
)
from alphalens_data.errors import DataContractError


def parent_key(record: Revision) -> str | None:
    if record.supersedes_revision_id is None:
        return None
    return revision_key(record.model_copy(update={"revision_id": record.supersedes_revision_id}))


def validate_parent(record: Revision, parent: Revision | None) -> None:
    if parent is None:
        if record.supersedes_revision_id is not None:
            raise DataContractError("MISSING_REVISION_PARENT")
        return
    if (
        record.kind != parent.kind
        or record.logical_record_id != parent.logical_record_id
        or record.security_id != parent.security_id
        or record.provenance.source != parent.provenance.source
        or record.provenance.classification != parent.provenance.classification
        or record.revision_number != parent.revision_number + 1
        or record.supersedes_revision_id != parent.revision_id
    ):
        raise DataContractError("INVALID_REVISION_CHAIN")
    if record.provenance.ingested_at < parent.provenance.ingested_at or (
        record.provenance.available_at
        and parent.provenance.available_at
        and record.provenance.available_at < parent.provenance.available_at
    ):
        raise DataContractError("REVISION_TIME_INVERSION")
    if isinstance(record, PriceRevision) and isinstance(parent, PriceRevision):
        if (record.session_date, record.price_basis) != (parent.session_date, parent.price_basis):
            raise DataContractError("PRICE_REVISION_SCOPE_CHANGED")
    elif isinstance(record, SessionRevision) and isinstance(parent, SessionRevision):
        if record.session_date != parent.session_date:
            raise DataContractError("SESSION_REVISION_SCOPE_CHANGED")
    elif isinstance(record, ActionRevision) and isinstance(parent, ActionRevision):
        if record.corporate_action_id != parent.corporate_action_id:
            raise DataContractError("ACTION_REVISION_SCOPE_CHANGED")
    elif isinstance(record, FundamentalRevision) and isinstance(parent, FundamentalRevision):
        if (record.fact_name, record.period_end, record.unit) != (
            parent.fact_name,
            parent.period_end,
            parent.unit,
        ):
            raise DataContractError("FUNDAMENTAL_REVISION_SCOPE_CHANGED")
    elif isinstance(record, IdentityRevision | MembershipRevision) and isinstance(
        parent, IdentityRevision | MembershipRevision
    ):
        if record.fact.fact_id != parent.fact.fact_id:
            raise DataContractError("P4_FACT_REVISION_SCOPE_CHANGED")
    elif (
        isinstance(record, QualityRevision)
        and isinstance(parent, QualityRevision)
        and record.evidence.session_date != parent.evidence.session_date
    ):
        raise DataContractError("QUALITY_REVISION_SCOPE_CHANGED")


def ordered_revisions(records: tuple[Revision, ...]) -> tuple[Revision, ...]:
    keyed = {revision_key(r): r for r in records}
    if len(keyed) != len(records):
        raise DataContractError("DUPLICATE_CANONICAL_REVISION")
    children: dict[str, str] = {}
    roots: dict[tuple[str, str, str], int] = defaultdict(int)
    for record in records:
        key = parent_key(record)
        validate_parent(record, keyed.get(key) if key else None)
        if key:
            if key in children:
                raise DataContractError("BRANCHING_CANONICAL_REVISION")
            children[key] = revision_key(record)
        else:
            roots[(record.kind, record.provenance.source, record.logical_record_id)] += 1
    if any(count != 1 for count in roots.values()):
        raise DataContractError("CANONICAL_REQUIRES_SINGLE_REVISION_ROOT")
    return tuple(sorted(records, key=lambda r: (r.revision_number, revision_key(r))))


def known(record: Revision, context: ReadContext) -> bool:
    provenance = record.provenance
    return (
        provenance.available_at is not None
        and provenance.available_at <= context.knowledge_cutoff
        and (context.mode == "historical" or provenance.ingested_at <= context.knowledge_cutoff)
    )


def select_known(records: tuple[Revision, ...], context: ReadContext) -> tuple[Revision, ...]:
    latest: dict[tuple[str, str, str], Revision] = {}
    for record in records:
        if not known(record, context):
            continue
        key = (record.kind, record.provenance.source, record.logical_record_id)
        if key not in latest or latest[key].revision_number < record.revision_number:
            latest[key] = record
    return tuple(sorted(latest.values(), key=revision_key))
