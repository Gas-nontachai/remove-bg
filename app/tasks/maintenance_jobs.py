from __future__ import annotations

import time

from app.infrastructure.object_storage import S3ObjectStorage


storage = S3ObjectStorage()
try:
    storage.ensure_bucket()
except Exception:  # noqa: BLE001
    pass


def cleanup_expired_outputs_job(older_than_seconds: int) -> dict[str, int]:
    now = int(time.time())
    deleted = 0
    scanned = 0

    for item in storage.iter_job_objects(prefix="jobs/"):
        scanned += 1
        modified_ts = int(item["last_modified"].timestamp())
        age_seconds = now - modified_ts
        if age_seconds < older_than_seconds:
            continue
        storage.delete_object(item["key"])
        deleted += 1

    return {"scanned": scanned, "deleted": deleted}
