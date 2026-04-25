"""Document parsing and chunking for the RAG pipeline.

Uses Docling for PDF/DOCX/XLSX parsing.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_core.documents import Document

from cafetera_core.config import CoreSettings

logger = logging.getLogger(__name__)


def ensure_models_cached(model_name: str) -> None:
    """Download tokenizer and Docling models if not cached, then enable offline mode.

    This should be called once at application startup (before any document
    parsing). After this call, HuggingFace will never attempt network requests.

    Args:
        model_name: HuggingFace model identifier (e.g. "Qwen/Qwen3-Embedding-0.6B").
    """
    from docling.document_converter import DocumentConverter
    from transformers import AutoTokenizer

    # 1. Cache tokenizer
    AutoTokenizer.from_pretrained(model_name)
    logger.info("Tokenizer '%s' cached", model_name)

    # 2. Cache Docling layout/TableFormer models
    DocumentConverter()
    logger.info("Docling models cached")

    # 3. Enable offline mode so no further network requests happen
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    logger.info("HuggingFace offline mode enabled")


def load_document(path: str | Path, settings: CoreSettings) -> list[Document]:
    """Parse a document file into chunked LangChain Document objects.

    Dispatches to the appropriate loader based on file extension:
    - .pdf, .docx, .xlsx -> _load_with_docling
    - .doc -> raises ValueError (legacy format no longer supported)

    Args:
        path: Path to the document file.
        settings: CoreSettings with chunk_size.

    Returns:
        List of LangChain Document objects.

    Raises:
        ValueError: If the file extension is not supported.
    """
    path = Path(path)
    ext = path.suffix.lower()

    if ext in (".pdf", ".docx", ".xlsx"):
        return _load_with_docling(path, settings)
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
    return HybridChunker(tokenizer=tokenizer, max_tokens=max_tokens)


def _load_with_docling(path: Path, settings: CoreSettings) -> list[Document]:
    """Parse PDF/DOCX/XLSX files using Docling with HybridChunker."""
    from langchain_docling import DoclingLoader
    from langchain_docling.loader import ExportType

    chunker = _get_chunker(settings.chunker_tokenizer_model, settings.chunk_size)
    loader = DoclingLoader(
        file_path=str(path),
        export_type=ExportType.DOC_CHUNKS,
        chunker=chunker,
    )
    docs = loader.load()
    logger.info("Docling loaded %d chunks from %s", len(docs), path.name)
    return docs
