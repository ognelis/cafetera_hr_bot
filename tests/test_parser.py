"""Tests for cafetera_admin.parser — document parsing with Docling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.documents import Document as LCDocument

from cafetera_admin.parser import load_document
from cafetera_core.config import CoreSettings


def _make_settings() -> CoreSettings:
    return CoreSettings(
        vk_access_token="t",
        chunk_size=500,
        _env_file=None,
    )


class TestLoadDocument:
    def test_load_document_docx(self, tmp_path: Path):
        docx_path = tmp_path / "test.docx"
        docx_path.write_text("dummy")

        mock_doc = LCDocument(page_content="chunk", metadata={"source": "test.docx"})
        settings = _make_settings()

        with patch(
            "cafetera_admin.parser._load_with_docling", return_value=[mock_doc]
        ) as mock_load:
            result = load_document(docx_path, settings)

        assert len(result) == 1
        assert result[0].page_content == "chunk"
        mock_load.assert_called_once_with(docx_path, settings)

    def test_load_document_pdf(self, tmp_path: Path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        mock_doc = LCDocument(page_content="pdf chunk", metadata={})
        settings = _make_settings()

        with patch(
            "cafetera_admin.parser._load_with_docling", return_value=[mock_doc]
        ) as mock_load:
            result = load_document(pdf_path, settings)

        assert len(result) == 1
        assert result[0].page_content == "pdf chunk"
        mock_load.assert_called_once_with(pdf_path, settings)

    def test_load_document_xlsx(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"
        xlsx_path.write_text("dummy")

        mock_doc = LCDocument(page_content="xlsx chunk", metadata={})
        settings = _make_settings()

        with patch(
            "cafetera_admin.parser._load_with_docling", return_value=[mock_doc]
        ) as mock_load:
            result = load_document(xlsx_path, settings)

        assert len(result) == 1
        assert result[0].page_content == "xlsx chunk"
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
