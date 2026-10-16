"""TEST_ONLY provider contracts and retained replay; no real prices or network calls."""

import copy
import gzip
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import digest, encoded
from workers.experimental_nse_v2 import data
from workers.providers import upstox
from workers.providers.store import ProviderStore

from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_contracts import Instrument

AT = datetime(2025, 1, 2, 12, tzinfo=UTC)
KEY = "NSE_EQ|INE002A01018"


def reply(value: Any, *, status: int = 200) -> upstox.Reply:
    return upstox.Reply(status, encoded(value), AT, "ACCEPTED")


def action_reference(events: list[Any]) -> dict[str, Any]:
    return data.action_facts(reply({"status": "success", "data": events}))


def row(day: str, key: str = KEY) -> dict[str, Any]:
    return {
        "key": key,
        "symbol": "TEST_ONLY",
        "isin": key.split("|")[1],
        "session": day,
        "open": "100",
        "high": "110",
        "low": "99",
        "close": "105",
        "volume": 1000,
        "received_at": AT.isoformat(),
    }


def test_action_metadata_preserves_uncertainty_and_all_declared_date_hazards() -> None:
    facts = action_reference(
        [
            {
                "name": "TEST_ONLY_DIVIDEND",
                "expiry_date": "2025-01-02",
                "event_details": [
                    {"name": "Announcement Date", "value": "01-Jan-2025"},
                    {"name": "Record Date", "value": "03 January 2025"},
                    {"name": "Amount", "value": "TEST_ONLY_NOT_A_DATE"},
                ],
            }
        ]
    )
    assert facts["hazard_dates"] == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert facts["complete"] is False and facts["raw_retained"] is False
    assert facts["unparsed_date_fields"] == 0
    assert "TEST_ONLY_DIVIDEND" not in encoded(facts).decode()
    # An empty returned list is still not exhaustive historical evidence.
    assert action_reference([])["complete"] is False


@pytest.mark.parametrize("events", [[None], [{"event_details": [None]}], [{"event_details": {}}]])
def test_malformed_action_reference_excludes_observations(events: list[Any]) -> None:
    facts = action_reference(events)
    assert facts["state"] == "ACTION_SCHEMA_UNAVAILABLE"
    result = data.quality([row("2025-01-02")], {KEY: facts})
    assert result["excluded_sessions"][KEY] == ["2025-01-02"]


def test_unparsed_action_date_rejects_eligibility_instead_of_guessing() -> None:
    facts = action_reference([{"expiry_date": "not-a-date"}])
    assert facts["unparsed_date_fields"] == 1
    assert data.quality([row("2025-01-02")], {KEY: facts})["excluded_sessions"][KEY] == [
        "2025-01-02"
    ]


def test_quality_rejects_duplicate_slots_and_quarantines_cross_security_copies() -> None:
    original = row("2025-01-02")
    with pytest.raises(ValueError, match="DUPLICATE_SECURITY_SESSION"):
        data.quality([original, original.copy()], {})
    other = row("2025-01-02", "NSE_EQ|INE000000001")
    facts = action_reference([])
    result = data.quality([original, other], {KEY: facts, other["key"]: facts})
    assert result["cross_security_identical_ohlcv_groups"] == 1
    assert result["excluded_sessions"] == {
        KEY: ["2025-01-02"],
        other["key"]: ["2025-01-02"],
    }
    assert result["official_calendar_complete"] is False


def timing(day: str) -> bytes:
    return encoded(
        {
            "status": "success",
            "data": [
                {
                    "exchange": "NSE",
                    "start_time": datetime.fromisoformat(day + "T03:45:00+00:00").timestamp()
                    * 1000,
                    "end_time": datetime.fromisoformat(day + "T10:00:00+00:00").timestamp() * 1000,
                }
            ],
        }
    )


@pytest.mark.parametrize(
    "body", [[], {"status": "success", "data": [None]}, {"status": "success", "data": [{}]}]
)
def test_malformed_timing_is_never_relabelled_as_closed(body: Any) -> None:
    with pytest.raises(ValueError, match="TIMING_UNAVAILABLE"):
        data.timing_fact(reply(body), date(2025, 1, 2))


