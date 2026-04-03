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

## Security test coverage
- Test that webhook endpoints return 403 when secret validation fails.
- Test that invalid or missing `X-Telegram-Bot-Api-Secret-Token` is rejected.
- Test that VK events with a wrong `secret` field are rejected.
- Do not use real tokens or secrets in test fixtures — use placeholder strings.

## Do not
- Do not rely on external network calls in default test runs.
- Do not make tests depend on real model credentials.
- Do not hide important assertions in helper functions.