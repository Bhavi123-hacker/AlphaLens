"""Future observations are read exclusively here, never passed to feature calculations."""

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from zoneinfo import ZoneInfo

from alphalens_data.canonical.models import (
    Availability,
    CanonicalDataset,
    IdentityRevision,
    MembershipRevision,
    QualityRevision,
    ReadContext,
    revision_key,
)
from alphalens_data.canonical.revisions import known
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_features.engine import build as build_features
from alphalens_features.models import FeatureDataset, FeatureRow
from alphalens_labels.models import LabelDataset, LabelDefinition, LabelPlan, LabelRow


def validate_features(reader: CanonicalReader, features: FeatureDataset) -> None:
    if (
        reader.batch.input_id != features.canonical_input_id
        or reader.batch.classification != features.classification
    ):
        raise DataContractError("FEATURE_CANONICAL_INPUT_OR_CLASSIFICATION_MISMATCH")
    replay = build_features(reader, features.feature_set.plan, features.feature_set)
    if replay.to_bytes() != features.to_bytes():
        raise DataContractError("PINNED_FEATURE_REPLAY_MISMATCH")


def _label(
    snapshot: CanonicalDataset,
    feature: FeatureRow,
    definition: LabelDefinition,
    reader: CanonicalReader,
) -> LabelRow:
    # Build only the next h sessions. A gap/unknown day is never skipped.
    sessions = {s.session_date: s for s in snapshot.sessions}
    cursor = feature.session_date + timedelta(days=1)
    future: list[date] = []
    reasons: set[str] = set()
    maturity = "MATURE"
    while len(future) < definition.horizon and cursor <= snapshot.end_session:
        session = sessions.get(cursor)
        if session is None or session.status == "UNKNOWN_SESSION_STATUS":
            maturity = "UNAVAILABLE"
            reasons.add("FUTURE_CALENDAR_EVIDENCE_UNAVAILABLE")
            break
        if session.status == "VERIFIED_TRADING_SESSION":
            if (
                session.session_close_at is None
                or session.session_close_at > snapshot.context.knowledge_cutoff
            ):
                maturity = "NOT_YET_MATURE"
                reasons.add("TARGET_SESSION_NOT_COMPLETED")
                break
            future.append(cursor)
        cursor += timedelta(days=1)
    if len(future) < definition.horizon and not reasons:
        maturity = "NOT_YET_MATURE"
        reasons.add("INSUFFICIENT_FUTURE_SESSION_EVIDENCE")
    entry_session = future[0] if future else None
    target_session = future[-1] if len(future) == definition.horizon else None
    if entry_session is not None:
        entry_date_start = datetime.combine(entry_session, time.min, ZoneInfo("Asia/Kolkata"))
        if feature.decision_time >= entry_date_start:
            maturity = "UNAVAILABLE"
            reasons.add("DECISION_NOT_PROVEN_BEFORE_ENTRY_OPEN")
    if not feature.analytical_eligible:
        maturity = "UNAVAILABLE"
        reasons.add("FEATURE_UNIVERSE_INELIGIBLE")
    keys: set[str] = set()
    availability_times: list[datetime] = []
    fact_revisions = {
        (r.logical_record_id, r.revision_id): r
        for r in reader.batch.revisions
        if isinstance(r, (IdentityRevision, MembershipRevision)) and known(r, snapshot.context)
    }
    quality_revisions = {
        revision_key(r): r
        for r in reader.batch.revisions
        if isinstance(r, QualityRevision) and known(r, snapshot.context)
    }
    for session_date in future:
        session = sessions[session_date]
        keys.add(revision_key(session))
        if session.provenance.available_at:
            availability_times.append(session.provenance.available_at)
        universe = reader.universe_as_of(session_date, snapshot.context)
        entry = next(
            (
                e
                for e in (*universe.eligible_securities, *universe.excluded_securities)
                if e.security_id == feature.security_id
            ),
            None,
        )
        if entry:
            for fact in (entry.identity, entry.membership_evidence):
                if fact is not None:
                    wrapped = fact_revisions.get((fact.fact_id, fact.revision_id))
                    if wrapped is not None:
                        keys.add(revision_key(wrapped))
                    if fact.provenance.available_at:
                        availability_times.append(fact.provenance.available_at)
        if entry and entry.membership_evidence:
            if entry.membership_evidence.provenance.available_at:
                availability_times.append(entry.membership_evidence.provenance.available_at)
            if entry.membership_evidence.listing_status == "DELISTED":
                maturity = "TERMINAL_EVENT"
                reasons.add("DELISTED_BEFORE_TARGET_NO_TERMINAL_VALUE_ASSUMPTION")
        if not entry or not entry.universe_membership:
            if maturity != "TERMINAL_EVENT":
                maturity = "UNAVAILABLE"
            reasons.add("FUTURE_MEMBERSHIP_UNAVAILABLE_OR_INELIGIBLE")
    views = {
        p.observation.session_date: p
        for p in snapshot.prices
        if p.observation.security_id == feature.security_id
    }
    window = [views.get(d) for d in future]
    # All h outcome slots must be usable: missing intermediate bars never disappear.
    if maturity == "MATURE":
        if any(v is None for v in window):
            maturity = "UNAVAILABLE"
            reasons.add("REQUIRED_FUTURE_PRICE_UNAVAILABLE")
        elif any(v is not None and not v.analysis_eligible for v in window):
            maturity = "UNAVAILABLE"
            reasons.add("FUTURE_PRICE_QUALITY_REJECTED_OR_UNAVAILABLE")
        elif any(v is not None and v.quality == "DEGRADED" for v in window):
            if definition.quality_policy == "VALID_ONLY":
                maturity = "UNAVAILABLE"
                reasons.add("DEGRADED_FUTURE_INPUT_DISALLOWED")
            else:
                reasons.add("DEGRADED_FUTURE_INPUT")
                reasons.update(reason for v in window if v is not None for reason in v.reason_codes)
    expected_basis = "RAW_UNADJUSTED" if definition.price_basis == "UNADJUSTED" else "ADJUSTED"
    if maturity == "MATURE" and any(
        v is not None and v.observation.price_basis != expected_basis for v in window
    ):
        maturity = "UNAVAILABLE"
        reasons.add("FUTURE_PRICE_BASIS_UNKNOWN_OR_MIXED")
    for view in window:
        if view is None:
            continue
        keys.add(revision_key(view.observation))
        if view.observation.quality_key:
            keys.add(view.observation.quality_key)
        if view.observation.provenance.available_at:
            availability_times.append(view.observation.provenance.available_at)
        quality = quality_revisions.get(view.observation.quality_key or "")
        if quality and quality.provenance.available_at:
            availability_times.append(quality.provenance.available_at)
    for action in snapshot.corporate_actions:
        if (
            action.security_id == feature.security_id
            and future
            and future[0] <= (action.ex_date or action.effective_from) <= future[-1]
        ):
            keys.add(revision_key(action))
            if action.provenance.available_at:
                availability_times.append(action.provenance.available_at)
            if action.event_type == "DELISTING":
                maturity = "TERMINAL_EVENT"
                reasons.add("DELISTED_BEFORE_TARGET_NO_TERMINAL_VALUE_ASSUMPTION")
            elif action.event_type != "SYMBOL_CHANGE" and definition.price_basis == "UNADJUSTED":
                reasons.add("CORPORATE_ACTION_UNADJUSTED_NOT_TOTAL_INVESTMENT_RETURN")
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    numerator: Decimal | None = None
    value: Decimal | None = None
    if maturity == "MATURE":
        entry_view, exit_view = window[0], window[-1]
        if (
            entry_view is None
            or exit_view is None
            or entry_view.observation.values is None
            or exit_view.observation.values is None
        ):
            raise DataContractError("MATURE_TARGET_WITHOUT_PRICE_EVIDENCE")
        entry_price, exit_price = (
            entry_view.observation.values.open,
            exit_view.observation.values.close,
        )
        with localcontext() as ctx:
            ctx.prec = 76  # exact subtraction over P5 NUMERIC(38,18) range
            numerator = exit_price - entry_price
        with localcontext() as ctx:
            ctx.prec = definition.decimal_precision
            ctx.rounding = ROUND_HALF_EVEN
            value = numerator / entry_price
    label_available_at = (
        max(availability_times) if value is not None and availability_times else None
    )
    return LabelRow.model_validate(
        dict(
            security_id=feature.security_id,
            session_date=feature.session_date,
            decision_time=feature.decision_time,
            horizon=definition.horizon,
            entry_session=entry_session,
            target_session=target_session,
            label_name=definition.label_name,
            direction_name=definition.direction_name,
            return_value=value,
            direction_value=(1 if value > 0 else 0) if value is not None else None,
            entry_price=entry_price,
            exit_price=exit_price,
            exact_numerator=numerator,
            exact_denominator=entry_price,
            maturity=maturity,
            label_available_at=label_available_at,
            quality_state=Availability.UNAVAILABLE
            if value is None
            else Availability.DEGRADED
            if reasons
            else Availability.AVAILABLE,
            reason_codes=tuple(sorted(reasons)),
            canonical_dataset_id=snapshot.dataset_id,
            feature_canonical_dataset_id=feature.canonical_dataset_id,
            universe_snapshot_id=feature.universe_snapshot_id,
            input_revision_keys=tuple(sorted(keys)),
            classification=snapshot.classification,
            price_basis=definition.price_basis,
        )
    )


