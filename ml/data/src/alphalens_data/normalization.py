"""Canonical serialization only. Vendor parsing belongs to the selected adapter."""

import hashlib
import json
from collections.abc import Sequence

from alphalens_data.contracts import Record
from alphalens_data.errors import DataContractError


def canonical_bytes(records: Sequence[Record]) -> bytes:
    """Stable ordering preserves revisions; ambiguous duplicate identities fail."""
    seen: dict[tuple[str, str, str, str, str], str] = {}
    for record in records:
        key = (
            type(record).__name__,
            record.security_id,
            record.provenance.source_id,
            record.provenance.source_record_id,
            record.provenance.revision_id,
        )
        value = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        if key in seen and seen[key] != value:
            raise DataContractError("CONFLICTING_DUPLICATE_REVISION")
        seen[key] = value
    return ("[" + ",".join(sorted(seen.values())) + "]").encode("utf-8")


def checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
