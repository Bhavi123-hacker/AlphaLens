"""Deterministic cross-record quality rules; no acquisition or provider parsing."""

from collections import Counter, defaultdict
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import CanonicalEOD, Classification
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.parsing import ParsedRow
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import (
    DatasetQualitySummary,
    QualityStatus,
    SessionQuality,
    ValidationInput,
    ValidationIssue,
    ValidationReport,
    ValidationRule,
    ValidationSeverity,
)

# Fixed severities are part of validator v1, not user-configurable downgrades.
RULES = {
    rule: ValidationRule(rule_id=rule, severity=severity, description=description)
    for severity, rules in (
        (
            ValidationSeverity.FATAL,
            {
                "EMPTY_DATASET": "No canonical observations available",
                "CLASSIFICATION": "Mixed or prohibited data classification",
                "DATE_RANGE": "Invalid declared date range",
                "CHECKSUM": "Raw or canonical/normalized bytes do not match evidence",
                "REFERENCE_CONFLICT": "Contradictory or duplicate reference evidence",
            },
        ),
        (
            ValidationSeverity.ERROR,
            {
                "DUPLICATE_SECURITY_SESSION": "Ambiguous repeated security/session observations",
                "CONFLICTING_REVISION": "Multiple unreconciled price revisions",
                "PROVENANCE": "Missing or inconsistent canonical lineage",
                "METADATA": "Source/dataset/version metadata inconsistent",
                "IDENTIFIER_CONFLICT": "Simultaneous incompatible security identities",
                "TEMPORAL_INVERSION": "Impossible timestamp or effective interval ordering",
                "USE_BEFORE_AVAILABLE": "Declared use precedes evidenced availability",
                "OUTSIDE_DATE_RANGE": "Record outside declared date range",
                "FUTURE_SESSION": "Session after acquisition context",
                "CONFIRMED_MISSING_SESSION": "Evidenced security trading session lacks observation",
                "NON_TRADING_OBSERVATION": "Observation conflicts with scoped non-trading evidence",
            },
        ),
        (
            ValidationSeverity.WARNING,
            {
                "UNSORTED_SESSIONS": "Input observations not chronologically ordered per security",
                "DUPLICATE_ARTIFACT_CONTENT": "Distinct artifacts contain identical raw bytes",
                "PARTIAL_POPULATION": "P2 quarantined rows remain explicitly accounted for",
                "OBSERVATION_GAP": "Observation gap; unverified dates are UNKNOWN_SESSION_STATUS",
                "ZERO_VOLUME": "Zero volume can be valid illiquid data",
                "EXTREME_RETURN": "Absolute consecutive observation return exceeds threshold",
                "EXTREME_RANGE": "High/low ratio exceeds threshold",
                "VOLUME_SPIKE": "Volume exceeds configured multiple of prior positive volume",
                "REPEATED_OHLC": "Identical OHLC run reaches threshold",
                "REPEATED_TIMESTAMP": "Different sessions share evidenced availability timestamps",
                "UNIVERSE_READINESS": "P2 identity/availability does not establish PIT universe",
            },
        ),
        (
            ValidationSeverity.INFO,
            {
                "CALENDAR_UNAVAILABLE": "No complete verified calendar; no inferred holidays",
                "NON_TRADING_SESSION": "Scoped reference explains a non-trading date",
            },
        ),
    )
    for rule, description in rules.items()
}


def validate(data: ValidationInput) -> ValidationReport:
    """Retain every record; explicit issues determine dataset and session eligibility."""
    with localcontext() as context:
        context.prec = 38
        context.rounding = ROUND_HALF_EVEN
        return _validate(data)


