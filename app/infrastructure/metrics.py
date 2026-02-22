from __future__ import annotations

from collections import defaultdict
from threading import Lock


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = defaultdict(int)

    def incr(self, key: str, value: int = 1) -> None:
        with self._lock:
            self._counters[key] += value

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)


metrics = MetricsStore()
