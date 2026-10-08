"""Constructed TEST_ONLY scenarios exercising the research contract, not market evidence."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from pydantic import ValidationError

from alphalens_data.ingestion.contracts import CanonicalEOD, Classification
from alphalens_data.research import ResearchProfile, assess, calendar, lineage, require_research
from alphalens_features.maths import calculate
from alphalens_features.models import BuildPlan, Decision
from alphalens_features.registry import default_set
from alphalens_features.research import numerical
from alphalens_labels.research import indexed_targets, targets


def synthetic_research_row(path: Path, session: date, isin: str | None = None) -> CanonicalEOD:
    from alphalens_data.ingestion.contracts import ArtifactSpec, Versions
    from alphalens_data.ingestion.normalizing import normalize
    from alphalens_data.ingestion.storage import RawLanding
    from alphalens_data.providers.tejhq import parse_batch

    # Synthetic TEST_ONLY bytes exercise an explicitly research-classified contract.
    spec = ArtifactSpec(
        source="synthetic",
        dataset="test-only-research-contract",
        source_identifier="TEST_ONLY_CONSTRUCTED_NOT_MARKET_DATA",
        original_filename="TEST_ONLY.parquet",
        content_type="application/parquet",
        classification=Classification.RESEARCH_ONLY,
        rights_evidence="TEST_ONLY",
    )
    manifest, _ = RawLanding(path).capture(
        b"TEST_ONLY_SYNTHETIC_NOT_REAL_MARKET_DATA", spec, Versions(parser="tejhq.parquet.v1")
    )
    rows, _ = normalize(
        parse_batch(
            [
                dict(
                    date=session,
                    symbol="TEST_ONLY",
                    isin=isin,
                    series="EQ",
                    open=10,
                    high=11,
                    low=9,
                    close=10,
                    volume=100,
                )
            ],
            2,
        ),
        manifest,
    )
    return rows[0]


def test_future_isin_does_not_backfill_and_provisional_years_stay_distinct(tmp_path: Path) -> None:
    from scripts.build_tejhq_research import research_id

    early = synthetic_research_row(tmp_path, date(2010, 1, 4))
    other = synthetic_research_row(tmp_path, date(2011, 1, 4))
    later = synthetic_research_row(tmp_path, date(2012, 1, 4), "INE_TEST_ONLY")
    assert early.isin is None and early.identity_basis == "SOURCE_SCOPED_SYMBOL"
    assert len({research_id(early), research_id(other), research_id(later)}) == 3


def test_research_resolver_hides_future_rows_and_names(tmp_path: Path) -> None:
    from alphalens_data.universe.research import ResearchUniverse

    early = synthetic_research_row(tmp_path, date(2010, 1, 4))
    sessions = calendar({date(2010, 1, 4), date(2010, 1, 5)}, ResearchProfile())
    resolver = ResearchUniverse(ResearchProfile(), sessions)
    before = datetime(2010, 1, 4, 23, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert resolver.resolve(early, before, "TEST_ONLY ETF") is None
    at = sessions.availability(early.session_date)
    assert at is not None
    resolved = resolver.resolve(early, at, "TEST_ONLY EQUITY")
    assert resolved is not None
    assert resolved.analytical_type == "RESEARCH_EQUITY_CANDIDATE"


def test_normal_p4_remains_fail_closed_for_unknown_availability() -> None:
    from alphalens_data.contracts import AvailabilityBasis
    from alphalens_data.universe.models import UniverseInput
    from alphalens_data.universe.service import HistoricalUniverse

    fixture = UniverseInput.model_validate_json(
        Path("tests/fixtures/p4/TEST_ONLY.universe.json").read_bytes()
    )
    identities = tuple(
        f.model_copy(
            update={
                "provenance": f.provenance.model_copy(
                    update={"available_at": None, "availability_basis": AvailabilityBasis.UNKNOWN}
                )
            }
        )
        for f in fixture.identities
    )
    memberships = tuple(
        f.model_copy(
            update={
                "provenance": f.provenance.model_copy(
                    update={"available_at": None, "availability_basis": AvailabilityBasis.UNKNOWN}
                )
            }
        )
        for f in fixture.memberships
    )
    result = HistoricalUniverse(
        fixture.model_copy(update={"identities": identities, "memberships": memberships})
    ).as_of(date(2024, 1, 5), datetime(2024, 1, 6, tzinfo=ZoneInfo("Asia/Kolkata")))
    assert not result.eligible_securities


def test_research_profile_cannot_claim_production_or_other_classification() -> None:
    for classification in ("PRODUCTION", "TEST_ONLY", "RESEARCH_FIXTURE"):
        with pytest.raises(ValidationError):
            ResearchProfile(classification=classification)
        with pytest.raises(ValueError, match="RESEARCH_ASSUMPTIONS_FORBIDDEN"):
            require_research(ResearchProfile(), Classification(classification))


def test_next_session_assumption_has_no_same_session_execution() -> None:
    sessions = calendar({date(2023, 11, 10), date(2023, 11, 13)}, ResearchProfile())
    at = sessions.availability(date(2023, 11, 10))
    assert at is not None and at.date() == date(2023, 11, 12)
    assert sessions.entry_allowed(date(2023, 11, 10), date(2023, 11, 12), at)
    assert not sessions.entry_allowed(date(2023, 11, 10), date(2023, 11, 10), at)
    assert not sessions.entry_allowed(date(2023, 11, 10), date(2023, 11, 13), at)
    assert sessions.sessions[1].price_status == "PRICE_OBSERVATION_MISSING"
    assert sessions.sessions[1].evidence == "OFFICIAL_VERIFIED_SESSION"


@pytest.mark.parametrize(
    "name",
    [
        "SYNTHETIC ETF",
        "SYNTHETIC REIT",
        "SYNTHETIC INVIT",
        "SYNTHETIC PREFERENCE",
        "SYNTHETIC BOND",
        "SYNTHETIC FUND",
        "SYNTHETIC INDEX",
    ],
)
def test_known_non_equity_names_excluded(name: str) -> None:
    assert assess("EQ", "INE_TEST_ONLY", name).analytical_type == "EXCLUDED_NON_EQUITY"


def test_candidate_is_not_authoritative_common_equity() -> None:
    result = assess("EQ", "INE_TEST_ONLY", None)
    assert result.analytical_type == "RESEARCH_EQUITY_CANDIDATE"
    assert result.production_security_type == "UNKNOWN"
    assert assess("EQ", "INF_TEST_ONLY", None).analytical_type == "EXCLUDED_NON_EQUITY"


def test_all_registry_array_formulas_match_scalar_reference_and_no_future_values() -> None:
    at = datetime(2020, 1, 2, tzinfo=ZoneInfo("Asia/Kolkata"))
    plan = BuildPlan(
        history_start=at.date(), decisions=(Decision(session_date=at.date(), knowledge_cutoff=at),)
    )
    rng = np.random.default_rng(1729)
    close = 100 + np.cumsum(rng.normal(0, 0.1, 260))
    high = close + 1
    low = close - 1
    volume = rng.integers(100, 1000, 260).astype(float)
    for d in default_set(plan).definitions:
        if d.feature_family == "CROSS_SECTIONAL":
            continue
        result = numerical(d, close, high, low, volume)
        for i in (d.minimum_history - 1, 49, 199, 259):
            if i < d.minimum_history - 1:
                continue
            start = max(0, i - d.lookback + 1)
            expected = calculate(
                d.feature_name, *(x[start : i + 1].tolist() for x in (close, high, low, volume))
            )
            assert result[i] == pytest.approx(expected, rel=1e-10, abs=1e-10)
        future = close.copy()
        future[230:] += 500
        changed = numerical(d, future, high, low, volume)
        np.testing.assert_allclose(result[:230], changed[:230], equal_nan=True)


def test_missing_muhurat_prices_never_filled_and_required_labels_unavailable() -> None:
    sessions = calendar(
        {date(2023, 11, 10), date(2023, 11, 13), date(2023, 11, 14)}, ResearchProfile()
    )
    values = [Decimal("10"), None, Decimal("11"), Decimal("12")]
    labels = targets(
        sessions, values, values, np.asarray([True, False, True, True]), np.zeros(4, dtype=bool), 1
    )
    assert labels[0]["entry_session"] == date(2023, 11, 12)
    assert labels[0]["maturity"] == "UNAVAILABLE"
    assert labels[0]["return_value"] is None
    assert labels[0]["exact_numerator"] is None
    selected = indexed_targets(
        sessions,
        values,
        values,
        np.asarray([True, False, True, True]),
        np.zeros(4, dtype=bool),
        1,
        [0, 2],
    )
    assert selected == {i: labels[i] for i in (0, 2)}


def test_trimmed_feature_history_matches_full_calendar_for_late_listing() -> None:
    at = datetime(2020, 1, 2, tzinfo=ZoneInfo("Asia/Kolkata"))
    plan = BuildPlan(
        history_start=at.date(), decisions=(Decision(session_date=at.date(), knowledge_cutoff=at),)
    )
    close = 100 + np.sin(np.arange(800) / 7) + np.arange(800) / 100
    arrays = [close, close + 1, close - 1, 1000 + np.arange(800) % 20]
    arrays = [np.asarray(a, dtype=float) for a in arrays]
    for a in arrays:
        a[:300] = np.nan
    for definition in default_set(plan).definitions:
        if definition.feature_family == "CROSS_SECTIONAL":
            continue
        full = numerical(definition, *arrays)
        trimmed = numerical(definition, *(a[100:651] for a in arrays))
        np.testing.assert_allclose(full[300:651], trimmed[200:], equal_nan=True)


def test_final_vintage_lineage_is_explicit_not_pit() -> None:
    profile = ResearchProfile()
    evidence = lineage(profile)
    assert evidence["final_vintage"] == "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
    assert evidence["research_profile_id"] == profile.profile_id
    assert evidence["research_profile"]["pit_claim"] == "NOT PRODUCTION PIT"  # type: ignore[index]


def test_research_canonical_preserves_prices_and_rejects_same_session_availability(
    tmp_path: Path,
) -> None:
    from alphalens_data.canonical.models import EODValues
    from alphalens_data.canonical.research import ResearchObservation
    from alphalens_data.ingestion.storage import stable_json
    from alphalens_data.normalization import checksum

    row = synthetic_research_row(tmp_path, date(2023, 11, 10), "INE_TEST_ONLY")
    sessions = calendar({date(2023, 11, 10), date(2023, 11, 13)}, ResearchProfile())
    available = sessions.availability(row.session_date)
    assert available is not None
    value = ResearchObservation.model_construct(
        profile=sessions.profile,
        source=row,
        values=EODValues(
            open=row.open, high=row.high, low=row.low, close=row.close, volume=row.volume
        ),
        quality="VALID",
        quality_reasons=(),
        assessment=assess(row.series, row.isin, None),
        assumed_available_at=available.astimezone(UTC),
        canonical_record_id="0" * 64,
    )
    data = value.model_dump(mode="json")
    data["canonical_record_id"] = checksum(
        stable_json({k: v for k, v in data.items() if k != "canonical_record_id"})
    )
    checked = ResearchObservation.model_validate(data)
    assert checked.values.close == row.close
    assert checked.assumed_available_at is not None
    with pytest.raises(ValidationError, match="MUST_FOLLOW_SOURCE_SESSION"):
        ResearchObservation.model_validate(
            dict(data, assumed_available_at="2023-11-10T23:59:59+05:30")
        )
    changed = dict(data["values"], close="11")
    with pytest.raises(ValidationError, match="PRESERVE_P2_VALUES"):
        ResearchObservation.model_validate(dict(data, values=changed))
