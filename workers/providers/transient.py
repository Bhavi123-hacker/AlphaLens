"""Passive memory expiry only. No data requests, retained storage or acquisition task."""

import threading
from collections.abc import MutableMapping
from typing import Any


def expire_after(
    cache: MutableMapping[Any, Any], key: Any, created: float, lock: Any, ttl: float
) -> None:
    def purge() -> None:
        with lock:
            entry = cache.get(key)
            if entry is not None and entry[0] == created:
                cache.pop(key, None)

    timer = threading.Timer(ttl, purge)
    timer.daemon = True
    timer.start()
