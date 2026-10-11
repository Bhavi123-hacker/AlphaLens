"""Bounded process-lifetime observations; no usernames, securities or arbitrary labels."""

import threading
import time
from collections import Counter, deque
from typing import Any

FAMILIES = (
    "auth",
    "stocks",
    "research",
    "models",
    "backtests",
    "portfolios",
    "paper",
    "alerts",
    "daily",
    "operations",
    "health",
    "system",
    "other",
)


class Metrics:
    def __init__(self) -> None:
        self.started = time.time()
        self.lock = threading.Lock()
        self.counts: Counter[str] = Counter()
        self.latencies: dict[str, deque[float]] = {}

    def observe(self, path: str, status: int, duration: float) -> str:
        part = path.removeprefix("/api/v1/").split("/", 1)[0]
        family = part if part in FAMILIES else "other"
        with self.lock:
            self.counts[family] += 1
            self.counts["errors"] += int(status >= 500)
            self.counts["denied"] += int(status in {401, 403, 429})
            self.latencies.setdefault(family, deque(maxlen=1000)).append(round(duration * 1000, 3))
        return family

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            rows = {}
            for family, values in self.latencies.items():
                samples = sorted(values)
                rows[family] = {
                    "count": self.counts[family],
                    "retained_samples": len(samples),
                    "p50_ms": samples[(len(samples) - 1) // 2],
                    "p95_ms": samples[min(len(samples) - 1, int(len(samples) * 0.95))],
                }
            return {
                "scope": "CURRENT_API_PROCESS",
                "started_at_epoch": self.started,
                "errors": self.counts["errors"],
                "denied": self.counts["denied"],
                "requests": rows,
            }
