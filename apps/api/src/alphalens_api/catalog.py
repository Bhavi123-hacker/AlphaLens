"""Offline derived discovery index. Source datasets are never rewritten."""

import hashlib
import json
import sqlite3
from contextlib import closing
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .artifacts import ArtifactReader, confined, read_json, sha256
from .core.config import Settings
from .core.domain_errors import APIError

REPORTS = (
    "ml/real-model-runs.json",
    "ml/walk-forward-results.json",
    "ml/real-model-comparison.json",
    "backtesting/backtest-comparison.json",
    "backtesting/real-research-economic-audit.json",
    "data/dataset-identity.json",
)


def build_catalog(settings: Settings) -> dict[str, Any]:
    """One explicit offline setup operation, bounded by batches and identity groups."""
    root, output = settings.research_data_root, settings.catalog_path
    if root is None or output is None or settings.research_report_root is None:
        raise ValueError("Data root, report root and catalog path are required")
    if output.resolve().is_relative_to(root.resolve()) or (
        settings.research_run_root is not None
        and output.resolve().is_relative_to(settings.research_run_root.resolve())
    ):
        raise ValueError("Discovery index must be outside frozen data and run roots")
    if output.exists() or output.with_suffix(".sources.json").exists():
        raise ValueError("Discovery index already exists; choose a new output path")
    reader = ArtifactReader(settings)
    manifest = reader.manifest("canonical-manifest.json")
    source = read_json(confined(settings.research_report_root, "data/dataset-identity.json"))
    source_id = hashlib.sha256(
        json.dumps(source["identity_inputs"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        source_id != source["source_dataset_identity"]
        or source_id != manifest["identity"]["source_identity"]
    ):
        raise ValueError("Source identity does not match canonical evidence")
    identities: dict[tuple[str, ...], tuple[str, str, int]] = {}
    columns = [
        "security_id",
        "symbol",
        "isin",
        "name",
        "analytical_type",
        "type_reason",
        "identity_basis",
        "session_date",
    ]
    for entry in manifest["identity"]["files"]:
        path = reader.verify(confined(root, entry["path"]), entry["sha256"])
        for batch in pq.ParquetFile(path).iter_batches(batch_size=65536, columns=columns):
            table = pa.Table.from_batches([batch])
            groups = table.group_by(columns[:-1], use_threads=False).aggregate(
                [("session_date", "min"), ("session_date", "max"), ("session_date", "count")]
            )
            for row in groups.to_pylist():
                key = tuple(str(row[c] or "") for c in columns[:-1])
                first, last = str(row["session_date_min"]), str(row["session_date_max"])
                count = int(row["session_date_count"])
                old = identities.get(key)
                identities[key] = (
                    min(first, old[0]) if old else first,
                    max(last, old[1]) if old else last,
                    count + old[2] if old else count,
                )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".building.sqlite")
    if temporary.exists():
        raise ValueError("Unfinished discovery index exists; choose a new output path")
    try:
        with closing(sqlite3.connect(temporary)) as connection, connection:
            connection.execute(
                "CREATE TABLE aliases(security_id TEXT,symbol TEXT,isin TEXT,name TEXT,"
                "analytical_type TEXT,type_reason TEXT,identity_basis TEXT,"
                "first_observed TEXT,last_observed TEXT,observation_count INTEGER)"
            )
            connection.executemany(
                "INSERT INTO aliases VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(*key, *value) for key, value in sorted(identities.items())],
            )
            connection.execute("CREATE INDEX alias_security ON aliases(security_id)")
            connection.execute("CREATE INDEX alias_symbol ON aliases(symbol)")
            connection.execute(
                "CREATE TABLE securities AS SELECT security_id,MIN(first_observed) first_observed,"
                "MAX(last_observed) last_observed,SUM(observation_count) observation_count "
                "FROM aliases GROUP BY security_id ORDER BY security_id"
            )
            connection.execute("CREATE UNIQUE INDEX security_identity ON securities(security_id)")
        receipt = {
            "version": "p17.discovery.v1",
            "canonical_dataset_id": manifest["dataset_id"],
            "catalog_sha256": sha256(temporary),
            "reports": {
                name: sha256(confined(settings.research_report_root, name)) for name in REPORTS
            },
            "alias_groups": len(identities),
            "data_reality": manifest["identity"]["data_reality"],
            "usage_classification": manifest["identity"]["usage_classification"],
            "final_vintage": manifest["identity"].get("final_vintage"),
            "source_identity": manifest["identity"]["source_identity"],
            "source_dataset": source["identity_inputs"]["source"],
            "source_revision": source["identity_inputs"]["revision"],
        }
        output.with_suffix(".sources.json").write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        temporary.replace(output)
        return receipt
    except BaseException:
        # Keep an incomplete index for inspection; it is never accepted as published.
        raise


class Catalog:
    def __init__(self, reader: ArtifactReader) -> None:
        self.reader = reader

    def connection(self) -> sqlite3.Connection:
        path = self.reader.settings.catalog_path
        if path is None:
            raise APIError("CATALOG_NOT_CONFIGURED", "Stock discovery index is not configured.")
        receipt = read_json(path.with_suffix(".sources.json"))
        manifest = self.reader.manifest("canonical-manifest.json")
        if receipt.get("canonical_dataset_id") != manifest["dataset_id"]:
            raise APIError("CATALOG_IDENTITY_FAILED", "Discovery index does not match the dataset.")
        self.reader.verify(path, str(receipt.get("catalog_sha256")))
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        return connection

    def search(self, query: str, limit: int, offset: int) -> tuple[list[dict[str, Any]], bool]:
        with closing(self.connection()) as connection:
            # Substring search is parameterized. Percent/underscore have no wildcard meaning.
            rows = connection.execute(
                "SELECT s.*,a.symbol latest_observed_symbol,a.name latest_observed_name,"
                "a.isin latest_observed_isin,a.analytical_type,a.identity_basis FROM securities s "
                "JOIN aliases a ON a.rowid=(SELECT rowid FROM aliases last "
                "WHERE last.security_id=s.security_id ORDER BY last.last_observed DESC,"
                "last.first_observed DESC,last.symbol,last.isin,last.name LIMIT 1) "
                "WHERE ?='' OR EXISTS "
                "(SELECT 1 FROM aliases a WHERE a.security_id=s.security_id AND "
                "(instr(lower(a.symbol),lower(?))>0 OR instr(lower(a.name),lower(?))>0 "
                "OR instr(lower(a.isin),lower(?))>0 OR instr(lower(a.security_id),lower(?))>0)) "
                "ORDER BY s.security_id LIMIT ? OFFSET ?",
                (query, query, query, query, query, limit + 1, offset),
            ).fetchall()
        return [dict(row) for row in rows[:limit]], len(rows) > limit

    def security(self, security_id: str) -> dict[str, Any]:
        with closing(self.connection()) as connection:
            row = connection.execute(
                "SELECT * FROM securities WHERE security_id=?", (security_id,)
            ).fetchone()
            if row is None:
                raise APIError("SECURITY_NOT_FOUND", "Security identity was not found.", 404)
            aliases = connection.execute(
                "SELECT * FROM aliases WHERE security_id=? "
                "ORDER BY first_observed,last_observed,symbol,isin,name",
                (security_id,),
            ).fetchall()
        return {
            **dict(row),
            "observed_identity_evidence": [dict(a) for a in aliases],
            "identity_semantics": "DATED_OBSERVATIONS_NOT_AUTHORITATIVE_LISTING_INTERVALS",
            "security_type_semantics": "RESEARCH_ANALYTICAL_TYPE_NOT_PRODUCTION_COMMON_EQUITY",
            "authoritative_listing_status": "UNAVAILABLE",
            "fundamental_pit_analysis": "UNAVAILABLE",
            "benchmark_status": "UNAVAILABLE",
            "price_basis": "RAW_UNADJUSTED",
        }


def bucket_for(security_id: str) -> int:
    return int(hashlib.sha256(security_id.encode()).hexdigest()[:8], 16) % 64
