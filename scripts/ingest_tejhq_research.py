"""Bounded P2 normalization/P3 validation of captured TejHQ yearly originals.

Reuses P2 normalization and the unmodified P3 engine. Previous sessions and the
complete trailing identical-OHLC run are carried across batches/years.
This creates P2 normalized records, NOT historical-eligible P5 observations.
"""

import argparse
import json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from scripts.acquire_tejhq_research import REVISION, digest_file

from alphalens_data.ingestion.contracts import CanonicalEOD, Classification, RawManifest
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.storage import RawLanding, publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.tejhq import iter_batches
from alphalens_data.quality.engine import validate
from alphalens_data.quality.models import ArtifactEvidence, ValidationInput


def previous_context(values: list[CanonicalEOD]) -> tuple[CanonicalEOD, ...]:
    """Preserve exact consecutive-run state, including runs longer than four bars."""
    first = max(0, len(values) - 4)
    trailing = len(values) - 1
    while trailing > 0:
        a, b = values[trailing - 1], values[trailing]
        if (a.open, a.high, a.low, a.close) != (b.open, b.high, b.low, b.close):
            break
        trailing -= 1
    return tuple(values[min(first, trailing) :])


def ingest(
    root: Path,
    raw_root: Path,
    output: Path,
    summary_path: Path,
    shards: int = 1,
    shard_index: int = 0,
) -> dict[str, Any]:
    acquisition = json.loads((root / "acquisition-manifest.json").read_bytes())
    if acquisition["revision"] != REVISION:
        raise ValueError("INGESTION_REVISION_MISMATCH")
    profile = json.loads(Path("docs/data/dataset-profile.json").read_bytes())
    if profile["counts"]["duplicate_identity_session_rows"]:
        # An artifact-wide ambiguous key index is needed before batching such a file.
        raise ValueError("GLOBAL_DUPLICATE_KEYS_REQUIRE_EXPLICIT_QUARANTINE_INDEX")
    if profile["counts"]["file_year_date_mismatch"]:
        raise ValueError("SOURCE_PARTITION_YEAR_CONFLICT")
    if shards > 1 and profile.get("raw_symbol_session_duplicate_rows") != 0:
        raise ValueError("GLOBAL_SYMBOL_SESSION_CONFLICT_PROFILE_REQUIRED")
    output.mkdir(parents=True, exist_ok=True)
    tails: dict[str, tuple[CanonicalEOD, ...]] = {}
    manifests: dict[str, RawManifest] = {}
    counts: Counter[str] = Counter()
    per_year = []
    for receipt in acquisition["files"]:
        source_path = root / receipt["filename"]
        if digest_file(source_path) != receipt["sha256"]:
            raise ValueError("NORMALIZATION_ORIGINAL_CHECKSUM_MISMATCH")
        manifest = RawManifest.model_validate(receipt["raw_manifest"])
        RawLanding(raw_root).read(manifest)
        manifests[manifest.artifact_id] = manifest
        year = Path(receipt["filename"]).stem[4:]
        destination = output / f"p2-p3-nse-{year}.parquet"
        if destination.exists():
            raise ValueError("DERIVED_PARTITION_EXISTS_USE_REPLAY_NEW_ROOT")
        year_counts: Counter[str] = Counter()
        writer = pq.ParquetWriter(
            destination,
            pa.schema(
                [
                    ("record_id", pa.string()),
                    ("security_id", pa.string()),
                    ("session_date", pa.date32()),
                    ("record_json", pa.large_string()),
                    ("quality", pa.string()),
                    ("quality_reasons", pa.list_(pa.string())),
                    ("data_reality", pa.string()),
                    ("usage_classification", pa.string()),
                ]
            ),
            compression="zstd",
        )
        try:
            for ordinal, parsed in enumerate(
                iter_batches(source_path, shards=shards, shard_index=shard_index)
            ):
                records, quarantine = normalize(parsed, manifest)
                current_ids = {r.record_id for r in records}
                relevant = {r.security_id for r in records}
                combined = sorted(
                    [r for key in sorted(relevant) for r in tails.get(key, ())] + list(records),
                    key=lambda r: (r.security_id, r.session_date, r.source_row_number),
                )
                by_artifact: dict[str, list[CanonicalEOD]] = defaultdict(list)
                for r in combined:
                    by_artifact[r.artifact_id].append(r)
                by_artifact.setdefault(manifest.artifact_id, [])
                evidence = tuple(
                    ArtifactEvidence(
                        manifest=manifests[key],
                        observed_sha256=manifests[key].sha256,
                        observed_byte_size=manifests[key].byte_size,
                        normalized_sha256=checksum(
                            stable_json(
                                [r.model_dump(mode="json", exclude={"record_id"}) for r in values]
                            )
                        ),
                    )
                    for key, values in sorted(by_artifact.items())
                )
                report = validate(
                    ValidationInput(
                        records=tuple(combined),
                        quarantine=quarantine,
                        artifacts=evidence,
                        classification=Classification.RESEARCH_ONLY,
                    )
                )
                qualities = {(s.security_id, s.session_date): s for s in report.sessions}
                rows = []
                for r in records:
                    s = qualities[(r.security_id, r.session_date)]
                    year_counts[f"quality_{s.status}"] += 1
                    rows.append(
                        {
                            "record_id": r.record_id,
                            "security_id": r.security_id,
                            "session_date": r.session_date,
                            "record_json": r.model_dump_json(),
                            "quality": str(s.status),
                            "quality_reasons": list(s.reason_codes),
                            "data_reality": "REAL_MARKET_OBSERVATIONS",
                            "usage_classification": "RESEARCH_ONLY",
                        }
                    )
                if rows:
                    writer.write_table(pa.Table.from_pylist(rows, schema=writer.schema))
                year_counts["source_rows"] += len(parsed)
                year_counts["normalized_rows"] += len(records)
                year_counts["quarantined_source_rows"] += len(
                    {q.source_row_number for q in quarantine}
                )
                for issue in report.issues:
                    if not issue.record_ids or current_ids.intersection(issue.record_ids):
                        year_counts[f"issue_{issue.rule_id}"] += 1
                grouped: dict[str, list[CanonicalEOD]] = defaultdict(list)
                for r in combined:
                    grouped[r.security_id].append(r)
                for key, values in grouped.items():
                    tails[key] = previous_context(values)
                # Scoped batch evidence retained immutably, not mislabelled a whole-artifact run.
                publish(output / "p3-reports" / year / f"{ordinal:05}.json", report.to_bytes())
                if quarantine:
                    publish(
                        output / "quarantine" / year / f"{ordinal:05}.json",
                        stable_json([q.model_dump(mode="json") for q in quarantine]),
                    )
        finally:
            writer.close()
        counts.update(year_counts)
        entry = {"year": year, **dict(year_counts), "derived_sha256": digest_file(destination)}
        per_year.append(entry)
        print(json.dumps(entry), flush=True)
    summary = {
        "schema_version": "tejhq.p2-p3-stream.v1",
        "revision": REVISION,
        "status": "P2_NORMALIZATION_P3_SCOPED_VALIDATION_COMPLETE",
        "data_reality": "REAL_MARKET_OBSERVATIONS",
        "usage_classification": "RESEARCH_ONLY",
        "production_market_data_use": "NOT_CLEARED",
        "counts": dict(counts),
        "years": per_year,
        "p3_policy": "UNMODIFIED_p3.policy.v1",
        "p3_validator": "p3.quality.v2",
        "batch_scope": "4096 rows plus prior context and complete trailing identical-OHLC run",
        "validation_scope_limitation": (
            "P3 batch reports are not a full-dataset cross-identity report; raw global duplicate "
            "profile is required first. No P4/P5 eligibility derives from this scoped report."
        ),
        "calendar": "UNAVAILABLE_AUTHORITATIVE",
        "historical_availability": "UNAVAILABLE",
        "p4_p5_historical_eligibility": "BLOCKED_MISSING_KNOWLEDGE_AND_CALENDAR_EVIDENCE",
        "derived_directory": str(output.resolve()),
        "identity_shards": shards,
        "shard_index": shard_index,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incoming", type=Path, default=Path("data/incoming/tejhq") / REVISION)
    parser.add_argument("--raw-root", type=Path, default=Path("data/tejhq-research/p2"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, default=Path("docs/data/tejhq-p2-p3-summary.json"))
    parser.add_argument("--workers", type=int, default=1, choices=(1, 2, 4))
    args = parser.parse_args()
    if args.workers == 1:
        ingest(args.incoming, args.raw_root, args.output, args.summary)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                ingest,
                args.incoming,
                args.raw_root,
                args.output / f"shard-{i}",
                args.output / f"shard-{i}-summary.json",
                args.workers,
                i,
            )
            for i in range(args.workers)
        ]
        summaries = [future.result() for future in futures]
    counts: Counter[str] = Counter()
    for summary in summaries:
        counts.update(summary["counts"])
    combined = {
        "schema_version": "tejhq.p2-p3-stream.v1",
        "revision": REVISION,
        "status": "P2_NORMALIZATION_P3_SCOPED_VALIDATION_COMPLETE",
        "data_reality": "REAL_MARKET_OBSERVATIONS",
        "usage_classification": "RESEARCH_ONLY",
        "production_market_data_use": "NOT_CLEARED",
        "counts": dict(counts),
        "identity_shards": args.workers,
        "shard_summaries": summaries,
        "global_duplicate_profile": "ZERO_IDENTITY_SESSION_AND_SYMBOL_SESSION_DUPLICATES",
        "p3_policy": "UNMODIFIED_p3.policy.v1",
        "p3_validator": "p3.quality.v2",
        "historical_availability": "UNAVAILABLE",
        "calendar": "UNAVAILABLE_AUTHORITATIVE",
        "p4_p5_historical_eligibility": "BLOCKED_MISSING_KNOWLEDGE_AND_CALENDAR_EVIDENCE",
        "derived_directory": str(args.output.resolve()),
        "validation_scope": (
            "Deterministic identity shards with past-only temporal context; scoped reports"
        ),
    }
    args.summary.write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
