"""Bounded, checksum-verified persisted reads; no estimator loading or execution."""

import hashlib
import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow.dataset as ds
import pyarrow.parquet as pq

from alphalens_data.ingestion.storage import stable_json

from .core.config import Settings
from .core.domain_errors import APIError


def sha256(path: Path, deadline: float | None = None) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            if deadline is not None and time.monotonic() > deadline:
                raise APIError(
                    "QUERY_TIMEOUT", "Artifact verification exceeded the read budget.", 504
                )
            result.update(block)
    return result.hexdigest()


def confined(root: Path, reference: str) -> Path:
    path = (root / reference.replace("\\", "/")).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise APIError("ARTIFACT_INVALID", "Artifact reference is invalid.")
    return path


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise APIError("ARTIFACT_UNAVAILABLE", "Required persisted evidence is not installed.")
    if path.stat().st_size > 8 * 1024 * 1024:
        raise APIError("ARTIFACT_INVALID", "Metadata exceeds the configured contract.")
    try:
        data = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise APIError("ARTIFACT_INVALID", "Persisted metadata could not be validated.") from exc
    if not isinstance(data, dict):
        raise APIError("ARTIFACT_INVALID", "Metadata contract is invalid.")
    return data


class ArtifactReader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._slots = threading.BoundedSemaphore(settings.max_concurrent_reads)
        self._lock = threading.Lock()
        self._verified: dict[Path, tuple[int, int, str]] = {}

    @contextmanager
    def budget(self) -> Iterator[float]:
        if not self._slots.acquire(blocking=False):
            raise APIError("READ_CAPACITY", "Read capacity is occupied; retry later.", 429)
        try:
            yield time.monotonic() + self.settings.query_timeout_seconds
        finally:
            self._slots.release()

    def verify(self, path: Path, expected: str, deadline: float | None = None) -> Path:
        if not path.is_file():
            raise APIError("ARTIFACT_UNAVAILABLE", "Required persisted evidence is not installed.")
        before = path.stat()
        fingerprint = (before.st_size, before.st_mtime_ns, expected)
        with self._lock:
            cached = self._verified.get(path) == fingerprint
        if not cached and sha256(path, deadline) != expected:
            raise APIError(
                "ARTIFACT_CHECKSUM_FAILED", "Persisted evidence failed checksum validation."
            )
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise APIError("ARTIFACT_CHANGED", "Persisted evidence changed during the read.")
        with self._lock:
            self._verified[path] = fingerprint
        return path

    def manifest(self, name: str) -> dict[str, Any]:
        root = self.settings.research_data_root
        if root is None:
            raise APIError("DATASET_NOT_CONFIGURED", "Research dataset is not configured.")
        data = read_json(confined(root, name))
        identity = data.get("identity", {})
        if not isinstance(identity, dict):
            raise APIError("ARTIFACT_INVALID", "Dataset manifest contract is invalid.")
        expected = hashlib.sha256(stable_json(identity)).hexdigest()
        if data.get("dataset_id") != expected:
            raise APIError("DATASET_IDENTITY_FAILED", "Research dataset identity is invalid.")
        reality = "TEST_ONLY" if self.settings.test_only_evidence else "REAL_MARKET_OBSERVATIONS"
        usage = "TEST_ONLY" if self.settings.test_only_evidence else "RESEARCH_ONLY"
        if (
            identity.get("data_reality") != reality
            or identity.get("usage_classification") != usage
            or (
                not self.settings.test_only_evidence
                and identity.get("final_vintage") != "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
            )
        ):
            raise APIError(
                "CLASSIFICATION_BLOCKED", "Dataset is outside the research API contract."
            )
        return data

    def report(self, reference: str) -> dict[str, Any]:
        root = self.settings.research_report_root
        catalog = self.settings.catalog_path
        if root is None or catalog is None:
            raise APIError(
                "REPORTS_NOT_CONFIGURED", "Research reports and source index are required."
            )
        receipt = read_json(catalog.with_suffix(".sources.json"))
        expected = receipt.get("reports", {}).get(reference)
        if not expected:
            raise APIError(
                "ARTIFACT_NOT_PINNED", "Research report is not pinned in the read index."
            )
        return read_json(self.verify(confined(root, reference), str(expected)))

    def calendar(self) -> dict[str, Any]:
        manifest = self.manifest("canonical-manifest.json")
        root = self.settings.research_data_root
        if root is None:
            raise APIError("DATASET_NOT_CONFIGURED", "Research dataset is not configured.")
        calendar = read_json(confined(root, "research-calendar.json"))
        if hashlib.sha256(stable_json(calendar)).hexdigest() != manifest["identity"]["calendar_id"]:
            raise APIError(
                "CALENDAR_IDENTITY_FAILED", "Calendar evidence does not match the dataset."
            )
        return calendar

    def provenance(self) -> dict[str, Any]:
        source = self.report("data/dataset-identity.json")
        manifest = self.manifest("canonical-manifest.json")
        if (
            hashlib.sha256(stable_json(source["identity_inputs"])).hexdigest()
            != source["source_dataset_identity"]
            or source["source_dataset_identity"] != manifest["identity"]["source_identity"]
        ):
            raise APIError(
                "SOURCE_IDENTITY_FAILED", "Source provenance does not match the dataset."
            )
        return {
            "dataset": source["identity_inputs"]["source"],
            "revision": source["identity_inputs"]["revision"],
            "source_identity": source["source_dataset_identity"],
            "canonical_dataset_id": manifest["dataset_id"],
            "profile_id": manifest["identity"].get("research_profile_id"),
            "historical_revision_timing": manifest["identity"].get("historical_revision_timing"),
        }

    def partition(self, manifest: dict[str, Any], security_id: str, deadline: float) -> Path:
        bucket = int(hashlib.sha256(security_id.encode()).hexdigest()[:8], 16) % 64
        suffix = f"bucket-{bucket:02d}.parquet"
        files = [f for f in manifest["identity"]["files"] if f["path"].endswith(suffix)]
        root = self.settings.research_data_root
        if root is None or len(files) != 1:
            raise APIError("ARTIFACT_INVALID", "Partition evidence is invalid.")
        return self.verify(confined(root, files[0]["path"]), files[0]["sha256"], deadline)

    def rows(
        self,
        path: Path,
        columns: list[str],
        security_id: str | None,
        start: date | None,
        end: date | None,
        limit: int,
        offset: int,
        deadline: float,
    ) -> tuple[list[dict[str, Any]], bool]:
        condition = None
        for expr in (
            ds.field("security_id") == security_id if security_id else None,
            ds.field("session_date") >= start if start else None,
            ds.field("session_date") <= end if end else None,
        ):
            if expr is not None:
                condition = expr if condition is None else condition & expr
        # Every supported source is stored in ascending (security_id, session_date) order.
        # Validate ordering while scanning; never silently rely on arbitrary file order.
        scanner = ds.dataset(path, format="parquet").scanner(
            columns=columns, filter=condition, batch_size=4096, use_threads=False
        )
        result: list[dict[str, Any]] = []
        seen = 0
        previous: tuple[str, str] | None = None
        for batch in scanner.to_batches():
            if time.monotonic() > deadline:
                raise APIError("QUERY_TIMEOUT", "Persisted query exceeded the read budget.", 504)
            for row in batch.to_pylist():
                key = (str(row.get("security_id", "")), str(row.get("session_date", "")))
                if previous is not None and key < previous:
                    raise APIError("ARTIFACT_ORDER_INVALID", "Persisted row ordering is invalid.")
                previous = key
                if seen >= offset:
                    result.append(row)
                seen += 1
                if len(result) > limit:
                    return result[:limit], True
        return result, False

    def oos(self, report: dict[str, Any], deadline: float) -> Path:
        root = self.settings.research_run_root
        if root is None:
            raise APIError("ARTIFACTS_NOT_CONFIGURED", "Research run artifacts are not configured.")
        path = self.verify(
            confined(root / "p9", report["oos_file"]), report["oos_sha256"], deadline
        )
        metadata = pq.read_schema(path).metadata or {}
        if (
            metadata.get(b"role") != b"FOLD_TEST"
            or metadata.get(b"model_run_id", b"").decode() != report["model_run_id"]
            or metadata.get(b"dataset_id", b"").decode() != report["dataset_id"]
            or json.loads(metadata.get(b"model_identity", b"{}")) != report["model_identity"]
        ):
            raise APIError("OOS_LINEAGE_INVALID", "Prediction lineage is invalid.")
        return path
