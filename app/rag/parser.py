"""Docx parsing and chunking for the RAG pipeline.

Extracts text from .docx files, splits into sections by heading, and chunks
for embedding.  Used by both ``scripts/ingest.py`` and the admin upload flow.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


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
            if paragraphs:
                sections.append((current_heading, "\n".join(paragraphs)))
                paragraphs = []
            current_heading = text

        paragraphs.append(text)

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