def _validate(data: ValidationInput) -> ValidationReport:
    if data.classification == Classification.PRODUCTION:
        raise DataContractError("PRODUCTION_VALIDATION_DISABLED")
    issues: list[ValidationIssue] = []
    manifests = {a.manifest.artifact_id: a.manifest for a in data.artifacts}

    def emit(
        rule: str,
        record: CanonicalEOD | None = None,
        *,
        security: str | None = None,
        session: date | None = None,
        related: tuple[CanonicalEOD, ...] = (),
        message: str | None = None,
        action: str | None = None,
    ) -> None:
        definition = RULES[rule]
        members = related or ((record,) if record else ())
        issues.append(
            ValidationIssue.model_validate(
                {
                    "rule_id": rule,
                    "severity": definition.severity,
                    "security_id": record.security_id if record else security,
                    "session_date": record.session_date if record else session,
                    "artifact_id": record.artifact_id if record else None,
                    "source": record.source if record else None,
                    "record_ids": tuple(sorted({r.record_id for r in members})),
                    "normalized_record_ids": tuple(
                        sorted({r.normalized_record_id for r in members})
                    ),
                    "original_row_numbers": tuple(sorted({r.source_row_number for r in members})),
                    "message": message or definition.description,
                    "action_status": action,
                }
            )
        )

    if not data.records:
        emit("EMPTY_DATASET")
    classifications = {r.classification for r in data.records}
    classifications.update(q.classification for q in data.quarantine)
    classifications.update(a.manifest.spec.classification for a in data.artifacts)
    if classifications - {data.classification}:
        emit("CLASSIFICATION")
    if data.start_session and data.end_session and data.start_session > data.end_session:
        emit("DATE_RANGE")
    if len(manifests) != len(data.artifacts):
        emit("METADATA", message="Artifact IDs must occur exactly once")
    if (
        len({a.manifest.spec.source for a in data.artifacts}) > 1
        or len({a.manifest.spec.dataset for a in data.artifacts}) > 1
    ):
        emit("METADATA", message="One validation input must declare one source/dataset scope")
    if len({a.manifest.versions.model_dump_json() for a in data.artifacts}) > 1:
        emit("METADATA", message="Parser/schema versions must be consistent within dataset scope")
    if len({r.currency for r in data.records if r.currency is not None}) > 1:
        emit("METADATA", message="Known currencies differ")

    artifact_records: dict[str, list[CanonicalEOD]] = defaultdict(list)
    groups: dict[tuple[str, date], list[CanonicalEOD]] = defaultdict(list)
    securities: dict[str, list[CanonicalEOD]] = defaultdict(list)
    missing_provenance: set[str] = set()
    for record in data.records:
        artifact_records[record.artifact_id].append(record)
        groups[(record.security_id, record.session_date)].append(record)
        securities[record.security_id].append(record)
        manifest = manifests.get(record.artifact_id)
        expected_normalized = checksum(
            stable_json(
                [
                    record.artifact_id,
                    record.source_row_number,
                    record.source_row_sha256,
                    record.versions.model_dump(),
                ]
            )
        )
        if (
            manifest is None
            or record.normalized_record_id != expected_normalized
            or record.record_id != checksum(stable_json([expected_normalized, "canonical"]))
            or record.source_row_number < 2
            or not record.source_row_identifier
        ):
            emit("PROVENANCE", record)
            missing_provenance.add(record.record_id)
        if manifest:
            if (
                record.raw_sha256 != manifest.sha256
                or record.source_version != manifest.artifact_id
                or record.source != manifest.spec.source
                or record.source_filename != manifest.spec.original_filename
                or record.versions != manifest.versions
                or record.acquired_at != manifest.acquired_at
                or record.currency != manifest.spec.currency
            ):
                emit("METADATA", record)
                missing_provenance.add(record.record_id)
            # Reuse P2 hard financial/identifier/date rules at the canonical boundary.
            # P3 never defines a second OHLC or numeric parsing policy.
            fields = tuple(
                (name, str(getattr(record, name)))
                for name in (
                    "security_id",
                    "session_date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                )
            ) + tuple((name, getattr(record, name) or "") for name in ("symbol", "isin", "series"))
            _, failures = normalize((ParsedRow(record.source_row_number, (), fields),), manifest)
            for failure in failures:
                issues.append(
                    ValidationIssue(
                        rule_id="P2_" + failure.validation_rule,
                        severity=ValidationSeverity.ERROR,
                        security_id=record.security_id,
                        session_date=record.session_date,
                        artifact_id=record.artifact_id,
                        source=record.source,
                        record_ids=(record.record_id,),
                        normalized_record_ids=(record.normalized_record_id,),
                        original_row_numbers=(record.source_row_number,),
                        message=failure.reason,
                    )
                )
        if record.session_date > record.acquired_at.date():
            emit("FUTURE_SESSION", record)
        if (data.start_session and record.session_date < data.start_session) or (
            data.end_session and record.session_date > data.end_session
        ):
            emit("OUTSIDE_DATE_RANGE", record)

    content = Counter(a.manifest.sha256 for a in data.artifacts)
    for evidence in data.artifacts:
        manifest = evidence.manifest
        members = tuple(artifact_records[manifest.artifact_id])
        if content[manifest.sha256] > 1:
            emit("DUPLICATE_ARTIFACT_CONTENT", related=members)
        if evidence.observed_sha256 is None or evidence.observed_byte_size is None:
            emit("PROVENANCE", related=members, message="Raw checksum verification unavailable")
            missing_provenance.update(r.record_id for r in members)
        elif (
            evidence.observed_sha256 != manifest.sha256
            or evidence.observed_byte_size != manifest.byte_size
        ):
            emit("CHECKSUM", related=members)
            missing_provenance.update(r.record_id for r in members)
        normalized = stable_json(
            [r.model_dump(mode="json", exclude={"record_id"}) for r in members]
        )
        if evidence.normalized_sha256 is None:
            emit("PROVENANCE", related=members, message="Normalized lineage bytes unavailable")
            missing_provenance.update(r.record_id for r in members)
        elif checksum(normalized) != evidence.normalized_sha256:
            emit("CHECKSUM", related=members)
            missing_provenance.update(r.record_id for r in members)
        if evidence.run:
            run = evidence.run
            qs = tuple(q for q in data.quarantine if q.artifact_id == manifest.artifact_id)
            if (
                run.artifact_id != manifest.artifact_id
                or run.versions != manifest.versions
                or run.classification != manifest.spec.classification
                or run.canonical_count != len(members)
                or run.quarantined_row_count != len({q.source_row_number for q in qs})
                or run.validation_error_count != len(qs)
            ):
                emit("METADATA", related=members, message="P2 run accounting disagrees with inputs")
            if run.canonical_sha256 != checksum(
                stable_json([r.model_dump(mode="json") for r in members])
            ) or run.quarantine_sha256 != checksum(
                stable_json([q.model_dump(mode="json") for q in qs])
            ):
                emit("CHECKSUM", related=members)
    quarantine_keys = {(q.artifact_id, q.source_row_number) for q in data.quarantine}
    scopes = {(s.artifact_id, s.source_row_number): s for s in data.quarantine_scopes}
    if len(scopes) != len(data.quarantine_scopes) or set(scopes) - quarantine_keys:
        emit(
            "REFERENCE_CONFLICT",
            message="Quarantine scope keys must uniquely match quarantined rows",
        )
    if quarantine_keys:
        emit("PARTIAL_POPULATION")
    for q in data.quarantine:
        manifest = manifests.get(q.artifact_id)
        scope = scopes.get((q.artifact_id, q.source_row_number))
        issues.append(
            ValidationIssue(
                rule_id="P2_" + q.validation_rule,
                severity=ValidationSeverity.ERROR,
                security_id=scope.security_id if scope else None,
                session_date=scope.session_date if scope else None,
                artifact_id=q.artifact_id,
                source=manifest.spec.source if manifest else None,
                original_row_numbers=(q.source_row_number,),
                message=q.reason,
            )
        )
        if (
            manifest is None
            or q.raw_sha256 != manifest.sha256
            or q.versions != manifest.versions
            or q.classification != data.classification
        ):
            emit("PROVENANCE", message="Quarantine lineage disagrees with artifact evidence")

    duplicates = 0
    for members_list in groups.values():
        members = tuple(members_list)
        if len(members) > 1:
            duplicates += len(members) - 1
            emit("DUPLICATE_SECURITY_SESSION", members[0], related=members)
            prices = {(r.open, r.high, r.low, r.close, r.volume) for r in members}
            if len(prices) > 1:
                emit("CONFLICTING_REVISION", members[0], related=members)
    # ISIN and symbol are simultaneous attributes, never permanent IDs.
    for attribute in ("isin", "symbol"):
        identities: dict[tuple[str, str, date], list[CanonicalEOD]] = defaultdict(list)
        for r in data.records:
            value = getattr(r, attribute)
            if value:
                identities[(r.source, value, r.session_date)].append(r)
        for members_list in identities.values():
            members = tuple(members_list)
            if len({r.security_id for r in members}) > 1:
                emit(
                    "IDENTIFIER_CONFLICT",
                    members[0],
                    related=members,
                    message=f"Same {attribute}/source/session has unexplained security IDs",
                )

    references = {(r.security_id, r.session_date): r for r in data.reference_sessions}
    temporal = {r.record_id: r for r in data.temporal_evidence}
    actions = {(r.security_id, r.session_date): r for r in data.action_evidence}
    if (
        len(references) != len(data.reference_sessions)
        or len(temporal) != len(data.temporal_evidence)
        or len(actions) != len(data.action_evidence)
    ):
        emit("REFERENCE_CONFLICT")
    if set(temporal) - {r.record_id for r in data.records}:
        emit("REFERENCE_CONFLICT", message="Temporal evidence refers to absent record IDs")
    for r in data.records:
        t = temporal.get(r.record_id)
        if t:
            if (
                (t.published_at and t.available_at and t.published_at > t.available_at)
                or (t.available_at and t.available_at > r.acquired_at)
                or (t.published_at and t.published_at > r.acquired_at)
                or (t.session_close_at and t.available_at and t.session_close_at > t.available_at)
                or (t.session_close_at and t.session_close_at > r.acquired_at)
                or (t.effective_from and t.effective_to and t.effective_from >= t.effective_to)
            ):
                emit("TEMPORAL_INVERSION", r)
            if data.decision_time and t.available_at and data.decision_time < t.available_at:
                emit("USE_BEFORE_AVAILABLE", r)
    timestamp_groups: dict[tuple[str, str], list[CanonicalEOD]] = defaultdict(list)
    for r in data.records:
        t = temporal.get(r.record_id)
        if t and t.available_at:
            timestamp_groups[(r.security_id, t.available_at.isoformat())].append(r)
    for repeated in timestamp_groups.values():
        if len({r.session_date for r in repeated}) > 1:
            emit("REPEATED_TIMESTAMP", repeated[0], related=tuple(repeated))
    confirmed = 0
    for key, ref in sorted(references.items()):
        if (data.start_session and ref.session_date < data.start_session) or (
            data.end_session and ref.session_date > data.end_session
        ):
            continue
        if ref.status == "TRADING" and key not in groups:
            confirmed += 1
            emit("CONFIRMED_MISSING_SESSION", security=key[0], session=key[1])
        elif ref.status == "NON_TRADING":
            if key in groups:
                emit("NON_TRADING_OBSERVATION", groups[key][0], related=tuple(groups[key]))
            else:
                emit("NON_TRADING_SESSION", security=key[0], session=key[1])
    emit("CALENDAR_UNAVAILABLE")
    if any(
        r.identity_basis == "SOURCE_SCOPED_SYMBOL"
        or r.record_id not in temporal
        or temporal[r.record_id].available_at is None
        for r in data.records
    ):
        emit("UNIVERSE_READINESS")

    gaps = 0
    for security, members_list in sorted(securities.items()):
        if any(
            a.session_date > b.session_date
            for a, b in zip(members_list, members_list[1:], strict=False)
        ):
            emit("UNSORTED_SESSIONS", security=security)
        ordered = sorted(members_list, key=lambda r: (r.session_date, r.record_id))
        identical_run = 1
        for index, r in enumerate(ordered):
            if r.volume == 0:
                emit("ZERO_VOLUME", r)
            if r.low > 0 and r.high / r.low > data.policy.high_low_ratio:
                emit("EXTREME_RANGE", r)
            if index == 0:
                continue
            previous = ordered[index - 1]
            days = (r.session_date - previous.session_date).days
            if days > 1:
                gaps += 1
                emit(
                    "OBSERVATION_GAP",
                    r,
                    message=(
                        f"OBSERVATION_GAP after {previous.session_date}; "
                        f"{days - 1} intervening dates; "
                        "UNKNOWN_SESSION_STATUS except separately evidenced dates"
                    ),
                )
            if (
                previous.close > 0
                and abs(r.close / previous.close - 1) > data.policy.absolute_return
            ):
                action = actions.get((security, r.session_date))
                emit(
                    "EXTREME_RETURN",
                    r,
                    action=action.status if action else "ACTION_DATA_UNAVAILABLE",
                )
            if previous.volume > 0 and r.volume > previous.volume * data.policy.volume_multiple:
                emit("VOLUME_SPIKE", r)
            same = (r.open, r.high, r.low, r.close) == (
                previous.open,
                previous.high,
                previous.low,
                previous.close,
            )
            identical_run = identical_run + 1 if same and days > 0 else 1
            if identical_run == data.policy.repeated_ohlc_sessions:
                emit("REPEATED_OHLC", r)

    issues.sort(
        key=lambda i: (
            i.rule_id,
            i.security_id or "",
            i.session_date or date.min,
            i.artifact_id or "",
            i.record_ids,
            i.original_row_numbers,
            i.message,
        )
    )
    blocking = {ValidationSeverity.ERROR, ValidationSeverity.FATAL}
    invalid_ids = {rid for i in issues if i.severity in blocking for rid in i.record_ids}
    dataset_blocked = any(i.severity in blocking and i.security_id is None for i in issues)
    status = (
        QualityStatus.REJECTED
        if any(i.severity in blocking for i in issues)
        else QualityStatus.DEGRADED
        if any(i.severity == ValidationSeverity.WARNING for i in issues)
        else QualityStatus.VALID
    )
    sessions: list[SessionQuality] = []
    issue_records: dict[str, set[int]] = defaultdict(set)
    issue_scopes: dict[tuple[str, date | None], set[int]] = defaultdict(set)
    global_reasons = {i.rule_id for i in issues if i.severity in blocking and i.security_id is None}
    for ordinal, issue in enumerate(issues):
        for rid in issue.record_ids:
            issue_records[rid].add(ordinal)
        if issue.security_id:
            issue_scopes[(issue.security_id, issue.session_date)].add(ordinal)
    for (security, session), session_members in sorted(groups.items()):
        ids = {r.record_id for r in session_members}
        relevant_ordinals = issue_scopes[(security, session)] | issue_scopes[(security, None)]
        for rid in ids:
            relevant_ordinals |= issue_records[rid]
        relevant = [issues[n] for n in sorted(relevant_ordinals)]
        rejected = (
            dataset_blocked
            or bool(ids.intersection(invalid_ids))
            or any(i.severity in blocking for i in relevant)
        )
        degraded = any(i.severity == ValidationSeverity.WARNING for i in relevant)
        sessions.append(
            SessionQuality(
                security_id=security,
                session_date=session,
                status=QualityStatus.REJECTED
                if rejected
                else QualityStatus.DEGRADED
                if degraded
                else QualityStatus.VALID,
                record_ids=tuple(sorted(ids)),
                reason_codes=tuple(
                    sorted(
                        {i.rule_id for i in relevant}
                        | (global_reasons if dataset_blocked else set())
                    )
                ),
            )
        )
    sessions.extend(
        SessionQuality(
            security_id=security,
            session_date=session,
            status=QualityStatus.REJECTED,
            record_ids=(),
            reason_codes=("CONFIRMED_MISSING_SESSION",),
        )
        for (security, session), ref in sorted(references.items())
        if ref.status == "TRADING"
        and (security, session) not in groups
        and (not data.start_session or session >= data.start_session)
        and (not data.end_session or session <= data.end_session)
    )
    existing_sessions = {(s.security_id, s.session_date) for s in sessions}
    quarantined_sessions = {(s.security_id, s.session_date) for s in scopes.values()}
    for security, session in sorted(quarantined_sessions - existing_sessions):
        reasons = tuple(
            sorted(
                {
                    i.rule_id
                    for i in issues
                    if i.security_id == security and i.session_date == session
                }
            )
        )
        sessions.append(
            SessionQuality(
                security_id=security,
                session_date=session,
                status=QualityStatus.REJECTED,
                record_ids=(),
                reason_codes=reasons,
            )
        )
    rejected_sessions = {
        (s.security_id, s.session_date) for s in sessions if s.status == QualityStatus.REJECTED
    }
    valid = sum((r.security_id, r.session_date) not in rejected_sessions for r in data.records)
    summary = DatasetQualitySummary(
        record_count=len(data.records),
        valid_record_count=valid,
        quarantined_record_count=len(quarantine_keys),
        error_count=sum(i.severity == ValidationSeverity.ERROR for i in issues),
        fatal_count=sum(i.severity == ValidationSeverity.FATAL for i in issues),
        warning_count=sum(i.severity == ValidationSeverity.WARNING for i in issues),
        unique_security_count=len(securities),
        first_session=min((r.session_date for r in data.records), default=None),
        last_session=max((r.session_date for r in data.records), default=None),
        duplicate_count=duplicates,
        candidate_gap_count=gaps,
        confirmed_missing_session_count=confirmed,
        zero_volume_count=sum(r.volume == 0 for r in data.records),
        price_anomaly_count=sum(
            i.rule_id in {"EXTREME_RETURN", "EXTREME_RANGE", "REPEATED_OHLC"} for i in issues
        ),
        provenance_complete_count=sum(r.record_id not in missing_provenance for r in data.records),
        provenance_missing_count=sum(r.record_id in missing_provenance for r in data.records),
        valid_record_ratio=Decimal(valid) / len(data.records) if data.records else None,
    )
    return ValidationReport(
        classification=data.classification,
        input_sha256=checksum(stable_json(data.model_dump(mode="json"))),
        policy=data.policy,
        status=status,
        dataset_blocked=dataset_blocked,
        session_calendar_status="PARTIALLY_VERIFIED" if references else "UNAVAILABLE",
        universe_input_status="PARTIALLY_VERIFIED"
        if temporal and not dataset_blocked
        else "UNAVAILABLE",
        summary=summary,
        issues=tuple(issues),
        sessions=tuple(sorted(sessions, key=lambda s: (s.security_id, s.session_date))),
    )
