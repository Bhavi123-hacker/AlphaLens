"""P4-P7 partitioned research replay of verified P2/P3 TejHQ artifacts.

All large outputs stay local. Normal verified PIT engines are not modified.
Research calendar/profile and every source hash enter reproducible manifests.
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from scripts.acquire_tejhq_research import REVISION, digest_file

from alphalens_data.canonical.models import EODValues
from alphalens_data.ingestion.contracts import CanonicalEOD
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchProfile, assess, calendar, lineage
from alphalens_data.universe.research import ResearchUniverse
from alphalens_features.models import BuildPlan, Decision
from alphalens_features.registry import default_set
from alphalens_features.research import numerical, window_flag
from alphalens_labels.research import targets

BUCKETS = 64
CANONICAL_SCHEMA = pa.schema(
    [
        ("canonical_record_id", pa.string()),
        ("p2_record_id", pa.string()),
        ("security_id", pa.string()),
        ("p2_security_id", pa.string()),
        ("session_date", pa.date32()),
        ("symbol", pa.string()),
        ("isin", pa.string()),
        ("series", pa.string()),
        ("name", pa.string()),
        *((n, pa.decimal128(38, 18)) for n in ("open", "high", "low", "close")),
        ("volume", pa.int64()),
        ("quality", pa.string()),
        ("quality_reasons", pa.list_(pa.string())),
        ("analytical_type", pa.string()),
        ("type_reason", pa.string()),
        ("identity_basis", pa.string()),
        ("assumed_available_at", pa.timestamp("us", tz="UTC")),
        ("economic_action", pa.bool_()),
        ("artifact_id", pa.string()),
        ("raw_sha256", pa.string()),
        ("source_row_number", pa.int64()),
    ]
)


def save(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(payload))


def research_id(row: CanonicalEOD) -> str:
    if row.isin:
        return row.security_id
    # No inference that two years' unresolved ticker observations are the same security.
    return "research:provisional:" + checksum(
        stable_json(
            [row.security_id, row.session_date.year, "SOURCE_YEAR_SCOPED_NO_FUTURE_ISIN_MERGE"]
        )
    )


def canonical_stage(output: Path) -> dict[str, Any]:
    profile = ResearchProfile()
    profile_id = profile.profile_id
    manifest = json.loads(Path("docs/data/tejhq-acquisition-manifest.json").read_bytes())
    summary = json.loads(Path("docs/data/tejhq-p2-p3-summary.json").read_bytes())
    source_identity = json.loads(Path("docs/data/dataset-identity.json").read_bytes())
    if manifest["revision"] != REVISION:
        raise ValueError("RESEARCH_SOURCE_REVISION_MISMATCH")
    incoming = Path("data/incoming/tejhq") / REVISION
    observed: set[date] = set()
    actions: set[tuple[str, date]] = set()
    for item in manifest["files"]:
        path = incoming / item["filename"]
        if digest_file(path) != item["sha256"]:
            raise ValueError("RESEARCH_SOURCE_CHECKSUM_MISMATCH")
        if item["filename"].startswith("nse/"):
            observed.update(
                pq.ParquetFile(path).read(columns=["date"]).column(0).unique().to_pylist()
            )
        elif item["filename"].startswith("actions/"):
            for row in pq.ParquetFile(path).read(columns=["symbol", "ex_date", "type"]).to_pylist():
                if row["type"] not in {"agm", "buyback"}:
                    actions.add((row["symbol"], row["ex_date"]))
    sessions = calendar(observed, profile)
    resolver = ResearchUniverse(profile, sessions)
    save(output / "research-calendar.json", sessions.model_dump(mode="json"))
    availability = {d: sessions.availability(d) for d in sessions.dates}
    metadata = {
        b"research_lineage": stable_json(lineage(profile)),
        b"schema_version": b"p5.research.canonical.v1",
    }
    schema = CANONICAL_SCHEMA.with_metadata(metadata)
    writers: dict[int, pq.ParquetWriter] = {}
    counts: Counter[str] = Counter()
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    security_types: dict[str, set[str]] = defaultdict(set)
    past_exclusion: dict[str, Any] = {}
    last_seen: dict[str, date] = {}
    for shard in summary["shard_summaries"]:
        folder = Path(shard["derived_directory"])
        for year in shard["years"]:
            part = folder / f"p2-p3-nse-{year['year']}.parquet"
            if digest_file(part) != year["derived_sha256"]:
                raise ValueError("P2_P3_DERIVED_CHECKSUM_MISMATCH")
            names = (
                pq.ParquetFile(incoming / f"nse/year={year['year']}/nse_{year['year']}.parquet")
                .read(columns=["name"])
                .column(0)
                .to_pylist()
            )
            # Native files can be grouped by historical symbol, not ISIN chronology.
            # Sort one bounded yearly shard before carrying prior type evidence.
            yearly_table = pq.ParquetFile(part).read()
            yearly_table = yearly_table.take(
                pc.sort_indices(
                    yearly_table,
                    sort_keys=[("security_id", "ascending"), ("session_date", "ascending")],
                )
            )
            for batch in yearly_table.to_batches(max_chunksize=4096):
                grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
                for item in batch.to_pylist():
                    row = CanonicalEOD.model_validate_json(item["record_json"])
                    security = research_id(row)
                    if security in last_seen and row.session_date <= last_seen[security]:
                        raise ValueError("RESEARCH_IDENTITY_OBSERVATIONS_NOT_CHRONOLOGICAL")
                    last_seen[security] = row.session_date
                    name = names[row.source_row_number - 2]
                    assumed = availability[row.session_date]
                    assessment = (
                        resolver.resolve(row, assumed, name)
                        if assumed
                        else assess(row.series, row.isin, name)
                    )
                    if assessment is None:
                        raise ValueError("RESEARCH_ROW_NOT_VISIBLE_AT_ASSUMED_BOUNDARY")
                    if security in past_exclusion:
                        assessment = past_exclusion[security]
                    elif assessment.analytical_type == "EXCLUDED_NON_EQUITY":
                        past_exclusion[security] = assessment
                    values = EODValues(
                        open=row.open,
                        high=row.high,
                        low=row.low,
                        close=row.close,
                        volume=row.volume,
                    )
                    canonical = dict(
                        p2_record_id=row.record_id,
                        security_id=security,
                        p2_security_id=row.security_id,
                        session_date=row.session_date,
                        symbol=row.symbol,
                        isin=row.isin,
                        series=row.series,
                        name=name,
                        **values.model_dump(exclude={"turnover", "trade_count", "vwap"}),
                        quality=item["quality"],
                        quality_reasons=item["quality_reasons"],
                        analytical_type=assessment.analytical_type,
                        type_reason=assessment.reason,
                        identity_basis="OBSERVED_ISIN"
                        if row.isin
                        else "SOURCE_YEAR_SCOPED_PROVISIONAL",
                        assumed_available_at=availability[row.session_date],
                        economic_action=(row.symbol, row.session_date) in actions,
                        artifact_id=row.artifact_id,
                        raw_sha256=row.raw_sha256,
                        source_row_number=row.source_row_number,
                    )
                    canonical["canonical_record_id"] = checksum(
                        stable_json(
                            dict(
                                profile_id=profile_id,
                                **{
                                    k: v.isoformat()
                                    if isinstance(v, date)
                                    else str(v)
                                    if isinstance(v, Decimal)
                                    else v
                                    for k, v in canonical.items()
                                },
                            )
                        )
                    )
                    bucket = int(checksum(security.encode())[:8], 16) % BUCKETS
                    grouped[bucket].append(canonical)
                    kind = assessment.analytical_type
                    counts[kind] += 1
                    counts["quality_" + item["quality"]] += 1
                    counts["identity_" + canonical["identity_basis"]] += 1
                    by_year[str(row.session_date.year)][kind] += 1
                    security_types[security].add(kind)
                for bucket, rows in grouped.items():
                    if bucket not in writers:
                        path = output / "canonical" / f"bucket-{bucket:02}.parquet"
                        path.parent.mkdir(parents=True, exist_ok=True)
                        if path.exists():
                            raise ValueError("CANONICAL_REPLAY_REQUIRES_NEW_OUTPUT_ROOT")
                        writers[bucket] = pq.ParquetWriter(path, schema, compression="zstd")
                    writers[bucket].write_table(pa.Table.from_pylist(rows, schema=schema))
            print(
                json.dumps(dict(stage="canonical", shard=shard["shard_index"], year=year["year"])),
                flush=True,
            )
    for writer in writers.values():
        writer.close()
    files = [
        {
            "path": str(p.relative_to(output)),
            "sha256": digest_file(p),
            "rows": pq.ParquetFile(p).metadata.num_rows,
        }
        for p in sorted((output / "canonical").glob("*.parquet"))
    ]
    identity = dict(
        **lineage(profile),
        source_identity=source_identity["source_dataset_identity"],
        raw_hashes=[{"file": f["filename"], "sha256": f["sha256"]} for f in manifest["files"]],
        p3_version="p3.quality.v2",
        p3_policy="UNMODIFIED_p3.policy.v1",
        calendar_id=sessions.calendar_id,
        identity_policy="SOURCE_YEAR_SCOPED_PROVISIONAL_NO_ISIN_MERGE_V1",
        universe="NSE_RESEARCH_EQUITY_CANDIDATE_UNIVERSE_V1",
        canonical_version="p5.research.canonical.v1",
        files=files,
    )
    result = dict(
        identity=identity,
        dataset_id=checksum(stable_json(identity)),
        counts=dict(counts),
        counts_by_year={y: dict(c) for y, c in sorted(by_year.items())},
        securities=len(security_types),
        security_type_counts={
            t: sum(t in kinds for kinds in security_types.values())
            for t in ("RESEARCH_EQUITY_CANDIDATE", "EXCLUDED_NON_EQUITY", "UNKNOWN_UNUSABLE")
        },
    )
    save(output / "canonical-manifest.json", result)
    save(Path("docs/data/research-canonical-summary.json"), result)
    return result


def definitions(sessions: Any) -> Any:
    plan = BuildPlan(
        history_start=sessions.dates[0],
        decisions=(
            Decision(
                session_date=sessions.dates[0],
                knowledge_cutoff=sessions.availability(sessions.dates[0]),
            ),
        ),
    )
    return default_set(plan).definitions


def identity_profile(output: Path) -> dict[str, Any]:
    """Descriptive identity coverage; never inferred delistings or universe inputs."""
    sessions = json.loads((output / "research-calendar.json").read_bytes())
    profile = ResearchProfile.model_validate(sessions["profile"])
    manifest = json.loads((output / "canonical-manifest.json").read_bytes())
    identities: dict[str, dict[str, Any]] = {}
    exclusions: Counter[str] = Counter()
    quality_by_year: dict[str, Counter[str]] = defaultdict(Counter)
    yearly_ids: dict[str, set[str]] = defaultdict(set)
    for part in manifest["identity"]["files"]:
        path = output / part["path"]
        if digest_file(path) != part["sha256"]:
            raise ValueError("RESEARCH_IDENTITY_PROFILE_CHECKSUM_MISMATCH")
        for batch in pq.ParquetFile(path).iter_batches(
            columns=[
                "security_id",
                "session_date",
                "symbol",
                "isin",
                "analytical_type",
                "quality",
                "type_reason",
                "identity_basis",
                "economic_action",
            ]
        ):
            for row in batch.to_pylist():
                day, security = row["session_date"], row["security_id"]
                state = identities.setdefault(
                    security,
                    dict(
                        first=day,
                        last=day,
                        identity_basis=row["identity_basis"],
                        symbols=set(),
                        types=set(),
                        action_rows=0,
                    ),
                )
                state["first"] = min(state["first"], day)
                state["last"] = max(state["last"], day)
                state["symbols"].add(row["symbol"])
                state["types"].add(row["analytical_type"])
                state["action_rows"] += int(row["economic_action"])
                yearly_ids[str(day.year)].add(security)
                quality_by_year[str(day.year)][row["quality"]] += 1
                if row["analytical_type"] != "RESEARCH_EQUITY_CANDIDATE":
                    exclusions[row["type_reason"]] += 1
    latest = max(r["last"] for r in identities.values())
    stable = [r for r in identities.values() if r["identity_basis"] == "OBSERVED_ISIN"]
    provisional = [r for r in identities.values() if r["identity_basis"] != "OBSERVED_ISIN"]
    result = dict(
        **lineage(profile),
        canonical_dataset_id=manifest["dataset_id"],
        identities=len(identities),
        stable_observed_isin_identities=len(stable),
        source_year_provisional_identities=len(provisional),
        latest_observed_session=latest.isoformat(),
        currently_observed_isin_identities=sum(r["last"] == latest for r in stable),
        historical_isin_identities_absent_latest=sum(r["last"] < latest for r in stable),
        provisional_identities_absent_latest=sum(r["last"] < latest for r in provisional),
        observed_isin_identities_with_multiple_symbols=sum(len(r["symbols"]) > 1 for r in stable),
        raw_economic_action_rows=sum(r["action_rows"] for r in identities.values()),
        noncandidate_rows_by_reason=dict(exclusions),
        identities_by_year={y: len(v) for y, v in sorted(yearly_ids.items())},
        quality_by_year={y: dict(v) for y, v in sorted(quality_by_year.items())},
        departure_semantics="ABSENT_LATEST_OBSERVATION_NOT_VERIFIED_DELISTING",
        classification_semantics="ANALYTICAL_RESEARCH_CANDIDATES_NOT_COMMON_EQUITY_FACTS",
        authoritative_common_equity_count=None,
        authoritative_delisted_count=None,
    )
    save(Path("docs/data/research-identity-profile.json"), result)
    save(output / "identity-profile.json", result)
    return result


def features_stage(output: Path) -> dict[str, Any]:
    from alphalens_data.research import ResearchCalendar

    sessions = ResearchCalendar.model_validate_json(
        (output / "research-calendar.json").read_bytes()
    )
    canon = json.loads((output / "canonical-manifest.json").read_bytes())
    if checksum(stable_json(canon["identity"])) != canon["dataset_id"] or (
        canon["identity"]["calendar_id"] != sessions.calendar_id
        or canon["identity"]["research_profile_id"] != sessions.profile.profile_id
    ):
        raise ValueError("P5_RESEARCH_MANIFEST_IDENTITY_MISMATCH")
    dates = sessions.dates
    date_index = {d: i for i, d in enumerate(dates)}
    registered = definitions(sessions)
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    quality_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    yearly: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    labels: dict[str, Counter[str]] = defaultdict(Counter)
    yearly_labels: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    security_availability = []
    technical = [d for d in registered if d.feature_family != "CROSS_SECTIONAL"]
    model_columns = [d.feature_name for d in registered]
    file_receipts: list[dict[str, Any]] = []
    row_count = 0
    missing_affected: Counter[str] = Counter()
    missing_slots = np.asarray(
        [s.price_status == "PRICE_OBSERVATION_MISSING" for s in sessions.sessions]
    )
    missing_windows = {d.feature_name: window_flag(missing_slots, d.lookback) for d in technical}
    for item in canon["identity"]["files"]:
        path = output / item["path"]
        if digest_file(path) != item["sha256"]:
            raise ValueError("P5_RESEARCH_PARTITION_CHECKSUM_MISMATCH")
        parquet = pq.ParquetFile(path)
        if json.loads(parquet.schema_arrow.metadata[b"research_lineage"]) != lineage(
            sessions.profile
        ):
            raise ValueError("P5_RESEARCH_PARTITION_LINEAGE_MISMATCH")
        table = parquet.read()
        table = table.take(
            pc.sort_indices(
                table, sort_keys=[("security_id", "ascending"), ("session_date", "ascending")]
            )
        )
        ids = table.column("security_id").to_pylist()
        starts = [0] + [i for i in range(1, len(ids)) if ids[i] != ids[i - 1]] + [len(ids)]
        rows = []
        for left, right in zip(starts, starts[1:], strict=False):
            security = ids[left]
            observations = table.slice(left, right - left).to_pylist()
            slots = [date_index[r["session_date"]] for r in observations]
            indexed = dict(zip(slots, observations, strict=True))
            opening: list[Decimal | None] = [None] * len(dates)
            closing: list[Decimal | None] = [None] * len(dates)
            arrays = {
                name: np.full(len(dates), np.nan) for name in ("close", "high", "low", "volume")
            }
            candidate = np.zeros(len(dates), dtype=bool)
            degraded = np.zeros(len(dates), dtype=bool)
            actions = np.zeros(len(dates), dtype=bool)
            for i, r in indexed.items():
                opening[i], closing[i] = r["open"], r["close"]
                candidate[i] = (
                    r["analytical_type"] == "RESEARCH_EQUITY_CANDIDATE"
                    and r["quality"] != "REJECTED"
                )
                degraded[i] = r["quality"] == "DEGRADED"
                actions[i] = r["economic_action"]
                for name in arrays:
                    if candidate[i]:
                        arrays[name][i] = float(r[name])
            numbers = {
                d.feature_name: numerical(
                    d, arrays["close"], arrays["high"], arrays["low"], arrays["volume"]
                )
                for d in technical
            }
            state = {d.feature_name: window_flag(degraded | actions, d.lookback) for d in technical}
            label_sets = {
                h: targets(sessions, opening, closing, candidate, actions, h)
                for h in (1, 5, 10, 20)
            }
            per_security: Counter[str] = Counter()
            for i, r in indexed.items():
                if r["analytical_type"] != "RESEARCH_EQUITY_CANDIDATE":
                    continue
                at = sessions.availability(dates[i])
                out = dict(
                    security_id=security,
                    session_date=dates[i],
                    decision_time=at,
                    canonical_record_id=r["canonical_record_id"],
                    quality=r["quality"],
                    analytical_type=r["analytical_type"],
                    economic_action=r["economic_action"],
                    open=r["open"],
                    close=r["close"],
                    symbol=r["symbol"],
                    isin=r["isin"],
                )
                row_count += 1
                per_security["total_rows"] += 1
                for d in technical:
                    n = d.feature_name
                    value = numbers[n][i] if at is not None else np.nan
                    out[n] = float(value) if np.isfinite(value) else None
                    status = (
                        "UNAVAILABLE"
                        if out[n] is None
                        else "DEGRADED"
                        if state[n][i]
                        else "AVAILABLE"
                    )
                    out[n + "__state"] = status
                    counts[n][status] += 1
                    quality_counts[r["quality"]][n][status] += 1
                    yearly[str(dates[i].year)][n][status] += 1
                    counts[n]["total"] += 1
                    per_security[n + "_available"] += int(out[n] is not None)
                    if out[n] is None and missing_windows[n][i]:
                        missing_affected[n] += 1
                out["momentum_percentile_20"] = None
                out["momentum_percentile_20__state"] = "UNAVAILABLE"
                feature_ok = at is not None and all(
                    out[d.feature_name] is not None for d in technical
                )
                missing_feature_slot = any(missing_windows[d.feature_name][i] for d in technical)
                for h, values in label_sets.items():
                    label = values[i]
                    label_ok = label["maturity"] == "MATURE" and not label["outcome_reasons"]
                    out[f"target_return_{h}"] = label["return_value"]
                    out[f"target_direction_{h}"] = label["direction_value"]
                    out[f"label_available_at_{h}"] = label["label_available_at"]
                    out[f"maturity_{h}"] = label["maturity"]
                    out[f"outcome_reasons_{h}"] = label["outcome_reasons"]
                    out[f"training_eligible_{h}"] = feature_ok and label_ok
                    out[f"exact_numerator_{h}"] = label["exact_numerator"]
                    out[f"exact_denominator_{h}"] = label["exact_denominator"]
                    labels[str(h)][label["maturity"]] += 1
                    yearly_labels[str(dates[i].year)][str(h)][label["maturity"]] += 1
                    if feature_ok and label_ok:
                        labels[str(h)]["TRAINING_ELIGIBLE"] += 1
                        yearly_labels[str(dates[i].year)][str(h)]["TRAINING_ELIGIBLE"] += 1
                    missing_outcome_slot = any(
                        missing_slots[j] for j in range(i + 1, min(len(dates), i + h + 1))
                    )
                    if missing_feature_slot or missing_outcome_slot:
                        missing_affected[f"candidate_training_rows_{h}"] += 1
                        yearly_labels[str(dates[i].year)][str(h)][
                            "MISSING_MUHURAT_REQUIRED_SLOT"
                        ] += 1
                    if (
                        label["maturity"] == "UNAVAILABLE"
                        and "REQUIRED_FUTURE_PRICE_UNAVAILABLE" in label["outcome_reasons"]
                        and any(
                            sessions.sessions[j].price_status == "PRICE_OBSERVATION_MISSING"
                            for j in range(i + 1, min(len(dates), i + h + 1))
                        )
                    ):
                        missing_affected[f"label_{h}"] += 1
                rows.append(out)
            security_availability.append(dict(security_id=security, **dict(per_security)))
        destination = output / "features-labels" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Explicit schema prevents all-null columns from becoming incompatible null types.
        fields = [
            ("security_id", pa.string()),
            ("session_date", pa.date32()),
            ("decision_time", pa.timestamp("us", tz="UTC")),
            ("canonical_record_id", pa.string()),
            ("quality", pa.string()),
            ("analytical_type", pa.string()),
            ("economic_action", pa.bool_()),
            ("open", pa.decimal128(38, 18)),
            ("close", pa.decimal128(38, 18)),
            ("symbol", pa.string()),
            ("isin", pa.string()),
        ]
        fields += [(n, pa.float64()) for n in model_columns]
        fields += [(n + "__state", pa.string()) for n in model_columns]
        for h in (1, 5, 10, 20):
            fields += [
                (f"target_return_{h}", pa.string()),
                (f"target_direction_{h}", pa.int8()),
                (f"label_available_at_{h}", pa.timestamp("us", tz="UTC")),
                (f"maturity_{h}", pa.string()),
                (f"outcome_reasons_{h}", pa.list_(pa.string())),
                (f"training_eligible_{h}", pa.bool_()),
                (f"exact_numerator_{h}", pa.string()),
                (f"exact_denominator_{h}", pa.string()),
            ]
        schema = pa.schema(
            fields,
            metadata={
                b"research_lineage": stable_json(lineage(sessions.profile)),
                b"feature_registry": b"p6.features.v1",
                b"label_contract": b"p7.research.labels.v1",
            },
        )
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), destination, compression="zstd")
        file_receipts.append(
            {
                "path": str(destination.relative_to(output)),
                "rows": len(rows),
                "sha256": digest_file(destination),
            }
        )
        print(
            json.dumps(dict(stage="features_labels", bucket=path.name, rows=len(rows))), flush=True
        )
    # Cross-section uses contemporaneous eligible return20 only, never today's universe.
    peer_tables = [
        pq.ParquetFile(output / r["path"]).read(
            columns=["security_id", "session_date", "return_20", "return_20__state"]
        )
        for r in file_receipts
    ]
    peers = pa.concat_tables(peer_tables).to_pandas()
    ranks = peers.groupby("session_date")["return_20"].rank(method="average")
    size = peers.groupby("session_date")["return_20"].transform("count")
    peers["percentile"] = (ranks - 1) / (size - 1)
    peers["degraded_peer"] = peers["return_20__state"] == "DEGRADED"
    peers["cross_degraded"] = peers.groupby("session_date")["degraded_peer"].transform("any")
    security_index = {r["security_id"]: r for r in security_availability}
    for h in (1, 5, 10, 20):
        labels[str(h)]["TRAINING_ELIGIBLE"] = 0
        for year in yearly_labels:
            yearly_labels[year][str(h)]["TRAINING_ELIGIBLE"] = 0
    # Two-pass artifacts avoid storing redundant full peer vectors in every row.
    offset = 0
    for r in file_receipts:
        p = output / r["path"]
        table = pq.ParquetFile(p).read()
        value = peers["percentile"].iloc[offset : offset + len(table)].to_numpy(dtype="float64")
        cross_degraded = peers["cross_degraded"].iloc[offset : offset + len(table)].to_numpy()
        offset += len(table)
        state_values = [
            "UNAVAILABLE" if not np.isfinite(v) else "DEGRADED" if flag else "AVAILABLE"
            for v, flag in zip(value, cross_degraded, strict=True)
        ]
        table = table.set_column(
            table.schema.get_field_index("momentum_percentile_20"),
            "momentum_percentile_20",
            pa.array(value, from_pandas=True),
        )
        table = table.set_column(
            table.schema.get_field_index("momentum_percentile_20__state"),
            "momentum_percentile_20__state",
            pa.array(state_values),
        )
        # P7 never admits a null selected cross-sectional feature.
        for h in (1, 5, 10, 20):
            eligibility = table.column(f"training_eligible_{h}").to_numpy() & np.isfinite(value)
            labels[str(h)]["TRAINING_ELIGIBLE"] += int(eligibility.sum())
            for day, accepted in zip(
                table.column("session_date").to_pylist(), eligibility, strict=True
            ):
                yearly_labels[str(day.year)][str(h)]["TRAINING_ELIGIBLE"] += int(accepted)
            table = table.set_column(
                table.schema.get_field_index(f"training_eligible_{h}"),
                f"training_eligible_{h}",
                pa.array(eligibility),
            )
        for day, v, status, quality, security in zip(
            table.column("session_date").to_pylist(),
            value,
            state_values,
            table.column("quality").to_pylist(),
            table.column("security_id").to_pylist(),
            strict=True,
        ):
            n = "momentum_percentile_20"
            counts[n][status] += 1
            quality_counts[quality][n][status] += 1
            counts[n]["total"] += 1
            yearly[str(day.year)][n][status] += 1
            security_index[security][n + "_available"] = security_index[security].get(
                n + "_available", 0
            ) + int(np.isfinite(v))
        pq.write_table(table, p, compression="zstd")
        r["sha256"] = digest_file(p)
    identity = dict(
        **lineage(sessions.profile),
        canonical_dataset_id=canon["dataset_id"],
        calendar_id=sessions.calendar_id,
        feature_definitions=[d.model_dump(mode="json") for d in registered],
        feature_engine="p6.research.partitioned.v1",
        label_engine="p7.research.labels.v1",
        quality_policy="ALLOW_DEGRADED_EXISTING_POLICY_RETAIN_P3_NO_REJECTION_OVERRIDE",
        feature_columns=model_columns,
        horizons=[1, 5, 10, 20],
        files=file_receipts,
        evaluation_plan_sha256=digest_file(Path("docs/ml/real-research-evaluation-plan.json")),
    )
    result = dict(
        identity=identity, dataset_id=checksum(stable_json(identity)), feature_rows=row_count
    )
    save(output / "supervised-manifest.json", result)
    save(Path("docs/data/research-dataset-identity.json"), result)
    report = dict(
        **lineage(sessions.profile),
        feature_rows=row_count,
        availability={
            n: dict(
                c,
                available_count=c["AVAILABLE"] + c["DEGRADED"],
                unavailable_count=c["UNAVAILABLE"],
                availability_percent=100 * (c["AVAILABLE"] + c["DEGRADED"]) / c["total"],
            )
            for n, c in counts.items()
        },
        by_year={
            y: {n: dict(c) for n, c in sorted(vals.items())} for y, vals in sorted(yearly.items())
        },
        missing_muhurat_affected=dict(missing_affected),
        missing_count_semantics=(
            "Required window contains a missing verified Muhurat slot; counts may overlap "
            "other insufficiencies and are not additive"
        ),
        by_quality={
            q: {n: dict(c) for n, c in values.items()} for q, values in quality_counts.items()
        },
        benchmark="UNAVAILABLE",
        fundamentals="UNAVAILABLE",
    )
    save(Path("docs/ml/feature-availability.json"), report)
    save(
        Path("docs/ml/label-distribution.json"),
        dict(
            **lineage(sessions.profile),
            horizons={h: dict(c) for h, c in labels.items()},
            by_year={
                y: {h: dict(c) for h, c in vals.items()}
                for y, vals in sorted(yearly_labels.items())
            },
            missing_muhurat_affected=dict(missing_affected),
        ),
    )
    pq.write_table(
        pa.Table.from_pylist(security_availability).replace_schema_metadata(
            {b"research_lineage": stable_json(lineage(sessions.profile))}
        ),
        output / "feature-availability-by-security.parquet",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("canonical", "profile", "features"), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.stage == "canonical":
        canonical_stage(args.output)
    elif args.stage == "profile":
        identity_profile(args.output)
    else:
        features_stage(args.output)


if __name__ == "__main__":
    main()
