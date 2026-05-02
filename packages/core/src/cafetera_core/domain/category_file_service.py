"""Category file service — manages document templates for VK bot categories.

This service coordinates between the PostgreSQL category file repository and
S3 storage for VK bot document templates. It handles upload, download,
and deletion of files organized by category/subcategory/entity slots.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from cafetera_core.storage.category_models import (
    LEGAL_ENTITIES,
    CategoryFileRecord,
    is_valid_slot,
)
from cafetera_core.storage.category_repo import CategoryFileRepository
from cafetera_core.storage.s3 import S3Storage


class CategoryFileService:
    """Manages category file lifecycle for VK bot document templates.

    Dependencies are injected via the constructor for testability.
    """

    def __init__(self, repo: CategoryFileRepository, s3: S3Storage) -> None:
        self._repo = repo
        self._s3 = s3

    async def upload_file(
        self,
        category: str,
        subcategory: str,
        entity_id: int,
        filename: str,
        data: bytes,
        content_type: str,
    ) -> CategoryFileRecord:
        """Upload a file for a category+subcategory+entity slot.

        - Validate the slot is valid (use is_valid_slot) and entity_id is in LEGAL_ENTITIES.
        - Check if a file already exists in this slot (via repo.get_by_slot).
        - If yes, delete the old S3 object first.
        - Upload new file to S3 under key: category-files/{entity_id}/{file_id}_{filename}
        - Upsert the DB record.
        - Return the new CategoryFileRecord.

        Raises:
            ValueError: For invalid slot or entity.
        """
        # Validate slot
        if not is_valid_slot(category, subcategory):
            raise ValueError(f"Invalid category/subcategory: {category}/{subcategory}")

        # Validate entity
        if entity_id not in LEGAL_ENTITIES:
            raise ValueError(f"Invalid entity_id: {entity_id}")

        # Check if file already exists in this slot
        existing = await self._repo.get_by_slot(category, subcategory, entity_id)
        if existing is not None:
            # Delete old S3 object
            await self._s3.delete(existing.s3_key)

        # Generate new file_id and S3 key
        file_id = uuid.uuid4().hex
        s3_key = f"category-files/{entity_id}/{file_id}_{filename}"

        now = datetime.now(UTC)
        record = CategoryFileRecord(
            file_id=file_id,
            category=category,
            subcategory=subcategory,
            entity_id=entity_id,
            filename=filename,
            s3_key=s3_key,
            mime_type=content_type,
            size_bytes=len(data),
            created_at=now,
            updated_at=now,
        )

        # Upload to S3
        await self._s3.upload(s3_key, data, content_type)

        # Upsert DB record
        return await self._repo.upsert(record)

    async def get_file(
        self, category: str, subcategory: str, entity_id: int
    ) -> CategoryFileRecord | None:
        """Return the file record for a slot+entity, or None."""
        return await self._repo.get_by_slot(category, subcategory, entity_id)

    async def get_all_files(self) -> list[CategoryFileRecord]:
        """Return all category files."""
        return await self._repo.list_all()

    async def delete_file(self, file_id: str) -> None:
        """Delete file from S3 and DB."""
        record = await self._repo.get(file_id)
        if record is None:
            return
        await self._s3.delete(record.s3_key)
        await self._repo.delete(file_id)

    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Download file bytes from S3. Returns (data, filename). Raises if not found."""
        record = await self._repo.get(file_id)
        if record is None:
            raise FileNotFoundError(f"Category file {file_id} not found")
        data = await self._s3.download(record.s3_key)
        return data, record.filename
