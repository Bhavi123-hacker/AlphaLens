"""Features consume only P5 cutoff snapshots; all trailing windows retain bad/missing slots."""

import math
from datetime import date, timedelta

from alphalens_data.canonical.models import (
    Availability,
    CanonicalDataset,
    PriceView,
    ReadContext,
    revision_key,
)
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.universe.models import UniverseEntry
from alphalens_features.maths import calculate
from alphalens_features.models import (
    BuildPlan,
    FeatureDataset,
    FeatureDefinition,
    FeatureRow,
    FeatureSet,
    FeatureValue,
)
from alphalens_features.registry import default_set


def unavailable(*reasons: str) -> FeatureValue:
    return FeatureValue(
        value=None, state=Availability.UNAVAILABLE, reason_codes=tuple(sorted(set(reasons)))
    )


def calendar_dates(snapshot: CanonicalDataset, end: date) -> tuple[list[date], str | None]:
    by_date = {s.session_date: s for s in snapshot.sessions}
    cursor = snapshot.start_session
    dates: list[date] = []
    while cursor <= end:
        session = by_date.get(cursor)
        if session is None or session.status == "UNKNOWN_SESSION_STATUS":
            return [], "CALENDAR_EVIDENCE_UNAVAILABLE"
        if session.status == "VERIFIED_TRADING_SESSION":
            if (
                session.session_close_at is None
                or session.session_close_at > snapshot.context.knowledge_cutoff
            ):
                return [], "SESSION_NOT_COMPLETED"
            dates.append(cursor)
        cursor += timedelta(days=1)
    if not dates or dates[-1] != end:
        return [], "DECISION_NOT_VERIFIED_TRADING_SESSION"
    return dates, None


def _window_value(
    definition: FeatureDefinition,
    dates: list[date],
    views: dict[date, PriceView],
    entry: UniverseEntry,
    snapshot: CanonicalDataset,
    plan: BuildPlan,
    name: str | None = None,
) -> FeatureValue:
    if not entry.universe_membership or not entry.analysis_eligible:
        return unavailable("UNIVERSE_INELIGIBLE", entry.analysis_reason, entry.membership_reason)
    if len(dates) < definition.minimum_history:
        return unavailable("INSUFFICIENT_HISTORY")
    window_dates = dates[-definition.lookback :]
    records = [views.get(d) for d in window_dates]
    reasons: set[str] = set()
    if any(r is None for r in records):
        return unavailable("REQUIRED_SESSION_PRICE_UNAVAILABLE")
    window = [r for r in records if r is not None]
    if any(not r.analysis_eligible for r in window):
        return unavailable(
            "UNUSABLE_LOOKBACK_OBSERVATION",
            *(reason for r in window if not r.analysis_eligible for reason in r.reason_codes),
        )
    if any(r.quality == "DEGRADED" for r in window):
        if definition.data_quality_policy == "VALID_ONLY":
            return unavailable("DEGRADED_INPUT_DISALLOWED")
        reasons.add("DEGRADED_INPUT")
        reasons.update(reason for r in window for reason in r.reason_codes)
    expected_basis = "RAW_UNADJUSTED" if plan.price_basis == "UNADJUSTED" else "ADJUSTED"
    if any(r.observation.price_basis != expected_basis for r in window):
        return unavailable("PRICE_BASIS_UNKNOWN_OR_MIXED")
    actions = [
        a
        for a in snapshot.corporate_actions
        if a.security_id == entry.security_id
        and a.event_type != "SYMBOL_CHANGE"
        and window_dates[0] <= (a.ex_date or a.effective_from) <= window_dates[-1]
    ]
    if actions and plan.price_basis == "UNADJUSTED":
        reasons.add("CORPORATE_ACTION_UNADJUSTED")
    # P5 exact values remain untouched. Derived indicators are explicitly float64.
    bars = [r.observation.values for r in window]
    if any(b is None for b in bars):
        return unavailable("DATA_QUALITY_REJECTED")
    values = [b for b in bars if b is not None]
    try:
        result = calculate(
            name or definition.feature_name,
            [float(b.close) for b in values],
            [float(b.high) for b in values],
            [float(b.low) for b in values],
            [float(b.volume) for b in values],
        )
    except (OverflowError, ValueError, ZeroDivisionError):
        return unavailable("NUMERICAL_DOMAIN_UNAVAILABLE")
    if result is None or not math.isfinite(result):
        return unavailable("ZERO_DENOMINATOR_OR_NONFINITE")
    return FeatureValue(
        value=result,
        state=Availability.DEGRADED if reasons else Availability.AVAILABLE,
        reason_codes=tuple(sorted(reasons)),
    )


