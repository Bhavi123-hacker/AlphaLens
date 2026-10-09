"""TEST_ONLY lifecycle evidence: no real prices, fits or backtest reruns."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.audit_research_backtests import (
    audit,
    check_output,
    digest,
    enrich_source_gaps,
    gap_classification,
    trade_evidence,
)

DAYS = ["2023-11-10", "2023-11-12", "2023-11-13", "2023-11-15"]


def trade(exit_day: str, status: str) -> dict[str, Any]:
    return {"entry_session": DAYS[0], "planned_exit_session": exit_day, "status": status}


def row(action: bool = False, quality: str = "VALID") -> dict[str, Any]:
    return {"economic_action": action, "quality": quality}


def test_temporary_missing_mark_is_not_a_permanent_missing_exit() -> None:
    result = trade_evidence(
        trade(DAYS[2], "CLOSED"),
        DAYS,
        {DAYS[0]: row(), DAYS[2]: row(), DAYS[3]: row()},
    )
    assert result["events"] == [("MISSING_MARK", DAYS[1])]
    assert result["unknown_sessions"] == [DAYS[1]]
    assert result["status_matches"]


def test_missing_exit_remains_unresolved_despite_later_price() -> None:
    result = trade_evidence(
        trade(DAYS[1], "UNRESOLVED_MISSING_EXIT"),
        DAYS,
        {DAYS[0]: row(), DAYS[2]: row(), DAYS[3]: row()},
    )
    assert result["events"] == [("MISSING_EXIT", DAYS[1])]
    assert result["unknown_sessions"] == DAYS[1:]
    assert result["status_matches"]


def test_action_blocks_same_day_exit() -> None:
    result = trade_evidence(
        trade(DAYS[0], "UNRESOLVED_RAW_ECONOMIC_ACTION"),
        DAYS,
        {d: row(action=d == DAYS[0]) for d in DAYS},
    )
    assert result["events"] == [("RAW_ACTION", DAYS[0])]
    assert result["unknown_sessions"] == DAYS
    assert result["status_matches"]


def test_later_action_overwrites_stored_status_but_preserves_initial_missing_exit_cause() -> None:
    result = trade_evidence(
        trade(DAYS[1], "UNRESOLVED_RAW_ECONOMIC_ACTION"),
        DAYS,
        {DAYS[0]: row(), DAYS[2]: row(action=True), DAYS[3]: row()},
    )
    assert result["events"] == [("MISSING_EXIT", DAYS[1]), ("RAW_ACTION_AFTER_UNRESOLVED", DAYS[2])]
    assert result["unknown_sessions"] == DAYS[1:]
    assert result["status_matches"]


def test_valid_end_of_period_open_position_does_not_invent_exit() -> None:
    result = trade_evidence(trade("2023-11-20", "OPEN"), DAYS, {d: row() for d in DAYS})
    assert result["expected_status"] == "OPEN"
    assert result["events"] == []
    assert result["unknown_sessions"] == []


def test_rejected_exit_is_separate_from_absent_observation() -> None:
    result = trade_evidence(
        trade(DAYS[1], "UNRESOLVED_MISSING_EXIT"),
        DAYS,
        {d: row(quality="REJECTED" if d == DAYS[1] else "VALID") for d in DAYS},
    )
    assert result["events"] == [("REJECTED_EXIT", DAYS[1])]
    assert result["status_matches"]


def test_wrong_stored_trade_status_is_a_detected_inconsistency() -> None:
    result = trade_evidence(trade(DAYS[0], "OPEN"), DAYS, {d: row() for d in DAYS})
    assert result["expected_status"] == "CLOSED"
    assert not result["status_matches"]


@pytest.mark.parametrize(
    ("price_status", "alternatives", "expected"),
    [
        ("PRICE_OBSERVATION_MISSING", [], "VERIFIED_SESSION_SOURCE_PRICE_MISSING"),
        (
            "SOURCE_ROWS_PRESENT",
            [{"p2_security_id": "same"}],
            "SOURCE_ID_PRESENT_UNDER_DIFFERENT_RESEARCH_ID",
        ),
        (
            "SOURCE_ROWS_PRESENT",
            [{"p2_security_id": "different"}],
            "SAME_SYMBOL_OTHER_ID_AMBIGUOUS_NOT_MERGED",
        ),
        ("SOURCE_ROWS_PRESENT", [], "NO_CANONICAL_OBSERVATION_NO_TERMINAL_VALUE_EVIDENCE"),
    ],
)
def test_gap_types_do_not_merge_identities_or_fabricate_prices(
    price_status: str, alternatives: list[dict[str, str]], expected: str
) -> None:
    assert (
        gap_classification({"price_status": price_status}, {"p2_security_id": "same"}, alternatives)
        == expected
    )


def test_output_cannot_overwrite_any_frozen_tree(tmp_path: Path) -> None:
    frozen = tmp_path / "frozen"
    for output in (frozen, frozen / "summary.json", frozen / "a" / "b.json"):
        with pytest.raises(ValueError, match="AUDIT_OUTPUT"):
            check_output(output, [frozen])
    check_output(tmp_path / "audit.json", [frozen])


def test_source_gap_checks_distinguish_absence_from_identity_and_preserve_classification(
    tmp_path: Path,
) -> None:
    original = tmp_path / "revision" / "nse" / "fixture.parquet"
    original.parent.mkdir(parents=True)
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "date": date(2023, 11, 13),
                    "symbol": "TEST_ONLY",
                    "isin": "TEST_ID",
                    "series": "EQ",
                    "open": 10,
                    "close": 11,
                }
            ]
        ),
        original,
    )
    before = original.read_bytes()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "revision": "revision",
                "files": [{"filename": "nse/fixture.parquet", "sha256": digest(original)}],
            }
        )
    )
    result = enrich_source_gaps(
        {
            "usage_classification": "TEST_ONLY",
            "events": [
                {
                    "kind": "MISSING_EXIT",
                    "symbol_at_entry": "TEST_ONLY",
                    "isin_at_entry": "TEST_ID",
                    "session": d,
                }
                for d in DAYS[1:3]
            ],
        },
        manifest,
        tmp_path,
    )
    assert result["usage_classification"] == "TEST_ONLY"
    assert result["events"][0]["source_gap_status"] == "SOURCE_OBSERVATION_ABSENT"
    assert result["events"][1]["source_gap_status"] == (
        "SOURCE_OBSERVATION_PRESENT_IDENTITY_RECONCILIATION_REQUIRED"
    )
    assert result["events"][1]["original_source_rows"][0]["source_row_number"] == 0
    assert original.read_bytes() == before
    manifest.write_text(
        json.dumps(
            {
                "revision": "revision",
                "files": [{"filename": "nse/fixture.parquet", "sha256": "incorrect"}],
            }
        )
    )
    with pytest.raises(ValueError, match="SOURCE_PRICE_CHECKSUM"):
        enrich_source_gaps(result, manifest, tmp_path)


def test_zero_trade_archive_and_phase_wrapper_are_audited_without_rewriting_inputs(
    tmp_path: Path,
) -> None:
    run, data = tmp_path / "run", tmp_path / "data"
    folder = run / "p10" / "TEST_ONLY"
    folder.mkdir(parents=True)
    data.mkdir()
    summary = {
        "backtest_id": "TEST_ONLY",
        "trade_count": 0,
        "unresolved_trade_count": 0,
        "status": "RESEARCH_RAW_PRICE_DIAGNOSTIC",
        "task": "classification",
        "horizon": 1,
        "model_family": "TEST_ONLY",
        "selection_rule": "TOP_K",
        "cost_scenario": "TEST_ONLY",
    }
    (folder / "summary.json").write_text(json.dumps(summary))
    pq.write_table(
        pa.Table.from_pylist([{"session": DAYS[0], "portfolio_value": "100"}]),
        folder / "equity.parquet",
    )
    for phase in ("development", "2025", "2026"):
        (run / f"{phase}-backtests.json").write_text(
            json.dumps(
                {"backtests": [dict(summary, phase=phase)] if phase == "development" else []}
            )
        )
    (data / "research-calendar.json").write_text(json.dumps({"sessions": []}))
    (data / "canonical-manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": "TEST_ONLY",
                "identity": {
                    "files": [],
                    "data_reality": "SYNTHETIC_TEST_ONLY",
                    "usage_classification": "TEST_ONLY",
                    "final_vintage": "TEST_ONLY",
                    "production_market_data_use": "NOT_CLEARED",
                },
            }
        )
    )
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(json.dumps({"revision": "TEST_ONLY", "files": []}))
    originals = {p: p.read_bytes() for p in run.rglob("*") if p.is_file()}
    result = audit(run, data, acquisition, tmp_path / "incoming")
    assert result["audit_status"] == "CONSISTENT_WITH_FROZEN_ENGINE"
    assert result["usage_classification"] == "TEST_ONLY"
    assert result["trade_status_counts"] == {}
    assert result["runs"][0]["event_ids"] == []
    assert "trades.parquet" not in result["runs"][0]["stored_evidence_sha256"]
    assert {p: p.read_bytes() for p in run.rglob("*") if p.is_file()} == originals
