from __future__ import annotations

from app.config import settings
from app.tasks.maintenance_jobs import cleanup_expired_outputs_job


if __name__ == "__main__":
    result = cleanup_expired_outputs_job(settings.cleanup_older_than_seconds)
    print(result)
