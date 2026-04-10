"""Async S3/MinIO file storage client using aiobotocore."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

from aiobotocore.session import AioSession, get_session  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class S3Storage:
    """Async wrapper around S3-compatible storage (MinIO / AWS S3).

    Intended to be created once during application lifespan and shared
    via ``app.state``.  Manages its own client session.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._region = region
        self._session: AioSession = get_session()
        self._client_ctx: Any = None
        self._client: Any = None
        self._opened: bool = False

    async def open(self) -> None:
        """Create the S3 client and ensure the bucket exists."""
        self._session = get_session()
        self._client_ctx = self._session.create_client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
        )
        self._client = await self._client_ctx.__aenter__()
        await self._ensure_bucket()
        self._opened = True

    async def _ensure_open(self) -> None:
        """Lazily open the S3 client on first use if not already opened."""
        if not self._opened:
            await self.open()

    async def close(self) -> None:
        """Close the underlying S3 client."""
        if not self._opened:
            return
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client_ctx = None
            self._client = None
        self._opened = False

    async def __aenter__(self) -> S3Storage:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    # ---- bucket management -----------------------------------------------

    async def _ensure_bucket(self) -> None:
        """Create the bucket if it doesn't already exist."""
        try:
            await self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            logger.info("Bucket %s not found — creating", self._bucket)
            await self._client.create_bucket(Bucket=self._bucket)

    # ---- file operations -------------------------------------------------

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream",
    ) -> None:
        """Upload bytes to the given S3 key."""
        await self._ensure_open()
        await self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def download(self, key: str) -> bytes:
        """Download a file and return its contents as bytes."""
        await self._ensure_open()
        resp = await self._client.get_object(Bucket=self._bucket, Key=key)
        async with resp["Body"] as stream:
            return await stream.read()

    async def delete(self, key: str) -> None:
        """Delete a file by key (no error if missing)."""
        await self._ensure_open()
        await self._client.delete_object(Bucket=self._bucket, Key=key)

    async def exists(self, key: str) -> bool:
        """Check whether a key exists in the bucket."""
        await self._ensure_open()
        try:
            await self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False
