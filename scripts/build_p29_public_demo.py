"""Deterministic TEST_ONLY public demo: entirely generated, no market/API/account input."""

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from math import cos, sin
from pathlib import Path
from typing import Any

import numpy as np
from workers.daily.features import definitions
from workers.intelligence.methods import regime

from alphalens_features.research import numerical

FIELDS = (
    "return_1",
    "return_20",
    "volatility_20",
    "distance_sma_20",
    "drawdown_20",
    "rsi_14",
    "volume_ratio_20",
    "sma_20",
)


def generate() -> dict[str, Any]:
    days: list[date] = []
    day = date(2024, 1, 2)
    while len(days) < 90:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    registry = {d.feature_name: d for d in definitions(days[-1], datetime(2024, 6, 1, tzinfo=UTC))}
    instruments = []
    cohorts: list[list[dict[str, Any]]] = [[] for _ in days]
    for i in range(128):
        prices = []
        prior: float = 80 + i * 7
        for j, _ in enumerate(days):
            # Original procedural teaching series, no actual NSE instrument/price input.
            close = round(
                (80 + i * 7)
                * (1 + 0.0008 * j + 0.06 * sin(j / 8 + i) + 0.02 * cos(j / 3 + i * 0.7)),
                2,
            )
            op = round(prior * (1 + 0.002 * sin(j + i)), 2)
            high = round(max(op, close) * (1 + 0.01 + 0.003 * cos(j)), 2)
            low = round(min(op, close) * (1 - 0.01 - 0.003 * sin(j)), 2)
            volume = int(10000 + i * 200 + abs(sin(j / 4 + i)) * 50000)
            prices.append([op, close, low, high, volume])
            prior = close
        close_a = np.array([p[1] for p in prices], dtype="float64")
        high_a = np.array([p[3] for p in prices], dtype="float64")
        low_a = np.array([p[2] for p in prices], dtype="float64")
        volume_a = np.array([p[4] for p in prices], dtype="float64")
        features = {f: numerical(registry[f], close_a, high_a, low_a, volume_a) for f in FIELDS}

        def value(field: str, at: int, feature_values: dict[str, Any] = features) -> float | None:
            v = float(feature_values[field][at])
            return round(v, 6) if np.isfinite(v) else None

        identity = f"TEST_ONLY:DEMO{i + 1:03}"
        for j, session in enumerate(days):
            cohorts[j].append(
                {
                    "security_id": identity,
                    "session": str(session),
                    "close": str(prices[j][1]),
                    "quality": "VALID",
                    **{f: value(f, j) for f in FIELDS},
                }
            )
        latest = {f: value(f, len(days) - 1) for f in FIELDS}
        instruments.append(
            {
                "id": identity,
                "symbol": f"DEMO{i + 1:03}",
                "name": f"Synthetic Example {i + 1:03}",
                "exchange": "DEMO_NOT_NSE",
                "isin": None,
                "group": [
                    "Synthetic Group A",
                    "Synthetic Group B",
                    "Synthetic Group C",
                    "Synthetic Group D",
                ][i % 4],
                "prices": prices,
                "normalized": [round(float(v / close_a[0] * 100), 4) for v in close_a],
                "sma20": [value("sma_20", j) for j in range(len(days))],
                "rsi14": [value("rsi_14", j) for j in range(len(days))],
                "drawdown20": [value("drawdown_20", j) for j in range(len(days))],
                "latest": {"close": prices[-1][1], "volume": prices[-1][4], **latest},
                "passport": {
                    "classification": "TEST_ONLY_SYNTHETIC_NOT_REAL_MARKET_DATA",
                    "source": "ORIGINAL_DETERMINISTIC_GENERATOR_V1",
                    "price_basis": "GENERATED_TEACHING_SERIES",
                    "observed_slots": len(days),
                    "features_available": sum(v is not None for v in latest.values()),
                    "features_shown": len(FIELDS),
                    "model": "NONE",
                    "current_inference": "UNAVAILABLE",
                    "corporate_actions": "NOT_A_REAL_INSTRUMENT",
                    "official_calendar": "UNAVAILABLE_SYNTHETIC_WEEKDAY_AXIS",
                    "confidence_percentage": None,
                },
            }
        )
    timeline = [regime(rows, session) for rows, session in zip(cohorts, days, strict=True)]
    for result in timeline:
        result["mode"] = "TEST_ONLY_SYNTHETIC_DEMONSTRATION"
        result["interpretation"] = "NOT_A_REAL_MARKET_STATE_OR_PERFORMANCE_CLAIM"
    return {
        "version": "p29.public-demo.v1",
        "classification": "TEST_ONLY_SYNTHETIC",
        "real_market_data": False,
        "private_api_calls": False,
        "prediction_or_trading": False,
        "dates": [str(d) for d in days],
        "instruments": instruments,
        "regimes": timeline,
        "limitations": [
            "No real NSE observations or stock recommendations",
            "All displayed instruments/prices are generated examples",
            "No trained model or measured accuracy is included",
            "Synthetic weekdays are not the official NSE calendar",
            "No private research, account, credential or financial record is bundled",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate()
    if (
        args.output.exists()
        and json.loads(args.output.read_bytes()).get("classification") != "TEST_ONLY_SYNTHETIC"
    ):
        raise ValueError("EXISTING_NONDEMO_FILE_PRESERVED")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, separators=(",", ":"), allow_nan=False), encoding="utf-8"
    )
    print("TEST_ONLY_PUBLIC_DEMO_GENERATED_ZERO_MARKET_OR_API_INPUT")


if __name__ == "__main__":
    main()
