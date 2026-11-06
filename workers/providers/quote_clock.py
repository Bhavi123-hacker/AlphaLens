"""Bounded on-demand NTP evidence for private quote display, never OS clock setting.

Assumes independent configured providers and no common-path active NTP attacker.
NTP is unauthenticated. A quote must precede the LOWER receipt bound, not merely
fit beneath its upper bound. No use in retained ingestion, models or scheduling.
"""

import ctypes
import secrets
import socket
import statistics
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite
from typing import Any

SOURCES = ("time.windows.com", "time.google.com")
MAX_AGE = 30.0
DRIFT = 0.001  # Conservative 1000 ppm envelope, not an estimated time correction.
MAX_RTT = 0.100
MAX_WIDTH = 0.100
MAX_DISAGREEMENT = 0.020
NTP_EPOCH = 2_208_988_800
_lock = threading.Lock()


def precise_utc() -> datetime:
    """Read native precise UTC; Python 3.12 datetime.now on Windows is coarser."""
    if sys.platform == "win32":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        query = kernel.GetSystemTimePreciseAsFileTime
        query.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
        query.restype = None
        ticks = ctypes.c_uint64()
        query(ctypes.byref(ticks))
        return datetime(1601, 1, 1, tzinfo=UTC) + timedelta(microseconds=ticks.value // 10)
    return datetime.now(UTC)


@dataclass(frozen=True)
class Sample:
    source: str
    local: datetime
    monotonic: float
    lower: float
    upper: float
    rtt: float


@dataclass(frozen=True)
class Calibration:
    local: datetime
    monotonic: float
    lower: float
    upper: float
    samples: tuple[Sample, ...]

    def receipt(self, local: datetime, monotonic: float) -> dict[str, Any]:
        age = monotonic - self.monotonic
        elapsed_wall = (local - self.local).total_seconds()
        if (
            local.tzinfo is None
            or self.local.tzinfo is None
            or not all(isfinite(v) for v in (self.lower, self.upper))
            or not -2 <= self.lower <= self.upper <= 2
            or not isfinite(age)
            or not 0 <= age <= MAX_AGE
            or abs(elapsed_wall - age) > 0.005 + age * DRIFT
        ):
            raise ValueError("NTP_EVIDENCE_STALE_OR_LOCAL_CLOCK_DISCONTINUITY")
        # Project anchor UTC through monotonic elapsed time, never a mutated
        # provider/local timestamp. Include drift in both directions.
        lower = self.local + timedelta(seconds=self.lower + age * (1 - DRIFT))
        upper = self.local + timedelta(seconds=self.upper + age * (1 + DRIFT))
        if (upper - lower).total_seconds() > MAX_WIDTH:
            raise ValueError("NTP_RECEIPT_INTERVAL_TOO_WIDE")
        return {
            "state": "BOUNDED_INDEPENDENT_NTP_ASSUMPTION",
            "policy": "p34.quote-clock-interval.v1",
            "receipt_lower_at": lower.isoformat(),
            "receipt_upper_at": upper.isoformat(),
            "evidence_age_seconds": age,
            "maximum_evidence_age_seconds": MAX_AGE,
            "local_anchor_at": self.local.isoformat(),
            "offset_lower_seconds_at_anchor": self.lower,
            "offset_upper_seconds_at_anchor": self.upper,
            "sources": list(SOURCES),
            "samples": [
                {
                    "source": s.source,
                    "local_received_at": s.local.isoformat(),
                    "offset_lower_seconds": s.lower,
                    "offset_upper_seconds": s.upper,
                    "roundtrip_seconds": s.rtt,
                }
                for s in self.samples
            ],
            "authentication": "UNAUTHENTICATED_NTP_NOT_PRODUCTION_TIME_ATTESTATION",
            "network_assumption": "INDEPENDENT_SOURCES_NO_COMMON_PATH_ACTIVE_ATTACKER",
            "acceptance_bound": "LOWER_RECEIPT_BOUND_NO_FUTURE_TOLERANCE",
        }


def decode(
    packet: bytes, nonce: bytes, source: str, local: datetime, mono: float, elapsed: float
) -> Sample:
    """Validate a connected-socket response and derive an asymmetric-delay bound."""
    if (
        source not in SOURCES
        or len(packet) != 48
        or len(nonce) != 8
        or packet[24:32] != nonce
        or packet[0] >> 6 != 0
        or (packet[0] >> 3) & 7 not in {3, 4}
        or packet[0] & 7 != 4
        or not 1 <= packet[1] <= 15
        or not isfinite(elapsed)
        or not 0 < elapsed <= MAX_RTT
        or local.tzinfo is None
    ):
        raise ValueError("NTP_PACKET_REJECTED")
    root_delay = struct.unpack("!i", packet[4:8])[0] / 65536
    dispersion = struct.unpack("!I", packet[8:12])[0] / 65536
    precision = struct.unpack("!b", packet[3:4])[0]
    if not -40 <= precision <= -10 or root_delay < 0:
        raise ValueError("NTP_ROOT_OR_PRECISION_REJECTED")
    root_error = root_delay / 2 + dispersion + 2.0**precision
    if root_error > 0.050:
        raise ValueError("NTP_ROOT_UNCERTAINTY_REJECTED")

    def stamp(raw: bytes) -> float:
        seconds, fraction = struct.unpack("!II", raw)
        if seconds == 0:
            raise ValueError("NTP_ZERO_TIMESTAMP")
        return float(seconds - NTP_EPOCH + fraction / 2**32)

    receive, transmit = stamp(packet[32:40]), stamp(packet[40:48])
    processing = transmit - receive
    if not 0 <= processing <= elapsed:
        raise ValueError("NTP_SERVER_CHRONOLOGY_REJECTED")
    # At t4 true UTC >= t3 and <= t2 + full local elapsed. This does not
    # assume symmetric paths. Account for server root uncertainty and drift.
    lower = transmit - local.timestamp() - root_error - elapsed * DRIFT - 0.001
    upper = receive + elapsed - local.timestamp() + root_error + elapsed * DRIFT + 0.001
    if max(abs(lower), abs(upper)) > 2 or upper - lower > MAX_WIDTH:
        raise ValueError("NTP_OFFSET_OR_DISTANCE_REJECTED")
    return Sample(source, local, mono, lower, upper, elapsed - processing)


def probe(source: str) -> tuple[Sample, ...]:
    if source not in SOURCES:
        raise ValueError("NTP_SOURCE_NOT_ALLOWED")
    result: list[Sample] = []
    deadline = time.perf_counter() + 8
    # One resolved IPv4 endpoint per configured independent operator, no URLs
    # or client-supplied destinations. Connected UDP checks peer address/port.
    address = socket.getaddrinfo(source, 123, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
    timeouts = 0
    for index in range(4):
        if len(result) == 3:
            break
        if time.perf_counter() > deadline:
            raise ValueError("NTP_PROBE_DEADLINE_EXCEEDED")
        if index:
            time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as channel:
            channel.settimeout(2)
            channel.connect(address)
            nonce = secrets.token_bytes(8)
            request = bytes([0x23]) + bytes(39) + nonce
            before_wall, before_mono = precise_utc(), time.perf_counter()
            channel.send(request)
            try:
                packet = channel.recv(512)
            except TimeoutError:
                # One bounded transport retry. Invalid replies/disagreement are
                # never discarded or retried into acceptance; three valid samples
                # per independent source and all original limits remain required.
                if index == 3 or timeouts:
                    raise
                timeouts += 1
                continue
            local, mono = precise_utc(), time.perf_counter()
            elapsed = mono - before_mono
            if abs((local - before_wall).total_seconds() - elapsed) > 0.002 + elapsed * DRIFT:
                raise ValueError("NTP_SAMPLE_CLOCK_DISCONTINUITY")
            result.append(decode(packet, nonce, source, local, mono, elapsed))
    if len(result) != 3:
        raise ValueError("NTP_THREE_VALID_SAMPLES_REQUIRED")
    return tuple(result)


def combine(rows: tuple[Sample, ...], local: datetime, mono: float) -> Calibration:
    if len(rows) != 6 or local.tzinfo is None:
        raise ValueError("NTP_TWO_COMPLETE_INDEPENDENT_SOURCES_REQUIRED")
    medians = []
    selected = []
    for source in SOURCES:
        samples = [s for s in rows if s.source == source]
        if len(samples) != 3:
            raise ValueError("NTP_TWO_COMPLETE_INDEPENDENT_SOURCES_REQUIRED")
        projected = []
        for s in samples:
            age = mono - s.monotonic
            if not 0 <= age <= 10:
                raise ValueError("NTP_SAMPLES_TOO_OLD")
            movement = (s.local - local).total_seconds() + age
            lo, hi = s.lower + movement - age * DRIFT, s.upper + movement + age * DRIFT
            if not all(isfinite(v) for v in (lo, hi, s.rtt)) or not 0 < s.rtt <= MAX_RTT:
                raise ValueError("NTP_NONFINITE_OR_LATENCY_REJECTED")
            if lo > hi or hi - lo > MAX_WIDTH or max(abs(lo), abs(hi)) > 2:
                raise ValueError("NTP_SAMPLE_BOUNDS_REJECTED")
            projected.append((lo, hi, s.rtt))
        if max(x[0] for x in projected) > min(x[1] for x in projected):
            raise ValueError("NTP_SOURCE_SAMPLES_CONTRADICT")
        medians.append(statistics.median((lo + hi) / 2 for lo, hi, _ in projected))
        selected.append(min(projected, key=lambda x: x[2]))
    if abs(medians[0] - medians[1]) > MAX_DISAGREEMENT:
        raise ValueError("NTP_SOURCES_DISAGREE")
    if max(x[0] for x in selected) > min(x[1] for x in selected):
        raise ValueError("NTP_SOURCE_INTERVALS_DO_NOT_OVERLAP")
    # Conservative union, not a falsely precise average/intersection.
    lower, upper = min(x[0] for x in selected), max(x[1] for x in selected)
    if upper - lower > MAX_WIDTH:
        raise ValueError("NTP_COMBINED_INTERVAL_TOO_WIDE")
    return Calibration(local, mono, lower, upper, rows)


_cached: Calibration | None = None
_attempted = float("-inf")
_last_failure: dict[str, Any] = {}


def last_failure() -> dict[str, Any]:
    """Sanitized last acquisition failure; never probes or exposes raw OS messages."""
    with _lock:
        return dict(_last_failure)


def recent() -> Calibration | None:
    """At most eight UDP probes/30s; three valid/source, at most one timeout retry."""
    global _cached, _attempted, _last_failure
    with _lock:
        now = time.perf_counter()
        if now - _attempted < MAX_AGE:
            return _cached if _cached and 0 <= now - _cached.monotonic <= MAX_AGE else None
        _attempted, _cached, _last_failure = now, None, {}
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                rows = tuple(s for group in executor.map(probe, SOURCES) for s in group)
            _cached = combine(rows, precise_utc(), time.perf_counter())
        except (OSError, ValueError, OverflowError) as exc:
            allowed = {
                "NTP_PROBE_DEADLINE_EXCEEDED",
                "NTP_THREE_VALID_SAMPLES_REQUIRED",
                "NTP_PACKET_REJECTED",
                "NTP_ROOT_OR_PRECISION_REJECTED",
                "NTP_ROOT_UNCERTAINTY_REJECTED",
                "NTP_ZERO_TIMESTAMP",
                "NTP_SERVER_CHRONOLOGY_REJECTED",
                "NTP_OFFSET_OR_DISTANCE_REJECTED",
                "NTP_SAMPLE_CLOCK_DISCONTINUITY",
                "NTP_TWO_COMPLETE_INDEPENDENT_SOURCES_REQUIRED",
                "NTP_SAMPLES_TOO_OLD",
                "NTP_NONFINITE_OR_LATENCY_REJECTED",
                "NTP_SAMPLE_BOUNDS_REJECTED",
                "NTP_SOURCE_SAMPLES_CONTRADICT",
                "NTP_SOURCES_DISAGREE",
                "NTP_SOURCE_INTERVALS_DO_NOT_OVERLAP",
                "NTP_COMBINED_INTERVAL_TOO_WIDE",
            }
            reason = (
                str(exc)
                if isinstance(exc, ValueError) and str(exc) in allowed
                else (
                    "NTP_TRANSPORT_TIMEOUT"
                    if isinstance(exc, TimeoutError)
                    else "NTP_DNS_RESOLUTION_FAILED"
                    if isinstance(exc, socket.gaierror)
                    else "NTP_TRANSPORT_OS_ERROR"
                    if isinstance(exc, OSError)
                    else "NTP_TIMESTAMP_OVERFLOW"
                    if isinstance(exc, OverflowError)
                    else "NTP_ACQUISITION_INVALID"
                )
            )
            _last_failure = {
                "reason": reason,
                "attempted_monotonic": now,
                "failed_at": precise_utc().isoformat(),
                "maximum_age_seconds": MAX_AGE,
                "automatic_retry_before_cadence": False,
            }
            return None
        return _cached
