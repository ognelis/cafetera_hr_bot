"""VK document attachment helper for category files.

Provides functionality to send S3-stored documents as VK message attachments.
"""

from __future__ import annotations

import logging
from io import BytesIO

import httpx
from vkbottle.bot import Message
from vkbottle.tools import Format

from cafetera_core.domain.category_file_service import CategoryFileService

logger = logging.getLogger(__name__)


async def send_category_document(
    message: Message,
    category_file_service: CategoryFileService | None,
    category: str,
    subcategory: str,
    entity_id: int,
    caption: str | Format | None = None,
) -> bool:
    """
    Send a category file as a VK document attachment.

    1. Queries CategoryFileService for the file in the given slot+entity.
    2. If found: downloads bytes from S3, uploads to VK via docs API.
    3. If not found or upload fails: returns False (caller falls back to static text).

    Args:
        message: The VK message to reply to (provides ctx_api and peer_id).
        category_file_service: Service for accessing category files.
        category: Category name (e.g., "hire", "fire", "vacation", "pay").
        subcategory: Subcategory name (e.g., "hire_contract", "fire_bypass").
        entity_id: Legal entity ID (1-4).
        caption: Optional text caption to send with the document.

    Returns:
        True if file was sent successfully, False if no file exists or upload failed.
    """
    # Service unavailable (e.g. S3 not running) — fall back to static text
    if category_file_service is None:
        return False

    # Query for file record
    record = await category_file_service.get_file(category, subcategory, entity_id)
    if record is None:
        logger.debug("No category file found for %s/%s/%s", category, subcategory, entity_id)
        return False

    # Download from S3
    try:
        data, filename = await category_file_service.download_file(record.file_id)
    except FileNotFoundError:
        logger.warning("Category file %s not found in S3 (key: %s)", record.file_id, record.s3_key)
        return False
    except Exception:
        logger.exception("Failed to download category file %s from S3", record.file_id)
        return False

    # Upload to VK docs
    try:
        api = message.ctx_api
        peer_id = message.peer_id

        # 1. Get upload server
        upload_server = await api.docs.get_messages_upload_server(
            peer_id=peer_id,
            type="doc",
        )
        upload_url = upload_server.upload_url

        # 2. Upload file to VK's upload server using httpx
        file_bytes = BytesIO(data)
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            files = {"file": (filename, file_bytes, record.mime_type)}
            upload_response = await client.post(upload_url, files=files)
            upload_response.raise_for_status()
            upload_result = upload_response.json()

        # 3. Save the uploaded file to VK docs
        file_field = upload_result.get("file")
        if not file_field:
            logger.error("VK upload response missing 'file' field: %s", upload_result)
            return False

        saved_doc = await api.docs.save(
            file=file_field,
            title=filename,
        )

        # 4. Build attachment string from saved doc
        # saved_doc is a list of doc objects, take the first one
        if not saved_doc or not saved_doc.doc:
            logger.error("VK docs.save returned empty result")
            return False

        doc = saved_doc.doc
        owner_id = doc.owner_id
        doc_id = doc.id
        attachment_str = f"doc{owner_id}_{doc_id}"

        # 5. Send message with attachment
        await message.answer(
            caption or "",
            attachment=attachment_str,
        )
        logger.debug(
            "Sent category document %s/%s/%s as attachment %s",
            category, subcategory, entity_id, attachment_str,
        )
        return True

    except Exception:
        logger.exception("Failed to upload/send document to VK")
        return False
