"""Tests for cafetera_rag_service.parser — document parsing with Docling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document as LCDocument

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.parser import (
    ParseResult,
    _build_heading_map,
    _format_page_numbers,
    _get_chunker,
    _load_with_docling,
    _resolve_chunk_headings,
    load_document,
)


def _make_settings() -> RagServiceSettings:
    return RagServiceSettings(
        chunk_size=500,
        _env_file=None,
    )


class TestLoadDocument:
    def test_load_document_docx(self, tmp_path: Path):
        docx_path = tmp_path / "test.docx"
        docx_path.write_text("dummy")

        mock_doc = LCDocument(
            page_content="chunk",
            metadata={
                "source": "test.docx",
                "headings": [],
                "captions": [],
                "page_numbers": [],
                "content_type": "text",
                "section_path": "",
            },
        )
        settings = _make_settings()

        mock_result = ParseResult(
            chunks=[mock_doc],
            page_count=5,
            binary_hash="abc123",
            extracted_title="Test Document",
        )

        with patch(
            "cafetera_rag_service.parser._load_with_docling", return_value=mock_result
        ) as mock_load:
            result = load_document(docx_path, settings)

        assert len(result.chunks) == 1
        assert result.chunks[0].page_content == "chunk"
        assert result.page_count == 5
        assert result.binary_hash == "abc123"
        assert result.extracted_title == "Test Document"
        mock_load.assert_called_once_with(
            docx_path, settings, original_filename=None
        )

    def test_load_document_pdf(self, tmp_path: Path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        mock_doc = LCDocument(
            page_content="pdf chunk",
            metadata={
                "source": "test.pdf",
                "headings": [],
                "captions": [],
                "page_numbers": [],
                "content_type": "text",
                "section_path": "",
            },
        )
        settings = _make_settings()

        mock_result = ParseResult(
            chunks=[mock_doc],
            page_count=3,
            binary_hash="pdf456",
            extracted_title="PDF Document",
        )

        with patch(
            "cafetera_rag_service.parser._load_with_docling", return_value=mock_result
        ) as mock_load:
            result = load_document(pdf_path, settings)

        assert len(result.chunks) == 1
        assert result.chunks[0].page_content == "pdf chunk"
        assert result.page_count == 3
        assert result.binary_hash == "pdf456"
        assert result.extracted_title == "PDF Document"
        mock_load.assert_called_once_with(
            pdf_path, settings, original_filename=None
        )

    def test_load_document_xlsx(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"
        xlsx_path.write_text("dummy")

        mock_doc = LCDocument(
            page_content="xlsx chunk",
            metadata={
                "source": "test.xlsx",
                "headings": [],
                "captions": [],
                "page_numbers": [],
                "content_type": "text",
                "section_path": "",
            },
        )
        settings = _make_settings()

        mock_result = ParseResult(
            chunks=[mock_doc],
            page_count=1,
            binary_hash="xlsx789",
            extracted_title="XLSX Document",
        )

        with patch(
            "cafetera_rag_service.parser._load_with_docling", return_value=mock_result
        ) as mock_load:
            result = load_document(xlsx_path, settings)

        assert len(result.chunks) == 1
        assert result.chunks[0].page_content == "xlsx chunk"
        assert result.page_count == 1
        assert result.binary_hash == "xlsx789"
        assert result.extracted_title == "XLSX Document"
        mock_load.assert_called_once_with(
            xlsx_path, settings, original_filename=None
        )

    def test_load_document_doc_raises_valueerror(self, tmp_path: Path):
        doc_path = tmp_path / "test.doc"
        doc_path.write_text("dummy")

        settings = _make_settings()
        with pytest.raises(ValueError) as exc_info:
            load_document(doc_path, settings)

        assert "no longer supported" in str(exc_info.value)

    def test_load_document_unsupported_extension(self, tmp_path: Path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("Some text content.")

        settings = _make_settings()
        with pytest.raises(ValueError) as exc_info:
            load_document(txt_path, settings)

        assert "Unsupported file format" in str(exc_info.value)

    def test_load_document_with_original_filename(self, tmp_path: Path):
        """extracted_title should use original_filename stem when provided."""
        test_file = tmp_path / "tmpABC123.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        with patch("docling.document_converter.DocumentConverter") as MockConverter:
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]  # 1 page
            mock_result.document.name = "tmpABC123"
            mock_result.document.origin.binary_hash = "abc123hash"
            mock_instance = MockConverter.return_value
            mock_instance.convert.return_value = mock_result

            with patch("cafetera_rag_service.parser._get_chunker") as mock_chunker, \
                 patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
                mock_chunker.return_value.chunk.return_value = []

                result = load_document(
                    test_file,
                    settings,
                    original_filename="My Important Report.pdf",
                )

        assert result.extracted_title == "My Important Report"


class TestGetChunker:
    """Tests for _get_chunker — HybridChunker construction."""

    def test_merge_peers_enabled(self):
        """Verify _get_chunker passes merge_peers=True to HybridChunker."""
        with patch("docling.chunking.HybridChunker") as MockChunker, \
             patch("transformers.AutoTokenizer") as MockTokenizer, \
             patch(
                 "docling_core.transforms.chunker.tokenizer.huggingface"
                 ".HuggingFaceTokenizer"
             ):
            MockTokenizer.from_pretrained.return_value = MagicMock()
            _get_chunker("some-model", 500)

        MockChunker.assert_called_once()
        call_kwargs = MockChunker.call_args.kwargs
        assert call_kwargs["merge_peers"] is True
        assert call_kwargs["max_tokens"] == 500


class TestLoadWithDocling:
    """Tests for _load_with_docling — low-level chunking behaviors."""

    def _make_chunk_mock(
        self,
        text: str,
        content_type: str = "text",
        headings: list[str] | None = None,
        page_numbers: list[int] | None = None,
        captions: list[str] | None = None,
    ):
        """Create a mock Docling chunk with proper structure."""
        from docling_core.types.doc.document import DocItemLabel, TextItem

        chunk = MagicMock()
        chunk.text = text

        pages = page_numbers if page_numbers is not None else [1]
        doc_items = []

        # Primary doc item
        doc_item = MagicMock()
        doc_item.prov = [MagicMock(page_no=p) for p in pages]
        doc_item.self_ref = "#/body/sections/0"
        if content_type == "table":
            doc_item.label = DocItemLabel.TABLE
        else:
            doc_item.label = DocItemLabel.PARAGRAPH
        doc_items.append(doc_item)

        # Caption items
        for cap_text in (captions or []):
            cap_item = MagicMock(spec=TextItem)
            cap_item.label = DocItemLabel.CAPTION
            cap_item.text = cap_text
            cap_item.prov = []
            doc_items.append(cap_item)

        chunk.meta.doc_items = doc_items
        chunk.meta.headings = headings if headings is not None else []
        return chunk

    def test_short_chunks_filtered_out(self, tmp_path: Path):
        """Chunks with page_content < 30 chars (after strip) are dropped."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        normal_chunk = self._make_chunk_mock("A" * 50, headings=["Heading"])
        short_chunk = self._make_chunk_mock("short")
        empty_chunk = self._make_chunk_mock("")

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = None
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [
                normal_chunk, short_chunk, empty_chunk,
            ]
            # contextualize returns the chunk.text as-is for text chunks
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        # Only the normal chunk (50 chars) should pass the 30-char filter
        assert len(result.chunks) == 1
        assert "A" * 50 in result.chunks[0].page_content

    def test_table_chunks_skip_contextualize(self, tmp_path: Path):
        """Table chunks use chunk.text directly; contextualize is NOT called."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        table_chunk = self._make_chunk_mock(
            "| Col1 | Col2 |\n| val1 | val2 |" + " " * 30,
            content_type="table",
            headings=[],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = None
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [table_chunk]
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        # contextualize should NOT be called for table chunks
        chunker_instance.contextualize.assert_not_called()
        assert len(result.chunks) == 1
        assert "| Col1 | Col2 |" in result.chunks[0].page_content
        assert result.chunks[0].metadata["content_type"] == "table"

    def test_document_title_in_metadata_and_content(self, tmp_path: Path):
        """Chunks include document_title in metadata but NOT in page_content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Some meaningful content here that is long enough",
            headings=[],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "TestDoc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        assert len(result.chunks) == 1
        doc = result.chunks[0]
        # document_title in metadata only
        assert doc.metadata["document_title"] == "TestDoc"
        # Title is NOT prepended to page_content
        assert "[Документ:" not in doc.page_content
        assert "Some meaningful content here" in doc.page_content

    def test_no_title_prepend_when_extracted_title_is_none(self, tmp_path: Path):
        """When extracted_title is None, no title prefix is added."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content without title prefix - long enough text",
            headings=[],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = None
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        assert len(result.chunks) == 1
        doc = result.chunks[0]
        assert doc.metadata["document_title"] == ""
        assert not doc.page_content.startswith("[Документ:")

    def test_headings_prefix_with_single_heading(self, tmp_path: Path):
        """Chunks with headings get [Разделы: ...] prefix as the first line."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content under a heading that is definitely long enough",
            headings=["Introduction"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "TestDoc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        assert len(result.chunks) == 1
        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Introduction]"
        assert "Content under a heading" in doc.page_content

    def test_headings_prefix_with_multiple_headings(self, tmp_path: Path):
        """Multiple headings are joined with ' > ' separator."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Deep nested content that is long enough for the filter",
            headings=["Chapter 1", "Section 1.1", "Subsection A"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Manual"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        assert len(result.chunks) == 1
        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Chapter 1 > Section 1.1 > Subsection A]"
        assert "Deep nested content" in doc.page_content

    def test_no_headings_prefix_when_headings_empty(self, tmp_path: Path):
        """Chunks without headings do NOT get [Разделы: ...] prefix."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content with no heading context and long enough text",
            headings=[],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "TestDoc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        assert len(result.chunks) == 1
        doc = result.chunks[0]
        assert "[Разделы:" not in doc.page_content
        assert "[Документ:" not in doc.page_content
        assert doc.page_content == "Content with no heading context and long enough text"

    def test_table_chunk_with_headings(self, tmp_path: Path):
        """Table chunks also receive heading context when headings exist."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        table_chunk = self._make_chunk_mock(
            "| Col1 | Col2 |\n| val1 | val2 |" + " " * 30,
            content_type="table",
            headings=["Data Tables", "Quarterly Results"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Report"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [table_chunk]
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        assert len(result.chunks) == 1
        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Data Tables > Quarterly Results]"
        assert "| Col1 | Col2 |" in doc.page_content
        assert doc.metadata["content_type"] == "table"
        # contextualize should NOT be called for table chunks
        chunker_instance.contextualize.assert_not_called()

    def test_heading_ordering_headings_then_content(self, tmp_path: Path):
        """Verify ordering: [Разделы:] first, content after."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Actual body text of the chunk is long enough for filter",
            headings=["Part A", "Chapter B"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "DocTitle"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Part A > Chapter B]"
        assert lines[1] == "Actual body text of the chunk is long enough for filter"

    def test_page_numbers_single_page(self, tmp_path: Path):
        """Chunk with page numbers stores them in metadata, not page_content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content on page twelve with enough text for filter",
            headings=["Chapter 1"],
            page_numbers=[12],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "ПВТР"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Chapter 1]"
        assert "[Страница:" not in doc.page_content
        assert doc.metadata["page_numbers"] == [12]
        assert "Content on page twelve" in doc.page_content

    def test_page_numbers_consecutive_range(self, tmp_path: Path):
        """Consecutive page numbers are stored in metadata, not page_content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content spanning multiple pages with enough text",
            headings=[],
            page_numbers=[5, 6, 7],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Doc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        assert "[Страница:" not in doc.page_content
        assert doc.metadata["page_numbers"] == [5, 6, 7]

    def test_page_numbers_non_consecutive(self, tmp_path: Path):
        """Non-consecutive page numbers are stored in metadata, not page_content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content on scattered pages with enough text here",
            headings=[],
            page_numbers=[3, 5, 9],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Doc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        assert "[Страница:" not in doc.page_content
        assert doc.metadata["page_numbers"] == [3, 5, 9]

    def test_no_page_prefix_when_empty(self, tmp_path: Path):
        """Chunks without page numbers don't get [Страница:] prefix."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content with no page numbers and enough text here",
            headings=[],
            page_numbers=[],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Doc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        assert "[Страница:" not in doc.page_content

    def test_captions_single(self, tmp_path: Path):
        """Chunk with captions stores them in metadata, not page_content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Table content that is long enough for filter check",
            content_type="table",
            headings=["Section A"],
            page_numbers=[3],
            captions=["Таблица 3. График рабочего времени"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "ПВТР"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Section A]"
        assert "[Подпись:" not in doc.page_content
        assert "[Страница:" not in doc.page_content
        assert doc.metadata["captions"] == ["Таблица 3. График рабочего времени"]
        assert doc.metadata["page_numbers"] == [3]

    def test_captions_multiple_joined(self, tmp_path: Path):
        """Multiple captions are stored in metadata, not page_content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content with multiple captions long enough for filter",
            headings=[],
            captions=["Caption A", "Caption B"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Doc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        assert "[Подпись:" not in doc.page_content
        assert doc.metadata["captions"] == ["Caption A", "Caption B"]

    def test_no_caption_prefix_when_empty(self, tmp_path: Path):
        """Chunks without captions don't get [Подпись:] prefix."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Content with no captions and enough text for filter",
            headings=[],
            captions=[],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "Doc"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        assert "[Подпись:" not in doc.page_content

    def test_full_prefix_ordering(self, tmp_path: Path):
        """Only [Разделы] remains in page_content; other metadata is in metadata dict."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock(
            "Body text of the chunk with all metadata present",
            headings=["Глава 7", "7.1 Общие положения"],
            page_numbers=[12],
            captions=["Таблица 3"],
        )

        with patch("docling.document_converter.DocumentConverter") as MockConverter, \
             patch("cafetera_rag_service.parser._get_chunker") as mock_get_chunker, \
             patch("docling_onnx_models.layoutmodel.layout_predictor.LayoutPredictor"):
            mock_result = MagicMock()
            mock_result.pages = [MagicMock()]
            mock_result.document.name = "ПВТР"
            mock_result.document.origin.binary_hash = "hash"
            MockConverter.return_value.convert.return_value = mock_result

            chunker_instance = MagicMock()
            chunker_instance.chunk.return_value = [chunk]
            chunker_instance.contextualize.side_effect = lambda c: c.text
            mock_get_chunker.return_value = chunker_instance

            result = _load_with_docling(test_file, settings)

        doc = result.chunks[0]
        lines = doc.page_content.split("\n")
        assert lines[0] == "[Разделы: Глава 7 > 7.1 Общие положения]"
        assert lines[1] == "Body text of the chunk with all metadata present"
        assert "[Документ:" not in doc.page_content
        assert "[Страница:" not in doc.page_content
        assert "[Подпись:" not in doc.page_content
        assert doc.metadata["document_title"] == "ПВТР"
        assert doc.metadata["page_numbers"] == [12]
        assert doc.metadata["captions"] == ["Таблица 3"]


