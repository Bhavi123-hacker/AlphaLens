"""TEST_ONLY adversarial clock packets and prices; no real market observations."""

import json
import struct
import time
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from test_p31_terminal import AT, identity, payload
from workers.providers import quote_clock as clock
from workers.providers import upstox
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply
from workers.providers.upstox_terminal import display_quote, quote


def calibration(mono: float = 1000) -> clock.Calibration:
    rows = tuple(
        clock.Sample(source, AT, mono, 0.18, 0.22, 0.04)
        for source in clock.SOURCES
        for _ in range(3)
    )
    return clock.combine(rows, AT, mono)


def observation(**values: Any) -> Reply:
    mono = time.perf_counter()
    stamp = AT + timedelta(seconds=0.15)
    body = payload(
        timestamp=stamp.isoformat(),
        last_trade_time=str(int((stamp - timedelta(milliseconds=1)).timestamp() * 1000)),
        **values,
    )
    return Reply(
        200,
        body,
        AT,
        "ACCEPTED",
        clock_required=True,
        calibration=calibration(mono),
        received_monotonic=mono,
        precise_received_at=AT,
    )


def test_calibrated_receipt_accepts_before_lower_bound_and_preserves_raw_times() -> None:
    reply = observation()
    result = quote(reply, identity())
    assert result["state"] == "VALIDATED_SNAPSHOT"
    assert result["clock"]["local_received_at"] == AT.isoformat()
    assert result["raw_provider_timestamp"] == (AT + timedelta(seconds=0.15)).isoformat()
    assert result["snapshot_age_seconds_interval"] == [0.03, 0.07]
    assert reply.body == observation().body


def test_cached_quote_expires_without_mutating_receipt_or_leaking_stale_headline() -> None:
    accepted = quote(observation(), identity())
    expired = display_quote(accepted, 31)
    assert "ltp" not in expired and expired["state"] == "QUOTE_EVIDENCE_EXPIRED_REFRESH_REQUIRED"
    assert accepted["state"] == "VALIDATED_SNAPSHOT" and "ltp" in accepted
    assert expired["clock"] == accepted["clock"]


def test_expired_reply_cannot_be_replayed_into_new_acceptance() -> None:
    reply = observation()
    reply = replace(reply, received_monotonic=time.perf_counter() - 31)
    assert quote(reply, identity())["state"] == "QUOTE_CLOCK_EVIDENCE_REJECTED"


@pytest.mark.parametrize("offset", [0.180001, 0.20, 0.22, 0.3, 1, 100])
def test_future_or_ambiguous_quote_rejected_even_below_upper_bound(offset: float) -> None:
    reply = observation()
    body = json.loads(reply.body)
    body["data"]["NSE_EQ:" + identity().symbol]["timestamp"] = (
        AT + timedelta(seconds=offset)
    ).isoformat()
    result = quote(replace(reply, body=json.dumps(body).encode()), identity())
    assert result["state"] == "QUOTE_TIME_REJECTED" and "ltp" not in result


@pytest.mark.parametrize(
    "mutation",
    [
        {"calibration": None},
        {"received_monotonic": 1031},
        {"received_monotonic": 999},
        {"precise_received_at": AT + timedelta(seconds=1)},
        {"capture_span": 0.002},
    ],
)
def test_missing_stale_backward_or_discontinuous_clock_fails_closed(
    mutation: dict[str, Any],
) -> None:
    result = quote(replace(observation(), **mutation), identity())
    assert result["state"] == "QUOTE_CLOCK_EVIDENCE_REJECTED" and "ltp" not in result


@pytest.mark.parametrize(
    "changes",
    [
        {"timestamp": "malformed"},
        {"timestamp": AT.replace(tzinfo=None).isoformat()},
        {"timestamp": (AT - timedelta(seconds=31)).isoformat()},
        {"last_trade_time": str(int((AT + timedelta(seconds=1)).timestamp() * 1000))},
    ],
)
def test_stale_malformed_naive_and_trade_after_generation(changes: dict[str, Any]) -> None:
    reply = observation()
    body = json.loads(reply.body)
    body["data"]["NSE_EQ:" + identity().symbol].update(changes)
    result = quote(replace(reply, body=json.dumps(body).encode()), identity())
    assert result["state"] != "VALIDATED_SNAPSHOT" and "ltp" not in result


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "disagree", "nan", "slow", "reversed", "old"]
)
def test_independent_source_failures_rejected(fault: str) -> None:
    rows = list(calibration().samples)
    if fault == "missing":
        rows.pop()
    if fault == "duplicate":
        rows[-1] = replace(rows[-1], source=clock.SOURCES[0])
    if fault == "disagree":
        rows[-1] = replace(rows[-1], lower=0.5, upper=0.52)
    if fault == "nan":
        rows[0] = replace(rows[0], lower=float("nan"))
    if fault == "slow":
        rows[0] = replace(rows[0], rtt=0.2)
    if fault == "reversed":
        rows[0] = replace(rows[0], lower=0.3, upper=0.2)
    if fault == "old":
        rows[0] = replace(rows[0], monotonic=900)
    with pytest.raises(ValueError):
        clock.combine(tuple(rows), AT, 1000)


