"""TEST_ONLY golden mathematics and actual P5/P4/P3/P2 anti-leakage integration."""

import math
from datetime import timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.build_p6_test_fixture import START, build_history, day, instant

from alphalens_data.canonical.assembly import EvidenceAssembly
from alphalens_data.canonical.models import (
    ActionRevision,
    CanonicalBatch,
    IdentityRevision,
    Revision,
)
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.universe.models import SecurityType
from alphalens_features.cli import main
from alphalens_features.engine import build
from alphalens_features.maths import calculate
from alphalens_features.models import BuildPlan, Decision, FeatureDataset, FeatureRow
from alphalens_features.output import manifest, parquet_bytes
from alphalens_features.registry import default_set


@pytest.fixture(scope="module")
def history(tmp_path_factory: pytest.TempPathFactory) -> CanonicalBatch:
    return build_history(tmp_path_factory.mktemp("TEST_ONLY_p6"))[0]


def plan(*indices: int, benchmark: bool = True, quality: str = "ALLOW_DEGRADED") -> BuildPlan:
    return BuildPlan.model_validate(
        dict(
            history_start=START,
            decisions=tuple(
                Decision(session_date=day(i), knowledge_cutoff=instant(i, 12)) for i in indices
            ),
            quality_policy=quality,
            benchmark_security_id="TEST:BENCHMARK" if benchmark else None,
            benchmark_evidence_reference="TEST_ONLY constructed benchmark" if benchmark else None,
        )
    )


def row(dataset: FeatureDataset, index: int, security: str = "TEST:ALPHA") -> FeatureRow:
    return next(
        r for r in dataset.rows if r.session_date == day(index) and r.security_id == security
    )


def revised_reference(batch: CanonicalBatch, record: Revision, root: Path) -> CanonicalBatch:
    """Different pinned hypothetical evidence, never mutate a stored revision in place."""
    assembly = EvidenceAssembly(root, Classification.TEST_ONLY)
    assembly.reference(record)
    evidence = next(a for a in batch.artifacts if a.sha256 == record.provenance.artifact_sha256)
    assembly.link_reference(record, evidence, {"evidence_sha256": evidence.sha256})
    records = tuple(
        r
        for r in batch.revisions
        if (r.kind, r.logical_record_id, r.revision_id)
        != (record.kind, record.logical_record_id, record.revision_id)
    ) + (record,)
    return batch.model_copy(
        update=dict(
            revisions=records,
            artifacts=(*batch.artifacts, *assembly.artifacts.values()),
            normalized=tuple(
                {
                    n.normalized_record_id: n
                    for n in (*batch.normalized, *assembly.normalized.values())
                }.values()
            ),
            lineage=(*batch.lineage, *assembly.lineage),
        )
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("return_5", 0.05),
        ("log_return_1", math.log(1.05)),
        ("sma_5", 103.0),
        ("distance_sma_5", 105 / 103 - 1),
        ("ema_12", 143.5),
        ("ema_26", 136.5),
        ("macd", 7.0),
        ("macd_signal", 7.0),
        ("macd_histogram", 0.0),
        ("rsi_14", 100.0),
        ("atr_14", 4.0),
        ("volume_sma_20", 1395.0),
        ("volume_ratio_20", 1490 / 1395),
        ("volume_zscore_20", 95 / math.sqrt(3500)),
        ("volatility_5", math.sqrt(0.001 / 4)),
        ("close_to_high_20", 149 / 151 - 1),
        ("drawdown_20", 0.0),
    ],
)
def test_golden_formula(name: str, expected: float) -> None:
    # Arithmetic sequences have hand-derived SMA/EMA, MACD, RSI and ATR.
    # Returns use [100,105], volatility uses five returns [1%,2%,3%,4%,5%].
    close = [float(100 + i) for i in range(50)]
    if name.startswith("log_return"):
        close = [100, 105]
    elif name.startswith("return"):
        close = [100, 101, 102, 103, 104, 105]
    elif name.startswith(("sma", "distance_sma")):
        close = [101, 102, 103, 104, 105]
    elif name == "volatility_5":
        # Exact independently derived sample stdev of returns 1%,2%,3%,4%,5%.
        close = [100, 101, 103.02, 106.1106, 110.355024, 115.8727752]
    high, low = [c + 2 for c in close], [c - 2 for c in close]
    assert calculate(
        name, close, high, low, [1000 + 10 * i for i in range(30, 50)]
    ) == pytest.approx(expected, abs=1e-12)


def test_rsi_flat_and_losses() -> None:
    assert calculate("rsi_14", [10.0] * 15, [], [], []) == 50
    assert calculate("rsi_14", list(map(float, range(30, 15, -1))), [], [], []) == 0
    close = [100.0 + (i % 2) for i in range(15)]
    assert calculate("rsi_14", close, [], [], []) == 50


