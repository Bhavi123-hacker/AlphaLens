"""Constructed TEST_ONLY PIT/survivorship cases, never real NSE performance."""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.build_p4_test_fixture import build_fixture

from alphalens_data.contracts import AvailabilityBasis
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import QualityStatus
from alphalens_data.universe.models import (
    IdentityFact,
    MembershipFact,
    QualityEvidence,
    SecurityType,
    UniverseEntry,
    UniverseInput,
    UniverseSnapshot,
)
from alphalens_data.universe.service import HistoricalUniverse, audit

FIXTURE = Path("tests/fixtures/p4/TEST_ONLY.universe.json")


@pytest.fixture
def universe_input() -> UniverseInput:
    return UniverseInput.model_validate_json(FIXTURE.read_bytes())


@pytest.fixture(scope="module")
def quality_universe(tmp_path_factory: pytest.TempPathFactory) -> UniverseInput:
    return build_fixture(tmp_path_factory.mktemp("TEST_ONLY_p4"))


def at(day: int) -> datetime:
    return datetime(2024, 1, day, 12, tzinfo=UTC)


def snapshot(data: UniverseInput, day: int, known_day: int | None = None) -> UniverseSnapshot:
    return HistoricalUniverse(data).as_of(date(2024, 1, day), at(known_day or day))


def entry(result: UniverseSnapshot, letter: str) -> UniverseEntry:
    return next(
        e
        for e in (*result.eligible_securities, *result.excluded_securities)
        if e.security_id == f"TEST:{letter}"
    )


def test_future_listing_never_appears_early(universe_input: UniverseInput) -> None:
    assert not entry(snapshot(universe_input, 1), "B").universe_membership
    assert entry(snapshot(universe_input, 4), "B").membership_reason == "EXCLUDED_NOT_YET_LISTED"
    assert entry(snapshot(universe_input, 5), "B").universe_membership
    assert (
        entry(snapshot(universe_input, 1, 20), "B").membership_reason == "EXCLUDED_NOT_YET_LISTED"
    )


def test_future_symbol_cannot_leak_backward(universe_input: UniverseInput) -> None:
    early = entry(snapshot(universe_input, 5, 20), "D")
    assert early.identity and early.identity.symbol == "TEST_D_OLD"
    changed = entry(snapshot(universe_input, 10), "D")
    assert changed.identity and changed.identity.symbol == "TEST_D_NEW"
    assert changed.identity.aliases == ("TEST_D_OLD",)
    assert changed.identity.security_id == early.identity.security_id


def test_delisting_does_not_erase_history(universe_input: UniverseInput) -> None:
    assert entry(snapshot(universe_input, 1, 20), "C").universe_membership
    assert entry(snapshot(universe_input, 10), "C").universe_membership
    assert entry(snapshot(universe_input, 10), "C").membership_evidence is not None
    before = entry(snapshot(universe_input, 10), "C").membership_evidence
    assert before and before.effective_to is None  # Departure not yet announced.
    assert entry(snapshot(universe_input, 12), "C").membership_reason == "EXCLUDED_DELISTED"


def test_late_availability_cannot_be_used_at_effective_time(universe_input: UniverseInput) -> None:
    early = entry(snapshot(universe_input, 10), "H")
    assert early.identity and early.identity.symbol == "TEST_H_OLD"
    corrected_knowledge = entry(snapshot(universe_input, 10, 12), "H")
    assert corrected_knowledge.identity and corrected_knowledge.identity.symbol == "TEST_H_NEW"
    assert (
        early.identity.provenance.available_at
        != corrected_knowledge.identity.provenance.available_at
    )


def test_current_constituents_fail_loudly(universe_input: UniverseInput) -> None:
    definition = universe_input.definition.model_copy(
        update={"evidence_scope": "CURRENT_SNAPSHOT_ONLY"}
    )
    with pytest.raises(DataContractError, match="CURRENT_SNAPSHOT_CANNOT_DEFINE_HISTORICAL"):
        HistoricalUniverse(universe_input.model_copy(update={"definition": definition}))