def packet() -> bytes:
    result = bytearray(48)
    result[0:4] = bytes([0x24, 2, 0, 236])
    result[24:32] = b"TESTONLY"
    seconds = int(AT.timestamp()) + clock.NTP_EPOCH
    result[32:40] = struct.pack("!II", seconds, 0)
    result[40:48] = struct.pack("!II", seconds, 0)
    return bytes(result)


def test_packet_interval_uses_full_delay_and_connected_origin_nonce() -> None:
    sample = clock.decode(packet(), b"TESTONLY", clock.SOURCES[0], AT, 1000, 0.02)
    assert sample.lower < 0 and sample.upper > 0.02
    with pytest.raises(ValueError):
        clock.decode(packet(), b"REPLAYED", clock.SOURCES[0], AT, 1000, 0.02)


@pytest.mark.parametrize("field,value", [(0, 0xE4), (0, 0x23), (1, 0), (1, 16), (3, 1)])
def test_leap_unsynchronized_kod_mode_stratum_precision_rejected(field: int, value: int) -> None:
    body = bytearray(packet())
    body[field] = value
    with pytest.raises(ValueError):
        clock.decode(bytes(body), b"TESTONLY", clock.SOURCES[0], AT, 1000, 0.02)


def test_no_clock_evidence_falls_back_to_original_local_validation_only_when_not_requested() -> (
    None
):
    reply = replace(observation(), clock_required=False, calibration=None)
    assert quote(reply, identity())["state"] == "QUOTE_TIME_REJECTED"


def test_failed_measurement_cools_down_without_silent_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(clock, "_attempted", float("-inf"))
    monkeypatch.setattr(clock, "_cached", None)
    calls = []

    def unavailable(source: str) -> tuple[clock.Sample, ...]:
        calls.append(source)
        raise OSError("TEST_ONLY unavailable")

    monkeypatch.setattr(clock, "probe", unavailable)
    assert clock.recent() is None
    first = len(calls)
    assert first > 0 and clock.recent() is None and len(calls) == first


def test_calibrated_transport_unavailable_never_loads_token_or_fetches_quote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(upstox, "recent", lambda: None)

    def forbidden() -> str:
        raise AssertionError("TEST_ONLY no protected credential access allowed")

    monkeypatch.setattr(upstox, "load_token", forbidden)
    client = upstox.UpstoxClient(ProviderStore(tmp_path / "not-initialized"), calibrate_quotes=True)
    result = client.get("quote")
    assert result.state == "CLOCK_CALIBRATION_UNAVAILABLE" and result.clock_required
    assert client.calls == 0 and result.body == b""


@pytest.mark.parametrize("timeouts,success,expected_reads", [(1, True, 4), (2, False, 2)])
def test_one_ntp_timeout_retry_keeps_three_valid_samples_and_strict_budget(
    monkeypatch: pytest.MonkeyPatch, timeouts: int, success: bool, expected_reads: int
) -> None:
    events: list[Any] = [TimeoutError() for _ in range(timeouts)] + [b"TEST_ONLY_PACKET"] * 3
    reads = []

    class Channel:
        def __enter__(self) -> "Channel":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def settimeout(self, value: float) -> None:
            assert value == 2

        def connect(self, address: Any) -> None:
            assert address == ("192.0.2.1", 123)

        def send(self, body: bytes) -> None:
            assert len(body) == 48

        def recv(self, size: int) -> bytes:
            reads.append(size)
            event = events.pop(0)
            if isinstance(event, TimeoutError):
                raise event
            return bytes(event)

    monkeypatch.setattr(
        "workers.providers.quote_clock.socket.getaddrinfo",
        lambda *args: [(0, 0, 0, "", ("192.0.2.1", 123))],
    )
    monkeypatch.setattr("workers.providers.quote_clock.socket.socket", lambda *args: Channel())
    monkeypatch.setattr("workers.providers.quote_clock.time.sleep", lambda _: None)
    monkeypatch.setattr(
        clock, "decode", lambda *args: clock.Sample(args[2], args[3], args[4], 0.18, 0.22, 0.01)
    )
    if success:
        assert len(clock.probe(clock.SOURCES[0])) == 3
    else:
        with pytest.raises(TimeoutError):
            clock.probe(clock.SOURCES[0])
    assert len(reads) == expected_reads


@pytest.mark.parametrize(
    "fault", ["short", "long", "root", "negative_root", "zero", "backward", "slow"]
)
def test_adversarial_packet_size_roots_server_chronology_and_latency(fault: str) -> None:
    body = bytearray(packet())
    elapsed = 0.02
    if fault == "short":
        body = body[:-1]
    if fault == "long":
        body.extend(b"TEST_ONLY_EXTENSION")
    if fault == "root":
        body[8:12] = struct.pack("!I", 65536)
    if fault == "negative_root":
        body[4:8] = struct.pack("!i", -65536)
    if fault == "zero":
        body[40:48] = bytes(8)
    if fault == "backward":
        body[40:48] = struct.pack("!II", int(AT.timestamp()) + clock.NTP_EPOCH - 1, 0)
    if fault == "slow":
        elapsed = 0.2
    with pytest.raises(ValueError):
        clock.decode(bytes(body), b"TESTONLY", clock.SOURCES[0], AT, 1000, elapsed)