def test_official_timing_distinguishes_absence_date_and_publication() -> None:
    assert data.timing_fact(reply({"status": "success", "data": []}), date(2025, 1, 2)) is None
    actual = data.timing_fact(
        upstox.Reply(200, timing("2025-01-02"), AT, "ACCEPTED"), date(2025, 1, 2)
    )
    assert actual and actual["open_at"] == "2025-01-02T03:45:00+00:00"
    assert "official_final_close_verified" not in actual
    with pytest.raises(DataContractError, match="DATE_REJECTED"):
        data.timing_fact(upstox.Reply(200, timing("2025-01-02"), AT, "ACCEPTED"), date(2025, 1, 3))


def current_fixture(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    evidence = root / "current-raw"
    evidence.mkdir()
    master = gzip.compress(
        encoded(
            [
                {
                    "segment": "NSE_EQ",
                    "exchange": "NSE",
                    "instrument_type": "EQ",
                    "instrument_key": KEY,
                    "isin": KEY.split("|")[1],
                    "trading_symbol": "TEST_ONLY",
                }
            ]
        )
    )
    identities, _ = upstox.instrument_master(
        upstox.Reply(200, master, AT, "ACCEPTED"), require_reliance=False
    )
    identity = identities[0]
    raw = encoded(
        {
            "status": "success",
            "data": {"candles": [["2025-01-02T00:00:00+05:30", 100, 110, 99, 105, 1000, 0]]},
        }
    )
    (evidence / "master.json.gz").write_bytes(master)
    filename = str(identity.isin) + ".json"
    (evidence / filename).write_bytes(raw)
    facts: dict[str, dict[str, Any]] = {}
    receipts = {}
    for day in ("2025-01-02", "2025-01-03"):
        body = timing(day)
        (evidence / (day + ".json")).write_bytes(body)
        receipts[day] = {"sha256": digest(body), "received_at": AT.isoformat()}
        fact = data.timing_fact(upstox.Reply(200, body, AT, "ACCEPTED"), date.fromisoformat(day))
        assert fact is not None
        facts[day] = fact
    parent: dict[str, Any] = {
        "dataset_id": "TEST_ONLY_PARENT",
        "rows": [row("2025-01-01")],
        "sessions": ["2025-01-01"],
        "identities": [identity.model_dump(mode="json")],
        "actions": {KEY: action_reference([])},
    }
    monkeypatch.setattr(data, "load", lambda path: copy.deepcopy(parent))
    rows = [*parent["rows"], *data.normalized(raw, identity, AT)]
    return {
        "parent_dataset_id": parent["dataset_id"],
        "rows": rows,
        "sessions": ["2025-01-01", "2025-01-02"],
        "identities": parent["identities"],
        "actions": parent["actions"],
        "quality": data.quality(rows, parent["actions"]),
        "source_observed_at": AT.isoformat(),
        "session_timing": facts["2025-01-02"],
        "next_session_timing": {
            **facts["2025-01-03"],
            "previous_session": "2025-01-02",
            "intervening_dates_verified_closed": True,
            "closed_dates": [],
        },
        "timing_receipts": receipts,
        "current_receipts": [
            {
                "filename": filename,
                "sha256": digest(raw),
                "received_at": AT.isoformat(),
                "identity": identity.model_dump(mode="json"),
            }
        ],
        "current_master_sha256": digest(master),
        "current_master_received_at": AT.isoformat(),
    }


def seal(root: Path, value: dict[str, Any]) -> None:
    value.pop("dataset_id", None)
    value["dataset_id"] = digest(encoded(value))
    body = encoded(value)
    (root / "current.json").write_bytes(body)
    (root / "current.sha256").write_text(digest(body))


def test_current_retained_replay_is_zero_transport_and_rejects_raw_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = current_fixture(tmp_path, monkeypatch)
    seal(tmp_path, value)
    monkeypatch.setattr(
        upstox.UpstoxClient,
        "get",
        lambda *args, **kwargs: pytest.fail("Replay must not call provider"),
    )
    assert data.load_current(tmp_path)["rows"] == value["rows"]
    target = tmp_path / "current-raw" / value["current_receipts"][0]["filename"]
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="RAW_CHECKSUM"):
        data.load_current(tmp_path)


