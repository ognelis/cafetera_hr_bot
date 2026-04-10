"""Document parsing and chunking for the RAG pipeline.

Extracts text from .docx, .doc, and .xlsx files, splits into sections, and chunks
for embedding.  Used by both ``scripts/ingest.py`` and the admin upload flow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import sharepoint2text
from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
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
    path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    strategy: str = "recursive",
    embeddings: Embeddings | None = None,
    breakpoint_threshold_type: Literal[
        "percentile", "standard_deviation", "interquartile", "gradient"
    ] = "percentile",
    breakpoint_threshold_amount: float | int = 95,
) -> list[LCDocument]:
    """Parse a .docx file into chunked LangChain ``Document`` objects.

    Each chunk carries metadata: ``source`` (filename) and ``section``
    (nearest heading above the chunk).

    Args:
        path: Path to the .docx file.
        chunk_size: Maximum chunk size for recursive strategy.
        chunk_overlap: Overlap between chunks for recursive strategy.
        strategy: Chunking strategy - "recursive" (default) or "semantic".
        embeddings: Embeddings model required for semantic chunking.
        breakpoint_threshold_type: Threshold type for semantic chunking.
        breakpoint_threshold_amount: Threshold amount for semantic chunking.

    Returns:
        List of LangChain Document objects.

    Raises:
        ValueError: If strategy is "semantic" and embeddings is None.
    """
    sections = _extract_sections(path)

    if strategy == "recursive":
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

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

    if strategy == "semantic":
        if embeddings is None:
            raise ValueError("embeddings are required for semantic chunking strategy")

        # Build full text with section offsets tracking
        section_offsets: list[tuple[int, int, str]] = []
        full_text_parts: list[str] = []
        current_offset = 0

        for heading, body in sections:
            section_text = body
            start_offset = current_offset
            end_offset = current_offset + len(section_text)
            section_offsets.append((start_offset, end_offset, heading))
            full_text_parts.append(section_text)
            current_offset = end_offset + 2  # +2 for "\n\n" separator

        full_text = "\n\n".join(full_text_parts)

        chunker = SemanticChunker(
            embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

        semantic_chunks: list[LCDocument] = chunker.create_documents([full_text])

        semantic_documents: list[LCDocument] = []
        for sem_chunk in semantic_chunks:
            chunk_text = sem_chunk.page_content
            # Find chunk position in full text
            chunk_start = full_text.find(chunk_text)
            if chunk_start == -1:
                chunk_start = 0
            chunk_end = chunk_start + len(chunk_text)

            # Find section with largest overlap
            best_heading = ""
            best_overlap = 0
            for start, end, heading in section_offsets:
                overlap_start = max(start, chunk_start)
                overlap_end = min(end, chunk_end)
                overlap = max(0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_heading = heading

            semantic_documents.append(
                LCDocument(
                    page_content=chunk_text,
                    metadata={
                        "source": path.name,
                        "section": best_heading,
                    },
                )
            )

        return semantic_documents

    raise ValueError(f"Unknown chunking strategy: {strategy}")


def load_doc(
    path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    strategy: str = "recursive",
    embeddings: Embeddings | None = None,
    breakpoint_threshold_type: Literal[
        "percentile", "standard_deviation", "interquartile", "gradient"
    ] = "percentile",
    breakpoint_threshold_amount: float | int = 95,
) -> list[LCDocument]:
    """Parse a legacy .doc file into chunked LangChain ``Document`` objects.

    Since .doc files lack structured heading styles, the entire text is treated
    as one section with the filename stem as the heading for recursive strategy,
    or empty section for semantic strategy.

    Each chunk carries metadata: ``source`` (filename) and ``section``
    (filename stem for recursive, empty for semantic).

    Args:
        path: Path to the .doc file.
        chunk_size: Maximum chunk size for recursive strategy.
        chunk_overlap: Overlap between chunks for recursive strategy.
        strategy: Chunking strategy - "recursive" (default) or "semantic".
        embeddings: Embeddings model required for semantic chunking.
        breakpoint_threshold_type: Threshold type for semantic chunking.
        breakpoint_threshold_amount: Threshold amount for semantic chunking.

    Returns:
        List of LangChain Document objects.

    Raises:
        ValueError: If strategy is "semantic" and embeddings is None.
    """
    # Use sharepoint2text to extract text from legacy .doc files
    # timeout_seconds=0 disables signal-based timeout (requires main thread)
    # since this function may be called via asyncio.to_thread() in a worker thread
    result = next(sharepoint2text.read_file(str(path), timeout_seconds=0))
    text = result.get_full_text()

    if strategy == "recursive":
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

        section_heading = path.stem
        chunks = splitter.split_text(text)
        doc_chunks: list[LCDocument] = []

        for chunk in chunks:
            doc_chunks.append(
                LCDocument(
                    page_content=chunk,
                    metadata={
                        "source": path.name,
                        "section": section_heading,
                    },
                )
            )

        return doc_chunks

    if strategy == "semantic":
        if embeddings is None:
            raise ValueError("embeddings are required for semantic chunking strategy")

        chunker = SemanticChunker(
            embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

        semantic_chunks: list[LCDocument] = chunker.create_documents([text])

        documents: list[LCDocument] = []
        for sem_chunk in semantic_chunks:
            documents.append(
                LCDocument(
                    page_content=sem_chunk.page_content,
                    metadata={
                        "source": path.name,
                        "section": "",
                    },
                )
            )

        return documents

    raise ValueError(f"Unknown chunking strategy: {strategy}")


def load_xlsx(
    path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    strategy: str = "recursive",
    embeddings: Embeddings | None = None,
    breakpoint_threshold_type: Literal[
        "percentile", "standard_deviation", "interquartile", "gradient"
    ] = "percentile",
    breakpoint_threshold_amount: float | int = 95,
) -> list[LCDocument]:
    """Parse an .xlsx spreadsheet into chunked LangChain ``Document`` objects.

    Each worksheet becomes a section (sheet name as heading). Rows are formatted
    with `` | `` separators to preserve column structure. Empty rows are skipped.

    Each chunk carries metadata: ``source`` (filename) and ``section`` (sheet name).

    Args:
        path: Path to the .xlsx file.
        chunk_size: Maximum chunk size for recursive strategy.
        chunk_overlap: Overlap between chunks for recursive strategy.
        strategy: Chunking strategy - "recursive" (default) or "semantic".
        embeddings: Embeddings model required for semantic chunking.
        breakpoint_threshold_type: Threshold type for semantic chunking.
        breakpoint_threshold_amount: Threshold amount for semantic chunking.

    Returns:
        List of LangChain Document objects.

    Raises:
        ValueError: If strategy is "semantic" and embeddings is None.
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sections: list[tuple[str, str]] = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows_text: list[str] = []
        for row in ws.iter_rows(values_only=True):
            # Skip completely empty rows
            cells = [str(cell) if cell is not None else "" for cell in row]
            if any(c.strip() for c in cells):
                rows_text.append(" | ".join(cells))
        if rows_text:
            sections.append((sheet_name, "\n".join(rows_text)))

    wb.close()

    if strategy == "recursive":
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

        documents: list[LCDocument] = []
        for sheet_name, body in sections:
            chunks = splitter.split_text(body)
            for chunk in chunks:
                documents.append(
                    LCDocument(
                        page_content=chunk,
                        metadata={
                            "source": path.name,
                            "section": sheet_name,
                        },
                    )
                )
        return documents

    if strategy == "semantic":
        if embeddings is None:
            raise ValueError("embeddings are required for semantic chunking strategy")

        # Build full text with section offsets tracking
        section_offsets: list[tuple[int, int, str]] = []
        full_text_parts: list[str] = []
        current_offset = 0

        for sheet_name, body in sections:
            section_text = body
            start_offset = current_offset
            end_offset = current_offset + len(section_text)
            section_offsets.append((start_offset, end_offset, sheet_name))
            full_text_parts.append(section_text)
            current_offset = end_offset + 2  # +2 for "\n\n" separator

        full_text = "\n\n".join(full_text_parts)

        chunker = SemanticChunker(
            embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

        semantic_chunks: list[LCDocument] = chunker.create_documents([full_text])

        semantic_documents: list[LCDocument] = []
        for sem_chunk in semantic_chunks:
            chunk_text = sem_chunk.page_content
            # Find chunk position in full text
            chunk_start = full_text.find(chunk_text)
            if chunk_start == -1:
                chunk_start = 0
            chunk_end = chunk_start + len(chunk_text)

            # Find section with largest overlap
            best_sheet_name = ""
            best_overlap = 0
            for start, end, sheet_name in section_offsets:
                overlap_start = max(start, chunk_start)
                overlap_end = min(end, chunk_end)
                overlap = max(0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_sheet_name = sheet_name

            semantic_documents.append(
                LCDocument(
                    page_content=chunk_text,
                    metadata={
                        "source": path.name,
                        "section": best_sheet_name,
                    },
                )
            )

        return semantic_documents

    raise ValueError(f"Unknown chunking strategy: {strategy}")



def load_document(
    path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    strategy: str = "recursive",
    embeddings: Embeddings | None = None,
    breakpoint_threshold_type: Literal[
        "percentile", "standard_deviation", "interquartile", "gradient"
    ] = "percentile",
    breakpoint_threshold_amount: float | int = 95,
) -> list[LCDocument]:
    """Parse a document file into chunked LangChain ``Document`` objects.

    Dispatches to the appropriate loader based on file extension:
    - .docx -> load_docx
    - .doc -> load_doc
    - .xlsx -> load_xlsx

    Args:
        path: Path to the document file.
        chunk_size: Maximum chunk size for recursive strategy.
        chunk_overlap: Overlap between chunks for recursive strategy.
        strategy: Chunking strategy - "recursive" (default) or "semantic".
        embeddings: Embeddings model required for semantic chunking.
        breakpoint_threshold_type: Threshold type for semantic chunking.
        breakpoint_threshold_amount: Threshold amount for semantic chunking.

    Raises:
        ValueError: If the file extension is not supported.
    """
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return load_docx(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=strategy,
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
    elif suffix == ".doc":
        return load_doc(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=strategy,
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
    elif suffix == ".xlsx":
        return load_xlsx(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=strategy,
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")
