"""Two official authenticated GETs for explicit NSE holiday/timing metadata only."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from workers.providers.calendar import calendar, nse_holidays, nse_timing
from workers.providers.store import ProviderStore
from workers.providers.upstox import UpstoxClient


def main() -> None:
    root = Path(__file__).resolve().parents[1] / ".local-data/p30-upstox-validation"
    client = UpstoxClient(ProviderStore(root), budget=2)
    holidays = client.get("holidays")
    timing = client.get("timings", end=date(2026, 10, 13))
    sessions = nse_holidays(holidays)
    receipt = {
        "schema": "p30.provider-session-metadata.v1",
        "holiday_status": holidays.status,
        "timings_status": timing.status,
        "holiday_nse_explicit_facts": len(sessions),
        "latest_daily_session_timing": nse_timing(timing, date(2026, 10, 13)),
        "calls": client.calls,
        "calendar": calendar(sessions).model_dump(mode="json"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
    (root / "provider-calendar.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "calendar"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps(
                {"state": "PROVIDER_CALENDAR_REJECTED", "error_category": type(exc).__name__}
            )
        )
        raise SystemExit(1) from None
