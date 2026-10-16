"""Manual bounded V2 development, reproducible inference and forward reconciliation.

No dashboard request trains models or acquires provider data. No task is enabled.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import encoded, write_new
from workers.providers.daily_clock import guard

from . import data, models
from .features import build
from .forward import append_forecasts, reconcile, summary

PROTOCOL = Path(__file__).resolve().parents[2] / "docs/development/ml-v2-registered-protocol.md"
PROTOCOL_SHA256 = "442811892836665af150967b406a9dab2eb30872a9cd33f2a5c819fbd34d8151"
COMPANION_SHA256 = "5b16c0bb9763c606f64c6f7dba6612a2ca33d6ab191ec38902fa29d62acbb2b6"


def protocol_id(price_only: bool = False) -> str:
    path = PROTOCOL.with_name("ml-v2-price-only-registered-protocol.md") if price_only else PROTOCOL
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != (COMPANION_SHA256 if price_only else PROTOCOL_SHA256):
        raise ValueError("REGISTERED_V2_PROTOCOL_CHANGED")
    return actual


def train(root: Path, price_only: bool = False) -> dict[str, Any]:
    dataset = data.load(root)
    output = root / "price-only" if price_only else root
    output.mkdir(exist_ok=True)
    target = output / "evaluation.json"
    if target.exists():
        report = verified(target)
        model = models.load_model(output / "model.json", report["model_sha256"])
        if (
            model["model_id"] != report["model_id"]
            or model["dataset_id"] != dataset["dataset_id"]
            or model["protocol_id"] != protocol_id(price_only)
        ):
            raise ValueError("V2_TRAINING_REPLAY_LINEAGE_MISMATCH")
        return report
    model, report = models.train(
        dataset["rows"],
        dataset["sessions"],
        dataset["dataset_id"],
        protocol_id(price_only),
        datetime.now(UTC),
        datetime.fromisoformat(dataset["source_observed_at"]),
        dataset["quality"]["excluded_sessions"],
        output / "fits",
        include_context=not price_only,
    )
    checksum = models.save_model(output / "model.json", model)
    report["model_sha256"] = checksum
    write_checked(target, report)
    return report


def write_checked(path: Path, value: Any) -> None:
    body = encoded(value)
    write_new(path, body)
    write_new(path.with_suffix(".sha256"), hashlib.sha256(body).hexdigest().encode())


def verified(path: Path) -> dict[str, Any]:
    if path.is_symlink() or path.with_suffix(".sha256").is_symlink():
        raise ValueError("V2_EVIDENCE_SYMLINK_FORBIDDEN")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != path.with_suffix(".sha256").read_text():
        raise ValueError("V2_EVIDENCE_CHECKSUM_MISMATCH")
    value: dict[str, Any] = json.loads(body)
    return value


def training_baseline(root: Path, output: Path, model: dict[str, Any]) -> float:
    """Freeze refit prevalence from the immutable training snapshot, never later revisions."""
    path = output / "training-baseline.json"
    if path.exists():
        facts = verified(path)
    else:
        base = data.load(root)
        frame = build(
            base["rows"],
            base["sessions"],
            base["quality"]["excluded_sessions"],
            include_context=len(model["feature_names"]) == 20,
        )
        labels = [
            r.target
            for r in frame.samples
            if r.target is not None
            and r.session <= model["training_last_session"]
            and str(r.target_session) <= model["training_target_last_session"]
        ]
        if not labels:
            raise ValueError("V2_ORIGINAL_REFIT_BASELINE_UNAVAILABLE")
        facts = {
            "model_id": model["model_id"],
            "dataset_id": base["dataset_id"],
            "majority_score": sum(labels) / len(labels),
            "training_rows": len(labels),
        }
        write_checked(path, facts)
    if facts["model_id"] != model["model_id"] or facts["dataset_id"] != model["dataset_id"]:
        raise ValueError("V2_REFIT_BASELINE_LINEAGE_MISMATCH")
    return float(facts["majority_score"])


def infer(root: Path) -> dict[str, Any]:
    price_only = (root / "price-only/evaluation.json").exists()
    output = root / "price-only" if price_only else root
    report = verified(output / "evaluation.json")
    model = models.load_model(output / "model.json", report["model_sha256"])
    if model["protocol_id"] != protocol_id(price_only) or model["model_id"] != report["model_id"]:
        raise ValueError("V2_MODEL_REPORT_LINEAGE_MISMATCH")
    dataset = data.load_current(root)
    pointer = output / "latest-inference.txt"
    if pointer.exists():
        if pointer.is_symlink():
            raise ValueError("V2_POINTER_SYMLINK_FORBIDDEN")
        name = pointer.read_text(encoding="utf-8")
        if not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z\.json", name):
            raise ValueError("V2_INFERENCE_PATH_REJECTED")
        previous = verified(output / "inference" / name)
        if (
            previous["model_id"] == model["model_id"]
            and previous["dataset_id"] == dataset["dataset_id"]
        ):
            return {
                **previous,
                "replayed": True,
                "forecast_write": {"inserted": 0, "replayed": len(previous["candidates"])},
                "prospective": summary(output),
            }
    features = build(
        dataset["rows"],
        dataset["sessions"],
        dataset["quality"]["excluded_sessions"],
        include_context=not price_only,
    )
    clock = guard()
    decision = datetime.now(UTC)
    timing = dataset.get("session_timing")
    following = dataset.get("next_session_timing")
    candidates: list[dict[str, Any]] = []
    gap: str | None = None
    if timing and following:
        if datetime.fromisoformat(following["open_at"]) <= datetime.fromisoformat(
            clock["upper_at"]
        ):
            raise ValueError("V2_ENTRY_MUST_FOLLOW_INDEPENDENT_CLOCK_UPPER_BOUND")
        candidates = models.score(
            model,
            dataset["rows"],
            dataset["sessions"],
            decision,
            datetime.fromisoformat(dataset["source_observed_at"]),
            datetime.fromisoformat(following["open_at"]),
            following["session"],
            dataset["quality"]["excluded_sessions"],
            completed_session_end=datetime.fromisoformat(timing["close_at"]),
        )
        majority = training_baseline(root, output, model)
        for row in candidates:
            source_row = next(
                r
                for r in dataset["rows"]
                if r["key"] == row["key"] and r["session"] == row["session"]
            )
            row.update(
                {
                    "training_dataset_id": model["dataset_id"],
                    "dataset_id": dataset["dataset_id"],
                    "session_timing": timing,
                    "next_session_timing": following,
                    "feature_names": model["feature_names"],
                    "source_sha256": source_row["raw_sha256"],
                    "decision_clock": clock,
                    "baseline_majority_score": majority,
                }
            )
    else:
        gap = "OFFICIAL_CLOSED_CURRENT_SESSION_AND_NEXT_ENTRY_TIMING_REQUIRED"
    stored = (
        append_forecasts(
            output,
            model_id=model["model_id"],
            dataset_id=dataset["dataset_id"],
            protocol_id=protocol_id(price_only),
            scores=candidates,
            source_observed_at=datetime.fromisoformat(dataset["source_observed_at"]),
        )
        if candidates
        else {"inserted": 0}
    )
    source = datetime.fromisoformat(dataset["source_observed_at"])
    from zoneinfo import ZoneInfo

    prior_rows = [
        r
        for r in dataset["rows"]
        if r["session"] < source.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    ]
    outcomes = reconcile(
        output,
        prior_rows,
        dataset["sessions"],
        source_observed_at=source,
        excluded_sessions=dataset["quality"]["excluded_sessions"],
        official_timings=data.collected_timings(root),
        require_official_sessions=True,
    )
    result = {
        "model_id": model["model_id"],
        "dataset_id": dataset["dataset_id"],
        "generated_at": decision.isoformat(),
        "decision_clock": clock,
        "candidates": candidates,
        "exclusions": list(features.exclusions),
        "gap": gap,
        "forecast_write": stored,
        "reconciliation": outcomes,
        "prospective": summary(output),
    }
    # Immutable individual runs; pointer contains no model and must verify its content hash.
    run = output / "inference" / (decision.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    run.parent.mkdir(exist_ok=True)
    write_checked(run, result)
    (output / "latest-inference.txt").write_text(run.name, encoding="utf-8")
    return result
