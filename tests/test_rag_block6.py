"""Tests for Block 6 — RAG infrastructure."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument

from app.config import Settings
from app.rag.chain import _format_docs, build_rag_chain
from app.rag.prompts import SYSTEM_PROMPT
from app.rag.retriever import COLLECTION_NAME, build_vectorstore

# ── Helpers ────────────────────────────────────────────────────────


def _make_docx(path: Path, paragraphs: list[tuple[str | None, str]]) -> None:
    """Create a .docx with paragraphs; if style is given, apply it."""
    doc = DocxDocument()
    for style, text in paragraphs:
        if style:
            doc.add_paragraph(text, style=style)
        else:
            doc.add_paragraph(text)
    doc.save(str(path))


# ── 6.0 — Config / Settings ───────────────────────────────────────


class TestRagSettings:
    def test_defaults_for_qdrant(self):
        s = Settings(vk_access_token="t", _env_file=None)
        assert s.qdrant_url == "http://localhost:6333"
        assert s.qdrant_api_key is None
        assert s.qdrant_collection == "hr_documents"

    def test_defaults_for_llm(self):
        s = Settings(vk_access_token="t", _env_file=None)
        assert s.llm_provider == "ollama"
        assert s.llm_model == "qwen3.5:4b-q4_K_M"
        assert s.llm_base_url == "http://localhost:11434"
        assert s.llm_api_key == ""

    def test_defaults_for_embeddings(self):
        s = Settings(vk_access_token="t", _env_file=None)
        assert s.embedding_model == "nomic-embed-text"

    def test_qdrant_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("VK_ACCESS_TOKEN", "t")
        monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
        monkeypatch.setenv("QDRANT_API_KEY", "secret")
        monkeypatch.setenv("QDRANT_COLLECTION", "custom_col")
        s = Settings()
        assert s.qdrant_url == "http://qdrant:6333"
        assert s.qdrant_api_key == "secret"
        assert s.qdrant_collection == "custom_col"

    def test_llm_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("VK_ACCESS_TOKEN", "t")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("LLM_API_KEY", "sk-xxx")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        s = Settings()
        assert s.llm_provider == "openai"
        assert s.llm_model == "gpt-4o-mini"
        assert s.llm_api_key == "sk-xxx"


# ── 6.1 — Ingestion: docx parsing ─────────────────────────────────


class TestExtractSections:
    def test_single_section_no_heading(self):
        from scripts.ingest import _extract_sections

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.docx"
            _make_docx(path, [(None, "Hello world"), (None, "Second line")])
            sections = _extract_sections(path)

        assert len(sections) == 1
        heading, body = sections[0]
        assert heading == ""
        assert "Hello world" in body
        assert "Second line" in body

    def test_multiple_headings(self):
        from scripts.ingest import _extract_sections

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.docx"
            _make_docx(
                path,
                [
                    ("Heading 1", "Chapter One"),
                    (None, "Body of chapter one."),
                    ("Heading 2", "Section Two"),
                    (None, "Body of section two."),
                ],
            )
            sections = _extract_sections(path)

        assert len(sections) == 2
        assert sections[0][0] == "Chapter One"
        assert "Body of chapter one." in sections[0][1]
        assert sections[1][0] == "Section Two"
        assert "Body of section two." in sections[1][1]

    def test_empty_paragraphs_skipped(self):
        from scripts.ingest import _extract_sections

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.docx"
            _make_docx(path, [(None, "Text"), (None, "   "), (None, "More text")])
            sections = _extract_sections(path)

        assert len(sections) == 1
        assert "   " not in sections[0][1]


class TestLoadDocx:
    def test_returns_lc_documents(self):
        from scripts.ingest import load_docx

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.docx"
            _make_docx(path, [(None, "Some content for the HR bot.")])
            docs = load_docx(path)

        assert len(docs) >= 1
        assert all(isinstance(d, LCDocument) for d in docs)

    def test_metadata_contains_source(self):
        from scripts.ingest import load_docx

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.docx"
            _make_docx(path, [(None, "Policy text here.")])
            docs = load_docx(path)

        assert docs[0].metadata["source"] == "policy.docx"

    def test_metadata_contains_section(self):
        from scripts.ingest import load_docx

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "manual.docx"
            _make_docx(
                path,
                [
                    ("Heading 1", "Vacation Policy"),
                    (None, "Employees are entitled to 28 days of leave."),
                ],
            )
            docs = load_docx(path)

        assert docs[0].metadata["section"] == "Vacation Policy"

    def test_long_text_is_chunked(self):
        from scripts.ingest import CHUNK_SIZE, load_docx

        long_text = "Word " * 500  # ~2500 chars, should be split
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.docx"
            _make_docx(path, [(None, long_text)])
            docs = load_docx(path)

        assert len(docs) > 1
        for doc in docs:
            assert len(doc.page_content) <= CHUNK_SIZE + 50  # allow minor overshoot


# ── 6.2 — Prompts ─────────────────────────────────────────────────


class TestSystemPrompt:
    def test_prompt_is_nonempty(self):
        assert len(SYSTEM_PROMPT) > 100

    def test_prompt_contains_context_placeholder(self):
        assert "{context}" in SYSTEM_PROMPT

    def test_prompt_mentions_hr(self):
        assert "HR" in SYSTEM_PROMPT

    def test_prompt_mentions_no_personal_data(self):
        lower = SYSTEM_PROMPT.lower()
        assert "персональные данные" in lower or "конфиденциальн" in lower

    def test_prompt_language_is_russian(self):
        assert "русском" in SYSTEM_PROMPT.lower()


# ── 6.2 — Chain helpers ───────────────────────────────────────────


class TestFormatDocs:
    def test_single_document(self):
        docs = [LCDocument(page_content="Hello")]
        assert _format_docs(docs) == "Hello"

    def test_multiple_documents_joined_with_separator(self):
        docs = [LCDocument(page_content="A"), LCDocument(page_content="B")]
        result = _format_docs(docs)
        assert "A" in result
        assert "B" in result
        assert "---" in result

    def test_empty_list(self):
        assert _format_docs([]) == ""


# ── 6.2 — Retriever / vectorstore ─────────────────────────────────


class TestCollectionName:
    def test_default_collection_name(self):
        assert COLLECTION_NAME == "hr_documents"


class TestBuildVectorstore:
    def test_creates_vectorstore_instance(self):
        mock_client = MagicMock()
        mock_embeddings = MagicMock()

        with patch("app.rag.retriever.QdrantVectorStore") as mock_vs_cls:
            build_vectorstore(mock_client, mock_embeddings, "test_col")
            mock_vs_cls.assert_called_once_with(
                client=mock_client,
                collection_name="test_col",
                embedding=mock_embeddings,
            )


# ── 6.2 — Chain building ──────────────────────────────────────────


class TestBuildRagChain:
    def test_returns_runnable(self):
        mock_retriever = MagicMock()
        mock_llm = MagicMock()

        chain = build_rag_chain(mock_retriever, mock_llm)
        # The chain should be a LangChain Runnable (has invoke method)
        assert hasattr(chain, "invoke")
