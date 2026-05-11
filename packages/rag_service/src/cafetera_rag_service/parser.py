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
    return HybridChunker(tokenizer=tokenizer, max_tokens=max_tokens, merge_peers=True)  # type: ignore[call-arg]


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


def _format_page_numbers(pages: list[int]) -> str:
    """Format page numbers as single value, range, or comma-separated list.

    Examples: `5` for single, `5-6` for consecutive, `5, 7` for non-consecutive.
    """
    if not pages:
        return ""
    if len(pages) == 1:
        return str(pages[0])
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"{pages[0]}-{pages[-1]}"
    return ", ".join(str(p) for p in pages)


def _detect_content_type(chunk) -> str:
    """Detect the dominant content type of a chunk from its doc_items labels."""
    from docling_core.types.doc.document import DocItemLabel

    for item in chunk.meta.doc_items:
        if item.label == DocItemLabel.TABLE:
            return "table"
        if item.label in (DocItemLabel.PICTURE, DocItemLabel.CHART):
            return "figure"
    return "text"


def _build_heading_map(dl_doc) -> dict[str, list[str]]:
    """Build a mapping from item self_ref to its full heading ancestry path.

    Uses the actual tree nesting depth from iterate_items (not SectionHeaderItem.level)
    to correctly reconstruct heading hierarchy even when level field is wrong.
    """
    from docling_core.types.doc.document import SectionHeaderItem, TitleItem

    heading_map: dict[str, list[str]] = {}
    heading_stack: dict[int, str] = {}

    try:
        for idx, (item, level) in enumerate(dl_doc.iterate_items(with_groups=True)):
            if idx > 100_000:
                break
            if isinstance(item, (SectionHeaderItem, TitleItem)):
                heading_stack[level] = item.text
                keys_to_remove = [k for k in heading_stack if k > level]
                for k in keys_to_remove:
                    del heading_stack[k]
                sorted_keys = sorted(k for k in heading_stack if k <= level)
                heading_map[item.self_ref] = [heading_stack[k] for k in sorted_keys]
            else:
                sorted_keys = sorted(k for k in heading_stack if k < level)
                if sorted_keys:
                    heading_map[item.self_ref] = [heading_stack[k] for k in sorted_keys]
    except Exception:
        pass

    return heading_map


def _resolve_chunk_headings(chunk, heading_map: dict[str, list[str]]) -> list[str]:
    """Resolve the full heading path for a chunk using the pre-built heading map.

    Looks up the first doc_item's self_ref in the heading map.
    Falls back to chunk.meta.headings if not found in the map.
    """
    if chunk.meta.doc_items:
        ref = chunk.meta.doc_items[0].self_ref
        if ref in heading_map:
            return heading_map[ref]
    return list(chunk.meta.headings) if chunk.meta.headings else []


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
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_onnx_models.layoutmodel.layout_predictor import (
        LayoutPredictor,  # noqa: F401  — force ONNX backend
    )

    pdf_pipeline_options = PdfPipelineOptions(do_ocr=False)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pdf_pipeline_options,
                backend=PyPdfiumDocumentBackend,
            ),
        },
    )
    result = converter.convert(str(path))
    dl_doc = result.document

    page_count = len(result.pages) if result.pages else None
    binary_hash = str(dl_doc.origin.binary_hash) if dl_doc.origin else None
    extracted_title = (
        Path(original_filename).stem if original_filename
        else (dl_doc.name if dl_doc.name else None)
    )

    chunker = _get_chunker(settings.chunker_tokenizer_model, settings.chunk_size)
    heading_map = _build_heading_map(dl_doc)
    docs: list[Document] = []
    for chunk in chunker.chunk(dl_doc=dl_doc):
        content_type = _detect_content_type(chunk)

        # Tables retain structure better without contextualize
        if content_type == "table":
            page_content = chunk.text
        else:
            page_content = chunker.contextualize(chunk)

        page_numbers = _extract_page_numbers(chunk)
        captions = _extract_captions(chunk)
        headings = _resolve_chunk_headings(chunk, heading_map)

        if headings:
            headings_prefix = " > ".join(headings)
            page_content = f"[Разделы: {headings_prefix}]\n{page_content}"

        if not page_content or len(page_content.strip()) < 30:
            continue

        metadata = {
            "source": str(path),
            "headings": headings,
            "captions": captions,
            "page_numbers": page_numbers,
            "content_type": content_type,
            "document_title": extracted_title or "",
            "section_path": chunk.meta.doc_items[0].self_ref if chunk.meta.doc_items else "",
        }
        docs.append(Document(page_content=page_content, metadata=metadata))

    logger.info("Docling loaded %d chunks from %s", len(docs), path.name)
    return ParseResult(
        chunks=docs,
        page_count=page_count,
        binary_hash=binary_hash,
        extracted_title=extracted_title,
    )
