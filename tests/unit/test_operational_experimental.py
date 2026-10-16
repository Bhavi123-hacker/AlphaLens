"""TEST_ONLY experimental preflight never manufactures features or promotes models."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from workers.daily.experimental import REQUIRED_REVIEWS, preflight, score
from workers.daily.features import definitions

from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_contracts import Access


def evidence() -> tuple[dict[str, Any], dict[str, Any], Access]:
    at = datetime(2026, 10, 16, 5, tzinfo=UTC)
    columns = [d.feature_name for d in definitions(at.date(), at)]
    bundle: dict[str, Any] = {
        "session": "2026-10-15",
        "decision_at": at.isoformat(),
        "received_at": at.isoformat(),
        "price_basis": "TEST_ONLY_COMPATIBLE_BASIS",
        "features": {
            name: {"state": "AVAILABLE", "value": 1.0, "available_at": at.isoformat()}
            for name in columns
        },
    }
    sha = checksum(stable_json(bundle))
    bundle["reviews"] = {
        name: {"reference": "TEST_ONLY_NOT_REAL_REVIEW", "bundle_sha256": sha}
        for name in REQUIRED_REVIEWS
    }
    access = Access(
        provider="upstox",
        account_status="ACTIVE",
        credential_configured=True,
        permission_reference="TEST_ONLY_PERMISSION",
        automation_permitted=True,
        retention_permitted=True,
        research_permitted=True,
        display_permitted=True,
        nse_verified=True,
        token_kind="READ_ONLY_ANALYTICS",
        operator_activation=True,
    )
    return {"model_identity": {"feature_columns": columns}}, bundle, access


def test_complete_test_only_bundle_is_experimental_never_accepted() -> None:
    report, bundle, access = evidence()
    result = preflight(report, bundle, access)
    assert result["eligible_for_experimental_scoring"]
    assert len(result["values"]) == 38
    assert not result["accepted_model"] and not result["accepted_rankings"]
    assert result["classification"] == "EXPERIMENTAL_UNVALIDATED_RESEARCH"


@pytest.mark.parametrize(
    "change", ["missing", "nan", "future", "basis", "review", "order", "rights"]
)
def test_ineligible_bundle_never_loads_an_estimator(change: str, tmp_path: Path) -> None:
    report, bundle, access = evidence()
    first = next(iter(bundle["features"]))
    if change == "missing":
        bundle["features"].pop(first)
    elif change == "nan":
        # Non-finite input cannot even enter the checksum-pinned JSON contract.
        bundle["features"][first]["value"] = None
    elif change == "future":
        bundle["features"][first]["available_at"] = "2027-01-01T00:00:00+00:00"
    elif change == "basis":
        bundle["price_basis"] = "UNKNOWN"
    elif change == "review":
        bundle["reviews"].pop("dated_peer_universe")
    elif change == "order":
        report["model_identity"]["feature_columns"].reverse()
    else:
        access = access.model_copy(update={"research_permitted": False})
    result = score(tmp_path, report, bundle, access)
    assert result["state"] == "INPUT_EVIDENCE_INCOMPLETE"
    assert result["values"] is None and result["predictions_generated"] == 0
    assert result["reasons"]