@pytest.mark.parametrize("change", ["same_next_day", "closed_flag_false", "wrong_source_receipt"])
def test_current_replay_rejects_forged_chronology_even_with_recomputed_outer_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    value = current_fixture(tmp_path, monkeypatch)
    if change == "same_next_day":
        value["next_session_timing"]["session"] = value["session_timing"]["session"]
    elif change == "closed_flag_false":
        value["next_session_timing"]["intervening_dates_verified_closed"] = False
    else:
        value["source_observed_at"] = "2025-01-02T11:00:00+00:00"
    seal(tmp_path, value)
    with pytest.raises(ValueError, match="CHAIN_REJECTED|NORMALIZATION_REPLAY_CHANGED"):
        data.load_current(tmp_path)


def test_current_day_transport_is_exact_single_key_bounded_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderStore(tmp_path / "TEST_ONLY_provider")
    store.initialize()
    paths = []

    class Response:
        status = 200

        def getheader(self, *args: Any) -> str:
            return "0"

        def read(self, *args: Any) -> bytes:
            return b'{"status":"success","data":{"candles":[]}}'

    class Connection:
        def __init__(self, host: str, **kwargs: Any) -> None:
            assert host == "api.upstox.com"

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            assert method == "GET"
            assert "TEST_ONLY_SECRET" not in path
            paths.append(path)

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            return None

    monkeypatch.setattr(upstox, "HTTPSConnection", Connection)
    monkeypatch.setattr(upstox, "load_token", lambda: "TEST_ONLY_SECRET")
    client = upstox.UpstoxClient(store, budget=1)
    assert client.get("intraday_candles", key=KEY).state == "ACCEPTED"
    assert paths == ["/v3/historical-candle/intraday/NSE_EQ%7CINE002A01018/days/1"]
    for kwargs in (
        {"start": date(2025, 1, 1)},
        {"end": date(2025, 1, 2)},
        {"keys": (KEY,)},
        {"key": "BSE_EQ|INE002A01018"},
    ):
        with pytest.raises(DataContractError):
            client.get("intraday_candles", **kwargs)
    assert client.calls == 1


def test_naive_source_receipt_is_not_silently_interpreted() -> None:
    identity = Instrument(
        provider="upstox",
        provider_key=KEY,
        exchange="NSE",
        segment="NSE_EQ",
        symbol="TEST_ONLY",
        isin=KEY.split("|")[1],
        observed_at=AT,
        revision_sha256="a" * 64,
        identity_evidence="TEST_ONLY",
    )
    with pytest.raises(ValueError, match="AWARE_SOURCE_RECEIPT"):
        data.normalized(b"{}", identity, AT.replace(tzinfo=None))


def future_capture_transport(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    published: bool,
    capture_day: str = "2025-01-03",
) -> list[str]:
    calls: list[str] = []
    at = datetime.fromisoformat(capture_day + "T12:00:00+00:00")
    monkeypatch.setattr(data, "initialize", lambda path: None)
    monkeypatch.setattr(
        data, "guard", lambda: {"session_date": capture_day, "lower_at": at.isoformat()}
    )
    master = (root / "current-raw/master.json.gz").read_bytes()

    class Client:
        def __init__(self, store: ProviderStore, *, budget: int, retries: int) -> None:
            assert budget in (50, 60) and retries == 0
            self.calls = 0

        def get(self, operation: str, **kwargs: Any) -> upstox.Reply:
            self.calls += 1
            calls.append(operation)
            if operation == "instruments":
                return upstox.Reply(200, master, at, "ACCEPTED")
            if operation == "timings":
                day = str(kwargs["end"])
                raw = (
                    encoded({"status": "success", "data": []})
                    if day in ("2025-01-04", "2025-01-05")
                    else timing(day)
                )
            elif operation == "actions":
                raw = encoded({"status": "success", "data": []})
            else:
                assert operation == "intraday_candles" and kwargs["key"] == KEY
                candles = (
                    [[capture_day + "T00:00:00+05:30", 100, 110, 99, 106, 1001, 0]]
                    if published
                    else []
                )
                raw = encoded({"status": "success", "data": {"candles": candles}})
            return upstox.Reply(200, raw, at, "ACCEPTED")

    monkeypatch.setattr(data, "UpstoxClient", Client)
    return calls