def build(
    reader: CanonicalReader, plan: BuildPlan, feature_set: FeatureSet | None = None
) -> FeatureDataset:
    definitions = feature_set or default_set(plan)
    # v1 has a closed executable registry; modified executable formulas require new code/version.
    if definitions != default_set(plan):
        raise DataContractError("UNSUPPORTED_FEATURE_DEFINITIONS")
    rows: list[FeatureRow] = []
    last_snapshot: CanonicalDataset | None = None
    for decision in plan.decisions:
        context = ReadContext(knowledge_cutoff=decision.knowledge_cutoff)
        known_sessions = sorted(
            s.session_date
            for s in reader.sessions_as_of(
                plan.history_start, decision.session_date, context
            ).records
            if s.status == "VERIFIED_TRADING_SESSION"
        )
        start = known_sessions[-201] if len(known_sessions) > 201 else plan.history_start
        snapshot = reader.build(
            start,
            decision.session_date,
            context,
        )
        last_snapshot = snapshot
        dates, calendar_reason = calendar_dates(snapshot, decision.session_date)
        dates = dates[-201:]
        universe = reader.universe_as_of(decision.session_date, context)
        entries = {
            e.security_id: e
            for e in (*universe.eligible_securities, *universe.excluded_securities)
            if e.identity is not None or e.membership_evidence is not None
        }
        price_index: dict[str, dict[date, PriceView]] = {}
        for view in snapshot.prices:
            price_index.setdefault(view.observation.security_id or "", {})[
                view.observation.session_date
            ] = view
        session_rows: list[FeatureRow] = []
        for security, entry in sorted(entries.items()):
            values: dict[str, FeatureValue] = {}
            for definition in definitions.definitions:
                if calendar_reason:
                    result = unavailable(calendar_reason)
                elif definition.feature_family == "CROSS_SECTIONAL":
                    result = unavailable("CROSS_SECTION_PENDING")
                elif definition.feature_family in {"MARKET_CONTEXT", "RELATIVE_STRENGTH"}:
                    benchmark = entries.get(plan.benchmark_security_id or "")
                    result = unavailable("BENCHMARK_UNAVAILABLE")
                    if benchmark:
                        name = (
                            "volatility_20"
                            if definition.feature_name == "market_volatility_20"
                            else "return_20"
                        )
                        result = _window_value(
                            definition,
                            dates,
                            price_index.get(benchmark.security_id, {}),
                            benchmark,
                            snapshot,
                            plan,
                            name,
                        )
                        if definition.feature_name == "relative_return_20":
                            own = _window_value(
                                definition,
                                dates,
                                price_index.get(security, {}),
                                entry,
                                snapshot,
                                plan,
                                "return_20",
                            )
                            if own.value is None or result.value is None:
                                result = unavailable(*own.reason_codes, *result.reason_codes)
                            else:
                                result = FeatureValue(
                                    value=own.value - result.value,
                                    state=Availability.DEGRADED
                                    if Availability.DEGRADED in (own.state, result.state)
                                    else Availability.AVAILABLE,
                                    reason_codes=tuple(
                                        sorted(set(own.reason_codes + result.reason_codes))
                                    ),
                                )
                else:
                    result = _window_value(
                        definition, dates, price_index.get(security, {}), entry, snapshot, plan
                    )
                if not entry.analysis_eligible:
                    result = unavailable(
                        "UNIVERSE_INELIGIBLE", entry.analysis_reason, entry.membership_reason
                    )
                values[definition.feature_name] = result
            inspected = [
                v
                for s in {security, plan.benchmark_security_id}
                if s
                for d, v in price_index.get(s, {}).items()
                if d in dates
            ]
            keys = {revision_key(v.observation) for v in inspected}
            keys.update(v.observation.quality_key for v in inspected if v.observation.quality_key)
            keys.update(revision_key(s) for s in snapshot.sessions if s.session_date in dates)
            actions = tuple(
                sorted(
                    revision_key(a)
                    for a in snapshot.corporate_actions
                    if a.security_id == security and a.effective_from <= decision.session_date
                )
            )
            reasons = tuple(
                sorted(
                    {
                        reason
                        for v in values.values()
                        for reason in v.reason_codes
                        if reason != "CROSS_SECTION_PENDING"
                    }
                )
            )
            session_rows.append(
                FeatureRow(
                    security_id=security,
                    session_date=decision.session_date,
                    decision_time=decision.knowledge_cutoff,
                    knowledge_cutoff=decision.knowledge_cutoff,
                    canonical_dataset_id=snapshot.dataset_id,
                    universe_snapshot_id=universe.snapshot_id,
                    input_versions=tuple(
                        sorted(
                            set(
                                (
                                    *snapshot.normalization_versions,
                                    *snapshot.validation_versions,
                                    snapshot.schema_version,
                                    universe.identity_version,
                                    universe.membership_version,
                                )
                            )
                        )
                    ),
                    input_revision_keys=tuple(sorted(keys)),
                    classification=snapshot.classification,
                    price_basis=plan.price_basis,
                    quality_state=Availability.UNAVAILABLE,
                    analytical_eligible=entry.analysis_eligible,
                    reason_codes=reasons,
                    corporate_action_keys=actions,
                    values=values,
                )
            )
        peers = [
            r
            for r in session_rows
            if r.analytical_eligible
            and r.security_id != plan.benchmark_security_id
            and r.values["return_20"].value is not None
        ]
        peer_values = [r.values["return_20"].value for r in peers]
        peer_keys = {key for r in peers for key in r.input_revision_keys}
        peer_degraded = any(r.values["return_20"].state == Availability.DEGRADED for r in peers)
        for row in session_rows:
            values = dict(row.values)
            rank = unavailable("CROSS_SECTION_INSUFFICIENT_ELIGIBLE_PEERS")
            value = row.values["return_20"].value
            if row in peers and value is not None and len(peers) > 1:
                less = sum(v is not None and v < value for v in peer_values)
                equal = sum(v == value for v in peer_values)
                rank = FeatureValue(
                    value=(less + (equal - 1) / 2) / (len(peers) - 1),
                    state=Availability.DEGRADED if peer_degraded else Availability.AVAILABLE,
                    reason_codes=("DEGRADED_CROSS_SECTION_INPUT",) if peer_degraded else (),
                )
            if not row.analytical_eligible:
                rank = unavailable("UNIVERSE_INELIGIBLE")
            values["momentum_percentile_20"] = rank
            state = (
                Availability.UNAVAILABLE
                if all(v.value is None for v in values.values())
                else Availability.DEGRADED
                if any(v.state != Availability.AVAILABLE for v in values.values())
                else Availability.AVAILABLE
            )
            rows.append(
                row.model_copy(
                    update=dict(
                        values=values,
                        quality_state=state,
                        input_revision_keys=tuple(sorted(set(row.input_revision_keys) | peer_keys)),
                        reason_codes=tuple(
                            sorted({reason for v in values.values() for reason in v.reason_codes})
                        ),
                    )
                )
            )
    if last_snapshot is None:
        raise DataContractError("NO_FEATURE_DECISIONS")
    dataset = FeatureDataset(
        feature_set_id="0" * 64,
        canonical_dataset_id=last_snapshot.dataset_id,
        canonical_input_id=reader.batch.input_id,
        classification=last_snapshot.classification,
        universe_definition_version=reader.batch.definition.version,
        feature_set=definitions,
        rows=tuple(rows),
    )
    return dataset.model_copy(
        update={
            "feature_set_id": checksum(
                stable_json(dataset.model_dump(mode="json", exclude={"feature_set_id"}))
            )
        }
    )
