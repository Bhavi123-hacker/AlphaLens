"""Read-only Windows Time/NTP measurements; never set time or override financial clocks."""

import argparse
import ctypes
import json
import re
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def samples(text: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for block in re.split(r"(?=\d\d:\d\d:\d\d,)", text):
        timing = re.search(r"d:([+-]\d+\.\d+)s o:([+-]\d+\.\d+)s", block)
        if not timing:
            continue
        delay, offset = (float(timing.group(i)) for i in (1, 2))
        root_delay = re.search(r"Root Delay:.*\(([+-]\d+\.\d+)s\)", block)
        zero_root_delay = bool(re.search(r"Root Delay: 0x0000\.0000 \(unspecified\)", block))
        dispersion = re.search(r"Root Dispersion:.*\((\d+\.\d+)s\)", block)
        valid_server = bool(
            re.search(r"Leap Indicator: 0\b", block)
            and re.search(r"Mode: 4\b", block)
            and re.search(r"Stratum: (?:[1-9]|1[0-5])\b", block)
        )
        distance = None
        if valid_server and delay >= 0 and (root_delay or zero_root_delay) and dispersion:
            distance = (
                delay / 2
                + (max(0, float(root_delay.group(1))) / 2 if root_delay else 0)
                + float(dispersion.group(1))
            )
        rows.append(
            {
                "roundtrip_seconds": delay,
                "server_minus_local_seconds": offset,
                "reported_distance_seconds": distance,
                "offset_interval_seconds": [offset - distance, offset + distance]
                if distance is not None
                else None,
            }
        )
    return {
        "sample_count": len(rows),
        "samples": rows,
        "median_server_minus_local_seconds": statistics.median(
            r["server_minus_local_seconds"] for r in rows
        )
        if rows
        else None,
        "maximum_reported_distance_seconds": max(
            (
                r["reported_distance_seconds"]
                for r in rows
                if r["reported_distance_seconds"] is not None
            ),
            default=None,
        ),
        "method": "NTP_REPORTED_ROOT_DISPERSION_PLUS_HALF_ROOT_DELAY_PLUS_HALF_ROUNDTRIP",
        "limitations": "UNAUTHENTICATED_NTP_ASSUMPTIONS_NOT_INDEPENDENT_UTC_PROOF_OR_GATE_OVERRIDE",
    }


def adjustment() -> dict[str, Any]:
    if sys.platform != "win32":
        return {"state": "WINDOWS_ONLY"}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    api_name = "GetSystemTimeAdjustmentPrecise"
    try:
        query = ctypes.WinDLL(
            "api-ms-win-core-version-l1-2-3.dll", use_last_error=True
        ).GetSystemTimeAdjustmentPrecise
        integer: Any = ctypes.c_uint64
    except (AttributeError, OSError):
        api_name = "GetSystemTimeAdjustment"
        query = kernel.GetSystemTimeAdjustment
        integer = ctypes.c_uint32
    query.argtypes = [
        ctypes.POINTER(integer),
        ctypes.POINTER(integer),
        ctypes.POINTER(ctypes.c_int),
    ]
    query.restype = ctypes.c_int
    adjusted, nominal, disabled = integer(), integer(), ctypes.c_int()
    if not query(ctypes.byref(adjusted), ctypes.byref(nominal), ctypes.byref(disabled)):
        return {"state": "ADJUSTMENT_QUERY_UNAVAILABLE", "winerror": ctypes.get_last_error()}
    return {
        "state": "READ_ONLY_SYSTEM_TIME_ADJUSTMENT",
        "api": api_name,
        "adjusted_increment": adjusted.value,
        "nominal_increment": nominal.value,
        "periodic_programmed_adjustment_disabled": bool(disabled.value),
        "programmed_rate_difference_ppm": (adjusted.value / nominal.value - 1) * 1e6
        if nominal.value and not disabled.value
        else None,
        "interpretation": "DISABLED_DOES_NOT_EXCLUDE_OTHER_KERNEL_OR_HYPERVISOR_TIME_CORRECTION",
    }


def wall_rate(duration: int) -> dict[str, Any]:
    if sys.platform != "win32" or not 1 <= duration <= 45:
        raise ValueError("BOUNDED_WINDOWS_READ_ONLY_MEASUREMENT_REQUIRED")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    precise = kernel.GetSystemTimePreciseAsFileTime
    precise.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    precise.restype = None

    def stamp() -> tuple[float, int]:
        value = ctypes.c_uint64()
        before = time.perf_counter()
        precise(ctypes.byref(value))
        after = time.perf_counter()
        return (before + after) / 2, value.value

    before = stamp()
    time.sleep(duration)
    after = stamp()
    elapsed = after[0] - before[0]
    wall = (after[1] - before[1]) / 1e7
    return {
        "monotonic_elapsed_seconds": elapsed,
        "precise_wall_elapsed_seconds": wall,
        "wall_minus_monotonic_seconds": wall - elapsed,
        "wall_relative_rate_ppm": (wall / elapsed - 1) * 1e6,
        "interpretation": "SHORT_LOCAL_RATE_COMPARISON_NOT_UTC_ACCURACY_OR_CONVERGENCE_PROOF",
    }


def time_tool() -> str:
    """Use the actual protected system directory, never a PATH-resolved executable."""
    if sys.platform != "win32":
        raise ValueError("WINDOWS_DIAGNOSTICS_REQUIRED")
    buffer = ctypes.create_unicode_buffer(32768)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    size = kernel.GetSystemDirectoryW(buffer, len(buffer))
    if not 0 < size < len(buffer):
        raise ValueError("WINDOWS_SYSTEM_DIRECTORY_UNAVAILABLE")
    executable = Path(buffer.value) / "w32tm.exe"
    if not executable.is_file():
        raise ValueError("WINDOWS_TIME_TOOL_UNAVAILABLE")
    return str(executable)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source",
        choices=("time.windows.com", "time.google.com", "time.nist.gov"),
        default="time.windows.com",
    )
    parser.add_argument("--rate-seconds", type=int, choices=(15, 30, 45))
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("NEW_CLOCK_METADATA_PATH_REQUIRED")
    executable = time_tool()
    status = subprocess.run(
        [executable, "/query", "/status", "/verbose"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    measurement = subprocess.run(
        [
            executable,
            "/stripchart",
            "/computer:" + args.source,
            "/samples:5",
            "/period:1",
            "/packetinfo",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    result = {
        "version": "p34.clock-diagnostics.v1",
        "observed_at": datetime.now(UTC).isoformat(),
        "time_source": args.source,
        "read_only": True,
        "windows_status": status.stdout.splitlines() if status.returncode == 0 else [],
        "measurement_exit_code": measurement.returncode,
        "ntp": samples(measurement.stdout),
        "time_or_service_configuration_modified": False,
        "financial_timestamp_validation_modified": False,
        "programmed_adjustment": adjustment(),
        "local_rate_measurement": wall_rate(args.rate_seconds) if args.rate_seconds else None,
    }
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print('{"state":"CLOCK_MEASUREMENT_UNAVAILABLE","configuration_modified":false}')
        raise SystemExit(1) from None