def test_quality_rejection_preserves_existence(quality_universe: UniverseInput) -> None:
    result = snapshot(quality_universe, 10)
    g = entry(result, "G")
    assert g.universe_membership
    assert not g.analysis_eligible
    assert g.data_quality_status == "REJECTED"
    assert g.analysis_reason == "DATA_QUALITY_REJECTED"
    assert "P2_OHLC_HIGH_OPEN" in g.data_quality_reasons
    assert entry(result, "A").analysis_eligible
    assert not quality_universe.quality[2].report.dataset_blocked
    assert quality_universe.quality[2].report.summary.quarantined_record_count == 1


def test_temporary_price_absence_preserves_membership(quality_universe: UniverseInput) -> None:
    g = entry(snapshot(quality_universe, 5), "G")
    assert g.universe_membership
    assert g.data_quality_status == "UNAVAILABLE"
    assert not g.analysis_eligible
    assert entry(snapshot(quality_universe, 12), "G").analysis_eligible


def test_later_classification_correction_does_not_rewrite_old_knowledge(
    universe_input: UniverseInput,
) -> None:
    universe = HistoricalUniverse(universe_input)
    original = universe.as_of(date(2024, 1, 10), at(10))
    fact = next(f for f in universe_input.memberships if f.security_id == "TEST:F")
    provenance = fact.provenance.model_copy(update={"available_at": at(15), "published_at": at(15)})
    correction = fact.model_copy(
        update={
            "revision_id": "r2",
            "supersedes_revision_id": "r1",
            "security_type": SecurityType.COMMON_EQUITY,
            "provenance": provenance,
        }
    )
    revised_input = universe_input.model_copy(
        update={"memberships": universe_input.memberships + (correction,)}
    )
    rebuilt = snapshot(revised_input, 10)
    assert rebuilt.eligible_securities == original.eligible_securities
    assert rebuilt.excluded_securities == original.excluded_securities
    assert rebuilt.known_evidence_sha256 == original.known_evidence_sha256
    assert rebuilt.input_sha256 != original.input_sha256
    assert universe.replay(original)
    assert entry(snapshot(revised_input, 10, 20), "F").universe_membership


@pytest.mark.parametrize("kind", ["ETF", "REIT", "INVIT", "PREFERENCE", "DEBT"])
def test_non_common_equity_never_eligible(universe_input: UniverseInput, kind: str) -> None:
    facts = tuple(
        f.model_copy(update={"security_type": SecurityType(kind)})
        if f.security_id == "TEST:E"
        else f
        for f in universe_input.memberships
    )
    result = snapshot(universe_input.model_copy(update={"memberships": facts}), 10)
    assert entry(result, "E").membership_reason == "EXCLUDED_SECURITY_TYPE"
    assert not entry(result, "E").universe_membership  # Series EQ alone proves nothing.


def test_unknown_type_remains_unknown(universe_input: UniverseInput) -> None:
    f = entry(snapshot(universe_input, 10), "F")
    assert f.membership_evidence and f.membership_evidence.security_type == "UNKNOWN"
    assert f.membership_reason == "EXCLUDED_UNKNOWN_CLASSIFICATION"
    assert snapshot(universe_input, 10).historical_universe_status == "DEGRADED"


def test_unknown_availability_fails_closed(universe_input: UniverseInput) -> None:
    facts = tuple(
        f.model_copy(
            update={
                "provenance": f.provenance.model_copy(
                    update={
                        "available_at": None,
                        "published_at": None,
                        "availability_basis": AvailabilityBasis.UNKNOWN,
                    }
                )
            }
        )
        if f.security_id == "TEST:A"
        else f
        for f in universe_input.memberships
    )
    a = entry(snapshot(universe_input.model_copy(update={"memberships": facts}), 10), "A")
    assert a.membership_reason == "EXCLUDED_INFORMATION_NOT_AVAILABLE"
    assert a.membership_evidence is None


def test_future_fact_identity_is_not_exposed(universe_input: UniverseInput) -> None:
    b = entry(snapshot(universe_input, 1), "B")
    assert b.identity is None and b.membership_evidence is None
    assert b.evidence_status == "UNKNOWN"


