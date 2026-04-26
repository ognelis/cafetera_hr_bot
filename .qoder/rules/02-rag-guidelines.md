---
trigger: glob
glob: packages/core/src/cafetera_core/rag/**/*.py, packages/core/src/cafetera_core/domain/**/*.py, packages/admin/src/cafetera_admin/indexer.py, packages/admin/src/cafetera_admin/parser.py
---
# RAG Guidelines

## Rules
- Use LangChain as the orchestration layer unless explicitly asked otherwise.
- Use Qdrant as the production vector store abstraction.
- Retrieval logic must be centralized in `cafetera_core/rag`.
- Prompt templates must be centralized and reusable.
- Preserve source metadata for citations, tracing, and debugging.
- Keep ingestion code separate from online query path.
- The project uses hybrid retrieval (dense + sparse BM25) by default, with optional ColBERT reranking.
- Keep model provider details out of business logic where possible.

## Retrieval
- Prefer simple and debuggable retrieval over premature complexity.
- Keep retriever construction isolated from endpoint code.
- Use configurable search parameters instead of magic constants.
- Make it easy to switch retrieval mode via config or feature flag.
- Hybrid search uses Qdrant prefetch + RRF (Reciprocal Rank Fusion).
- ColBERT reranking is enabled via `RERANKING_ENABLED=true` in settings.

## Prompting
- Keep prompts in dedicated modules.
- Avoid giant inline prompt strings inside services or route handlers.
- Prefer short, explicit system instructions.
- System prompts are split per package: `SYSTEM_PROMPT` in `cafetera_vk_bot/prompts.py`, `GLOBAL_EXPERTS_PROMPT` + `DOCUMENT_EXPERTS_PROMPT` in `cafetera_admin/prompts.py`. Never share prompts across packages.

## Do not
- Do not embed or index documents inside request handlers.
- Do not couple prompt templates to Telegram or VK response formatting.
- Do not hide retrieval side effects across unrelated modules.

Reference: https://python.langchain.com/docs/concepts/rag/
