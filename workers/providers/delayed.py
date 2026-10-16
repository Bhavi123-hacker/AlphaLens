"""One-second private presentation delay, independent of quote time classification."""

import time
from typing import Any

from .upstox import Reply

MODE = "DELAYED_AUTHENTICATED_PROVIDER_PRICE"
DELAY_SECONDS = 1.0


def presentation(reply: Reply, strict: dict[str, Any], indicative: Any) -> dict[str, Any] | None:
    """Delay only eligible observations. Never use waiting as chronology evidence."""
    if strict.get("state") != "VALIDATED_SNAPSHOT" and indicative is None:
        return None
    anchor = reply.received_monotonic
    if anchor is None:
        return None
    elapsed = time.perf_counter() - anchor
    if not 0 <= elapsed < 30:
        return None
    if elapsed < DELAY_SECONDS:
        time.sleep(DELAY_SECONDS - elapsed)
    return {
        "mode": MODE,
        "intentional_delay_seconds": DELAY_SECONDS,
        "elapsed_since_network_receipt_seconds": time.perf_counter() - anchor,
        "classification": strict["state"] if indicative is None else indicative["state"],
        "local_network_received_at": reply.received_at.isoformat(),
        "receipt_unchanged": True,
        "delay_proves_chronology": False,
        "financial_input_eligible": False,
    }
