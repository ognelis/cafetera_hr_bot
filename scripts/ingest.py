"""Ingest documents into Qdrant for RAG.

Usage:
    uv run python scripts/ingest.py <docs_directory>
    uv run python scripts/ingest.py data/documents/

Reads all .docx, .doc, and .xlsx files from the given directory, splits them into chunks,
generates embeddings, and stores them in the Qdrant ``hr_documents`` collection.
Each file is tracked as a ``DocumentRecord`` in PostgreSQL with chunk count and
indexing timestamp.

Supported formats: DOCX, DOC, XLSX.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from databases import Database
from langchain_core.documents import Document as LCDocument
from qdrant_client import AsyncQdrantClient, models

# Allow running from project root
sys.path.insert(0, ".")

from app.config import Settings, configure_logging
from app.rag.indexer import index_chunks, prepare_chunks
from app.rag.parser import load_document
from app.rag.retriever import build_embeddings, build_qdrant_client, build_sparse_embeddings
from app.storage.database import init_db
from app.storage.document_repo import DocumentRepository
from app.storage.models import DocumentRecord, DocumentStatus

configure_logging()
logger = logging.getLogger(__name__)


# ── Main ingestion logic ──────────────────────────────────────────


async def ingest(docs_dir: Path, settings: Settings) -> int:
    """Ingest all supported files from *docs_dir* into Qdrant.

    Creates a ``DocumentRecord`` in PostgreSQL for every file and enriches
    each chunk with ``document_id``, ``chunk_id``, ``filename``, ``s3_key``,
    and ``is_search_enabled`` metadata.

    Returns the total number of stored chunks.
    """
    # Collect files for all supported extensions
    all_files = []
    for ext in ["*.docx", "*.doc", "*.xlsx"]:
        all_files.extend(docs_dir.glob(ext))
    all_files = sorted(all_files)

    if not all_files:
        logger.warning("No .docx, .doc, or .xlsx files found in %s", docs_dir)
        return 0

    logger.info("Found %d file(s) to ingest", len(all_files))

    # Initialise PostgreSQL
    db = Database(settings.database_url)
    await db.connect()
    try:
        await init_db(db)
        repo = DocumentRepository(db)

        # Load, chunk, and register each document
        all_docs: list[LCDocument] = []
        file_chunks: dict[str, list[LCDocument]] = {}

        # Build embeddings (needed for semantic chunking)
        embeddings = build_embeddings(settings)
        sparse = build_sparse_embeddings(settings)

        for path in all_files:
            logger.info("Processing %s ...", path.name)
            raw_chunks = load_document(
                path,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                strategy=settings.chunk_strategy,
                embeddings=embeddings,
                breakpoint_threshold_type=settings.semantic_breakpoint_threshold_type,
                breakpoint_threshold_amount=settings.semantic_breakpoint_threshold_amount,
            )
            logger.info("  -> %d chunk(s)", len(raw_chunks))

            doc_id = uuid.uuid4().hex
            now = datetime.now(UTC)
            record = DocumentRecord(
                document_id=doc_id,
                filename=path.name,
                title=path.stem,
                s3_key=f"documents/{path.name}",
                mime_type=None,  # Will be determined from file extension during upload
                size_bytes=path.stat().st_size,
                status=DocumentStatus.processing,
                created_at=now,
                updated_at=now,
            )
            await repo.create(record)

            enriched = prepare_chunks(
                raw_chunks,
                document_id=doc_id,
                filename=path.name,
                s3_key=f"documents/{path.name}",
            )
            all_docs.extend(enriched)
            file_chunks[doc_id] = enriched

        if not all_docs:
            logger.warning("No text extracted from any document")
            return 0

        logger.info("Total: %d chunk(s) from %d file(s)", len(all_docs), len(all_files))

        # Recreate collection for a clean ingest
        client: AsyncQdrantClient = build_qdrant_client(settings)
        try:
            collection = settings.qdrant_collection
            if await client.collection_exists(collection):
                await client.delete_collection(collection)
                logger.info("Deleted existing collection '%s'", collection)

            # Create collection with proper vector configuration
            test_embedding = embeddings.embed_documents(["test"])
            vector_size = len(test_embedding[0])
            vectors_config = models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            )
            sparse_vectors_config = None
            if sparse is not None:
                sparse_vectors_config = {
                    "text-sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False),
                    )
                }
            await client.create_collection(
                collection_name=collection,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            logger.info("Created collection '%s' with vector_size=%d", collection, vector_size)

            # Index chunks using async indexer
            await index_chunks(
                client=client,
                embeddings=embeddings,
                collection_name=collection,
                chunks=all_docs,
                sparse_embedding=sparse,
            )
            logger.info(
                "Ingestion complete: %d chunk(s) stored in '%s'",
                len(all_docs),
                collection,
            )

            # Update document records with results
            now = datetime.now(UTC)
            for doc_id, chunks in file_chunks.items():
                await repo.update(
                    doc_id,
                    status=DocumentStatus.completed,
                    chunk_count=len(chunks),
                    indexed_at=now,
                )
        except Exception:
            for doc_id in file_chunks:
                await repo.update(
                    doc_id,
                    status=DocumentStatus.failed,
                    error="Bulk ingestion failed",
                )
            raise
        finally:
            await client.close()
    finally:
        await db.disconnect()

    return len(all_docs)


# ── CLI ───────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <docs_directory>", file=sys.stderr)
        sys.exit(1)

    docs_dir = Path(sys.argv[1])
    if not docs_dir.is_dir():
        print(f"Error: '{docs_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    settings = Settings()
    total = asyncio.run(ingest(docs_dir, settings))
    if total:
        logger.info("Done — %d chunk(s) indexed.", total)
    else:
        logger.warning("Nothing was indexed.")


if __name__ == "__main__":
    main()
