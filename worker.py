from __future__ import annotations

from rq import Connection, Worker

from app.infrastructure.jobs import get_redis_connection


if __name__ == "__main__":
    connection = get_redis_connection()
    with Connection(connection):
        worker = Worker(["rmbg"])
        worker.work()
