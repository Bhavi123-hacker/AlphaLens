"""TEST_ONLY contract fixtures. No network, real market result or performance claim."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import PERMISSION, digest, encoded
from workers.experimental_nse_v2 import data as v2_data
from workers.experimental_nse_v2 import forward
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES, build
from workers.nse_market import daily, engine
from workers.providers.upstox import Reply

from alphalens_data.providers.multi_contracts import Instrument

AT = datetime(2025, 1, 4, 12, tzinfo=UTC)


def test_scheduler_view_requires_matching_immutable_approval_and_rejects_future_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "TEST_ONLY_market"
    folder = root / "operational"
    folder.mkdir(parents=True)
    saved = folder / "run.json"
    engine._checked(
        saved,
        {"state": "REPLAY", "policy": {"policy_sha256": "a" * 64, "expected_securities": 500}},
    )
    engine._pointer(root, "operational-latest.json", saved)
    engine._checked(
        folder / "collection-approval.json",
        {"policy_sha256": "a" * 64, "approved_by": "LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL"},
    )
    record = {
        "state": "REGISTERED_ENABLED_LAST_VERIFIED",
        "verified_at": datetime.now(UTC).isoformat(),
        "policy_sha256": "b" * 64,
        "fixed_scope": 500,
        "least_privilege": True,
        "interactive_token": True,
    }
    invalid = folder / "invalid.json"
    engine._checked(invalid, record)
    engine._pointer(root, "task-registration-latest.json", invalid)
    with pytest.raises(ValueError, match="APPROVAL_POLICY_MISMATCH"):
        engine._operations(root)
    record["policy_sha256"] = "a" * 64
    valid = folder / "valid.json"
    engine._checked(valid, record)
    engine._pointer(root, "task-registration-latest.json", valid)
    assert engine._operations(root)["scheduler"]["state"] == "REGISTERED_ENABLED_LAST_VERIFIED"
    record["verified_at"] = "2099-01-01T00:00:00+00:00"
    future = folder / "future.json"
    engine._checked(future, record)
    engine._pointer(root, "task-registration-latest.json", future)
    with pytest.raises(ValueError, match="VERIFICATION_TIME_REJECTED"):
        engine._operations(root)


def identity(number: int) -> Instrument:
    isin = f"INE{number:09d}"
    return Instrument(
        provider="upstox",
        provider_key="NSE_EQ|" + isin,
        exchange="NSE",
        segment="NSE_EQ",
        symbol=f"TEST_ONLY_{number}",
        isin=isin,
        series="EQ",
        instrument_type="EQ",
        observed_at=AT,
        identity_evidence="TEST_ONLY",
        revision_sha256="a" * 64,
    )


def observation(item: Instrument, day: str, index: int = 0) -> dict[str, Any]:
    return {
        "key": item.provider_key,
        "symbol": item.symbol,
        "isin": item.isin,
        "session": day,
        "open": str(100 + index),
        "high": str(110 + index),
        "low": str(99 + index),
        "close": str(105 + index),
        "volume": 1000 + index,
        "received_at": AT.isoformat(),
        "raw_sha256": "b" * 64,
    }


def fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "TEST_ONLY_private_market"
    items = [identity(i) for i in range(1, 5)]
    base = {
        "dataset_id": "c" * 64,
        "rows": [observation(items[0], "2025-01-02", 1), observation(items[1], "2025-01-02", 2)],
        "actions": {
            item.provider_key: {
                "state": "OBSERVED_ACTION_REFERENCE_NOT_EXHAUSTIVE",
                "hazard_dates": [],
                "unparsed_date_fields": 0,
            }
            for item in items[:2]
        },
        "identities": [item.model_dump(mode="json") for item in items[:2]],
        "source_observed_at": AT.isoformat(),
        "price_basis": "TEST_ONLY_SPLIT_BONUS_ADJUSTED",
    }
    monkeypatch.setattr(v2_data, "load_current", lambda unused: base)

    def clock() -> dict[str, Any]:
        return {
            "session_date": "2025-01-04",
            "lower_at": AT.isoformat(),
            "upper_at": AT.isoformat(),
        }

    monkeypatch.setattr(engine, "guard", clock)
    monkeypatch.setattr(daily, "guard", clock)
    engine.prepare(
        root,
        tmp_path / "TEST_ONLY_original_untouched",
        items,
        {"verified_common_equities": True, "evidence": "TEST_ONLY"},
        3,
    )
    return root


class Transport:
    def __init__(self, empty: bool = False, malformed: bool = False) -> None:
        self.calls = 0
        self.operations: list[str] = []
        self.empty = empty
        self.malformed = malformed

    def get(self, operation: str, **kwargs: Any) -> Reply:
        self.calls += 1
        self.operations.append(operation)
        body: dict[str, Any]
        if operation == "actions":
            body = {"status": "success", "data": []}
        elif operation == "timings":
            day = str(kwargs["end"])
            rows = []
            if day not in {"2025-01-04", "2025-01-05"}:
                rows = [
                    {
                        "exchange": "NSE",
                        "start_time": int(
                            datetime.fromisoformat(day + "T03:45:00+00:00").timestamp() * 1000
                        ),
                        "end_time": int(
                            datetime.fromisoformat(day + "T10:00:00+00:00").timestamp() * 1000
                        ),
                    }
                ]
            body = {"status": "success", "data": rows}
        else:
            day = str(kwargs["end"])
            candles = [] if self.empty else [[day + "T00:00:00+05:30", 110, 120, 109, 115, 1234, 0]]
            body = {"status": "success", "data": {"candles": [None] if self.malformed else candles}}
        return Reply(200, encoded(body), AT, "ACCEPTED")


def capture(root: Path, transport: Transport, maximum: int = 2) -> dict[str, Any]:
    return engine.capture(
        root,
        root / "TEST_ONLY_provider",
        max_new=1,
        max_requests=maximum,
        permission_reference=PERMISSION,
        meter=transport,
    )


def test_cohort_is_predeclared_deterministic_and_retains_original_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    plan = engine._pointed(root, "plan-latest.json")
    assert [i["symbol"] for i in plan["identities"]] == [
        "TEST_ONLY_1",
        "TEST_ONLY_2",
        "TEST_ONLY_3",
    ]
    assert plan["scheduled_collection_enabled"] is False
    assert plan["selection_policy"] == engine.SELECTION
    assert engine.coverage(root)["observations"] == 2
    original = (root / "seed.json").read_bytes()
    capture(root, Transport())
    assert (root / "seed.json").read_bytes() == original


def test_capture_replay_validates_source_and_uses_zero_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    transport = Transport()
    result = capture(root, transport)
    assert result["api_calls"] == 2 and transport.operations == ["candles", "actions"]
    assert result["validated_historical_securities"] == 3 and result["observations"] == 3
    second = Transport()
    assert capture(root, second)["api_calls"] == 0 and second.calls == 0
    path = root / "instruments" / str(identity(3).isin) / "candles.json"
    path.write_bytes(b"TEST_ONLY_TAMPERING")
    assert engine.coverage(root)["validated_historical_securities"] == 2
    assert engine.coverage(root)["not_observed"][0]["state"] == "REJECTED_SOURCE_EVIDENCE"


def test_interrupted_history_resumes_only_action_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    first = Transport()
    result = capture(root, first, maximum=1)
    assert result["api_calls"] == 1 and first.operations == ["candles"]
    raw = root / "instruments" / str(identity(3).isin) / "candles.json"
    original = raw.read_bytes()
    second = Transport()
    result = capture(root, second)
    assert result["newly_validated_securities"] == 1 and second.operations == ["actions"]
    assert raw.read_bytes() == original


def test_empty_and_malformed_history_are_distinct_and_not_filled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    result = capture(root, Transport(empty=True))
    assert result["observations"] == 2
    assert (
        result["not_observed"][0]["state"]
        == "EMPTY_HISTORY_PUBLICATION_OR_LISTING_COVERAGE_PENDING"
    )
    assert not list((root / "instruments").glob("*/completed.json"))
    assert list((root / "instruments").glob("*/history-attempts/*/candles.json"))
    later = Transport()
    assert capture(root, later)["newly_validated_securities"] == 1
    assert later.operations == ["candles", "actions"]
    root2 = fixture(tmp_path / "TEST_ONLY_other", monkeypatch)
    result2 = capture(root2, Transport(malformed=True))
    assert result2["observations"] == 2 and result2["failures"]
    assert result2["not_observed"][0]["state"] == "REJECTED_SOURCE_EVIDENCE"


@pytest.mark.parametrize("maximum", [0, -1, 601, True])
def test_invalid_request_budget_rejected_before_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, maximum: int
) -> None:
    root = fixture(tmp_path, monkeypatch)
    transport = Transport()
    with pytest.raises(ValueError, match="BOUNDED_REQUEST"):
        capture(root, transport, maximum)
    assert transport.calls == 0


def test_daily_dry_run_has_zero_requests_and_no_forecasts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        permission_reference=PERMISSION,
    )
    assert result["state"] == "DRY_RUN" and result["api_calls"] == 0
    assert result["pending_securities"] == 3
    assert not (root / "expanded-forecasts").exists()


def test_daily_published_capture_then_zero_get_replay_and_no_backdating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    transport = Transport()
    monkeypatch.setattr(engine, "Meter", lambda *args: transport)
    monkeypatch.setattr(engine, "_score", lambda *args: {"state": "TEST_ONLY", "new_forecasts": 0})
    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        max_stocks=3,
        collect=True,
        permission_reference=PERMISSION,
    )
    assert result["new_daily_observations"] == 3 and transport.operations.count("candles") == 3
    before = transport.calls
    replay = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        max_stocks=3,
        collect=True,
        permission_reference=PERMISSION,
    )
    assert replay["state"] == "REPLAY" and replay["api_calls"] == 0
    assert transport.calls == before
    assert not (root / "TEST_ONLY_v2").exists()


def test_publication_pending_does_not_freeze_empty_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    transport = Transport(empty=True)
    monkeypatch.setattr(engine, "Meter", lambda *args: transport)
    result = daily.run(
        root,
        root / "TEST_ONLY_provider",
        root / "TEST_ONLY_v2",
        session=date(2025, 1, 3),
        max_stocks=1,
        collect=True,
        permission_reference=PERMISSION,
    )
    assert result["state"] == "PARTIAL_OR_PUBLICATION_PENDING"
    assert result["new_daily_observations"] == 0
    assert not list((root / "daily").glob("*/INE*/record.json"))
    attempts = list((root / "daily").glob("*/INE*/publication-attempts/*.json"))
    assert len(attempts) == 1
    attempt = engine._read(attempts[0])
    assert attempt["completed_capture"] is False
    assert digest(bytes.fromhex(attempt["raw_hex"])) == attempt["raw_sha256"]
    assert engine.snapshot(root)["sessions"] == ["2025-01-02"]


def test_future_daily_date_rejected_before_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="NONFUTURE_SESSION"):
        daily.run(
            root,
            root / "TEST_ONLY_provider",
            root / "TEST_ONLY_v2",
            session=date(2025, 1, 5),
            collect=True,
            permission_reference=PERMISSION,
        )


def test_same_price_only_features_across_expansion_and_no_lookahead() -> None:
    first, second = identity(1), identity(2)
    days = [str(date(2024, 1, 1) + timedelta(days=index)) for index in range(66)]
    rows = [observation(first, day, index) for index, day in enumerate(days)]
    single = build(rows, days, include_context=False)
    broader = build(
        rows + [observation(second, day, 2 * index) for index, day in enumerate(days)],
        days,
        include_context=False,
    )
    before = next(
        item
        for item in single.samples
        if item.key == first.provider_key and item.session == days[60]
    )
    after = next(
        item
        for item in broader.samples
        if item.key == first.provider_key and item.session == days[60]
    )
    assert before.vector == after.vector and len(after.vector) == len(LOCAL_FEATURE_NAMES)
    changed = [dict(row) for row in rows]
    changed[-1].update(open="800", high="900", low="700", close="850")
    revised = build(changed, days, include_context=False)
    assert before.vector == next(
        item.vector for item in revised.samples if item.session == days[60]
    )
    missing = build(
        [row for row in rows if row["session"] != days[-1]], days, include_context=False
    )
    assert not any(item.session == days[-1] for item in missing.samples)
    excluded = build(rows, days, {first.provider_key: [days[-3]]}, include_context=False)
    assert not any(item.session == days[-1] for item in excluded.samples)


def test_checked_evidence_rejects_changes_without_overwriting(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY.json"
    engine._checked(path, {"value": "TEST_ONLY"})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        engine._checked(path, {"value": "CHANGED_TEST_ONLY"})
    assert path.read_bytes() == before
    path.write_bytes(encoded({"value": "TAMPERED_TEST_ONLY"}))
    assert digest(path.read_bytes()) != digest(before)
    with pytest.raises(ValueError, match="CHECKSUM"):
        engine._read(path)


@pytest.mark.parametrize("status", [401, 403, 429, 0])
def test_failed_actions_remain_retryable_without_redownloading_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    root = fixture(tmp_path, monkeypatch)

    class Denied(Transport):
        def get(self, operation: str, **kwargs: Any) -> Reply:
            result = super().get(operation, **kwargs)
            return (
                Reply(status, b"TEST_ONLY_NOT_RETAINED", AT, "TEST_ONLY_DENIED")
                if operation == "actions"
                else result
            )

    failed = capture(root, Denied())
    assert failed["newly_validated_securities"] == 0
    folder = root / "instruments" / str(identity(3).isin)
    assert not (folder / "completed.json").exists() and not (folder / "actions.json").exists()
    assert len(list((folder / "action-attempts").glob("*.json"))) == 1
    retry = Transport()
    assert capture(root, retry)["newly_validated_securities"] == 1
    assert retry.operations == ["actions"]


def test_normalized_cache_keeps_raw_validation_and_exact_frozen_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    capture(root, Transport())
    folder = root / "instruments" / str(identity(3).isin)
    original = engine._rows(folder, identity(3))
    assert engine.materialize(root)["api_calls"] == 0
    assert engine._rows(folder, identity(3)) == original
    (folder / "normalized.json.gz").write_bytes(b"TEST_ONLY_TAMPERED")
    with pytest.raises(ValueError, match="NORMALIZATION_CACHE_LINEAGE"):
        engine._rows(folder, identity(3))


def test_symbol_changes_keep_rows_and_refuse_incompatible_frozen_vectors() -> None:
    item = identity(1)
    days = [str(date(2024, 1, 1) + timedelta(days=index)) for index in range(61)]
    rows = [observation(item, day, index) for index, day in enumerate(days)]
    rows[-1]["symbol"] = "TEST_ONLY_NEW_DATED_SYMBOL"
    original = [dict(row) for row in rows]
    selected, _, features = engine._latest_features(
        {"rows": rows, "sessions": days, "quality": {"excluded_sessions": {}}}
    )
    assert selected == [] and features.samples == ()
    assert (
        features.exclusions[0]["reason"]
        == "DATED_SYMBOL_CHANGE_REQUIRES_FROZEN_MODEL_COMPATIBILITY_REVIEW"
    )
    assert rows == original


def test_reconciliation_keeps_seed_session_link_and_rejects_same_day_outcomes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, monkeypatch)
    folder = root / "expanded-forecasts" / "TEST_ONLY"
    folder.mkdir(parents=True)
    body = {
        "model_id": "TEST_ONLY",
        "key": identity(1).provider_key,
        "session": "2025-01-02",
        "recorded_at": AT.isoformat(),
    }
    with forward._connection(folder, write=True) as connection:
        connection.execute(
            "INSERT INTO experimental_forecasts VALUES(?,?,?,?,?,?)",
            (
                forward._hash(body),
                "TEST_ONLY",
                body["key"],
                body["session"],
                body["recorded_at"],
                forward._encode(body),
            ),
        )
    frame = {
        "rows": [
            observation(identity(1), "2025-01-02"),
            observation(identity(1), "2025-01-04"),
            observation(identity(2), "2025-01-02"),
        ],
        "sessions": ["2025-01-02", "2025-01-04"],
        "source_observed_at": AT.isoformat(),
        "quality": {"excluded_sessions": {}},
    }
    original_read = engine._read
    seed = {
        "session_timing": {"session": "2025-01-02"},
        "next_session_timing": {
            "session": "2025-01-03",
            "open_at": "2025-01-03T03:45:00+00:00",
            "closed_dates": [],
        },
    }
    monkeypatch.setattr(
        engine, "_read", lambda path: seed if path.name == "seed.json" else original_read(path)
    )

    def checked_reconcile(
        folder: Path, rows: list[dict[str, Any]], sessions: list[str], **kwargs: Any
    ) -> dict[str, int]:
        assert [row["session"] for row in rows] == ["2025-01-02"]
        assert {row["key"] for row in rows} == {identity(1).provider_key}
        assert sessions == frame["sessions"]
        assert kwargs["official_timings"]["2025-01-02"]["next_verified_session"] == "2025-01-03"
        assert kwargs["require_official_sessions"] is True
        return {"pending": 1}

    monkeypatch.setattr(forward, "reconcile", checked_reconcile)
    assert daily.reconcile(root, frame)["pending"] == 1
