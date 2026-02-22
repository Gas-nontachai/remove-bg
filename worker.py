from __future__ import annotations

import multiprocessing
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


def run_worker_instance(index: int) -> None:
    connection = get_redis_connection()
    with Connection(connection):
        worker = Worker(["rmbg"], name=f"rmbg-worker-{index}")
        worker.work()


if __name__ == "__main__":
    main_connection = get_redis_connection()
    with Connection(main_connection):
        queue = Queue("rmbg", connection=main_connection)
        CleanupScheduler(queue).start()

    worker_count = max(1, settings.worker_concurrency)
    if worker_count == 1:
        run_worker_instance(1)
    else:
        processes: list[multiprocessing.Process] = []
        for idx in range(worker_count):
            process = multiprocessing.Process(target=run_worker_instance, args=(idx + 1,))
            process.start()
            processes.append(process)
        for process in processes:
            process.join()