class TestFormatPageNumbers:
    """Tests for _format_page_numbers helper."""

    def test_empty_list(self):
        assert _format_page_numbers([]) == ""

    def test_single_page(self):
        assert _format_page_numbers([5]) == "5"

    def test_consecutive_range(self):
        assert _format_page_numbers([3, 4, 5]) == "3-5"

    def test_two_consecutive(self):
        assert _format_page_numbers([1, 2]) == "1-2"

    def test_non_consecutive(self):
        assert _format_page_numbers([1, 3, 7]) == "1, 3, 7"

    def test_mixed_gaps(self):
        assert _format_page_numbers([1, 2, 5]) == "1, 2, 5"


class TestBuildHeadingMap:
    """Tests for _build_heading_map — heading ancestry from document tree."""

    def test_heading_map_from_tree_nesting(self):
        """Heading paths are built from tree nesting, not SectionHeaderItem.level."""
        from docling_core.types.doc.document import SectionHeaderItem, TextItem

        h1 = MagicMock(spec=SectionHeaderItem)
        h1.self_ref = "#/body/sections/0"
        h1.text = "Chapter 1"

        h2 = MagicMock(spec=SectionHeaderItem)
        h2.self_ref = "#/body/sections/0/sections/0"
        h2.text = "Section 1.1"

        h3 = MagicMock(spec=SectionHeaderItem)
        h3.self_ref = "#/body/sections/0/sections/1"
        h3.text = "Section 1.2"

        h4 = MagicMock(spec=SectionHeaderItem)
        h4.self_ref = "#/body/sections/0/sections/1/sections/0"
        h4.text = "Subsection 1.2.1"

        p1 = MagicMock(spec=TextItem)
        p1.self_ref = "#/body/sections/0/sections/1/sections/0/paragraphs/0"

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (h1, 1),
            (h2, 2),
            (h3, 2),
            (h4, 3),
            (p1, 4),
        ]

        heading_map = _build_heading_map(doc)

        assert heading_map[h1.self_ref] == ["Chapter 1"]
        assert heading_map[h2.self_ref] == ["Chapter 1", "Section 1.1"]
        assert heading_map[h3.self_ref] == ["Chapter 1", "Section 1.2"]
        assert heading_map[h4.self_ref] == [
            "Chapter 1",
            "Section 1.2",
            "Subsection 1.2.1",
        ]
        assert heading_map[p1.self_ref] == [
            "Chapter 1",
            "Section 1.2",
            "Subsection 1.2.1",
        ]

    def test_heading_map_includes_title_items(self):
        """TitleItem nodes are also tracked as headings."""
        from docling_core.types.doc.document import TextItem, TitleItem

        t1 = MagicMock(spec=TitleItem)
        t1.self_ref = "#/body/title/0"
        t1.text = "Document Title"

        p1 = MagicMock(spec=TextItem)
        p1.self_ref = "#/body/paragraphs/0"

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (t1, 1),
            (p1, 2),
        ]

        heading_map = _build_heading_map(doc)

        assert heading_map[t1.self_ref] == ["Document Title"]
        assert heading_map[p1.self_ref] == ["Document Title"]

    def test_heading_map_graceful_with_malformed_doc(self):
        """Returns empty dict when iterate_items is missing or raises."""
        doc = MagicMock()
        doc.iterate_items.side_effect = AttributeError("no iterate_items")

        heading_map = _build_heading_map(doc)
        assert heading_map == {}

    def test_heading_map_clears_stale_siblings(self):
        """When a new heading appears at same tree level, deeper entries are cleared."""
        from docling_core.types.doc.document import SectionHeaderItem, TextItem

        h1 = MagicMock(spec=SectionHeaderItem)
        h1.self_ref = "#/s/0"
        h1.text = "A"

        h2 = MagicMock(spec=SectionHeaderItem)
        h2.self_ref = "#/s/0/s/0"
        h2.text = "A.1"

        h3 = MagicMock(spec=SectionHeaderItem)
        h3.self_ref = "#/s/0/s/1"
        h3.text = "A.2"

        p1 = MagicMock(spec=TextItem)
        p1.self_ref = "#/s/0/s/1/p/0"

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (h1, 1),
            (h2, 2),
            (h3, 2),
            (p1, 3),
        ]

        heading_map = _build_heading_map(doc)

        # h3 at level 2 should have cleared h2 from the stack
        assert heading_map[p1.self_ref] == ["A", "A.2"]


