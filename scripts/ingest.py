"""Ingest Word documents into Qdrant for RAG.

Usage:
    uv run python scripts/ingest.py <docs_directory>
    uv run python scripts/ingest.py data/documents/

Reads all .docx files from the given directory, splits them into chunks,
generates embeddings, and stores them in the Qdrant ``hr_documents`` collection.

Only .docx files are processed (NFR-3: PDF scans are not used).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

# Allow running from project root
sys.path.insert(0, ".")

from app.config import Settings
from app.rag.retriever import build_embeddings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


# ── Docx parsing ──────────────────────────────────────────────────


def _extract_sections(path: Path) -> list[tuple[str, str]]:
    """Extract ``(heading, body_text)`` pairs from a .docx file.

    Paragraphs with a ``Heading *`` style start a new section.  All
    subsequent paragraphs belong to the same section until the next
    heading.
    """
    doc = DocxDocument(str(path))
    sections: list[tuple[str, str]] = []
    current_heading = ""
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if para.style and para.style.name and para.style.name.startswith("Heading"):
            # Flush accumulated paragraphs as one section
            if paragraphs:
                sections.append((current_heading, "\n".join(paragraphs)))
                paragraphs = []
            current_heading = text

        paragraphs.append(text)

    # Flush remaining paragraphs
    if paragraphs:
        sections.append((current_heading, "\n".join(paragraphs)))

    return sections


def load_docx(path: Path) -> list[LCDocument]:
    """Parse a .docx file into chunked LangChain ``Document`` objects.

    Each chunk carries metadata: ``source`` (filename) and ``section``
    (nearest heading above the chunk).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )

    sections = _extract_sections(path)
    documents: list[LCDocument] = []

    for heading, body in sections:
        chunks = splitter.split_text(body)
        for chunk in chunks:
            documents.append(
                LCDocument(
                    page_content=chunk,
                    metadata={
                        "source": path.name,
                        "section": heading,
                    },
                )
            )

    return documents


# ── Main ingestion logic ──────────────────────────────────────────


def ingest(docs_dir: Path, settings: Settings) -> int:
    """Ingest all .docx files from *docs_dir* into Qdrant.

    Returns the total number of stored chunks.
    """
    docx_files = sorted(docs_dir.glob("*.docx"))
    if not docx_files:
        logger.warning("No .docx files found in %s", docs_dir)
        return 0

    logger.info("Found %d .docx file(s) to ingest", len(docx_files))

    # Load and chunk all documents
    all_docs: list[LCDocument] = []
    for path in docx_files:
        logger.info("Processing %s …", path.name)
        docs = load_docx(path)
        all_docs.extend(docs)
        logger.info("  -> %d chunk(s)", len(docs))

    if not all_docs:
        logger.warning("No text extracted from any document")
        return 0

    logger.info("Total: %d chunk(s) from %d file(s)", len(all_docs), len(docx_files))

    # Build embeddings
    embeddings = build_embeddings(settings)

    # Recreate collection for a clean ingest
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
    try:
        collection = settings.qdrant_collection
        if client.collection_exists(collection):
            client.delete_collection(collection)
            logger.info("Deleted existing collection '%s'", collection)

        QdrantVectorStore.from_documents(
            documents=all_docs,
            embedding=embeddings,
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=collection,
        )
        logger.info(
            "Ingestion complete: %d chunk(s) stored in '%s'",
            len(all_docs),
            collection,
        )
    finally:
        client.close()

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
    total = ingest(docs_dir, settings)
    if total:
        logger.info("Done — %d chunk(s) indexed.", total)
    else:
        logger.warning("Nothing was indexed.")


if __name__ == "__main__":
    main()
