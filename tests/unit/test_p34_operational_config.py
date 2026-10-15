"""TEST_ONLY CLI namespaces; no credential, provider or scheduling access."""

from pathlib import Path

import pytest
from workers.providers.daily import configured_pipeline

from alphalens_data.errors import DataContractError


def test_private_config_and_readiness_resolve_the_same_isolated_root(tmp_path: Path) -> None:
    expected = tmp_path / ".local-data/p34-private-operational-eod"
    assert configured_pipeline({"pipeline_root": str(expected)}, tmp_path) == expected.resolve()
    assert configured_pipeline({}, tmp_path) == tmp_path / ".local-data/p30-operational-data"


@pytest.mark.parametrize(
    "relative",
    [
        "../foreign",
        ".local-data/p32-runtime",
        ".local-data",
        ".local-data/p34-private-operational-eod/nested",
    ],
)
def test_non_operational_or_escaped_roots_are_refused(tmp_path: Path, relative: str) -> None:
    with pytest.raises(DataContractError):
        configured_pipeline({"pipeline_root": str(tmp_path / relative)}, tmp_path)
