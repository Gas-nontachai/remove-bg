from __future__ import annotations

import os


class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    s3_endpoint_url: str | None = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    s3_public_endpoint_url: str | None = os.getenv("S3_PUBLIC_ENDPOINT_URL")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    s3_access_key: str | None = os.getenv("S3_ACCESS_KEY", "minioadmin")
    s3_secret_key: str | None = os.getenv("S3_SECRET_KEY", "minioadmin")
    s3_bucket: str = os.getenv("S3_BUCKET", "rmbg-assets")
    s3_secure: bool = os.getenv("S3_SECURE", "false").lower() == "true"
    s3_addressing_style: str = os.getenv("S3_ADDRESSING_STYLE", "path")

    signed_url_ttl_seconds: int = int(os.getenv("SIGNED_URL_TTL_SECONDS", "3600"))
    max_image_bytes: int = int(os.getenv("MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))
    max_batch_files: int = int(os.getenv("MAX_BATCH_FILES", "15"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "45"))
    max_image_pixels: int = int(os.getenv("MAX_IMAGE_PIXELS", str(20_000_000)))

    job_result_ttl_seconds: int = int(os.getenv("JOB_RESULT_TTL_SECONDS", "86400"))
    job_failure_ttl_seconds: int = int(os.getenv("JOB_FAILURE_TTL_SECONDS", "86400"))
    job_retry_max: int = int(os.getenv("JOB_RETRY_MAX", "2"))
    job_retry_intervals: tuple[int, ...] = tuple(
        int(x.strip()) for x in os.getenv("JOB_RETRY_INTERVALS", "5,20").split(",") if x.strip()
    )

    cleanup_enabled: bool = os.getenv("CLEANUP_ENABLED", "true").lower() == "true"
    cleanup_interval_seconds: int = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "900"))
    cleanup_older_than_seconds: int = int(os.getenv("CLEANUP_OLDER_THAN_SECONDS", "86400"))


settings = Settings()
