---
trigger: glob
glob: tests/**/*.py
---
# Tests

## Rules
- Use pytest.
- Prefer unit tests for service logic and integration tests for API routes.
- Mock LLM and vector store interactions where practical.
- Avoid coupling tests to real Telegram or VK APIs.
- Cover both happy path and no-context path for RAG responses.
- Keep tests readable and focused on behavior.

## Priorities
- Test domain services before transport adapters.
- Test API contracts for `/health` and `/api/chat`.
- Test webhook handlers with normalized payload samples.

## Do not
- Do not rely on external network calls in default test runs.
- Do not make tests depend on real model credentials.
- Do not hide important assertions in helper functions.
