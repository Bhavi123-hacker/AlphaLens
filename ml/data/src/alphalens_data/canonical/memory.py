"""In-memory repositories for contract tests/local file builds, not a database substitute."""

from alphalens_data.canonical.models import (
    REVISION_ADAPTER,
    CanonicalBatch,
    CanonicalDataset,
    Revision,
    Security,
    revision_bytes,
    revision_key,
)
from alphalens_data.canonical.revisions import parent_key, validate_parent
from alphalens_data.canonical.validation import validate_batch
from alphalens_data.errors import DataContractError


class MemoryRevisions:
    def __init__(self) -> None:
        self.records: dict[str, Revision] = {}

    def put(self, record: Revision) -> None:
        record = REVISION_ADAPTER.validate_python(record.model_dump())
        if record.kind == "FUNDAMENTAL":
            raise DataContractError("FUNDAMENTAL_PIT_DATA_UNAVAILABLE")
        key = revision_key(record)
        previous = self.records.get(key)
        if previous:
            if revision_bytes(previous) != revision_bytes(record):
                raise DataContractError("IMMUTABLE_CANONICAL_REVISION_CONFLICT")
            return
        parent = parent_key(record)
        if parent is None and any(
            (r.kind, r.provenance.source, r.logical_record_id)
            == (record.kind, record.provenance.source, record.logical_record_id)
            for r in self.records.values()
        ):
            raise DataContractError("CONFLICTING_CANONICAL_REVISION_ROOT")
        validate_parent(record, self.records.get(parent) if parent else None)
        if parent and any(parent_key(r) == parent for r in self.records.values()):
            raise DataContractError("BRANCHING_CANONICAL_REVISION")
        self.records[key] = record

    def get(self, record_key: str) -> Revision | None:
        record = self.records.get(record_key)
        return REVISION_ADAPTER.validate_python(record.model_dump()) if record else None

    def list(self, kind: str, security_id: str | None = None) -> tuple[Revision, ...]:
        return tuple(
            REVISION_ADAPTER.validate_python(r.model_dump())
            for r in (
                sorted(
                    (
                        r
                        for r in self.records.values()
                        if r.kind == kind and (security_id is None or r.security_id == security_id)
                    ),
                    key=revision_key,
                )
            )
        )


class MemorySecurities:
    def __init__(self) -> None:
        self.records: dict[str, Security] = {}

    def put(self, security: Security) -> None:
        security = Security.model_validate(security.model_dump())
        if security.security_id in self.records and self.records[security.security_id] != security:
            raise DataContractError("IMMUTABLE_SECURITY_CONFLICT")
        self.records[security.security_id] = security

    def get(self, security_id: str) -> Security | None:
        return self.records.get(security_id)


class MemoryDatasets:
    def __init__(self) -> None:
        self.inputs: dict[str, CanonicalBatch] = {}
        self.snapshots: dict[str, CanonicalDataset] = {}

    def save_input(self, batch: CanonicalBatch) -> None:
        batch = validate_batch(batch)
        previous = self.inputs.get(batch.input_id)
        if previous and previous.to_bytes() != batch.to_bytes():
            raise DataContractError("IMMUTABLE_CANONICAL_INPUT_CONFLICT")
        self.inputs[batch.input_id] = batch

    def get_input(self, input_id: str) -> CanonicalBatch | None:
        batch = self.inputs.get(input_id)
        return CanonicalBatch.model_validate_json(batch.to_bytes()) if batch else None

    def save_snapshot(self, snapshot: CanonicalDataset) -> None:
        from alphalens_data.canonical.services import validate_snapshot

        snapshot = CanonicalDataset.model_validate_json(snapshot.to_bytes())
        batch = self.get_input(snapshot.input_id)
        if batch is None:
            raise DataContractError("SNAPSHOT_INPUT_NOT_FOUND")
        validate_snapshot(snapshot, batch)
        previous = self.snapshots.get(snapshot.dataset_id)
        if previous and previous.to_bytes() != snapshot.to_bytes():
            raise DataContractError("IMMUTABLE_CANONICAL_SNAPSHOT_CONFLICT")
        self.snapshots[snapshot.dataset_id] = snapshot

    def get_snapshot(self, dataset_id: str) -> CanonicalDataset | None:
        snapshot = self.snapshots.get(dataset_id)
        return CanonicalDataset.model_validate_json(snapshot.to_bytes()) if snapshot else None
