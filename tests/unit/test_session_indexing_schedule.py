"""Unit tests for T+5 and T+10 session-indexing schedule and trade completeness."""

import pytest


def get_schedule(total_sessions: int, test_start_idx: int, horizon: int) -> tuple[list[tuple[int, int]], int | None]:
    """Computes exact non-overlapping (entry_idx, exit_idx) pairs and incomplete tail."""
    completed = []
    incomplete = None
    for idx in range(test_start_idx, total_sessions, horizon):
        exit_idx = idx + horizon
        if exit_idx < total_sessions:
            completed.append((idx, exit_idx))
        else:
            incomplete = idx
            break
    return completed, incomplete


def test_t5_session_indexing_exact_counts() -> None:
    # 120 total sessions (0 to 119), test window starts at 36 (84 sessions total)
    completed, incomplete = get_schedule(total_sessions=120, test_start_idx=36, horizon=5)
    # Total completed trades must be exactly 16
    assert len(completed) == 16
    # First trade: entry 36, exit 41 (fifth subsequent session)
    assert completed[0] == (36, 41)
    # Final completed trade: entry 111, exit 116 (both <= 119)
    assert completed[-1] == (111, 116)
    # Incomplete trade: entry 116 would exit at 121 (> 119), so it cannot be completed
    assert incomplete == 116
    assert incomplete + 5 >= 120


def test_t10_session_indexing_exact_counts() -> None:
    completed, incomplete = get_schedule(total_sessions=120, test_start_idx=36, horizon=10)
    # Total completed trades must be exactly 8
    assert len(completed) == 8
    # First trade: entry 36, exit 46
    assert completed[0] == (36, 46)
    # Final completed trade: entry 106, exit 116
    assert completed[-1] == (106, 116)
    # Incomplete trade: entry 116 would exit at 126 (> 119)
    assert incomplete == 116


def test_no_future_leakage_and_boundary_safety() -> None:
    completed, _ = get_schedule(total_sessions=120, test_start_idx=36, horizon=5)
    for entry_idx, exit_idx in completed:
        # Strict temporal order: exit must be strictly greater than entry by horizon
        assert exit_idx - entry_idx == 5
        # Exit must be strictly within available dataset
        assert exit_idx < 120
        assert entry_idx >= 36


def test_overlapping_vs_non_overlapping_discrimination() -> None:
    # Non-overlapping step size = horizon
    non_overlap, _ = get_schedule(total_sessions=120, test_start_idx=36, horizon=5)
    # Overlapping step size = 1
    overlap = []
    for idx in range(36, 120 - 5):
        overlap.append((idx, idx + 5))

    # Overlapping produces 79 correlated observations
    assert len(overlap) == 79
    # Non-overlapping produces 16 approximately independent observations
    assert len(non_overlap) == 16
    # Overlapping must not be described as independent observations
    assert len(overlap) != len(non_overlap)
