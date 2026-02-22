from __future__ import annotations

from app.infrastructure.object_storage import S3ObjectStorage


if __name__ == "__main__":
    storage = S3ObjectStorage()
    storage.ensure_bucket()
    print(f"bucket-ready:{storage.bucket}")