def test_new_day_appends_immutable_capture_chain_and_same_day_replay_has_zero_gets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = current_fixture(tmp_path, monkeypatch)
    seal(tmp_path, previous)
    old_bytes = (tmp_path / "current.json").read_bytes()
    calls = future_capture_transport(tmp_path, monkeypatch, published=True)
    updated = data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")
    assert len(updated["rows"]) == 3 and updated["sessions"][-1] == "2025-01-03"
    assert updated["base_dataset_id"] == "TEST_ONLY_PARENT"
    assert updated["parent_dataset_id"] == previous["dataset_id"]
    assert updated["parent_capture_id"] == "LEGACY_CURRENT"
    assert updated["current_api_calls"] == len(calls) == 7
    assert (tmp_path / "current.json").read_bytes() == old_bytes
    count = len(calls)
    assert (
        data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")["dataset_id"]
        == updated["dataset_id"]
    )
    assert len(calls) == count
    facts = data.collected_timings(tmp_path)
    assert set(facts) == {"2025-01-02", "2025-01-03", "2025-01-06"}
    assert facts["2025-01-02"]["source"] == "UPSTOX_OFFICIAL_MARKET_TIMINGS"
    assert facts["2025-01-02"]["next_verified_session"] == "2025-01-03"
    assert facts["2025-01-03"]["next_verified_session"] == "2025-01-06"
    assert facts["2025-01-03"]["verified_closed_dates"] == ["2025-01-04", "2025-01-05"]
    previous_capture_id = updated["capture_id"]
    prior_dataset_id = updated["dataset_id"]
    future_capture_transport(tmp_path, monkeypatch, published=True, capture_day="2025-01-06")
    following = data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")
    assert following["parent_capture_id"] == previous_capture_id
    assert following["parent_dataset_id"] == prior_dataset_id
    assert following["base_dataset_id"] == "TEST_ONLY_PARENT"
    assert following["sessions"] == ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06"]
    assert set(data.collected_timings(tmp_path)) == {
        "2025-01-02",
        "2025-01-03",
        "2025-01-06",
        "2025-01-07",
    }
    assert data.collected_timings(tmp_path)["2025-01-06"]["next_verified_session"] == "2025-01-07"


def test_newer_action_reference_cannot_erase_a_previously_observed_hazard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = current_fixture(tmp_path, monkeypatch)
    previous["actions"][KEY]["hazard_dates"] = ["2025-01-01"]
    previous["quality"] = data.quality(previous["rows"], previous["actions"])
    seal(tmp_path, previous)
    future_capture_transport(tmp_path, monkeypatch, published=True)
    actual = data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")
    assert actual["actions"][KEY]["hazard_dates"] == ["2025-01-01"]
    assert actual["actions"][KEY]["includes_previous_capture_hazards"] is True


def test_pending_publication_does_not_freeze_an_empty_dataset_or_prevent_later_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = current_fixture(tmp_path, monkeypatch)
    seal(tmp_path, previous)
    calls = future_capture_transport(tmp_path, monkeypatch, published=False)
    pending = data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")
    assert pending["dataset_id"] == previous["dataset_id"]
    assert pending["collection_pending"]["new_observations"] == 0
    assert not (tmp_path / "current-latest.json").exists()
    assert len(calls) == 7
    assert len(list((tmp_path / "captures").glob("*/pending.json"))) == 1
    calls = future_capture_transport(tmp_path, monkeypatch, published=True)
    result = data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")
    assert result["sessions"][-1] == "2025-01-03" and len(calls) == 7


@pytest.mark.parametrize("change", ["parent_hash", "cycle", "base"])
def test_capture_parent_chain_rejects_tampering_cycles_and_unrelated_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    previous = current_fixture(tmp_path, monkeypatch)
    seal(tmp_path, previous)
    future_capture_transport(tmp_path, monkeypatch, published=True)
    actual = data.closed_current(tmp_path, tmp_path / "TEST_ONLY_provider")
    folder = tmp_path / "captures" / actual["capture_id"]
    if change == "parent_hash":
        actual["parent_capture_sha256"] = "0" * 64
    elif change == "cycle":
        actual["parent_capture_id"] = actual["capture_id"]
    else:
        actual["base_dataset_id"] = "TEST_ONLY_UNRELATED"
    seal(folder, actual)
    (tmp_path / "current-latest.json").write_bytes(
        encoded(
            {
                "capture_id": actual["capture_id"],
                "sha256": digest((folder / "current.json").read_bytes()),
            }
        )
    )
    with pytest.raises(ValueError, match="PARENT_HASH|CYCLE_OR_HASH|BASE_OR_ID"):
        data.load_current(tmp_path)
