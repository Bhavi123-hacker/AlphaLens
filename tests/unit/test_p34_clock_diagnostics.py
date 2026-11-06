"""TEST_ONLY constructed Windows diagnostic text, never a clock-accuracy claim."""

import pytest
from scripts.p34_clock_diagnostics import samples


def test_offset_distance_and_uncertainty_are_distinct_from_synchronization() -> None:
    result = samples("""TEST_ONLY constructed packet
14:20:53, d:+00.0400000s o:+00.3900000s
Leap Indicator: 0(no warning)
Mode: 4 (Server)
Stratum: 4
Root Delay: 0x0000.0007 (+00.0020000s)
Root Dispersion: 0x0000.0007 (0.0100000s)
""")
    assert result["sample_count"] == 1
    assert result["median_server_minus_local_seconds"] == 0.39
    assert result["maximum_reported_distance_seconds"] == pytest.approx(0.031)
    assert result["samples"][0]["offset_interval_seconds"] == pytest.approx([0.359, 0.421])
    assert "GATE_OVERRIDE" in result["limitations"]


def test_unsynchronized_incomplete_and_failed_packets_never_supply_false_uncertainty() -> None:
    assert samples("14:20:53, error: 0x800705B4\nStratum: 0")["sample_count"] == 0
    result = samples("14:20:53, d:+00.04s o:-00.39s\nLeap Indicator: 3\nMode: 4\nStratum: 0")
    assert result["median_server_minus_local_seconds"] == -0.39
    assert result["maximum_reported_distance_seconds"] is None
    assert result["samples"][0]["offset_interval_seconds"] is None


def test_primary_server_zero_root_delay_keeps_its_declared_dispersion() -> None:
    result = samples("""TEST_ONLY primary server
14:29:40, d:+00.040s o:+00.350s
Leap Indicator: 0
Mode: 4
Stratum: 1
Root Delay: 0x0000.0000 (unspecified)
Root Dispersion: 0x0000.0007 (0.0001000s)
""")
    assert result["maximum_reported_distance_seconds"] == pytest.approx(0.0201)