def test_half_open_intervals_at_change_boundary(universe_input: UniverseInput) -> None:
    before = entry(snapshot(universe_input, 9), "D")
    after = entry(snapshot(universe_input, 10), "D")
    assert before.identity and before.identity.effective_to == date(2024, 1, 10)
    assert after.identity and after.identity.effective_from == date(2024, 1, 10)
    assert before.identity.symbol != after.identity.symbol


@pytest.mark.parametrize("end", ["2020-01-01", "2019-12-31"])
def test_invalid_effective_intervals_rejected(universe_input: UniverseInput, end: str) -> None:
    value = universe_input.identities[0].model_dump(mode="json")
    value["effective_to"] = end
    with pytest.raises(ValidationError, match="positive half-open"):
        IdentityFact.model_validate(value)


def test_overlapping_intervals_fail_without_arbitrary_winner(universe_input: UniverseInput) -> None:
    original = universe_input.identities[0]
    overlapping = original.model_copy(update={"fact_id": "TEST_OVERLAP", "symbol": "TEST_OTHER"})
    data = universe_input.model_copy(
        update={"identities": universe_input.identities + (overlapping,)}
    )
    with pytest.raises(DataContractError, match="OVERLAPPING_EXCLUSIVE"):
        snapshot(data, 10)


@pytest.mark.parametrize(
    "change",
    [
        {"revision_id": "r1"},
        {"revision_id": "r2", "supersedes_revision_id": "absent"},
        {"revision_id": "r2", "supersedes_revision_id": None},
    ],
)
def test_invalid_revision_chains_fail(
    universe_input: UniverseInput, change: dict[str, Any]
) -> None:
    extra = universe_input.memberships[0].model_copy(update=change)
    data = universe_input.model_copy(update={"memberships": universe_input.memberships + (extra,)})
    with pytest.raises(DataContractError):
        HistoricalUniverse(data)


def test_timestamp_inversions_rejected(universe_input: UniverseInput) -> None:
    value = universe_input.memberships[0].model_dump(mode="json")
    value["provenance"]["available_at"] = "2023-01-01T00:00:00Z"
    with pytest.raises(ValidationError, match="inversion"):
        MembershipFact.model_validate(value)


def test_live_mode_requires_receipt_and_historical_mode_keeps_evidence(
    universe_input: UniverseInput,
) -> None:
    universe = HistoricalUniverse(universe_input)
    historical = universe.as_of(date(2024, 1, 10), at(10))
    live = universe.as_of(date(2024, 1, 10), at(10), mode="live")
    assert historical.eligible_securities
    assert not live.eligible_securities  # Historical evidence ingested in 2026.
    with pytest.raises(DataContractError, match="NAIVE_DECISION"):
        universe.as_of(date(2024, 1, 10), datetime(2024, 1, 10))


def test_unavailable_quality_cannot_become_analysis_eligible(
    quality_universe: UniverseInput,
) -> None:
    reports = tuple(q.model_copy(update={"available_at": at(20)}) for q in quality_universe.quality)
    data = quality_universe.model_copy(update={"quality": reports})
    a = entry(snapshot(data, 10), "A")
    assert a.universe_membership
    assert not a.analysis_eligible
    assert a.analysis_reason == "DATA_QUALITY_UNAVAILABLE"


def test_snapshot_hash_and_replay_are_deterministic(quality_universe: UniverseInput) -> None:
    universe = HistoricalUniverse(quality_universe)
    result = universe.as_of(date(2024, 1, 10), at(10))
    assert result.to_bytes() == universe.as_of(date(2024, 1, 10), at(10)).to_bytes()
    assert universe.replay(result)
    payload = result.model_dump(mode="json", exclude={"snapshot_id"})
    assert result.snapshot_id == checksum(stable_json(payload))
    ids = tuple(e.security_id for e in result.eligible_securities)
    assert ids == tuple(sorted(ids))
    changed = result.model_copy(update={"snapshot_id": "0" * 64})
    with pytest.raises(DataContractError, match="REPLAY_INPUT_OR_OUTPUT_MISMATCH"):
        universe.replay(changed)


