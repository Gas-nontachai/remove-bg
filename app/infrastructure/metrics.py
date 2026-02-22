from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import time


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = defaultdict(float)
        self._last_update_ts: int = int(time())

    def incr(self, key: str, value: int = 1) -> None:
        with self._lock:
            self._counters[key] += value
            self._last_update_ts = int(time())

    def set_gauge(self, key: str, value: float) -> None:
        with self._lock:
            self._gauges[key] = value
            self._last_update_ts = int(time())

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            merged: dict[str, int | float] = dict(self._counters)
            merged.update(self._gauges)
            merged["metrics_last_update_ts"] = self._last_update_ts
            return merged

    def to_prometheus_text(self) -> str:
        snapshot = self.snapshot()
        lines = []
        for key, value in sorted(snapshot.items()):
            metric = key.lower().replace("-", "_")
            lines.append(f"rmbg_{metric} {value}")
        return "\n".join(lines) + "\n"


metrics = MetricsStore()