def test_wilder_smoothing_and_ema_initialization() -> None:
    # 14 gains of 1 followed by a loss of 2: gain=13/14, loss=2/14, RSI=100*13/15.
    close = list(map(float, range(100, 115))) + [112.0]
    assert calculate("rsi_14", close, [], [], []) == pytest.approx(100 * 13 / 15)
    close = [10.0] * 12 + [23.0]
    assert calculate("ema_12", close, [], [], []) == 12


def test_registry_versions_and_history(history: CanonicalBatch) -> None:
    data = build(CanonicalReader(history), plan(4, 14, 25, 49, 69))
    assert row(data, 4).values["sma_5"].value == 102
    assert row(data, 14).values["rsi_14"].value == 100
    assert row(data, 25).values["ema_26"].value == 112.5
    assert row(data, 49).values["sma_50"].value == 124.5
    for name in ("sma_100", "sma_200", "return_60"):
        assert "INSUFFICIENT_HISTORY" in row(data, 49).values[name].reason_codes
    assert row(data, 69).values["return_60"].value == pytest.approx(169 / 109 - 1)
    assert data.fundamental_pit_data == "UNAVAILABLE"
    assert all(d.feature_family != "FUNDAMENTAL" for d in data.feature_set.definitions)


def test_long_canonical_history_computes_sma100_and_sma200(tmp_path: Path) -> None:
    """P8 prerequisite audit: recursive 50-session bound does not truncate SMA windows."""
    batch = build_history(tmp_path, length=205)[0]
    data = build(CanonicalReader(batch), plan(69, 99, 199, 204))
    for name in ("sma_100", "sma_200"):
        assert "INSUFFICIENT_HISTORY" in row(data, 69).values[name].reason_codes
    assert row(data, 99).values["sma_100"].value == 149.5
    assert "INSUFFICIENT_HISTORY" in row(data, 99).values["sma_200"].reason_codes
    assert row(data, 199).values["sma_200"].value == 199.5
    assert row(data, 204).values["sma_100"].value == 254.5
    assert row(data, 204).values["sma_200"].value == 204.5
    assert row(data, 204).values["distance_sma_200"].value == pytest.approx(304 / 204.5 - 1)


def test_context_and_historical_cross_section(history: CanonicalBatch) -> None:
    data = build(CanonicalReader(history), plan(20, 34, 54, 55, 69))
    assert row(data, 20).values["relative_return_20"].value == 0
    assert row(data, 20).values["market_return_20"].value == pytest.approx(0.2)
    assert row(data, 20, "TEST:BETA").values["momentum_percentile_20"].value == 1
    assert row(data, 20).values["momentum_percentile_20"].value == 0.25
    assert all(r.security_id != "TEST:NEW" for r in data.rows if r.session_date < day(35))
    assert not row(data, 55, "TEST:DEPART").analytical_eligible
    assert row(data, 55, "TEST:DEPART").values["sma_5"].value is None
    assert row(data, 54, "TEST:DEPART").analytical_eligible


