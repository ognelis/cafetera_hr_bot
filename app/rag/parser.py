"""Document parsing and chunking for the RAG pipeline.

Extracts text from .docx and .doc files, splits into sections, and chunks
for embedding.  Used by both ``scripts/ingest.py`` and the admin upload flow.
"""

from __future__ import annotations

from pathlib import Path

import docx2txt
from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

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


def load_docx(
    path: Path, *, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[LCDocument]:
    """Parse a .docx file into chunked LangChain ``Document`` objects.

    Each chunk carries metadata: ``source`` (filename) and ``section``
    (nearest heading above the chunk).
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
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


def load_doc(
    path: Path, *, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[LCDocument]:
    """Parse a legacy .doc file into chunked LangChain ``Document`` objects.

    Since .doc files lack structured heading styles, the entire text is treated
    as one section with the filename stem as the heading.

    Each chunk carries metadata: ``source`` (filename) and ``section``
    (filename stem).
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " "],
    )

    text = docx2txt.process(str(path))
    section_heading = path.stem
    chunks = splitter.split_text(text)
    documents: list[LCDocument] = []

    for chunk in chunks:
        documents.append(
            LCDocument(
                page_content=chunk,
                metadata={
                    "source": path.name,
                    "section": section_heading,
                },
            )
        )

    return documents



def load_document(
    path: Path, *, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[LCDocument]:
    """Parse a document file into chunked LangChain ``Document`` objects.

    Dispatches to the appropriate loader based on file extension:
    - .docx -> load_docx
    - .doc -> load_doc

    Raises:
        ValueError: If the file extension is not supported.
    """
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return load_docx(path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif suffix == ".doc":
        return load_doc(path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")
