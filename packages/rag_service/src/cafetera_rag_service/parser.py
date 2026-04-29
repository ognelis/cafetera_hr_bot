"""Document parsing and chunking for the RAG pipeline.

Uses Docling for PDF/DOCX/XLSX parsing.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document

from cafetera_rag_service.config import RagServiceSettings

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Document parsing result with chunks and document-level metadata."""

    chunks: list[Document]
    page_count: int | None = None
    binary_hash: str | None = None
    extracted_title: str | None = None


def ensure_models_cached(model_name: str) -> None:
    """Download tokenizer and Docling models if not cached, then enable offline mode.

    This should be called once at application startup (before any document
    parsing). After this call, HuggingFace will never attempt network requests.

    Args:
        model_name: HuggingFace model identifier (e.g. "Qwen/Qwen3-Embedding-0.6B").
    """
    from docling.document_converter import DocumentConverter
    from docling_onnx_models.layoutmodel.layout_predictor import (
        LayoutPredictor,  # noqa: F401  — force ONNX backend
    )
    from transformers import AutoTokenizer

    # 1. Cache tokenizer
    AutoTokenizer.from_pretrained(model_name)
    logger.info("Tokenizer '%s' cached", model_name)

    # 2. Cache Docling layout/TableFormer models (ONNX backend via docling-onnx-models)
    DocumentConverter()
    logger.info("Docling ONNX models cached")

    # 3. Enable offline mode so no further network requests happen
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    logger.info("HuggingFace offline mode enabled")


def load_document(
    path: str | Path,
    settings: RagServiceSettings,
    *,
    original_filename: str | None = None,
) -> ParseResult:
    """Parse a document file into chunked LangChain Document objects.

    Dispatches to the appropriate loader based on file extension:
    - .pdf, .docx, .xlsx -> _load_with_docling
    - .doc -> raises ValueError (legacy format no longer supported)

    Args:
        path: Path to the document file.
        settings: RagServiceSettings with chunk_size and chunker_tokenizer_model.
        original_filename: Original filename (before temp-file rename) used for
            extracted_title so that the title reflects the real document name
            rather than the temp path.

    Returns:
        ParseResult with chunks and document-level metadata.

    Raises:
        ValueError: If the file extension is not supported.
    """
    path = Path(path)
    ext = path.suffix.lower()

    if ext in (".pdf", ".docx", ".xlsx"):
        return _load_with_docling(path, settings, original_filename=original_filename)
    if ext == ".doc":
        raise ValueError(
            "Legacy .doc format is no longer supported. Please convert to .docx"
        )
    raise ValueError(f"Unsupported file format: {ext}")


def _get_chunker(tokenizer_model: str, max_tokens: int):
    """Create a HybridChunker with the given tokenizer.

    Uses ``local_files_only=True`` because the tokenizer is guaranteed to be
    cached at startup by ``ensure_models_cached()``.
    """
    from docling.chunking import HybridChunker
    from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
    from transformers import AutoTokenizer

    tokenizer = HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(tokenizer_model, local_files_only=True),
        max_tokens=max_tokens,
    )
    return HybridChunker(tokenizer=tokenizer, max_tokens=max_tokens)  # type: ignore[call-arg]


def _extract_page_numbers(chunk) -> list[int]:
    """Extract unique sorted page numbers from chunk's doc_items provenance."""
    pages: set[int] = set()
    for item in chunk.meta.doc_items:
        for prov in item.prov:
            pages.add(prov.page_no)
    return sorted(pages)


def _extract_captions(chunk) -> list[str]:
    """Extract caption texts from chunk doc_items.

    Non-deprecated replacement for DocMeta.captions.
    """
    from docling_core.types.doc.document import DocItemLabel, TextItem

    return [
        item.text
        for item in chunk.meta.doc_items
        if item.label == DocItemLabel.CAPTION and isinstance(item, TextItem)
    ]


def _detect_content_type(chunk) -> str:
    """Detect the dominant content type of a chunk from its doc_items labels."""
    from docling_core.types.doc.document import DocItemLabel

    for item in chunk.meta.doc_items:
        if item.label == DocItemLabel.TABLE:
            return "table"
        if item.label in (DocItemLabel.PICTURE, DocItemLabel.CHART):
            return "figure"
    return "text"


def _load_with_docling(
    path: Path,
    settings: RagServiceSettings,
    *,
    original_filename: str | None = None,
) -> ParseResult:
    """Parse PDF/DOCX/XLSX files using Docling with HybridChunker.

    Uses DocumentConverter + HybridChunker directly (instead of langchain-docling
    DoclingLoader) for full access to chunk metadata: headings, captions,
    page numbers, content type, and structural path.
    """
    from docling.document_converter import DocumentConverter
    from docling_onnx_models.layoutmodel.layout_predictor import (
        LayoutPredictor,  # noqa: F401  — force ONNX backend
    )

    converter = DocumentConverter()
    result = converter.convert(str(path))
    dl_doc = result.document

    page_count = len(result.pages) if result.pages else None
    binary_hash = str(dl_doc.origin.binary_hash) if dl_doc.origin else None
    extracted_title = (
        Path(original_filename).stem if original_filename
        else (dl_doc.name if dl_doc.name else None)
    )

    chunker = _get_chunker(settings.chunker_tokenizer_model, settings.chunk_size)
    docs: list[Document] = []
    for chunk in chunker.chunk(dl_doc=dl_doc):
        contextualized = chunker.contextualize(chunk)
        page_numbers = _extract_page_numbers(chunk)
        content_type = _detect_content_type(chunk)

        metadata = {
            "source": str(path),
            "headings": list(chunk.meta.headings) if chunk.meta.headings else [],
            "captions": _extract_captions(chunk),
            "page_numbers": page_numbers,
            "content_type": content_type,
            "section_path": chunk.meta.doc_items[0].self_ref if chunk.meta.doc_items else "",
        }
        docs.append(Document(page_content=contextualized, metadata=metadata))

    logger.info("Docling loaded %d chunks from %s", len(docs), path.name)
    return ParseResult(
        chunks=docs,
        page_count=page_count,
        binary_hash=binary_hash,
        extracted_title=extracted_title,
    )
