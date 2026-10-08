"""Bounded profile of actual frozen flags; no target values or model metrics."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from alphalens_data.ingestion.storage import stable_json
from alphalens_data.research import ResearchCalendar, lineage
from alphalens_features.research import window_flag


def profile(root: Path) -> dict[str, Any]:
    supervised = json.loads((root / "supervised-manifest.json").read_bytes())
    canonical = json.loads((root / "canonical-manifest.json").read_bytes())
    calendar = ResearchCalendar.model_validate_json((root / "research-calendar.json").read_bytes())
    positions = {d: i for i, d in enumerate(calendar.dates)}
    lookbacks = {
        d["feature_name"]: d["lookback"]
        for d in supervised["identity"]["feature_definitions"]
        if d["feature_name"] != "momentum_percentile_20"
    }
    counts: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    canonical_by_name = {Path(f["path"]).name: f for f in canonical["identity"]["files"]}
    for receipt in supervised["identity"]["files"]:
        source = root / receipt["path"]
        canon_receipt = canonical_by_name[source.name]
        for path, expected in (
            (source, receipt["sha256"]),
            (root / canon_receipt["path"], canon_receipt["sha256"]),
        ):
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise ValueError("RESEARCH_ACTION_PROFILE_FILE_CHECKSUM_MISMATCH")
        originals = pq.ParquetFile(root / canon_receipt["path"]).read(
            columns=["security_id", "session_date", "economic_action"]
        )
        action_indices: dict[str, list[int]] = {}
        for s, d, action in zip(
            *(
                originals.column(n).to_pylist()
                for n in ("security_id", "session_date", "economic_action")
            ),
            strict=True,
        ):
            if action:
                action_indices.setdefault(s, []).append(positions[d])
        columns = ["security_id", "session_date"] + list(lookbacks)
        columns += [f"outcome_reasons_{h}" for h in (1, 5, 10, 20)]
        table = pq.ParquetFile(source).read(columns=columns)
        ids = np.asarray(table.column("security_id").to_pylist())
        slots = np.asarray([positions[d] for d in table.column("session_date").to_pylist()])
        starts = np.r_[0, np.flatnonzero(ids[1:] != ids[:-1]) + 1, len(ids)]
        for left, right in zip(starts, starts[1:], strict=False):
            flags = np.zeros(len(calendar.sessions), dtype=bool)
            flags[action_indices.get(str(ids[left]), [])] = True
            for name, lookback in lookbacks.items():
                observed = (
                    table.column(name).slice(left, right - left).to_numpy(zero_copy_only=False)
                )
                affected = window_flag(flags, lookback)[slots[left:right]]
                counts[name] += int((np.isfinite(observed) & affected).sum())
        for h in (1, 5, 10, 20):
            outcomes[str(h)] += sum(
                "CORPORATE_ACTION_UNADJUSTED" in reasons
                for reasons in table.column(f"outcome_reasons_{h}").to_pylist()
            )
    result = dict(
        **lineage(calendar.profile),
        dataset_id=supervised["dataset_id"],
        available_feature_rows_with_raw_action_in_required_trailing_window=dict(
            sorted(counts.items())
        ),
        label_rows_with_unadjusted_action_outcome_exclusion=dict(sorted(outcomes.items())),
        semantics="Counts overlap P3 degradation and other exclusions; not additive. "
        "Contemporaneous cross-sectional peer degradation is not attributed to a specific cause.",
        adjustment_factors="UNAVAILABLE_NOT_CREATED",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = profile(args.data_root)
    args.output.write_bytes(stable_json(result))
    print(json.dumps(result["label_rows_with_unadjusted_action_outcome_exclusion"]))


if __name__ == "__main__":
    main()
