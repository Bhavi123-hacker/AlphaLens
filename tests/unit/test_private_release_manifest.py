"""TEST_ONLY release boundaries; never schedules a job or opens a port."""

import json
from pathlib import Path
from typing import Any

import pytest
from scripts.verify_private_release_manifest import validate


def manifest() -> dict[str, Any]:
    return json.loads(Path("infra/release/alphalens-private.json").read_bytes())  # type: ignore[no-any-return]


def test_prepared_manifest_keeps_live_activation_closed() -> None:
    value = manifest()
    validate(value)
    assert value["collector_candidate_activation"] == "BLOCKED_APPROVAL"


@pytest.mark.parametrize(
    "key,value",
    [
        ("backend_host", "0.0.0.0"),
        ("database_host", "TEST_ONLY_PUBLIC_HOST"),
        ("public_ingress_enabled", True),
        ("trading_enabled", True),
        ("public_market_data_authorized", True),
        ("collector_candidate_activation", "ENABLED"),
        ("configured_securities", 3207),
        ("reserved_gets_per_day", 2400),
        ("collector_candidate_wrapper", "../outside.cmd"),
    ],
)
def test_unsafe_or_unapproved_manifest_is_rejected(key: str, value: Any) -> None:
    current = manifest()
    current[key] = value
    with pytest.raises(ValueError):
        validate(current)
