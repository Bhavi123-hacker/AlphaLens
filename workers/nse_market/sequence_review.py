"""Report-only engineering correction, never model fitting or independent approval.

The original report/model/history remain immutable. A corrected derivative removes
probability diagnostics from Ridge return-ranking scores and separately attests
that the saved current scores exist before the documented next opening now.
This does not assert that the training process executed this later review guard.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import verify
from workers.experimental_nse.acquire import digest
from workers.nse_market import engine
from workers.providers.daily_clock import guard

PROBABILITY_FIELDS = ("brier_score", "calibration_bins", "probability_calibration_established")
METADATA = ("original_report_sha256", "corrected_at", "reasons", "engineering_review")


def validate_correction(original: dict[str, Any], corrected: dict[str, Any]) -> None:
    """Only the declared non-probability removals and new review metadata may differ."""
    expected = copy.deepcopy(original)
    metrics = expected["comparisons"]["RIDGE"]["metrics"]
    for name in PROBABILITY_FIELDS:
        metrics.pop(name, None)
    for name in METADATA:
        if name in original or name not in corrected:
            raise ValueError("SEQUENCE_REVIEW_METADATA_CONFLICT")
        expected[name] = corrected[name]
    if expected != corrected:
        raise ValueError("SEQUENCE_REVIEW_UNDECLARED_REPORT_CHANGE")


def _timing(original: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    """Read qualified source first, then obtain a new independent current bound."""
    scores = original["current_scores"]
    if not isinstance(scores, list):
        raise ValueError("SEQUENCE_SAVED_SCORE_LIST_REQUIRED")
    clock = guard()
    lower, upper = (datetime.fromisoformat(clock[name]) for name in ("lower_at", "upper_at"))
    if lower.utcoffset() is None or upper.utcoffset() is None or lower > upper:
        raise ValueError("SEQUENCE_REVIEW_INDEPENDENT_CLOCK_REQUIRED")
    completed = datetime.fromisoformat(original["completed_at"])
    if completed.utcoffset() is None or completed > lower:
        raise ValueError("SEQUENCE_REVIEW_REPORT_MUST_ALREADY_EXIST")
    result = {
        "clock": clock,
        "attested_at": datetime.now(UTC).isoformat(),
        "status": "NO_SAVED_CURRENT_SCORES"
        if not scores
        else "SAVED_SCORES_BEFORE_NEXT_OPEN_AT_REVIEW",
        "original_process_executed_this_guard": False,
        "forecast_records_created": 0,
        "accepted_rankings": 0,
        "classification": "DATED_EXPERIMENTAL_SCORES_NOT_FORECASTS_OR_INDEPENDENT_ACCEPTANCE",
    }
    if not scores:
        return result
    timing, following = frame["session_timing"], frame["next_session_timing"]
    latest = frame["sessions"][-1]
    close, entry = (
        datetime.fromisoformat(value) for value in (timing["close_at"], following["open_at"])
    )
    if (
        timing["session"] != latest
        or following["session"] <= latest
        or close.utcoffset() is None
        or entry.utcoffset() is None
        or close >= entry
        or upper >= entry
    ):
        raise ValueError("SEQUENCE_REVIEW_FUTURE_OFFICIAL_ENTRY_UNPROVEN")
    lookup = {(row["key"], row["session"]): row for row in frame["rows"]}
    seen: set[str] = set()
    for row in scores:
        actual = lookup[(row["key"], row["session"])]
        inferred, observed = (
            datetime.fromisoformat(row[name]) for name in ("inference_at", "source_observed_at")
        )
        score = row["score"]
        if (
            row["key"] in seen
            or row["session"] != latest
            or actual["symbol"] != row["symbol"]
            or actual["close"] != row["observed_price"]
            or row["model_sha256"] != original["model_sha256"]
            or inferred.utcoffset() is None
            or observed.utcoffset() is None
            or not close < observed <= inferred <= completed
            or inferred >= entry
            or row["forecast_created"] is not False
            or row["classification"] != "EXPERIMENTAL_ML"
            or row["calibration_status"] != "NOT_ESTABLISHED"
            or type(score) not in {int, float}
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            raise ValueError("SEQUENCE_REVIEW_SAVED_SCORE_IDENTITY_OR_CHRONOLOGY_INVALID")
        seen.add(row["key"])
    result.update(
        observation_session=latest,
        official_session_close_at=timing["close_at"],
        next_session=following["session"],
        official_entry_open_at=following["open_at"],
        source_dataset_id=frame["dataset_id"],
        saved_scores_attested=len(scores),
    )
    return result


def review(root: Path, source: Path) -> dict[str, Any]:
    """Create one checksum-pinned derivative after a genuine completed run; no refits."""
    verify(root)
    verify(source)
    original = engine._read(root / "report.json")
    model = engine._read(root / "model.json")
    history = engine._read(root / "historical-predictions.json")
    report_sha = digest((root / "report.json").read_bytes())
    model_sha = digest((root / "model.json").read_bytes())
    history_sha = digest((root / "historical-predictions.json").read_bytes())
    executing = engine._read(root / "executing-source.json")
    if (
        original["family"] != "ALPHALENS_SEQUENCE_BENCHMARK_V1"
        or original["accepted_rankings"] != 0
        or original["prospective_forecasts"] != 0
        or original["matured_prospective_outcomes"] != 0
        or original["model_sha256"] != model_sha
        or history["model_sha256"] != model_sha
        or model["protocol_sha256"] != original["protocol_sha256"]
        or digest((root / "executing-source.py").read_bytes()) != executing["sha256"]
    ):
        raise ValueError("SEQUENCE_REVIEW_ORIGINAL_PROVENANCE_INVALID")
    target = root / "report-final.json"
    if target.exists():
        result = engine._read(target)
        validate_correction(original, result)
        if (
            result["original_report_sha256"] != report_sha
            or result["engineering_review"]["original_model_sha256"] != model_sha
            or result["engineering_review"]["original_history_sha256"] != history_sha
        ):
            raise ValueError("SEQUENCE_REVIEW_ORIGINAL_BYTES_CHANGED")
        return result
    frame = engine.snapshot(source)
    attestation = _timing(original, frame)
    result = copy.deepcopy(original)
    for name in PROBABILITY_FIELDS:
        result["comparisons"]["RIDGE"]["metrics"].pop(name, None)
    result.update(
        original_report_sha256=report_sha,
        corrected_at=datetime.now(UTC).isoformat(),
        reasons=[
            (
                "Ridge is a transformed return-ranking score; probability Brier/calibration "
                "diagnostics are not applicable under the registered classifier-only rule."
            ),
            (
                "A separate engineering guard attests actual saved-score existence before "
                "the official future opening at review time; the original process did not "
                "execute this later guard."
            ),
        ],
        engineering_review={
            "classification": "REPORT_ENGINEERING_CORRECTION_NOT_INDEPENDENT_REVIEW",
            "removed_ridge_fields": list(PROBABILITY_FIELDS),
            "original_model_sha256": model_sha,
            "original_history_sha256": history_sha,
            "executing_source_sha256": executing["sha256"],
            "model_fitting_performed": False,
            "scores_or_other_metrics_changed": False,
            "timing_attestation": attestation,
        },
    )
    validate_correction(original, result)
    if (
        digest((root / "report.json").read_bytes()) != report_sha
        or digest((root / "model.json").read_bytes()) != model_sha
        or digest((root / "historical-predictions.json").read_bytes()) != history_sha
    ):
        raise ValueError("SEQUENCE_REVIEW_SOURCE_CHANGED_DURING_REVIEW")
    engine._checked(target, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    arguments = parser.parse_args()
    result = review(arguments.root, arguments.source)
    print(
        json.dumps(
            {
                "state": "ENGINEERING_REPORT_CORRECTION_COMPLETE",
                "original_report_sha256": result["original_report_sha256"],
                "corrected_at": result["corrected_at"],
                "original_scores_preserved": True,
                "accepted_rankings": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
