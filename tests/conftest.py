"""TEST-ONLY constructed edge cases. NOT market history or provider evidence."""

import json
import os
import secrets
import tempfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from scripts.build_p8_test_fixture import prepare
from scripts.build_p9_training_snapshots import snapshots

from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.contracts import HistoryRequest, PriceBar, Provenance
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import SupervisedDataset

EvaluationSource = tuple[
    CanonicalBatch,
    FeatureDataset,
    dict[int, SupervisedDataset],
    dict[int, dict[str, SupervisedDataset]],
]


def pytest_configure(config: pytest.Config) -> None:
    """Keep Windows hash-nested artifacts below native hard-link path limits.

    Each run gets an absent owned child: pytest must never reset another run or
    a user-selected parent. Explicit --basetemp remains the user's responsibility.
    """
    if os.name != "nt" or config.option.basetemp is not None:
        return
    configured = os.environ.get("ALPHALENS_TEST_TEMP_ROOT")
    root = Path(configured) if configured else Path(tempfile.gettempdir()).anchor / Path("al-tests")
    if not root.is_absolute() or len(str(root.resolve())) > 32:
        raise pytest.UsageError("ALPHALENS_TEST_TEMP_ROOT needs a short absolute root (<=32 chars)")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"r{os.getpid()}-{secrets.token_hex(3)}"
    if target.exists():
        raise pytest.UsageError("Refusing to reset an existing verification workspace")
    config.option.basetemp = str(target)


@pytest.fixture(scope="session")
def evaluation_source(tmp_path_factory: pytest.TempPathFactory) -> EvaluationSource:
    """One independently constructed P2–P9 capture shared by P9/P10 regression cases."""
    root = tmp_path_factory.mktemp("TEST_ONLY_evaluation")
    aligned = prepare(root)
    features = FeatureDataset.model_validate_json((root / "features.json").read_bytes())
    batch = CanonicalBatch.model_validate(
        json.loads((root / "canonical/canonical-input.json").read_bytes())["batch"]
    )
    return batch, features, aligned, snapshots(root, features)


def make_test_only_provenance(**changes: object) -> Provenance:
    values: dict[str, object] = {
        "source_id": "TEST_ONLY",
        "source_record_id": "TEST_ONLY_BAR_1",
        "revision_id": "TEST_ONLY_REVISION_1",
        "ingested_at": datetime(2000, 1, 10, tzinfo=UTC),
        "published_at": datetime(2000, 1, 3, 10, tzinfo=UTC),
        "available_at": datetime(2000, 1, 3, 11, tzinfo=UTC),
        "availability_basis": "VERIFIED_PUBLICATION",
        "availability_evidence": "TEST-ONLY constructed eligibility fixture",
        "origin": "TEST_ONLY",
    }
    return Provenance.model_validate(values | changes)


def make_test_only_price(**changes: object) -> PriceBar:
    values: dict[str, object] = {
        "security_id": "TEST_ONLY_SECURITY",
        "provenance": make_test_only_provenance(),
        "session_date": date(2000, 1, 3),
        "session_close_at": datetime(2000, 1, 3, 10, tzinfo=UTC),
        "open": Decimal("10"),
        "high": Decimal("12"),
        "low": Decimal("9"),
        "close": Decimal("11"),
        "volume": 5,
    }
    return PriceBar.model_validate(values | changes)


@pytest.fixture
def price() -> PriceBar:
    return make_test_only_price()


@pytest.fixture
def history_request() -> HistoryRequest:
    return HistoryRequest(
        security_ids=("TEST_ONLY_SECURITY",),
        start_session=date(2000, 1, 3),
        end_session=date(2000, 1, 3),
        as_of=datetime(2000, 1, 11, tzinfo=UTC),
    )
