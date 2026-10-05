"""Offline P1 fixture verification. No network, scheduler, model or market-universe builder."""

import argparse
import json
from pathlib import Path
from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum
from alphalens_data.providers.mendeley import (
    NORMALIZATION_VERSION,
    PARSER_VERSION,
    ResearchCatalog,
    parse_sample,
    read_artifact,
    research_bytes,
)


def replay(catalog: ResearchCatalog, raw_root: Path) -> tuple[bytes, dict[str, Any]]:
    """Normalize twice from reread/checksummed inputs; preserve every missing-row finding."""
    if len({a.dataset_id for a in catalog.artifacts}) != len(catalog.artifacts):
        raise DataContractError("DUPLICATE_ARTIFACT")
    samples = [
        parse_sample(
            read_artifact(raw_root, artifact),
            artifact,
            catalog.start_session,
            catalog.end_session,
        )
        for artifact in catalog.artifacts
    ]
    rows = tuple(row for sample in samples for row in sample.rows)
    first = research_bytes(rows)
    second = research_bytes(
        tuple(
            row
            for artifact in catalog.artifacts
            for row in parse_sample(
                read_artifact(raw_root, artifact),
                artifact,
                catalog.start_session,
                catalog.end_session,
            ).rows
        )
    )
    if first != second:
        raise DataContractError("NONDETERMINISTIC_REPLAY")
    observed_union = {day for sample in samples for day in sample.observed_dates}
    details = []
    for artifact, sample in zip(catalog.artifacts, samples, strict=True):
        valid_dates = {row.bar.session_date for row in sample.rows}
        details.append(
            {
                "doi": artifact.doi,
                "symbol": artifact.symbol,
                "raw_artifact_ref": artifact.raw_relative_path,
                "sha256": artifact.sha256,
                "byte_size": artifact.byte_size,
                "acquired_at": artifact.acquired_at.isoformat(),
                "source_row_count": sample.source_row_count,
                "source_date_start": sample.first_source_date.isoformat(),
                "source_date_end": sample.last_source_date.isoformat(),
                "selected_row_count": sample.selected_row_count,
                "canonical_row_count": len(sample.rows),
                "input_ordered": sample.input_ordered,
                "unavailable_rows": [row.model_dump(mode="json") for row in sample.unavailable],
                "missing_relative_to_observed_cohort": [
                    day.isoformat() for day in sorted(observed_union - valid_dates)
                ],
                "zero_volume_dates": [
                    row.bar.session_date.isoformat() for row in sample.rows if row.bar.volume == 0
                ],
                "state": "DEGRADED" if sample.unavailable else "AVAILABLE",
            }
        )
    report: dict[str, Any] = {
        "scope": "RESEARCH_FIXTURE_DATASET",
        "research_fixture_use": "ACCEPTED_WITH_RESIDUAL_RISK",
        "production_data_clearance": "OPEN",
        "production_market_data_use": "NOT_CLEARED",
        "parsing_version": PARSER_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "canonical_schema_version": "p1.v2",
        "requested_start": catalog.start_session.isoformat(),
        "requested_end": catalog.end_session.isoformat(),
        "observed_start": min(observed_union).isoformat(),
        "observed_end": max(observed_union).isoformat(),
        "observed_dates": len(observed_union),
        "selected_source_rows": sum(s.selected_row_count for s in samples),
        "canonical_rows": len(rows),
        "unavailable_rows": sum(len(s.unavailable) for s in samples),
        "normalized_sha256": checksum(first),
        "replayed_sha256": checksum(second),
        "byte_equivalent_replay": True,
        "duplicate_security_sessions": 0,
        "invalid_canonical_ohlcv_rows": 0,
        "historical_pit_eligible_rows": 0,
        "limitations": [
            "Observed dates are not an independently verified exchange calendar.",
            "Missing source values are unavailable, not zero or forward-filled.",
            "Zero volume is preserved; source correctness is not independently certified.",
            "Session close, historical publication/availability and adjustment basis are unknown.",
            "Research fixture is not a market universe; survivorship bias is unresolved.",
            "No index, corporate actions, PIT fundamentals, sector or departed-security evidence.",
            "AVAILABLE/DEGRADED describes fixture parsing only; live freshness is STALE.",
        ],
        "artifacts": details,
    }
    return first, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # Keep third-party records out of tracked product/test directories by policy.
    if not args.output_dir.resolve().is_relative_to((Path.cwd() / ".local-data").resolve()):
        raise DataContractError("OUTPUT_MUST_BE_IGNORED_LOCAL_DATA")
    catalog = ResearchCatalog.model_validate_json(args.manifest.read_bytes())
    payload, report = replay(catalog, args.raw_dir)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "canonical.json").write_bytes(payload)
    (args.output_dir / "validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "ATTRIBUTION.md").write_text(
        "Local derivative research fixture; original artifacts unchanged.\n"
        "Bounded filtering and canonical normalization performed by AlphaLens.\n"
        "CC BY 4.0: https://creativecommons.org/licenses/by/4.0/\n"
        "No endorsement by contributors; production/live clearance remains OPEN.\n\n"
        + "\n".join(
            f"{'; '.join(a.contributors)} (2024). {a.title}. Mendeley Data V{a.version}. "
            f"https://doi.org/{a.doi}. {a.license}."
            for a in catalog.artifacts
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