def build(reader: CanonicalReader, features: FeatureDataset, plan: LabelPlan) -> LabelDataset:
    validate_features(reader, features)
    if plan.outcome_end < features.feature_set.plan.decisions[-1].session_date:
        raise DataContractError("OUTCOME_SCOPE_PRECEDES_FEATURE_DECISIONS")
    if any(r.decision_time > plan.outcome_cutoff for r in features.rows):
        raise DataContractError("OUTCOME_CUTOFF_PRECEDES_FEATURE_DECISION")
    snapshot = reader.build(
        features.feature_set.plan.history_start,
        plan.outcome_end,
        ReadContext(knowledge_cutoff=plan.outcome_cutoff),
    )
    prices = [
        (p.observation.security_id, p.observation.session_date, p.observation.price_basis)
        for p in snapshot.prices
    ]
    if len(prices) != len(set(prices)) or len(snapshot.sessions) != len(
        {s.session_date for s in snapshot.sessions}
    ):
        raise DataContractError("AMBIGUOUS_CANONICAL_OUTCOME_SLOTS")
    definitions = tuple(
        LabelDefinition(
            label_name=f"forward_return_{h}",
            direction_name=f"direction_{h}",
            horizon=h,
            price_basis=features.feature_set.plan.price_basis,
            quality_policy=plan.quality_policy,
        )
        for h in plan.horizons
    )
    rows = tuple(
        _label(snapshot, feature, definition, reader)
        for feature in features.rows
        for definition in definitions
    )
    dataset = LabelDataset(
        label_set_id="0" * 64,
        canonical_dataset_id=snapshot.dataset_id,
        canonical_input_id=reader.batch.input_id,
        feature_set_id=features.feature_set_id,
        classification=snapshot.classification,
        universe_definition_version=snapshot.universe_definition.version,
        plan=plan,
        definitions=definitions,
        rows=rows,
    )
    return dataset.model_copy(
        update={
            "label_set_id": checksum(
                stable_json(dataset.model_dump(mode="json", exclude={"label_set_id"}))
            )
        }
    )
