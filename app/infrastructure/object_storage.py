from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse, urlunparse

from botocore.client import Config
from botocore.exceptions import ClientError
import boto3

from app.config import settings


class S3ObjectStorage:
    def __init__(self) -> None:
        if not settings.s3_access_key or not settings.s3_secret_key:
            raise RuntimeError("S3_ACCESS_KEY and S3_SECRET_KEY are required")

        self._bucket = settings.s3_bucket
        self._public_endpoint_url = settings.s3_public_endpoint_url
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            use_ssl=settings.s3_secure,
            config=Config(signature_version="s3v4", s3={"addressing_style": settings.s3_addressing_style}),
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchBucket"}:
                self._client.create_bucket(Bucket=self._bucket)
                return
            raise

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        body = response["Body"].read()
        response["Body"].close()
        return body

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def iter_job_objects(self, prefix: str = "jobs/") -> list[dict[str, datetime | str]]:
        paginator = self._client.get_paginator("list_objects_v2")
        items: list[dict[str, datetime | str]] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                items.append({"key": obj["Key"], "last_modified": obj["LastModified"]})
        return items

    def presigned_get_url(self, key: str, ttl_seconds: int) -> str:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=ttl_seconds,
        )
        return self._to_public_url(url)

    def _to_public_url(self, signed_url: str) -> str:
        if not self._public_endpoint_url:
            return signed_url

        signed = urlparse(signed_url)
        public = urlparse(self._public_endpoint_url)
        return urlunparse(
            (
                public.scheme or signed.scheme,
                public.netloc or signed.netloc,
                signed.path,
                signed.params,
                signed.query,
                signed.fragment,
            )
        )
