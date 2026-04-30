---
trigger: glob
glob: packages/rag_service/src/cafetera_rag_service/**/*.py, packages/core/src/cafetera_core/rag_client.py
---
# RAG Guidelines

## Architecture

The RAG pipeline runs as a standalone FastAPI microservice (`packages/rag_service`) on port 8001.
Other packages (admin, vk_bot) never import RAG internals directly — they communicate
via `RAGClient`, a thin async HTTP client in `cafetera_core/rag_client.py`.

### Package layout
- `packages/rag_service/src/cafetera_rag_service/` — RAG microservice (retrieval, chains, embeddings, indexing, parsing).
- `packages/core/src/cafetera_core/rag_client.py` — `RAGClient` HTTP bridge used by admin and vk_bot.

### Key modules inside `cafetera_rag_service`
- `rag/chain.py` — `build_llm()`, `build_rag_chain()`: LLM instantiation and chain assembly (retrieve → format → prompt → LLM → text).
- `rag/retriever.py` — `AsyncQdrantRetriever`, `build_retriever()`, `build_retriever_for_document()`, `build_qdrant_client()`, `build_embeddings()`.
- `rag/reranker.py` — `CrossEncoderReranker`, `RerankingRetriever`: optional cross-encoder reranking via FastEmbed.
- `rag/prompts.py` — `CATEGORY_HINTS` dict, `DOCUMENT_EXPERTS_PROMPT`. Package-specific system prompts live elsewhere (see Prompting).
- `rag/text_processor.py` — Russian lemmatization for BM25 queries.
- `qa_service.py` — `QAService`: stateful service holding chain, qdrant client, embeddings, LLM. Provides `ask()`, `ask_about_document()`, `stream_ask()`, `stream_about_document()`.
- `parser.py` — `load_document()`, `ParseResult`: Docling-based PDF/DOCX/XLSX parsing and chunking.
- `config.py` — `RagServiceSettings` (pydantic-settings).

### Inter-service communication
- `RAGClient` (`cafetera_core/rag_client.py`) wraps `httpx.AsyncClient` and provides typed methods: `ask()`, `stream_ask()`, `ask_about_document()`, `stream_about_document()`, `index_chunks()`, `ingest_document()`, `toggle_search()`, `delete_document()`, `invalidate_cache()`, `health()`.
- Admin and vk_bot create `RAGClient` in their lifespan, passing `rag_service_url` and `rag_service_api_key` from settings.
- System prompts are passed per-request from the caller (admin or vk_bot) to the RAG service via the HTTP payload — the RAG service itself does not own caller-specific prompts.

---

## Rules
- Use LangChain as the orchestration layer unless explicitly asked otherwise.
- Use Qdrant as the production vector store abstraction.
- Retrieval logic must be centralized in `cafetera_rag_service/rag/`.
- Preserve source metadata for citations, tracing, and debugging.
- Keep ingestion code separate from online query path.
- The project uses hybrid retrieval (dense + sparse BM25) by default, with optional ColBERT reranking.
- Keep model provider details out of business logic where possible.

## Retrieval
- Prefer simple and debuggable retrieval over premature complexity.
- Keep retriever construction isolated from endpoint code.
- Use configurable search parameters instead of magic constants.
- Make it easy to switch retrieval mode via config or feature flag.
- Hybrid search uses Qdrant prefetch + RRF (Reciprocal Rank Fusion) via `AsyncQdrantRetriever`.
- ColBERT reranking is enabled via `RERANKING_ENABLED=true` in `RagServiceSettings`.
- Adaptive `k` is computed by `estimate_k()` in `retriever.py` based on question complexity.
- `build_retriever()` applies a filter excluding chunks where `is_search_enabled` is `False`.
- `build_retriever_for_document()` scopes search to a single `document_id`.

## Prompting
- Keep prompts in dedicated modules — never inline giant prompt strings in services or handlers.
- Prefer short, explicit system instructions.
- Package-specific prompts live in their own packages:
  - `cafetera_vk_bot/prompts.py` — `SYSTEM_PROMPT` for VK bot.
  - `cafetera_admin/prompts.py` — `GLOBAL_EXPERTS_PROMPT` for admin chat.
- These prompts are passed to the RAG service at call time via `RAGClient.ask(system_prompt=...)`.
- RAG-internal prompts (`CATEGORY_HINTS`, `DOCUMENT_EXPERTS_PROMPT`) stay in `cafetera_rag_service/rag/prompts.py`.
- Never share system prompts across packages.

## QAService
- `QAService` in `cafetera_rag_service/qa_service.py` is the core domain service.
- Initialized with chain, qdrant client, embeddings, LLM, settings, and optional reranker.
- Callers use `ask()` / `stream_ask()` for global Q&A, `ask_about_document()` / `stream_about_document()` for document-scoped Q&A.
- Document chains are LRU-cached internally (max 50).
- On error, returns user-friendly Russian error strings — never exposes exceptions.

## Do not
- Do not embed or index documents inside request handlers.
- Do not couple prompt templates to Telegram or VK response formatting.
- Do not hide retrieval side effects across unrelated modules.
- Do not import from `cafetera_rag_service` in admin, vk_bot, or core — use `RAGClient` HTTP calls only.
- Do not duplicate RAG logic (retrieval, chain building, embedding) in admin, core, or vk_bot.
- Do not put caller-specific system prompts inside the RAG service — pass them per-request.
- Do not create Qdrant or LLM clients outside of `cafetera_rag_service` for query purposes.
