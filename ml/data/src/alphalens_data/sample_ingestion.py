"""P1 in-memory sample check; no selected provider, raw landing or scheduled ingestion."""

import json
from dataclasses import dataclass
from typing import Literal

from alphalens_data.contracts import Capability, CapabilityStatus, HistoryRequest
from alphalens_data.errors import DataContractError, ProviderNotSelectedError
from alphalens_data.manifest import SampleManifest
from alphalens_data.normalization import canonical_bytes, checksum
from alphalens_data.provider import MarketDataProvider
from alphalens_data.validation import eligible_at


@dataclass(frozen=True)
class SampleResult:
    manifest: SampleManifest
    normalized_payload: bytes


def evaluate_price_sample(
    provider: MarketDataProvider | None,
    request: HistoryRequest,
    *,
    origin: Literal["REAL_PROVIDER", "TEST_ONLY"] = "REAL_PROVIDER",
) -> SampleResult:
    """Never silently drop invalid/future rows or label test fixtures as real evidence."""
    if provider is None:
        raise ProviderNotSelectedError()
    capabilities = provider.get_capabilities()
    for capability in (Capability.EOD_PRICES, Capability.LICENSED_SAMPLE_USE):
        status = capabilities.status(capability)
        if status != CapabilityStatus.VERIFIED_SUPPORTED:
            raise DataContractError(f"{capability.value}_{status.value}")
    batch = provider.get_prices(request)
    if batch.provider_id != capabilities.provider_id:
        raise DataContractError("PROVIDER_ID_MISMATCH")
    if not batch.complete:
        raise DataContractError("INCOMPLETE_PROVIDER_BATCH")
    if not batch.records or not batch.raw_payload:
        raise DataContractError("EMPTY_PROVIDER_SAMPLE")
    for record in batch.records:
        if record.provenance.origin != origin:
            raise DataContractError("SAMPLE_ORIGIN_MISMATCH")
        if record.provenance.source_id != batch.provider_id:
            raise DataContractError("SOURCE_ID_MISMATCH")
        if record.security_id not in request.security_ids:
            raise DataContractError("UNREQUESTED_SECURITY")
        if not request.start_session <= record.session_date <= request.end_session:
            raise DataContractError("OUT_OF_RANGE_SESSION")
        if not eligible_at(record, request.as_of):
            raise DataContractError("POINT_IN_TIME_INELIGIBLE")
    payload = canonical_bytes(batch.records)
    manifest = SampleManifest(
        provider_id=batch.provider_id,
        request=request,
        record_count=len(json.loads(payload)),
        raw_sha256=checksum(batch.raw_payload),
        normalized_sha256=checksum(payload),
        origin=origin,
    )
    return SampleResult(manifest, payload)


def main() -> int:
    print(
        json.dumps(
            {
                "status": "BLOCKED",
                "error_code": "PROVIDER_NOT_SELECTED",
                "capabilities": "UNKNOWN",
                "scope": "PRODUCTION_PROVIDER",
                "production_provider_records_ingested": 0,
                "message": (
                    "Production provider clearance remains open; research fixtures are separate."
                ),
            },
            sort_keys=True,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
