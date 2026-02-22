from __future__ import annotations

import threading
import time

from rq import Connection, Queue, Worker

from app.config import settings
from app.infrastructure.jobs import get_redis_connection


class CleanupScheduler(threading.Thread):
    def __init__(self, queue: Queue) -> None:
        super().__init__(daemon=True)
        self._queue = queue

    def run(self) -> None:
        while True:
            if settings.cleanup_enabled:
                self._queue.enqueue(
                    "app.tasks.maintenance_jobs.cleanup_expired_outputs_job",
                    settings.cleanup_older_than_seconds,
                    result_ttl=settings.job_result_ttl_seconds,
                    failure_ttl=settings.job_failure_ttl_seconds,
                )
            time.sleep(max(60, settings.cleanup_interval_seconds))


if __name__ == "__main__":
    connection = get_redis_connection()
    with Connection(connection):
        queue = Queue("rmbg", connection=connection)
        CleanupScheduler(queue).start()
        worker = Worker(["rmbg"])
        worker.work()
