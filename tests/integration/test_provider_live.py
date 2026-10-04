"""Real-provider gate remains blocked; TEST-ONLY fixtures cannot satisfy it."""

import pytest


@pytest.mark.provider_live
def test_licensed_representative_history() -> None:
    pytest.skip("BLOCKED: no approved vendor adapter, licensed access or historical sample")
