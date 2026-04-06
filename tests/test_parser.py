"""Tests for app.rag.parser — document parsing functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument

from app.rag.parser import load_doc, load_document

# ── load_doc ──────────────────────────────────────────────────────


class TestLoadDoc:
    def test_load_doc_returns_documents(self, tmp_path: Path):
        doc_path = tmp_path / "test.doc"

        with patch("app.rag.parser.docx2txt.process") as mock_process:
            mock_process.return_value = "First paragraph.\n\nSecond paragraph with more content."
            result = load_doc(doc_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        mock_process.assert_called_once_with(str(doc_path))

    def test_load_doc_metadata(self, tmp_path: Path):
        doc_path = tmp_path / "my_document.doc"

        with patch("app.rag.parser.docx2txt.process") as mock_process:
            mock_process.return_value = "Some content here."
            result = load_doc(doc_path)

        assert len(result) > 0
        for doc in result:
            assert doc.metadata["source"] == "my_document.doc"
            assert doc.metadata["section"] == "my_document"

    def test_load_doc_multi_paragraph_content(self, tmp_path: Path):
        doc_path = tmp_path / "test.doc"
        sample_text = "Paragraph one.\n\nParagraph two.\n\nParagraph three with more text."

        with patch("app.rag.parser.docx2txt.process") as mock_process:
            mock_process.return_value = sample_text
            result = load_doc(doc_path)

        assert len(result) > 0
        combined_content = " ".join(doc.page_content for doc in result)
        assert "Paragraph one" in combined_content
        assert "Paragraph two" in combined_content
        assert "Paragraph three" in combined_content


# ── load_document dispatcher ──────────────────────────────────────


class TestLoadDocumentDispatcher:
    def test_load_document_docx(self, tmp_path: Path):
        docx_path = tmp_path / "test.docx"
        doc = DocxDocument()
        doc.add_heading("Test Heading", level=1)
        doc.add_paragraph("Test paragraph content.")
        doc.save(docx_path)

        result = load_document(docx_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        for doc in result:
            assert doc.metadata["source"] == "test.docx"

    def test_load_document_doc(self, tmp_path: Path):
        doc_path = tmp_path / "test.doc"

        with patch("app.rag.parser.docx2txt.process") as mock_process:
            mock_process.return_value = "Legacy document content."
            result = load_document(doc_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        mock_process.assert_called_once_with(str(doc_path))

    def test_load_document_unsupported_extension(self, tmp_path: Path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("Some text content.")

        with pytest.raises(ValueError) as exc_info:
            load_document(txt_path)

        assert "Unsupported file extension: .txt" in str(exc_info.value)

