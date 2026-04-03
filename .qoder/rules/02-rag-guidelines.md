---
trigger: glob
glob: app/rag/**/*.py, app/domain/**/*.py, scripts/ingest*.py
---
# RAG Guidelines

## Rules
- Use LangChain as the orchestration layer unless explicitly asked otherwise.
- Use Qdrant as the production vector store abstraction.
- Retrieval logic must be centralized in `app/rag`.
- Prompt templates must be centralized and reusable.
- Preserve source metadata for citations, tracing, and debugging.
- Keep ingestion code separate from online query path.
- Start with dense retrieval; only add hybrid retrieval on explicit request.
- Keep model provider details out of business logic where possible.

## Retrieval
- Prefer simple and debuggable retrieval over premature complexity.
- Keep retriever construction isolated from endpoint code.
- Use configurable search parameters instead of magic constants.
- Make it easy to switch retrieval mode via config or feature flag.

## Prompting
- Keep prompts in dedicated modules.
- Avoid giant inline prompt strings inside services or route handlers.
- Prefer short, explicit system instructions.

## Do not
- Do not embed or index documents inside request handlers.
- Do not couple prompt templates to Telegram or VK response formatting.
- Do not hide retrieval side effects across unrelated modules.