def test_future_price_changes_never_change_earlier_features(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    changed = build_history(
        tmp_path,
        length=37,
        overrides={
            (35, "TEST:ALPHA"): {"close": "200", "high": "202"},
            (36, "TEST:BETA"): {"close": "300", "high": "302"},
        },
    )[0]
    earlier = plan(4, 14, 20, 34)
    a, b = build(CanonicalReader(history), earlier), build(CanonicalReader(changed), earlier)
    assert [(r.security_id, r.session_date, r.values, r.analytical_eligible) for r in a.rows] == [
        (r.security_id, r.session_date, r.values, r.analytical_eligible) for r in b.rows
    ]
    assert (
        a.feature_set_id != b.feature_set_id
    )  # New input identity, unchanged earlier numerical values.


def test_revision_after_cutoff_is_invisible(history: CanonicalBatch, tmp_path: Path) -> None:
    changed = build_history(tmp_path, length=47, revision=(10, 45, "120"))[0]
    before = build(CanonicalReader(changed), plan(20))
    original = build(CanonicalReader(history), plan(20))
    assert row(before, 20).values == row(original, 20).values
    after = build(CanonicalReader(changed), plan(46))
    assert (
        row(after, 46).values["ema_26"].value
        != row(build(CanonicalReader(history), plan(46)), 46).values["ema_26"].value
    )


def test_later_symbols_and_current_changes_do_not_rewrite_past(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    old = next(
        r
        for r in history.revisions
        if isinstance(r, IdentityRevision) and r.security_id == "TEST:ALPHA"
    )
    fact = old.fact.model_copy(
        update=dict(
            revision_id="r2",
            supersedes_revision_id="r1",
            symbol="TEST_FUTURE_SYMBOL",
            provenance=old.provenance.model_copy(update={"available_at": instant(60)}),
        )
    )
    new = old.model_copy(
        update=dict(
            revision_id="r2",
            revision_number=2,
            supersedes_revision_id="r1",
            provenance=fact.provenance,
            fact=fact,
        )
    )
    changed = revised_reference(history, new, tmp_path)
    frozen = build(CanonicalReader(history), plan(20, 34))
    payload = frozen.to_bytes()
    fresh = build(CanonicalReader(changed), plan(20, 34))
    assert [r.values for r in frozen.rows] == [r.values for r in fresh.rows]
    assert frozen.to_bytes() == payload
    current = history.definition.model_copy(update={"evidence_scope": "CURRENT_SNAPSHOT_ONLY"})
    with pytest.raises(DataContractError, match="CURRENT_SNAPSHOT"):
        build(CanonicalReader(history.model_copy(update={"definition": current})), plan(20))


def test_late_action_evidence_requires_new_pin(history: CanonicalBatch, tmp_path: Path) -> None:
    old = next(r for r in history.revisions if isinstance(r, IdentityRevision))
    action = ActionRevision(
        logical_record_id="TEST_ONLY_SPLIT",
        revision_id="r1",
        revision_number=1,
        security_id="TEST:ALPHA",
        effective_from=day(15),
        ex_date=day(15),
        corporate_action_id="TEST_ONLY_SPLIT",
        event_type="SPLIT",
        provenance=old.provenance.model_copy(update={"available_at": instant(40)}),
    )
    changed = revised_reference(history, action, tmp_path)
    early, later = (
        build(CanonicalReader(changed), plan(20)),
        build(CanonicalReader(changed), plan(41)),
    )
    assert row(early, 20).values == row(build(CanonicalReader(history), plan(20)), 20).values
    assert "CORPORATE_ACTION_UNADJUSTED" in row(later, 41).values["ema_26"].reason_codes
    assert early.feature_set_id != later.feature_set_id
    assert row(early, 20).price_basis == "UNADJUSTED"


def test_rejected_missing_and_degraded_history_are_not_shortened(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    bad = build_history(
        tmp_path,
        length=25,
        overrides={(18, "TEST:ALPHA"): {"close": ""}, (20, "TEST:BETA"): {"volume": "0"}},
    )[0]
    data = build(CanonicalReader(bad), plan(20, 24))
    assert row(data, 20).values["sma_5"].value is None
    assert "UNUSABLE_LOOKBACK_OBSERVATION" in row(data, 20).values["sma_5"].reason_codes
    assert row(data, 24).values["sma_5"].value == 122
    assert row(data, 24).values["sma_20"].value is None
    assert row(data, 20, "TEST:BETA").values["sma_5"].state == "DEGRADED"
    strict = build(CanonicalReader(bad), plan(20, quality="VALID_ONLY"))
    assert row(strict, 20, "TEST:BETA").values["sma_5"].value is None


def test_deterministic_identity_parquet_manifest_and_no_scalers(history: CanonicalBatch) -> None:
    data = build(CanonicalReader(history), plan(20, 49))
    replay = build(CanonicalReader(history), plan(20, 49))
    assert data.to_bytes() == replay.to_bytes()
    assert parquet_bytes(data) == parquet_bytes(replay)
    table = pq.read_table(pa.BufferReader(parquet_bytes(data)))
    assert table.schema.field("sma_5").type == pa.float64()
    assert (
        table.schema.metadata
        and table.schema.metadata[b"feature_set_id"] == data.feature_set_id.encode()
    )
    assert manifest(data)["row_count"] == len(data.rows)
    assert (
        data.feature_set_id
        != build(CanonicalReader(history), plan(20, 49, quality="VALID_ONLY")).feature_set_id
    )
    assert (
        data.feature_set_id
        != build(CanonicalReader(history), plan(20, 49, benchmark=False)).feature_set_id
    )
    assert row(data, 49).values["volume_ratio_20"].value == pytest.approx(1490 / 1395)
    assert row(data, 49).values["volume_zscore_20"].value == pytest.approx(95 / math.sqrt(3500))
    assert not any("scaler" in d.feature_name for d in default_set(plan(20)).definitions)


def test_unknown_calendar_and_availability_fail_closed(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    from alphalens_data.canonical.models import SessionRevision

    session = next(
        r for r in history.revisions if isinstance(r, SessionRevision) and r.session_date == day(10)
    )
    changed = revised_reference(
        history, session.model_copy(update={"status": "UNKNOWN_SESSION_STATUS"}), tmp_path
    )
    assert row(build(CanonicalReader(changed), plan(20)), 20).values["sma_5"].value is None
    early = plan(20).model_copy(
        update={"decisions": (Decision(session_date=day(20), knowledge_cutoff=instant(20, 10)),)}
    )
    data = build(CanonicalReader(history), early)
    assert all(v.value is None for r in data.rows for v in r.values.values())


def test_cli_and_definition_boundary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            ["build", str(tmp_path / "missing.json"), "--plan", str(tmp_path / "missing-plan.json")]
        )
        == 2
    )
    assert "FEATURE_BUILD_FAILED" in capsys.readouterr().out
    assert "PRODUCTION" not in {
        r.value for r in (Classification.TEST_ONLY, Classification.RESEARCH_FIXTURE)
    }
    with pytest.raises(ValueError):
        plan(20).model_copy(update={"benchmark_evidence_reference": None}).model_validate(
            plan(20).model_dump() | {"benchmark_evidence_reference": None}
        )


def test_plan_rejects_naive_duplicate_or_future_order() -> None:
    with pytest.raises(ValueError):
        plan(20, 20)
    with pytest.raises(ValueError):
        plan(20, 10)
    with pytest.raises(ValueError):
        BuildPlan(
            history_start=START,
            decisions=(
                Decision(session_date=START, knowledge_cutoff=instant(0).replace(tzinfo=None)),
            ),
        )
    assert day(5) == START + timedelta(
        days=5
    )  # Artificial calendar ONLY; no real trading-day claim.


def test_nonlinear_macd_atr_and_zero_denominators() -> None:
    close = [100.0] * 33 + [113.0]
    assert calculate("macd", close, [], [], []) == pytest.approx(28 / 27)
    assert calculate("macd_signal", close, [], [], []) == pytest.approx(28 / 243)
    close = [100.0] * 15 + [110.0]
    assert calculate("atr_14", close, close, close, []) == pytest.approx(10 / 14)
    assert calculate("volume_ratio_20", [], [], [], [0.0] * 20) is None
    assert calculate("volume_zscore_20", [], [], [], [10.0] * 20) is None
    assert calculate("bollinger_location_20", [100.0] * 20, [], [], []) is None


def test_unknown_basis_and_production_are_never_upgraded(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    from alphalens_data.canonical.models import PriceRevision

    bar = next(
        r
        for r in history.revisions
        if isinstance(r, PriceRevision)
        and r.security_id == "TEST:ALPHA"
        and r.session_date == day(20)
    )
    changed = revised_reference(
        history, bar.model_copy(update={"price_basis": "OBSERVED_UNKNOWN_BASIS"}), tmp_path
    )
    data = build(CanonicalReader(changed), plan(20))
    assert "PRICE_BASIS_UNKNOWN_OR_MIXED" in row(data, 20).values["return_1"].reason_codes
    with pytest.raises(ValueError, match="classification"):
        FeatureDataset.model_validate(data.model_dump() | {"classification": "PRODUCTION"})


def test_current_membership_correction_is_hidden_before_knowledge(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    from alphalens_data.canonical.models import MembershipRevision

    old = next(
        r
        for r in history.revisions
        if isinstance(r, MembershipRevision) and r.security_id == "TEST:ALPHA"
    )
    fact = old.fact.model_copy(
        update=dict(
            revision_id="r2",
            supersedes_revision_id="r1",
            security_type=SecurityType.ETF,
            provenance=old.provenance.model_copy(update={"available_at": instant(60)}),
        )
    )
    new = old.model_copy(
        update=dict(
            revision_id="r2",
            revision_number=2,
            supersedes_revision_id="r1",
            provenance=fact.provenance,
            fact=fact,
        )
    )
    changed = revised_reference(history, new, tmp_path)
    a, b = build(CanonicalReader(history), plan(20)), build(CanonicalReader(changed), plan(20))
    assert [(r.security_id, r.values, r.analytical_eligible) for r in a.rows] == [
        (r.security_id, r.values, r.analytical_eligible) for r in b.rows
    ]


def test_successful_cli_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    build_history(Path("data/src"), length=6)
    arguments = [
        "build",
        "data/src/canonical-input.json",
        "--plan",
        "data/src/feature-plan.json",
        "--output",
        "data/out",
    ]
    assert main(arguments) == 0
    first = capsys.readouterr().out
    assert main(arguments) == 0
    assert capsys.readouterr().out == first
    assert '"feature_count":41' in first
    assert '"classification":"TEST_ONLY"' in first
