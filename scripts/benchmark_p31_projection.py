"""Actual frozen-row scan parity and latency. No models, forecasts or market claims."""

import argparse
import hashlib
import json
import time
from datetime import date
from pathlib import Path

import pyarrow.dataset as ds

from alphalens_api.artifacts import ArtifactReader, confined
from alphalens_api.local.cli import configured
from alphalens_api.visual import FEATURES, snapshot_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    reader = ArtifactReader(
        configured(repo / ".local-data/p31-browser-runtime/operator-config.json")
    )
    observed = [
        r["session_date"]
        for r in reader.calendar()["sessions"]
        if r["price_status"] == "SOURCE_ROWS_PRESENT"
    ]
    start, end = map(date.fromisoformat, observed[-2:])
    root = reader.settings.research_data_root
    assert root is not None
    entries = reader.manifest(
        "canonical-manifest.json" if args.canonical else "supervised-manifest.json"
    )["identity"]["files"]
    if not args.all:
        entries = entries[:3]
    columns = ["security_id", "session_date", *FEATURES, *(f + "__state" for f in FEATURES)]
    if args.canonical:
        all_days = [r["session_date"] for r in reader.calendar()["sessions"]]
        start = date.fromisoformat(all_days[max(0, all_days.index(observed[-2]) - 1)])
        columns = [
            "security_id",
            "session_date",
            "symbol",
            "isin",
            "name",
            "analytical_type",
            "close",
            "volume",
            "quality",
            "quality_reasons",
        ]
    results = []
    for entry in entries:
        path = reader.verify(confined(root, entry["path"]), entry["sha256"])
        variants = []
        for batch_size in (4096, 65536):
            began = time.perf_counter()
            scanner = ds.dataset(path, format="parquet").scanner(
                columns=columns,
                filter=(ds.field("session_date") >= start) & (ds.field("session_date") <= end),
                batch_size=batch_size,
                use_threads=False,
            )
            rows = [row for batch in scanner.to_batches() for row in batch.to_pylist()]
            rows.sort(key=lambda r: (r["security_id"], r["session_date"]))
            digest = hashlib.sha256(
                json.dumps(rows, default=str, sort_keys=True).encode()
            ).hexdigest()
            variants.append(
                {
                    "batch_size": batch_size,
                    "seconds": round(time.perf_counter() - began, 6),
                    "rows": len(rows),
                    "digest": digest,
                }
            )
        if variants[0]["digest"] != variants[1]["digest"]:
            raise ValueError("PROJECTION_PARITY_FAILED")
        began = time.perf_counter()
        actual, more = snapshot_rows(
            path, columns, None, start, end, 50000, 0, time.monotonic() + 30
        )
        actual_digest = hashlib.sha256(
            json.dumps(actual, default=str, sort_keys=True).encode()
        ).hexdigest()
        if more or actual_digest != variants[0]["digest"]:
            raise ValueError("ACTUAL_PROJECTION_PARITY_FAILED")
        variants.append(
            {
                "batch_size": "ACTUAL_EXISTING_FUNCTION",
                "seconds": round(time.perf_counter() - began, 6),
                "rows": len(actual),
                "digest": actual_digest,
            }
        )
        results.append(
            {"partition": Path(entry["path"]).name, "identical_rows": True, "variants": variants}
        )
    (
        repo
        / (
            ".local-data/p31-canonical-projection-benchmark.json"
            if args.canonical
            else ".local-data/p31-projection-benchmark.json"
        )
    ).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "partitions": len(results),
                "identical_rows": True,
                "seconds": {
                    str(results[0]["variants"][i]["batch_size"]): round(
                        sum(r["variants"][i]["seconds"] for r in results), 6
                    )
                    for i in range(3)
                },
                "slowest_existing": sorted(
                    results, key=lambda r: r["variants"][2]["seconds"], reverse=True
                )[:3],
            }
        )
    )


if __name__ == "__main__":
    main()
