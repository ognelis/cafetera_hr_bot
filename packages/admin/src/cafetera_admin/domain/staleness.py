"""Startup staleness detection for documents with outdated indexing config."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cafetera_admin.indexer import set_search_enabled
from cafetera_core.config import is_config_stale
from cafetera_core.storage.models import DocumentStatus

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient

    from cafetera_core.storage.document_repo import DocumentRepository

logger = logging.getLogger(__name__)


async def detect_and_mark_stale(
    doc_repo: DocumentRepository,
    qdrant_client: AsyncQdrantClient,
    collection_name: str,
    current_config: dict[str, Any],
) -> list[str]:
    """Compare completed documents against *current_config* and mark stale ones.

    A document is stale when its stored ``indexing_config`` differs from
    *current_config* (or is ``None`` — legacy rows before this feature).

    Returns the list of document IDs that were marked stale.
    """
    completed_docs, _ = await doc_repo.list_page(
        page=1, per_page=10000, status="completed",
    )

    stale_ids: list[str] = []
    for doc in completed_docs:
        if not is_config_stale(doc.indexing_config, current_config):
            continue

        doc_id = doc.document_id
        try:
            await set_search_enabled(
                qdrant_client, collection_name, doc_id, enabled=False,
            )
        except Exception:
            logger.warning(
                "Failed to update Qdrant chunks for stale document %s",
                doc_id,
                exc_info=True,
            )
            # Still mark in PG so the admin sees it needs attention.

        await doc_repo.update(
            doc_id, status=DocumentStatus.stale, is_search_enabled=False,
        )
        stale_ids.append(doc_id)

    if stale_ids:
        logger.info(
            "Startup staleness check: marked %d of %d completed document(s) as stale",
            len(stale_ids),
            len(completed_docs),
        )
    else:
        logger.info(
            "Startup staleness check: all %d completed document(s) up to date",
            len(completed_docs),
        )

    return stale_ids