def test_immutable_snapshot_publication(quality_universe: UniverseInput, tmp_path: Path) -> None:
    result = snapshot(quality_universe, 10)
    target = tmp_path / (result.snapshot_id + ".json")
    publish(target, result.to_bytes())
    publish(target, result.to_bytes())
    with pytest.raises(DataContractError, match="IMMUTABLE_FILE_CONFLICT"):
        publish(target, b"different TEST_ONLY snapshot")
    assert target.read_bytes() == result.to_bytes()


def test_survivorship_audit_retains_departed_security(quality_universe: UniverseInput) -> None:
    snapshots = tuple(snapshot(quality_universe, day) for day in (1, 5, 10, 12, 20))
    report = audit(snapshots)
    assert report.unique_historical_security_count == 6
    assert report.entries == 6 and report.exits == 1
    assert report.symbol_changes == 2
    assert report.historically_present_absent_at_end == ("TEST:C",)
    assert report.unknown_classification_count == 5
    assert report.data_quality_exclusion_count == 2  # G temporary absence and invalid session.
    assert report.to_bytes() == audit(snapshots).to_bytes()
    assert report.classification == "TEST_ONLY" and not report.production_claims_permitted
    with pytest.raises(DataContractError, match="CHRONOLOGICAL"):
        audit(tuple(reversed(snapshots)))


def test_quality_checksum_and_classification_guard(quality_universe: UniverseInput) -> None:
    value = quality_universe.quality[0].model_dump(mode="json")
    value["report_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="checksum"):
        QualityEvidence.model_validate(value)
    value = quality_universe.model_dump(mode="json")
    value["memberships"][0]["provenance"]["classification"] = "RESEARCH_FIXTURE"
    value["memberships"][0]["provenance"]["rights_evidence"] = "TEST_ONLY accepted rights case"
    with pytest.raises(DataContractError, match="MIXED_UNIVERSE_CLASSIFICATION"):
        HistoricalUniverse(UniverseInput.model_validate(value))


def test_identifier_conflict_is_rejected(universe_input: UniverseInput) -> None:
    a = universe_input.identities[0]
    identities = tuple(
        f.model_copy(update={"isin": a.isin}) if f.security_id == "TEST:E" else f
        for f in universe_input.identities
    )
    with pytest.raises(DataContractError, match="SIMULTANEOUS_IDENTITY_CONFLICT"):
        snapshot(universe_input.model_copy(update={"identities": identities}), 10)


def test_cli_is_deterministic_and_rejects_current_snapshot(
    quality_universe: UniverseInput,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from alphalens_data.universe.cli import main

    source = tmp_path / "TEST_ONLY.input.json"
    source.write_bytes(stable_json(quality_universe.model_dump(mode="json")))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "alphalens-universe",
            "--input",
            str(source),
            "--date",
            "2024-01-10",
            "--decision-time",
            at(10).isoformat(),
        ],
    )
    assert main() == 0
    output = capsys.readouterr().out
    assert main() == 0
    assert capsys.readouterr().out == output
    value = quality_universe.model_dump(mode="json")
    value["definition"]["evidence_scope"] = "CURRENT_SNAPSHOT_ONLY"
    source.write_bytes(stable_json(value))
    assert main() == 2
    assert "CURRENT_SNAPSHOT_CANNOT_DEFINE_HISTORICAL_MEMBERSHIP" in capsys.readouterr().out


def test_reordered_evidence_reconstructs_identical_snapshot(
    quality_universe: UniverseInput,
) -> None:
    reordered = quality_universe.model_copy(
        update={
            "identities": tuple(reversed(quality_universe.identities)),
            "memberships": tuple(reversed(quality_universe.memberships)),
            "quality": tuple(reversed(quality_universe.quality)),
        }
    )
    assert snapshot(reordered, 10).to_bytes() == snapshot(quality_universe, 10).to_bytes()


def test_series_change_preserves_security_id(universe_input: UniverseInput) -> None:
    identities = tuple(
        f.model_copy(update={"series": "BE"}) if f.fact_id == "TEST_ID_D_NEW" else f
        for f in universe_input.identities
    )
    data = universe_input.model_copy(update={"identities": identities})
    old = entry(snapshot(data, 9), "D")
    new = entry(snapshot(data, 10), "D")
    assert old.identity and new.identity
    assert old.identity.series == "EQ" and new.identity.series == "BE"
    assert old.identity.security_id == new.identity.security_id


