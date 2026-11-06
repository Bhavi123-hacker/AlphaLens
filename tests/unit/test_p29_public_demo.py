"""Public fixtures contain original synthetic examples, never private or market input."""

import json

from scripts.build_p29_public_demo import generate


def test_generated_demo_is_deterministic_and_exchange_explicit() -> None:
    a, b = generate(), generate()
    assert a == b
    assert a["classification"] == "TEST_ONLY_SYNTHETIC"
    assert a["real_market_data"] is False and a["private_api_calls"] is False
    assert len(a["instruments"]) == 128
    assert len(a["dates"]) == 90 and a["dates"] == sorted(set(a["dates"]))
    for instrument in a["instruments"]:
        assert instrument["exchange"] == "DEMO_NOT_NSE" and instrument["isin"] is None
        assert instrument["passport"]["confidence_percentage"] is None
        for op, close, low, high, volume in instrument["prices"]:
            assert 0 < low <= min(op, close) <= max(op, close) <= high and volume >= 0
    text = json.dumps(a)
    assert "RELIANCE" not in text and "postgresql://" not in text
    assert a["instruments"][0]["sma20"][:19] == [None] * 19
