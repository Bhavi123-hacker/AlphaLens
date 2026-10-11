"""Evidence-gated provider status. Network metadata never implies price clearance."""

import json
import time
from datetime import UTC, date, datetime
from http.client import HTTPException, HTTPSConnection
from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum

from .contracts import Provider

PINNED_REVISION = "14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98"
BASELINE = "f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2"


def publication_status(payload: bytes, received_at: datetime) -> dict[str, Any]:
    """Publisher-reported metadata only, never proof of prices or exchange clocks."""
    if len(payload) > 10000 or received_at.tzinfo is None:
        raise DataContractError("PUBLICATION_METADATA_INVALID")
    try:
        value = json.loads(payload)
        day = date.fromisoformat(value["trading_date"])
        clocks = {
            name: datetime.fromisoformat(value[name].replace("Z", "+00:00"))
            for name in ("prices_published_at", "derived_published_at", "generated_at")
            if value.get(name) is not None
        }
        if (
            value["stage"] not in {"prices", "derived"}
            or "prices_published_at" not in clocks
            or "generated_at" not in clocks
            or any(t.tzinfo is None or t > received_at for t in clocks.values())
            or day > received_at.date()
            or clocks["prices_published_at"] > clocks["generated_at"]
            or (value["stage"] == "derived" and "derived_published_at" not in clocks)
            or (
                "derived_published_at" in clocks
                and not clocks["prices_published_at"]
                <= clocks["derived_published_at"]
                <= clocks["generated_at"]
            )
        ):
            raise ValueError
    except (KeyError, ValueError, TypeError, AttributeError):
        raise DataContractError("PUBLICATION_METADATA_SCHEMA_INVALID") from None
    return {
        "availability": "PUBLIC_STATUS_REACHABLE",
        "advertised_session": day.isoformat(),
        "publisher_stage": value["stage"],
        "publisher_reported_clocks": {k: t.isoformat() for k, t in clocks.items()},
        "received_at": received_at.isoformat(),
        "payload_sha256": checksum(payload),
        "evidence_status": "PUBLISHER_REPORTED_NOT_VERIFIED_SESSION_OBSERVATIONS",
        "exchange_publication_at": None,
        "price_download_attempted": False,
        "live_data_activation": "BLOCKED",
    }


def check_publication() -> dict[str, Any]:
    """One finite keyless status request; never fetches prices, redirects or retries 429."""
    connection = HTTPSConnection("api.tejhq.dev", timeout=10)
    try:
        connection.request("GET", "/v1/status")
        response = connection.getresponse()
        if response.status != 200:
            return dict(
                availability="RATE_LIMITED" if response.status == 429 else "STATUS_UNAVAILABLE",
                http_status=response.status,
                live_data_activation="BLOCKED",
                price_download_attempted=False,
            )
        return publication_status(response.read(10001), datetime.now(UTC))
    except (OSError, HTTPException, DataContractError):
        return dict(
            availability="STATUS_UNAVAILABLE_OR_SCHEMA_REJECTED",
            live_data_activation="BLOCKED",
            price_download_attempted=False,
        )
    finally:
        connection.close()


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
