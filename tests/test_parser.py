"""Tests for cafetera_rag_service.parser — document parsing with Docling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.documents import Document as LCDocument

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.parser import ParseResult, load_document


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
        mock_load.assert_called_once_with(docx_path, settings)

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
        mock_load.assert_called_once_with(pdf_path, settings)

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
        mock_load.assert_called_once_with(xlsx_path, settings)

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
