"""Transactional immutable PostgreSQL repositories; db/ owns all migrations."""

from psycopg import Connection, sql
from psycopg.types.json import Jsonb

from alphalens_data.canonical.models import (
    REVISION_ADAPTER,
    ActionRevision,
    CanonicalBatch,
    CanonicalDataset,
    IdentityRevision,
    MembershipRevision,
    PriceRevision,
    QualityRevision,
    Revision,
    Security,
    SessionRevision,
    revision_key,
)
from alphalens_data.canonical.revisions import ordered_revisions, parent_key
from alphalens_data.canonical.services import validate_snapshot
from alphalens_data.canonical.validation import validate_batch
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.repository import PostgresMetadataRepository
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum


class PostgresCanonical:
    """Caller owns connection. Each batch/snapshot write is an atomic transaction."""

    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.connection = connection

    def _insert(self, table: str, values: dict[str, object], keys: tuple[str, ...]) -> None:
        columns = tuple(values)
        query = sql.SQL(
            "INSERT INTO canonical.{} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING"
        ).format(
            sql.Identifier(table),
            sql.SQL(",").join(map(sql.Identifier, columns)),
            sql.SQL(",").join(sql.Placeholder() for _ in columns),
            sql.SQL(",").join(map(sql.Identifier, keys)),
        )
        self.connection.execute(query, tuple(values.values()))
        row = self.connection.execute(
            sql.SQL("SELECT {} FROM canonical.{} WHERE {}").format(
                sql.SQL(",").join(map(sql.Identifier, columns)),
                sql.Identifier(table),
                sql.SQL(" AND ").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in keys),
            ),
            tuple(values[k] for k in keys),
        ).fetchone()
        expected = tuple(v.obj if isinstance(v, Jsonb) else v for v in values.values())
        if row != expected:
            raise DataContractError("IMMUTABLE_CANONICAL_CONFLICT")

    def put_security(self, security: Security) -> None:
        security = Security.model_validate(security.model_dump())
        self._insert("securities", security.model_dump(), ("security_id",))

    def get_security(self, security_id: str) -> Security | None:
        row = self.connection.execute(
            "SELECT security_id,exchange,classification FROM canonical.securities "
            "WHERE security_id=%s",
            (security_id,),
        ).fetchone()
        return (
            Security.model_validate(
                dict(zip(("security_id", "exchange", "classification"), row, strict=True))
            )
            if row
            else None
        )

    def put_revision(self, record: Revision) -> None:
        record = REVISION_ADAPTER.validate_python(record.model_dump())
        if record.kind == "FUNDAMENTAL":
            raise DataContractError("FUNDAMENTAL_PIT_DATA_UNAVAILABLE")
        p = record.provenance
        key = revision_key(record)
        self._insert(
            "record_revisions",
            dict(
                record_key=key,
                kind=record.kind,
                source=p.source,
                logical_record_id=record.logical_record_id,
                revision_id=record.revision_id,
                revision_number=record.revision_number,
                parent_key=parent_key(record),
                security_id=record.security_id,
                classification=p.classification,
                effective_from=record.effective_from,
                effective_to=record.effective_to,
                published_at=p.published_at,
                available_at=p.available_at,
                ingested_at=p.ingested_at,
                artifact_sha256=p.artifact_sha256,
                payload=Jsonb(record.model_dump(mode="json")),
            ),
            ("record_key",),
        )
        values: dict[str, object] = {"record_key": key}
        if isinstance(record, IdentityRevision):
            table = "security_identity_history"
            values.update(
                source_security_id=record.fact.source_security_id,
                symbol=record.fact.symbol,
                isin=record.fact.isin,
                series=record.fact.series,
            )
        elif isinstance(record, MembershipRevision):
            table = "membership_evidence"
            values.update(
                listing_status=record.fact.listing_status, security_type=record.fact.security_type
            )
        elif isinstance(record, SessionRevision):
            table = "trading_sessions"
            values.update(
                session_date=record.session_date,
                exchange=record.exchange,
                status=record.status,
                calendar_evidence_reference=record.calendar_evidence_reference,
            )
        elif isinstance(record, QualityRevision):
            table = "quality_reports"
            values.update(
                session_date=record.evidence.session_date,
                report_sha256=record.evidence.report_sha256,
                status=record.evidence.report.status,
            )
        elif isinstance(record, ActionRevision):
            table = "corporate_actions"
            values.update(
                corporate_action_id=record.corporate_action_id,
                event_type=record.event_type,
                factor=record.factor,
                cash_value=record.cash_value,
                currency=record.currency,
            )
        else:
            table = "market_bars_eod"
            values.update(
                security_id=record.security_id,
                session_date=record.session_date,
                price_basis=record.price_basis,
                currency=record.currency,
                quality_key=record.quality_key,
                rejection_reason_codes=list(record.rejection_reason_codes),
                corporate_action_key=record.adjustment.corporate_action_key
                if record.adjustment
                else None,
                original_price_key=record.adjustment.original_price_key
                if record.adjustment
                else None,
            )
            for name in ("open", "high", "low", "close", "volume"):
                values[name] = getattr(record.values, name) if record.values else None
        self._insert(table, values, ("record_key",))

    def get_revision(self, key: str) -> Revision | None:
        row = self.connection.execute(
            "SELECT payload::text FROM canonical.record_revisions WHERE record_key=%s", (key,)
        ).fetchone()
        return REVISION_ADAPTER.validate_json(str(row[0])) if row else None

    def list_revisions(self, kind: str, security_id: str | None = None) -> tuple[Revision, ...]:
        rows = self.connection.execute(
            "SELECT payload::text FROM canonical.record_revisions WHERE kind=%s "
            "AND (%s::text IS NULL OR security_id=%s) ORDER BY record_key",
            (kind, security_id, security_id),
        ).fetchall()
        return tuple(REVISION_ADAPTER.validate_json(str(row[0])) for row in rows)

    def save_input(self, batch: CanonicalBatch) -> None:
        batch = CanonicalBatch.model_validate_json(validate_batch(batch).to_bytes())
        with self.connection.transaction():
            p2 = PostgresMetadataRepository(self.connection)
            for artifact in batch.artifacts:
                p2.save_manifest(artifact)
            for run in batch.runs:
                p2.save_run(run)
            for security in batch.securities:
                self.put_security(security)
            for n in batch.normalized:
                self._insert(
                    "normalized_evidence",
                    dict(
                        normalized_record_id=n.normalized_record_id,
                        artifact_id=n.artifact_id,
                        normalization_version=n.normalization_version,
                        payload=Jsonb(n.payload),
                    ),
                    ("normalized_record_id",),
                )
            for q in batch.quarantine:
                self._insert(
                    "quarantine_evidence",
                    dict(
                        quarantine_key=q.quarantine_key,
                        artifact_id=q.record.artifact_id,
                        payload=Jsonb(q.record.model_dump(mode="json")),
                    ),
                    ("quarantine_key",),
                )
            records = ordered_revisions(batch.revisions)
            # FK dependencies: reports/actions before bars; unadjusted before adjusted.
            priority = {
                "QUALITY": 0,
                "ACTION": 1,
                "IDENTITY": 2,
                "MEMBERSHIP": 3,
                "SESSION": 4,
                "BAR": 5,
            }
            for record in sorted(
                records,
                key=lambda r: (
                    priority[r.kind],
                    isinstance(r, PriceRevision) and r.price_basis == "ADJUSTED",
                    r.revision_number,
                    revision_key(r),
                ),
            ):
                self.put_revision(record)
            for link in batch.lineage:
                values = link.model_dump()
                values["lineage_id"] = checksum(stable_json(link.model_dump(mode="json")))
                self._insert("record_lineage", values, ("lineage_id",))
            self._insert(
                "dataset_inputs",
                dict(input_id=batch.input_id, payload=Jsonb(batch.model_dump(mode="json"))),
                ("input_id",),
            )
            for record in batch.revisions:
                self._insert(
                    "input_records",
                    dict(input_id=batch.input_id, record_key=revision_key(record)),
                    ("input_id", "record_key"),
                )

    def get_input(self, input_id: str) -> CanonicalBatch | None:
        row = self.connection.execute(
            "SELECT payload::text FROM canonical.dataset_inputs WHERE input_id=%s", (input_id,)
        ).fetchone()
        return CanonicalBatch.model_validate_json(str(row[0])) if row else None

    def save_snapshot(self, snapshot: CanonicalDataset) -> None:
        batch = self.get_input(snapshot.input_id)
        if batch is None:
            raise DataContractError("SNAPSHOT_INPUT_NOT_FOUND")
        validate_snapshot(snapshot, batch)
        with self.connection.transaction():
            self._insert(
                "dataset_snapshots",
                dict(
                    dataset_id=snapshot.dataset_id,
                    input_id=snapshot.input_id,
                    knowledge_cutoff=snapshot.context.knowledge_cutoff,
                    start_session=snapshot.start_session,
                    end_session=snapshot.end_session,
                    payload=Jsonb(snapshot.model_dump(mode="json")),
                ),
                ("dataset_id",),
            )

    def get_snapshot(self, dataset_id: str) -> CanonicalDataset | None:
        row = self.connection.execute(
            "SELECT payload::text FROM canonical.dataset_snapshots WHERE dataset_id=%s",
            (dataset_id,),
        ).fetchone()
        return CanonicalDataset.model_validate_json(str(row[0])) if row else None


class PostgresRevisions:
    """RevisionRepository interface, separate from batch orchestration."""

    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.store = PostgresCanonical(connection)

    def put(self, record: Revision) -> None:
        self.store.put_revision(record)

    def get(self, record_key: str) -> Revision | None:
        return self.store.get_revision(record_key)

    def list(self, kind: str, security_id: str | None = None) -> tuple[Revision, ...]:
        return self.store.list_revisions(kind, security_id)


class PostgresSecurities:
    """SecurityRepository interface; no timeless membership or classification attributes."""

    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.store = PostgresCanonical(connection)

    def put(self, security: Security) -> None:
        self.store.put_security(security)

    def get(self, security_id: str) -> Security | None:
        return self.store.get_security(security_id)
