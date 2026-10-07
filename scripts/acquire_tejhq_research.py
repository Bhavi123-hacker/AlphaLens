"""Acquire audited native Parquet bytes, verify them, then preserve through P2.

Public Hub resolve endpoint only. No HTML scraping, credentials, viewer conversion,
dataset substitution, price transformation or implicit historical availability.
"""

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_data.ingestion.contracts import ArtifactSpec, Classification, Versions
from alphalens_data.ingestion.repository import FileMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, publish, stable_json

DATASET = "tejhq/indian-markets"
REVISION = "14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98"
RIGHTS = "DECISIONS:D69:USER_AUTHORIZED_NONCOMMERCIAL_RESEARCH"


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def acquire_one(expected: dict[str, Any], incoming: Path, landing: RawLanding) -> dict[str, Any]:
    name = str(expected["path"])
    price_path = re.fullmatch(
        r"nse/year=20(?:1[0-9]|2[0-6])/nse_20(?:1[0-9]|2[0-6])\.parquet", name
    )
    if not price_path and not re.fullmatch(
        r"actions/nse_20(?:1[0-9]|2[0-6])\.parquet|symbol_history/nse\.parquet", name
    ):
        raise ValueError("UNEXPECTED_NSE_ARTIFACT_PATH")
    if price_path and name.split("/")[1][5:] != Path(name).stem[4:]:
        raise ValueError("YEAR_PATH_MISMATCH")
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{name}"
    target = incoming / name
    receipt_path = target.with_suffix(".receipt.json")
    if receipt_path.exists():
        receipt: dict[str, Any] = json.loads(receipt_path.read_bytes())
        if (
            not target.exists()
            or target.stat().st_size != expected["byte_size"]
            or digest_file(target) != expected["publisher_lfs_sha256"]
            or receipt["sha256"] != expected["publisher_lfs_sha256"]
            or receipt["revision"] != REVISION
        ):
            raise ValueError("EXISTING_DOWNLOAD_OR_RECEIPT_MISMATCH")
        manifest = json.loads(
            (landing.root / "manifests" / f"{receipt['p2_artifact_id']}.json").read_bytes()
        )
        from alphalens_data.ingestion.contracts import RawManifest

        landing.read(RawManifest.model_validate(manifest))
        return receipt
    if target.exists():
        raise ValueError("UNRECEIPTED_EXISTING_FILE_REQUIRES_REVIEW")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".download-part")
    if partial.exists():
        raise ValueError("INTERRUPTED_DOWNLOAD_REQUIRES_REVIEW")
    try:
        # URL is constructed solely from fixed public HTTPS repository/revision paths.
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("xb") as output:  # nosec B310
            if response.status != 200:
                raise ValueError("PUBLIC_DOWNLOAD_NOT_SUCCESSFUL")
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except urllib.error.HTTPError as exc:
        # Never print a redirected signed CDN URL or request headers.
        raise ValueError(f"PUBLIC_DOWNLOAD_HTTP_STATUS_{exc.code}") from None
    if (
        partial.stat().st_size != expected["byte_size"]
        or digest_file(partial) != expected["publisher_lfs_sha256"]
    ):
        raise ValueError("DOWNLOAD_CHECKSUM_OR_SIZE_MISMATCH_RETAINED_FOR_REVIEW")
    acquired_at = datetime.now(UTC).isoformat()
    # Exclusive publication avoids replacing an existing original on recovery.
    os.link(partial, target)
    partial.unlink()
    spec = ArtifactSpec(
        source="tejhq",
        dataset="indian-markets-nse",
        source_identifier=f"HF:{DATASET}@{REVISION}:{name}",
        original_filename=name,
        content_type="application/vnd.apache.parquet",
        classification=Classification.RESEARCH_ONLY,
        currency="INR",
        currency_evidence=f"HF:{DATASET}:NSE-cash-INR",
        rights_evidence=RIGHTS,
    )
    manifest, _ = landing.capture(target.read_bytes(), spec, Versions(parser="tejhq.parquet.v1"))
    FileMetadataRepository(landing.root / "metadata").save_manifest(manifest)
    receipt = {
        "dataset_id": DATASET,
        "revision": REVISION,
        "subset": "nse" if price_path else name.split("/")[0],
        "exchange": "NSE",
        "split": None,
        "split_basis": "PUBLISHER_YEAR_PARTITIONS_NO_DECLARED_TRAIN_TEST_SPLIT",
        "filename": name,
        "source_url": url,
        "byte_size": target.stat().st_size,
        "sha256": digest_file(target),
        "publisher_sha256": expected["publisher_lfs_sha256"],
        "checksum_verified": True,
        "acquired_at": acquired_at,
        "format_origin": "PUBLISHER_NATIVE_PARQUET",
        "auto_converted": False,
        "data_reality": "REAL_MARKET_OBSERVATIONS",
        "usage_classification": "RESEARCH_ONLY",
        "production_market_data_use": "NOT_CLEARED",
        "rights_evidence": RIGHTS,
        "p2_artifact_id": manifest.artifact_id,
        "raw_manifest": manifest.model_dump(mode="json"),
    }
    publish(receipt_path, stable_json(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incoming", type=Path, default=Path("data/incoming/tejhq") / REVISION)
    parser.add_argument("--raw-root", type=Path, default=Path("data/tejhq-research/p2"))
    parser.add_argument("--audit", type=Path, default=Path("docs/data/source-audit.json"))
    parser.add_argument("--references", type=Path)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_bytes())
    source = next(x for x in audit["detailed_candidates"] if x["candidate_id"] == DATASET)
    if source["repository_revision"] != REVISION:
        raise ValueError("AUDIT_REVISION_MISMATCH")
    receipts = []
    landing = RawLanding(args.raw_root)
    expected_files = source["expected_price_files"]
    if args.references:
        reference_plan = json.loads(args.references.read_bytes())
        if reference_plan["revision"] != REVISION:
            raise ValueError("REFERENCE_REVISION_MISMATCH")
        expected_files = expected_files + reference_plan["expected_reference_files"]
    for expected in expected_files:
        receipts.append(acquire_one(expected, args.incoming, landing))
        print(json.dumps({"file": expected["path"], "sha256_verified": True}), flush=True)
    manifest_name = (
        "acquisition-with-references.json" if args.references else "acquisition-manifest.json"
    )
    publish(
        args.incoming / manifest_name,
        stable_json(
            {
                "dataset_id": DATASET,
                "revision": REVISION,
                "files": receipts,
                "total_bytes": sum(x["byte_size"] for x in receipts),
                "data_reality": "REAL_MARKET_OBSERVATIONS",
                "usage_classification": "RESEARCH_ONLY",
                "production_market_data_use": "NOT_CLEARED",
            }
        ),
    )


if __name__ == "__main__":
    main()
