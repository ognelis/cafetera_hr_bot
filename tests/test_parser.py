"""Tests for app.rag.parser — document parsing functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument

from app.rag.parser import load_doc, load_document, load_xlsx

# ── load_doc ──────────────────────────────────────────────────────


class TestLoadDoc:
    def test_load_doc_returns_documents(self, tmp_path: Path):
        doc_path = tmp_path / "test.doc"

        with patch("app.rag.parser.sharepoint2text.read_file") as mock_read_file:
            mock_result = MagicMock()
            mock_result.get_full_text.return_value = "First paragraph.\n\nSecond paragraph with more content."
            mock_read_file.return_value = iter([mock_result])
            result = load_doc(doc_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        mock_read_file.assert_called_once_with(str(doc_path), timeout_seconds=0)

    def test_load_doc_metadata(self, tmp_path: Path):
        doc_path = tmp_path / "my_document.doc"

        with patch("app.rag.parser.sharepoint2text.read_file") as mock_read_file:
            mock_result = MagicMock()
            mock_result.get_full_text.return_value = "Some content here."
            mock_read_file.return_value = iter([mock_result])
            result = load_doc(doc_path)

        assert len(result) > 0
        for doc in result:
            assert doc.metadata["source"] == "my_document.doc"
            assert doc.metadata["section"] == "my_document"

    def test_load_doc_multi_paragraph_content(self, tmp_path: Path):
        doc_path = tmp_path / "test.doc"
        sample_text = "Paragraph one.\n\nParagraph two.\n\nParagraph three with more text."

        with patch("app.rag.parser.sharepoint2text.read_file") as mock_read_file:
            mock_result = MagicMock()
            mock_result.get_full_text.return_value = sample_text
            mock_read_file.return_value = iter([mock_result])
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

        with patch("app.rag.parser.sharepoint2text.read_file") as mock_read_file:
            mock_result = MagicMock()
            mock_result.get_full_text.return_value = "Legacy document content."
            mock_read_file.return_value = iter([mock_result])
            result = load_document(doc_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        mock_read_file.assert_called_once_with(str(doc_path), timeout_seconds=0)

    def test_load_document_unsupported_extension(self, tmp_path: Path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("Some text content.")

        with pytest.raises(ValueError) as exc_info:
            load_document(txt_path)

        assert "Unsupported file extension: .txt" in str(exc_info.value)


# ── load_xlsx ─────────────────────────────────────────────────────


def _create_mock_workbook(sheet_data: dict[str, list[tuple]]) -> MagicMock:
    """Create a mock openpyxl workbook with specified sheet data.

    Args:
        sheet_data: Dict mapping sheet name to list of row tuples.
    """
    mock_wb = MagicMock()
    mock_wb.sheetnames = list(sheet_data.keys())

    def get_sheet(name: str):
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = sheet_data[name]
        return mock_ws

    mock_wb.__getitem__ = lambda self, name: get_sheet(name)
    return mock_wb


class TestLoadXlsx:
    def test_load_xlsx_returns_documents(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"

        sheet_data = {
            "Sheet1": [
                ("A1", "B1", "C1"),
                ("A2", "B2", "C2"),
            ]
        }
        mock_wb = _create_mock_workbook(sheet_data)

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_wb
            result = load_xlsx(xlsx_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        mock_load.assert_called_once_with(xlsx_path, read_only=True, data_only=True)
        mock_wb.close.assert_called_once()

    def test_load_xlsx_metadata(self, tmp_path: Path):
        xlsx_path = tmp_path / "my_spreadsheet.xlsx"

        sheet_data = {
            "Sales": [
                ("Product", "Revenue"),
                ("Widget", "1000"),
            ]
        }
        mock_wb = _create_mock_workbook(sheet_data)

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_wb
            result = load_xlsx(xlsx_path)

        assert len(result) > 0
        for doc in result:
            assert doc.metadata["source"] == "my_spreadsheet.xlsx"
            assert doc.metadata["section"] == "Sales"

    def test_load_xlsx_multi_row_content(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"

        sheet_data = {
            "Data": [
                ("Row1Col1", "Row1Col2"),
                ("Row2Col1", "Row2Col2"),
                ("Row3Col1", "Row3Col2"),
            ]
        }
        mock_wb = _create_mock_workbook(sheet_data)

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_wb
            result = load_xlsx(xlsx_path)

        assert len(result) > 0
        combined_content = " ".join(doc.page_content for doc in result)
        assert "Row1Col1" in combined_content
        assert "Row2Col2" in combined_content
        assert "Row3Col1" in combined_content

    def test_load_xlsx_skips_empty_rows(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"

        sheet_data = {
            "Sheet1": [
                ("A1", "B1"),
                (None, None),  # Empty row
                ("A3", "B3"),
            ]
        }
        mock_wb = _create_mock_workbook(sheet_data)

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_wb
            result = load_xlsx(xlsx_path)

        assert len(result) > 0
        combined_content = " ".join(doc.page_content for doc in result)
        assert "A1" in combined_content
        assert "A3" in combined_content

    def test_load_xlsx_multiple_sheets(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"

        sheet_data = {
            "Sheet1": [("Data1",), ("Data2",)],
            "Sheet2": [("Data3",), ("Data4",)],
        }
        mock_wb = _create_mock_workbook(sheet_data)

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_wb
            result = load_xlsx(xlsx_path)

        assert len(result) > 0
        sheet1_docs = [doc for doc in result if doc.metadata["section"] == "Sheet1"]
        sheet2_docs = [doc for doc in result if doc.metadata["section"] == "Sheet2"]
        assert len(sheet1_docs) > 0
        assert len(sheet2_docs) > 0


# ── load_document dispatcher for xlsx ─────────────────────────────


class TestLoadDocumentXlsxDispatcher:
    def test_load_document_xlsx(self, tmp_path: Path):
        xlsx_path = tmp_path / "test.xlsx"

        sheet_data = {
            "Sheet1": [("Spreadsheet content from xlsx.",)],
        }
        mock_wb = _create_mock_workbook(sheet_data)

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_wb
            result = load_document(xlsx_path)

        assert len(result) > 0
        assert all(isinstance(doc, LCDocument) for doc in result)
        mock_load.assert_called_once_with(xlsx_path, read_only=True, data_only=True)

