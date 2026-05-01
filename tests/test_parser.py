"""Tests for cafetera_rag_service.parser — document parsing with Docling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document as LCDocument

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.parser import (
    ParseResult,
    _get_chunker,
    _load_with_docling,
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

    def _make_chunk_mock(self, text: str, content_type: str = "text"):
        """Create a mock Docling chunk with proper structure."""
        from docling_core.types.doc.document import DocItemLabel

        chunk = MagicMock()
        chunk.text = text
        doc_item = MagicMock()
        doc_item.prov = [MagicMock(page_no=1)]
        doc_item.self_ref = "#/body/sections/0"
        if content_type == "table":
            doc_item.label = DocItemLabel.TABLE
        else:
            doc_item.label = DocItemLabel.PARAGRAPH
        chunk.meta.doc_items = [doc_item]
        chunk.meta.headings = ["Heading"]
        return chunk

    def test_short_chunks_filtered_out(self, tmp_path: Path):
        """Chunks with page_content < 30 chars (after strip) are dropped."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        normal_chunk = self._make_chunk_mock("A" * 50)
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
        """Chunks include document_title in metadata and prepend title to content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock("Some meaningful content here that is long enough")

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
        # document_title in metadata
        assert doc.metadata["document_title"] == "TestDoc"
        # Content is prepended with title
        assert doc.page_content.startswith("[Документ: TestDoc]\n")
        assert "Some meaningful content here" in doc.page_content

    def test_no_title_prepend_when_extracted_title_is_none(self, tmp_path: Path):
        """When extracted_title is None, no title prefix is added."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 minimal")
        settings = _make_settings()

        chunk = self._make_chunk_mock("Content without title prefix - long enough text")

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
