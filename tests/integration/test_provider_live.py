"""Production/live provider gate is separate from the accepted research-fixture gate."""

import pytest


@pytest.mark.provider_live
def test_licensed_representative_history() -> None:
    pytest.skip("BLOCKED: production/live source clearance and adapter remain open")
