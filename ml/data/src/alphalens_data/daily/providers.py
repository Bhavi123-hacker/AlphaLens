"""Evidence-gated provider status. Network metadata never implies price clearance."""

import json
import time
from http.client import HTTPException, HTTPSConnection
from typing import Any

from alphalens_data.errors import DataContractError

from .contracts import Provider

PINNED_REVISION = "14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98"
BASELINE = "f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2"


def assessment() -> Provider:
    return Provider(
        revision=PINNED_REVISION,
        status="SOURCE_CONDITIONALLY_SUPPORTED",
        evidence_reference="D69_PINNED_ARCHIVE_ONLY_P19_PROVIDER_AUDIT",
        reasons=("ONGOING_AUTOMATION_RIGHTS_NOT_ESTABLISHED", "NO_VERIFIED_NEW_SESSION_SOURCE"),
    )


def check_source(*, network: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = assessment().model_dump(mode="json")
    result.update(live_data_activation="BLOCKED", price_download_attempted=False)
    if not network:
        result["availability"] = "NOT_CHECKED_OFFLINE"
        return result
    # Fixed public API only; no credentials, arbitrary URL, browser scraping or price download.
    for attempt in range(3):
        try:
            connection = HTTPSConnection("huggingface.co", timeout=10)
            try:
                connection.request("GET", "/api/datasets/tejhq/indian-markets")
                response = connection.getresponse()
                if response.status != 200:
                    raise OSError("SOURCE_METADATA_UNAVAILABLE")
                payload = response.read(2_000_001)
            finally:
                connection.close()
            if len(payload) > 2_000_000:
                raise DataContractError("SOURCE_METADATA_SIZE_LIMIT")
            metadata = json.loads(payload)
            result.update(
                availability="PUBLIC_METADATA_REACHABLE",
                observed_revision=metadata["sha"],
                last_modified=metadata.get("lastModified"),
            )
            return result
        except (HTTPException, TimeoutError, OSError):
            if attempt < 2:
                time.sleep(0.5 * (2**attempt))
    result["availability"] = "SOURCE_UNAVAILABLE_RETRY_LIMIT"
    return result
