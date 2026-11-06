"""Process-local continuity observations; no network or clock-setting operations.

These observations do not establish UTC correctness. They reject discontinuity
while independent clock evidence is being renewed. Windows uses precise biased
and unbiased interrupt clocks to detect suspend without GetTickCount64's coarse
tick quantization; the latter is retained only as a diagnostic observation.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from datetime import datetime
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .quote_clock import DRIFT, precise_utc

POLICY = "daily.process-clock-continuity.v1"
MAX_INTERVAL_SECONDS = 120.0
MAX_CAPTURE_SECONDS = 0.005
_PROCESS_ID = str(uuid4())
_NATIVE: Any = ctypes


def _boot_identity() -> str:
    if sys.platform == "win32":
        # SystemBootEnvironmentInformation is an internal Windows interface.
        # Require the exact Windows 8+ 32-byte layout and fail closed if absent.
        query = _NATIVE.WinDLL("ntdll").NtQuerySystemInformation
        query.argtypes = [
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        query.restype = ctypes.c_int32
        buffer = (ctypes.c_ubyte * 32)()
        returned = ctypes.c_uint32()
        status = query(90, ctypes.byref(buffer), 32, ctypes.byref(returned))
        if status != 0 or returned.value != 32:
            raise ValueError("CLOCK_CONTINUITY_BOOT_ID_UNAVAILABLE")
        identity = UUID(bytes_le=bytes(buffer[:16]))
    elif sys.platform == "linux":
        identity = UUID(Path("/proc/sys/kernel/random/boot_id").read_text().strip())
    else:
        raise ValueError("CLOCK_CONTINUITY_PLATFORM_UNSUPPORTED")
    if identity.int == 0:
        raise ValueError("CLOCK_CONTINUITY_BOOT_ID_UNAVAILABLE")
    return str(identity)


def _suspend_timers() -> tuple[float, float, float]:
    if sys.platform == "win32":
        # Bind the documented API set: some Windows builds do not forward these
        # precise exports through kernel32 even though they are supported.
        realtime = _NATIVE.WinDLL("api-ms-win-core-realtime-l1-1-1", use_last_error=True)
        values = []
        for name in ("QueryInterruptTimePrecise", "QueryUnbiasedInterruptTimePrecise"):
            query = getattr(realtime, name)
            query.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
            query.restype = None
            ticks = ctypes.c_uint64()
            query(ctypes.byref(ticks))
            values.append(ticks.value / 10_000_000)
        tick_count = _NATIVE.WinDLL("kernel32", use_last_error=True).GetTickCount64
        tick_count.argtypes = []
        tick_count.restype = ctypes.c_uint64
        return values[0], values[1], tick_count() / 1000
    if sys.platform == "linux":
        boot_clock = getattr(time, "CLOCK_BOOTTIME", None)
        if boot_clock is None:
            raise ValueError("CLOCK_CONTINUITY_SUSPEND_TIMER_UNAVAILABLE")
        inclusive = time.clock_gettime(boot_clock)
        return inclusive, time.monotonic(), inclusive
    raise ValueError("CLOCK_CONTINUITY_PLATFORM_UNSUPPORTED")


def capture() -> dict[str, Any]:
    """Capture fresh native observations, including exact boot/process identity."""
    try:
        boot_id = _boot_identity()
        started = time.perf_counter()
        local = precise_utc()
        monotonic = time.perf_counter()
        inclusive, exclusive, tick_count = _suspend_timers()
        ended = time.perf_counter()
        observation = {
            "policy": POLICY,
            "platform": sys.platform,
            "boot_id": boot_id,
            "process_id": _PROCESS_ID,
            "pid": os.getpid(),
            "wall_at": local.isoformat(),
            "monotonic_seconds": monotonic,
            "suspend_inclusive_seconds": inclusive,
            "suspend_exclusive_seconds": exclusive,
            "tick_count_seconds": tick_count,
            "capture_span_seconds": ended - started,
        }
        _parsed(observation)
        return observation
    except (OSError, AttributeError, TypeError, ValueError, OverflowError):
        raise ValueError("CLOCK_CONTINUITY_CAPTURE_UNAVAILABLE") from None


def _parsed(observation: dict[str, Any]) -> tuple[datetime, tuple[float, ...]]:
    try:
        if observation["policy"] != POLICY or observation["platform"] not in {"win32", "linux"}:
            raise ValueError
        for field in ("boot_id", "process_id"):
            if not isinstance(observation[field], str) or UUID(observation[field]).int == 0:
                raise ValueError
        pid = observation["pid"]
        if type(pid) is not int or pid <= 0:
            raise ValueError
        wall = datetime.fromisoformat(observation["wall_at"])
        if wall.tzinfo is None or wall.utcoffset() is None:
            raise ValueError
        fields = (
            "monotonic_seconds",
            "suspend_inclusive_seconds",
            "suspend_exclusive_seconds",
            "tick_count_seconds",
            "capture_span_seconds",
        )
        values = []
        for field in fields:
            value = observation[field]
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError
            values.append(float(value))
        if values[-1] > MAX_CAPTURE_SECONDS:
            raise ValueError
        return wall, tuple(values)
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError("CLOCK_CONTINUITY_MISSING_OR_INVALID") from None


def validate(previous: dict[str, Any], current: dict[str, Any]) -> None:
    """Reject restart, boot change, suspend or inconsistent clocks; never correct UTC."""
    before_wall, before = _parsed(previous)
    after_wall, after = _parsed(current)
    if previous["boot_id"] != current["boot_id"]:
        raise ValueError("CLOCK_CONTINUITY_BOOT_CHANGED")
    if any(previous[key] != current[key] for key in ("platform", "process_id", "pid")):
        raise ValueError("CLOCK_CONTINUITY_PROCESS_CHANGED")
    elapsed = after[0] - before[0]
    if not 0 <= elapsed <= MAX_INTERVAL_SECONDS:
        raise ValueError("CLOCK_CONTINUITY_INTERVAL_INVALID")
    tolerance = 0.005 + elapsed * DRIFT
    wall_elapsed = (after_wall - before_wall).total_seconds()
    if wall_elapsed < 0 or abs(wall_elapsed - elapsed) > tolerance:
        raise ValueError("CLOCK_CONTINUITY_WALL_MONOTONIC_DISAGREEMENT")
    inclusive, exclusive = after[1] - before[1], after[2] - before[2]
    if (
        inclusive < 0
        or exclusive < 0
        or abs(inclusive - exclusive) > tolerance
        or abs(inclusive - elapsed) > tolerance
        or abs(exclusive - elapsed) > tolerance
        or after[3] < before[3]
    ):
        raise ValueError("CLOCK_CONTINUITY_SUSPEND_OR_TIMER_DISAGREEMENT")
