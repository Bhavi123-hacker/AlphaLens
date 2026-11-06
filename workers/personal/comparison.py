"""Same-provider observed price indexing/correlation; adjustment compatibility unknown."""

import statistics
from contextlib import suppress
from fractions import Fraction
from typing import Any

from .analytics import mark, observed


def compare(items: dict[str, dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    available = {
        k: {r["session"]: r for r in items[k].get("rows", [])[-252:]}
        for k in keys
        if k in items and items[k].get("rows")
    }
    dates = sorted(set().union(*(set(rows) for rows in available.values()))) if available else []
    common = (
        sorted(set.intersection(*(set(rows) for rows in available.values()))) if available else []
    )
    anchor = common[0] if common else None
    series = []
    for key, rows in available.items():
        base = Fraction(rows[anchor]["close"]) if anchor else None
        series.append(
            {
                "instrument_key": key,
                "name": items[key]["symbol"],
                "values": [
                    float(Fraction(rows[day]["close"]) / base * 100)
                    if base and day in rows and day >= anchor
                    else None
                    for day in dates
                ],
            }
        )
    correlations = []
    for index, left in enumerate(available):
        for right in list(available)[index + 1 :]:
            a = [
                float(
                    Fraction(available[left][day]["close"])
                    / Fraction(available[left][prior]["close"])
                    - 1
                )
                for prior, day in zip(common[:-1], common[1:], strict=True)
            ]
            b = [
                float(
                    Fraction(available[right][day]["close"])
                    / Fraction(available[right][prior]["close"])
                    - 1
                )
                for prior, day in zip(common[:-1], common[1:], strict=True)
            ]
            value = None
            if len(a) >= 20:
                with suppress(statistics.StatisticsError):
                    value = statistics.correlation(a, b)
            correlations.append(
                {
                    "left": items[left]["symbol"],
                    "right": items[right]["symbol"],
                    "value": value,
                    "shared_intervals": len(a),
                    "minimum_display_intervals": 20,
                }
            )
    return {
        "dates": dates,
        "anchor": anchor,
        "series": series,
        "correlations": correlations,
        "rows": [
            {
                "instrument_key": k,
                "symbol": items[k]["symbol"],
                "mark": mark(items[k]),
                "metrics": observed(items[k].get("rows", [])[-252:]),
            }
            for k in keys
            if k in items
        ],
        "selected_count": len(keys),
        "history_count": len(available),
        "missing_histories": [k for k in keys if k not in available],
        "source": "UPSTOX_OBSERVED_CANDLE_DATES_ONLY",
        "adjustment_compatibility": "UNVERIFIED_NOT_TOTAL_INVESTMENT_RETURNS",
        "calendar_completeness": "UNVERIFIED",
        "expires_in_seconds": min(
            (
                max(0, i.get("cache_ttl_seconds", 600) - i.get("cache_age_seconds", 0))
                for i in items.values()
            ),
            default=0,
        ),
    }
