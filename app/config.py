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


settings = Settings()