def test_unknown_listing_status_is_unavailable(universe_input: UniverseInput) -> None:
    facts = tuple(
        f.model_copy(update={"listing_status": "UNKNOWN"}) if f.security_id == "TEST:A" else f
        for f in universe_input.memberships
    )
    a = entry(snapshot(universe_input.model_copy(update={"memberships": facts}), 10), "A")
    assert not a.universe_membership
    assert a.membership_reason == "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE"


def test_future_session_query_fails(universe_input: UniverseInput) -> None:
    with pytest.raises(DataContractError, match="FUTURE_SESSION_QUERY"):
        snapshot(universe_input, 10, 9)


def test_branching_revision_and_time_inversion_are_rejected(universe_input: UniverseInput) -> None:
    revised = next(f for f in universe_input.memberships if f.supersedes_revision_id)
    branching = revised.model_copy(update={"revision_id": "r3"})
    with pytest.raises(DataContractError, match="BRANCHING_REVISION"):
        HistoricalUniverse(
            universe_input.model_copy(
                update={
                    "memberships": universe_input.memberships + (branching,),
                }
            )
        )
    parent = next(
        f
        for f in universe_input.memberships
        if f.fact_id == revised.fact_id and f.revision_id == "r1"
    )
    impossible = revised.model_copy(
        update={
            "provenance": revised.provenance.model_copy(
                update={
                    "available_at": parent.provenance.available_at.replace(year=2022)
                    if parent.provenance.available_at
                    else None,
                    "published_at": None,
                }
            )
        }
    )
    facts = tuple(impossible if f == revised else f for f in universe_input.memberships)
    with pytest.raises(DataContractError, match="REVISION_TIME_INVERSION"):
        HistoricalUniverse(universe_input.model_copy(update={"memberships": facts}))


def test_missing_departure_fact_is_not_inferred(universe_input: UniverseInput) -> None:
    facts = tuple(f for f in universe_input.memberships if f.fact_id != "TEST_MEMBER_C_DELISTED")
    c = entry(snapshot(universe_input.model_copy(update={"memberships": facts}), 20), "C")
    assert c.membership_reason == "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE"
    assert c.membership_reason != "EXCLUDED_DELISTED"


def test_wrong_source_quality_cannot_enable_analysis(quality_universe: UniverseInput) -> None:
    qualities = tuple(
        q.model_copy(update={"source": "unrelated-source"}) for q in quality_universe.quality
    )
    a = entry(snapshot(quality_universe.model_copy(update={"quality": qualities}), 10), "A")
    assert a.universe_membership and not a.analysis_eligible
    assert a.data_quality_status == "UNAVAILABLE"


def test_unknown_quality_availability_fails_closed(quality_universe: UniverseInput) -> None:
    qualities = tuple(q.model_copy(update={"available_at": None}) for q in quality_universe.quality)
    a = entry(snapshot(quality_universe.model_copy(update={"quality": qualities}), 10), "A")
    assert a.universe_membership and not a.analysis_eligible


def test_contradictory_p3_gate_is_rejected(quality_universe: UniverseInput) -> None:
    q = quality_universe.quality[2]
    report = q.report.model_copy(update={"status": QualityStatus.VALID})
    value = q.model_dump(mode="json")
    value["report"] = report.model_dump(mode="json")
    value["report_sha256"] = checksum(report.to_bytes())
    with pytest.raises(ValidationError, match="contradicts recorded severities"):
        QualityEvidence.model_validate(value)


def test_audit_rejects_mixed_inputs_and_ambiguous_quality(quality_universe: UniverseInput) -> None:
    original = snapshot(quality_universe, 10)
    other = snapshot(quality_universe, 12).model_copy(update={"input_sha256": "0" * 64})
    with pytest.raises(DataContractError, match="PINNED_INPUT"):
        audit((original, other))
    with pytest.raises(DataContractError, match="AMBIGUOUS_SESSION_QUALITY"):
        HistoricalUniverse(
            quality_universe.model_copy(
                update={
                    "quality": quality_universe.quality + (quality_universe.quality[0],),
                }
            )
        )