class TestResolveChunkHeadings:
    """Tests for _resolve_chunk_headings — map lookup with fallback."""

    def test_returns_map_entry_when_found(self):
        """When doc_item self_ref exists in heading_map, return mapped path."""
        chunk = MagicMock()
        chunk.meta.doc_items = [MagicMock()]
        chunk.meta.doc_items[0].self_ref = "ref1"
        chunk.meta.headings = ["Fallback"]

        heading_map = {"ref1": ["H1", "H2"]}
        result = _resolve_chunk_headings(chunk, heading_map)
        assert result == ["H1", "H2"]

    def test_fallback_when_ref_not_in_map(self):
        """When self_ref is not in heading_map, fall back to chunk.meta.headings."""
        chunk = MagicMock()
        chunk.meta.doc_items = [MagicMock()]
        chunk.meta.doc_items[0].self_ref = "ref2"
        chunk.meta.headings = ["Fallback Heading"]

        heading_map = {"ref1": ["H1"]}
        result = _resolve_chunk_headings(chunk, heading_map)
        assert result == ["Fallback Heading"]

    def test_fallback_when_doc_items_empty(self):
        """When doc_items is empty, fall back to chunk.meta.headings."""
        chunk = MagicMock()
        chunk.meta.doc_items = []
        chunk.meta.headings = ["Only Heading"]

        heading_map = {}
        result = _resolve_chunk_headings(chunk, heading_map)
        assert result == ["Only Heading"]

    def test_empty_when_no_headings_and_no_map(self):
        """Returns empty list when neither map nor fallback has headings."""
        chunk = MagicMock()
        chunk.meta.doc_items = [MagicMock()]
        chunk.meta.doc_items[0].self_ref = "ref1"
        chunk.meta.headings = []

        heading_map = {}
        result = _resolve_chunk_headings(chunk, heading_map)
        assert result == []
