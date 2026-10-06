"""TEST_ONLY canonical lineage, temporal and anti-leakage acceptance scenarios."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError
from scripts.build_p5_test_fixture import build_fixture_p5

from alphalens_data.canonical.assembly import EvidenceAssembly, verify_local_batch
from alphalens_data.canonical.memory import MemoryDatasets, MemoryRevisions, MemorySecurities
from alphalens_data.canonical.models import (
    ActionRevision,
    Availability,
    CanonicalBatch,
    EODValues,
    FundamentalRevision,
    PriceRevision,
    PriceView,
    QualityRevision,
    ReadContext,
    Security,
    revision_key,
)
from alphalens_data.canonical.output import parquet_bytes
from alphalens_data.canonical.revisions import ordered_revisions, select_known
from alphalens_data.canonical.services import CanonicalReader, validate_snapshot
from alphalens_data.canonical.validation import validate_batch
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.quality.models import QualityStatus


@pytest.fixture(scope="module")
def canonical(tmp_path_factory: pytest.TempPathFactory) -> CanonicalBatch:
    return build_fixture_p5(tmp_path_factory.mktemp("TEST_ONLY_p5"))[0]


def context(day: int, hour: int = 12) -> ReadContext:
    return ReadContext(knowledge_cutoff=datetime(2024, 1, day, hour, tzinfo=UTC))


def read_prices(
    reader: CanonicalReader, start: date, end: date, ctx: ReadContext
) -> tuple[PriceView, ...]:
    return reader.prices_as_of(start, end, ctx).records


def bar(batch: CanonicalBatch, number: int = 1) -> PriceRevision:
    return next(
        r
        for r in batch.revisions
        if isinstance(r, PriceRevision)
        and r.security_id == "TEST:A"
        and r.session_date == date(2024, 1, 10)
        and r.revision_number == number
    )


def test_cutoff_hides_prices_until_available(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    assert read_prices(reader, date(2024, 1, 10), date(2024, 1, 10), context(10, 10)) == ()
    assert read_prices(reader, date(2024, 1, 10), date(2024, 1, 10), context(10, 11))


def test_later_revision_is_invisible_earlier(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    before = next(
        v
        for v in read_prices(reader, date(2024, 1, 10), date(2024, 1, 10), context(14))
        if v.observation.security_id == "TEST:A"
    )
    after = next(
        v
        for v in read_prices(reader, date(2024, 1, 10), date(2024, 1, 10), context(15))
        if v.observation.security_id == "TEST:A"
    )
    assert before.observation.revision_id == "r1" and after.observation.revision_id == "r2"
    assert before.observation.values and after.observation.values
    assert before.observation.values.close == Decimal("100")
    assert after.observation.values.close == Decimal("101")


def test_future_symbols_and_availability_do_not_leak(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    old = reader.security_metadata_as_of(date(2024, 1, 5), context(20)).records
    assert next(r for r in old if r.security_id == "TEST:D").fact.symbol == "TEST_D_OLD"
    jan10 = reader.security_metadata_as_of(date(2024, 1, 10), context(10)).records
    assert next(r for r in jan10 if r.security_id == "TEST:D").fact.symbol == "TEST_D_NEW"
    assert next(r for r in jan10 if r.security_id == "TEST:H").fact.symbol == "TEST_H_OLD"
    jan12 = reader.security_metadata_as_of(date(2024, 1, 10), context(12)).records
    assert next(r for r in jan12 if r.security_id == "TEST:H").fact.symbol == "TEST_H_NEW"


def test_future_listing_and_delisting_preserve_history(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    first = reader.universe_as_of(date(2024, 1, 1), context(20))
    last = reader.universe_as_of(date(2024, 1, 20), context(20))
    assert "TEST:B" not in {e.security_id for e in first.eligible_securities}
    assert "TEST:C" in {e.security_id for e in first.eligible_securities}
    assert "TEST:C" not in {e.security_id for e in last.eligible_securities}
    history = read_prices(reader, date(2024, 1, 1), date(2024, 1, 20), context(20))
    assert any(v.observation.security_id == "TEST:C" for v in history)


def test_quality_rejection_does_not_erase_existence(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    result = reader.universe_as_of(date(2024, 1, 10), context(10))
    entry = next(e for e in result.eligible_securities if e.security_id == "TEST:G")
    assert entry.universe_membership and not entry.analysis_eligible
    values = read_prices(reader, date(2024, 1, 10), date(2024, 1, 10), context(10))
    rejected = next(v for v in values if v.observation.security_id == "TEST:G")
    assert rejected.quality == QualityStatus.REJECTED and rejected.observation.values is None
    assert rejected.universe_membership and not rejected.analysis_eligible
    assert any(
        link.record_key == revision_key(rejected.observation) and link.quarantine_key
        for link in canonical.lineage
    )


def test_unknown_and_non_equity_not_promoted(canonical: CanonicalBatch) -> None:
    result = CanonicalReader(canonical).universe_as_of(date(2024, 1, 10), context(10))
    reasons = {e.security_id: e.membership_reason for e in result.excluded_securities}
    assert reasons["TEST:E"] == "EXCLUDED_SECURITY_TYPE"
    assert reasons["TEST:F"] == "EXCLUDED_UNKNOWN_CLASSIFICATION"


def test_fundamentals_unavailable_and_not_persistable(canonical: CanonicalBatch) -> None:
    result = CanonicalReader(canonical).fundamentals_as_of(context(20))
    assert result.availability == Availability.UNAVAILABLE and result.records == ()
    source = bar(canonical)
    declaration = FundamentalRevision(
        logical_record_id="TEST_ONLY:unavailable",
        revision_id="r1",
        revision_number=1,
        security_id="TEST:A",
        effective_from=date(2023, 12, 31),
        provenance=source.provenance,
        fact_name="UNAVAILABLE",
        statement_type="OTHER",
        reporting_basis="UNKNOWN",
        period_start=None,
        period_end=date(2023, 12, 31),
        unit="INR",
        value=None,
    )
    assert declaration.provenance.available_at is not None
    assert declaration.period_end != declaration.provenance.available_at.date()
    with pytest.raises(DataContractError, match="FUNDAMENTAL_PIT_DATA_UNAVAILABLE"):
        MemoryRevisions().put(declaration)


def test_classification_cannot_become_production(canonical: CanonicalBatch) -> None:
    with pytest.raises(ValidationError):
        Security(security_id="TEST:A", classification=Classification.PRODUCTION)
    with pytest.raises(DataContractError, match="MIXED_CANONICAL_CLASSIFICATION"):
        validate_batch(
            canonical.model_copy(update={"classification": Classification.RESEARCH_FIXTURE})
        )


def test_current_constituent_protection(canonical: CanonicalBatch) -> None:
    with pytest.raises(DataContractError, match="CURRENT_SNAPSHOT"):
        validate_batch(
            canonical.model_copy(
                update={
                    "definition": canonical.definition.model_copy(
                        update={"evidence_scope": "CURRENT_SNAPSHOT_ONLY"}
                    )
                }
            )
        )


def test_pinned_snapshot_survives_new_knowledge(canonical: CanonicalBatch) -> None:
    roots = tuple(
        r for r in canonical.revisions if r.kind not in {"BAR", "QUALITY"} or r.revision_number == 1
    )
    keys = {revision_key(r) for r in roots}
    old_input = canonical.model_copy(
        update={
            "revisions": roots,
            "lineage": tuple(link for link in canonical.lineage if link.record_key in keys),
        }
    )
    repository = MemoryDatasets()
    repository.save_input(old_input)
    earlier = CanonicalReader(old_input).build(date(2024, 1, 1), date(2024, 1, 20), context(20))
    repository.save_snapshot(earlier)
    repository.save_input(canonical)
    newer = CanonicalReader(canonical).build(date(2024, 1, 1), date(2024, 1, 20), context(20))
    assert newer.dataset_id != earlier.dataset_id
    pinned = repository.get_input(earlier.input_id)
    assert pinned is not None
    validate_snapshot(earlier, pinned)
    assert repository.get_snapshot(earlier.dataset_id) == earlier


def test_snapshot_and_parquet_replay_determinism(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    one = reader.build(date(2024, 1, 1), date(2024, 1, 20), context(20))
    two = CanonicalReader(CanonicalBatch.model_validate_json(canonical.to_bytes())).build(
        date(2024, 1, 1), date(2024, 1, 20), context(20)
    )
    assert one.to_bytes() == two.to_bytes() and one.dataset_id == two.dataset_id
    assert parquet_bytes(one) == parquet_bytes(two)
    table = pq.read_table(pa.BufferReader(parquet_bytes(one)))
    assert table.schema.field("close").type == pa.decimal128(38, 18)
    assert table.schema.metadata and table.schema.metadata[b"dataset_id"] == one.dataset_id.encode()
    assert table.num_rows == len(one.prices)
    assert table.column("close").null_count == 1
    assert one.family_states["fundamentals"] == Availability.UNAVAILABLE
    assert all(
        r.provenance.available_at and r.provenance.available_at <= one.context.knowledge_cutoff
        for r in (
            *one.identities,
            *one.sessions,
            *one.corporate_actions,
            *one.quality,
            *(p.observation for p in one.prices),
        )
    )


def test_input_order_does_not_change_identity(canonical: CanonicalBatch) -> None:
    shuffled = canonical.model_copy(
        update={
            "revisions": tuple(reversed(canonical.revisions)),
            "lineage": tuple(reversed(canonical.lineage)),
        }
    )
    assert shuffled.input_id == canonical.input_id


def test_idempotent_revision_and_conflict(canonical: CanonicalBatch) -> None:
    repository = MemoryRevisions()
    first, second = bar(canonical), bar(canonical, 2)
    repository.put(first)
    repository.put(first)
    repository.put(second)
    assert len(repository.list("BAR", "TEST:A")) == 2
    assert repository.get(revision_key(second)) == second
    with pytest.raises(DataContractError, match="IMMUTABLE"):
        repository.put(first.model_copy(update={"currency": None}))
    with pytest.raises(DataContractError, match="MISSING"):
        MemoryRevisions().put(second)
    with pytest.raises(DataContractError, match="BRANCHING"):
        repository.put(second.model_copy(update={"revision_id": "r2-other"}))


@pytest.mark.parametrize(
    "changes",
    [
        {"high": "99"},
        {"low": "101"},
        {"open": "0"},
        {"close": "-1"},
        {"volume": -1},
        {"volume": 2**63},
        {"close": "NaN"},
        {"close": "1.0000000000000000001"},
        {"close": 100.0},
    ],
)
def test_numeric_and_ohlc_hard_invariants(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        EODValues.model_validate(
            dict(open="100", high="110", low="90", close="100", volume=10) | changes
        )


def test_temporal_close_and_unknown_availability(canonical: CanonicalBatch) -> None:
    record = bar(canonical)
    with pytest.raises(ValidationError):
        PriceRevision.model_validate(record.model_dump() | {"session_close_at": None})
    unknown = record.model_copy(
        update={
            "provenance": record.provenance.model_copy(
                update={"available_at": None, "availability_basis": "UNKNOWN"}
            )
        }
    )
    assert not select_known((unknown,), context(20))
    assert not select_known(
        (record,), ReadContext(knowledge_cutoff=context(20).knowledge_cutoff, mode="live")
    )
    with pytest.raises(ValidationError):
        ReadContext(knowledge_cutoff=datetime(2024, 1, 20))


def test_lineage_source_and_checksum_mismatch(canonical: CanonicalBatch) -> None:
    record = bar(canonical)
    changed = record.model_copy(
        update={"provenance": record.provenance.model_copy(update={"artifact_sha256": "0" * 64})}
    )
    with pytest.raises(DataContractError, match="PROVENANCE_CHECKSUM"):
        validate_batch(
            canonical.model_copy(
                update={
                    "revisions": tuple(changed if r == record else r for r in canonical.revisions)
                }
            )
        )
    with pytest.raises(DataContractError, match="ARTIFACT_MISSING"):
        validate_batch(canonical.model_copy(update={"artifacts": ()}))


def test_invalid_chain_and_scopes(canonical: CanonicalBatch) -> None:
    first, second = bar(canonical), bar(canonical, 2)
    with pytest.raises(DataContractError):
        ordered_revisions((first, second.model_copy(update={"revision_number": 3})))
    with pytest.raises(DataContractError):
        ordered_revisions(
            (
                first,
                second.model_copy(
                    update={"effective_from": date(2024, 1, 12), "session_date": date(2024, 1, 12)}
                ),
            )
        )


def test_action_evidence_and_adjustments_are_not_invented(canonical: CanonicalBatch) -> None:
    action = next(r for r in canonical.revisions if isinstance(r, ActionRevision))
    assert (
        action.event_type == "SYMBOL_CHANGE" and action.factor is None and action.cash_value is None
    )
    assert not any(
        isinstance(r, PriceRevision) and r.price_basis == "ADJUSTED" for r in canonical.revisions
    )
    with pytest.raises(ValidationError):
        PriceRevision.model_validate(
            bar(canonical).model_dump()
            | {"price_basis": "ADJUSTED", "price_basis_evidence": "TEST_ONLY"}
        )


def test_local_rebuild_and_artifact_verification(tmp_path: Path) -> None:
    first, roots = build_fixture_p5(tmp_path)
    second, _ = build_fixture_p5(tmp_path)
    assert first.to_bytes() == second.to_bytes()
    assert verify_local_batch(first, roots) == first
    with pytest.raises(DataContractError, match="RAW_ROOT"):
        verify_local_batch(first, {})
    altered = first.artifacts[0].model_copy(
        update={"acquired_at": datetime(2025, 1, 1, tzinfo=UTC)}
    )
    with pytest.raises(DataContractError, match="CAPTURED_MANIFEST_REPLAY"):
        verify_local_batch(
            first.model_copy(update={"artifacts": (altered, *first.artifacts[1:])}), roots
        )


def test_availability_quality_and_stale_policy_are_separate(canonical: CanonicalBatch) -> None:
    source = context(20)
    reader = CanonicalReader(canonical)
    stale = ReadContext(
        knowledge_cutoff=source.knowledge_cutoff,
        earliest_acceptable_availability=datetime(2024, 1, 19, tzinfo=UTC),
        freshness_evidence_reference="TEST_ONLY explicit freshness rule",
    )
    prices = read_prices(reader, date(2024, 1, 1), date(2024, 1, 1), stale)
    assert all(p.availability == Availability.STALE and not p.analysis_eligible for p in prices)
    assert all(p.quality != QualityStatus.REJECTED for p in prices)
    securities = MemorySecurities()
    securities.put(canonical.securities[0])
    assert securities.get(canonical.securities[0].security_id) == canonical.securities[0]


def test_quality_from_another_source_revision_cannot_certify_old_bar(
    canonical: CanonicalBatch,
    tmp_path: Path,
) -> None:
    original = bar(canonical)
    corrected_quality = next(
        r
        for r in canonical.revisions
        if isinstance(r, QualityRevision)
        and r.evidence.session_date == original.session_date
        and r.revision_number == 2
    )
    changed = original.model_copy(update={"quality_key": revision_key(corrected_quality)})
    assembly = EvidenceAssembly(tmp_path, Classification.TEST_ONLY)
    assembly.reference(changed)
    batch = canonical.model_copy(
        update={
            "revisions": tuple(changed if r == original else r for r in canonical.revisions),
            "artifacts": (*canonical.artifacts, *assembly.artifacts.values()),
            "normalized": (*canonical.normalized, *assembly.normalized.values()),
            "lineage": (*canonical.lineage, *assembly.lineage),
        }
    )
    with pytest.raises(DataContractError, match="PRICE_QUALITY_RECORD_LINEAGE_MISMATCH"):
        validate_batch(batch)


def test_empty_reads_have_explicit_unavailable_state(canonical: CanonicalBatch) -> None:
    reader = CanonicalReader(canonical)
    unavailable = reader.prices_as_of(date(2024, 1, 10), date(2024, 1, 10), context(10, 10))
    assert unavailable.availability == Availability.UNAVAILABLE
    assert unavailable.reason_codes == ("NO_KNOWN_PRICE_EVIDENCE",)
    assert unavailable.records == ()
    sessions = reader.sessions_as_of(date(2024, 1, 1), date(2024, 1, 20), context(20))
    assert all(s.status == "UNKNOWN_SESSION_STATUS" for s in sessions.records)
