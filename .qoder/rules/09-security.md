---
trigger: always_on
---
# Security

## General rules

- Treat security as a default requirement, not an optional enhancement.
- Never hardcode secrets, tokens, passwords, API keys, DSNs, or webhook secrets.
- Load secrets from environment variables via `pydantic-settings`.
- Use least-privilege access for all integrations and credentials.
- Prefer explicit validation over implicit trust for all external inputs.
- Do not expose internal implementation details in API responses.

---

## Secrets and configuration

- Store secrets only in environment variables or a dedicated secret manager.
- Never commit `.env` with real secrets to version control.
- Provide `.env.example` with placeholders only.
- Rotate bot tokens, API keys, and webhook secrets if they may have leaked.
- Keep production and development secrets separate.
- Do not print secrets to logs, traces, exceptions, or debug output.

### Do not
- Do not hardcode Telegram bot tokens.
- Do not hardcode VK access tokens.
- Do not hardcode Qdrant API keys.
- Do not include secrets in README examples or test fixtures.

---

## FastAPI application security

- Use HTTPS in production behind a reverse proxy.
- Disable debug mode in production.
- Sanitize error responses returned to clients.
- Log full technical details internally, but return generic failure messages externally.
- Use pydantic models for all request and response validation.
- Validate and sanitize all user input before using it in business logic.
- Add request size and timeout limits where appropriate.

### Do not
- Do not return stack traces to clients.
- Do not expose internal exception messages in production responses.
- Do not accept arbitrary unvalidated JSON into service logic.

---

## Authentication and authorization

- Protect internal or admin endpoints with explicit authentication.
- Use API keys, Bearer auth, or another explicit auth mechanism for protected routes.
- Use constant-time comparison for secret values where applicable.
- Validate permissions separately from authentication when roles or scopes exist.
- Keep public webhook endpoints narrow and purpose-specific.

### Do not
- Do not leave admin, reindex, or ingestion endpoints open without authentication.
- Do not trust user-supplied identity fields without verification.

---

## Telegram webhook security

- Use Telegram webhook mode for production.
- Always set and validate `secret_token` for Telegram webhooks.
- Reject requests with invalid `X-Telegram-Bot-Api-Secret-Token`.
- Accept only the webhook payload shape expected from Telegram.
- Keep Telegram webhook endpoint dedicated to Telegram only.

### Do not
- Do not process Telegram webhook requests if secret validation fails.
- Do not reuse Telegram webhook secret for other integrations.

---

## VK webhook security

- Use VK Callback API for production.
- Always validate the incoming `secret` field.
- Return `confirmation_token` only for VK confirmation events.
- Return plain text `ok` only after successful receipt of a valid VK event.
- Keep VK webhook endpoint dedicated to VK only.

### Do not
- Do not process VK events if `secret` validation fails.
- Do not expose VK callback internals in response bodies.

---

## Rate limiting and abuse protection

- Add rate limiting to public API endpoints and webhook-adjacent endpoints where appropriate.
- Protect chat endpoints from flooding, replay abuse, and accidental loops.
- Consider per-user, per-IP, and per-platform limits depending on the endpoint.
- Add backpressure for expensive RAG operations.
- Prefer graceful rejection over overload.

### Do not
- Do not allow unbounded parallel expensive requests.
- Do not let one user consume all model or retrieval capacity.

---

## Logging and privacy

- Log security-relevant events: auth failures, secret mismatches, repeated webhook failures, rate-limit triggers.
- Redact secrets, tokens, session identifiers, and sensitive payload fragments from logs.
- Log enough context for debugging without storing full personal data by default.
- Treat user messages as potentially sensitive.
- Prefer structured logging with explicit fields.

### Do not
- Do not log raw Authorization headers.
- Do not log full bot tokens, API keys, or webhook secrets.
- Do not dump full incoming webhook payloads in production without redaction.

---

## RAG-specific security

- Treat retrieved documents as untrusted input to the prompt pipeline.
- Keep prompts explicit about source-bounded answering.
- Preserve source metadata for auditability.
- Restrict ingestion sources to trusted directories, buckets, or approved inputs.
- Validate uploaded or imported files before indexing.
- Add size and type checks for ingestion inputs.

### Do not
- Do not index arbitrary files without validation.
- Do not let user input directly control filesystem paths.
- Do not trust retrieved content as safe for direct execution or rendering.

---

## HTTP and external integrations

- Use reasonable timeouts for all outgoing HTTP requests.
- Validate target URLs and avoid open redirect or arbitrary outbound call patterns.
- Reuse shared async clients instead of creating clients per request.
- Retry carefully and only for safe operations.
- Fail closed when security checks cannot be completed.

### Do not
- Do not make outbound calls to user-provided URLs without strict validation.
- Do not use infinite retries.
- Do not ignore TLS and certificate validation in production.

---

## Files and uploads

- Validate file size, type, and extension before processing or indexing.
- Reject files that exceed allowed limits.
- Store uploaded files outside executable paths when applicable.
- Sanitize filenames and do not trust client-provided names.
- Scan or validate file content before passing it into ingestion flows.

### Do not
- Do not rely only on file extension for validation.
- Do not accept executable or unsupported file types by default.

---

## Dependency and runtime safety

- Keep dependencies updated and avoid abandoned packages when possible.
- Prefer well-maintained official libraries for integrations.
- Pin project dependencies in the project lock workflow.
- Review security impact before adding new third-party packages.
- Remove unused dependencies.

### Do not
- Do not add a package only for a trivial helper if standard library is enough.
- Do not depend on unknown unofficial bot wrappers without reason.

---

## Canonical patterns

### Secret comparison
```python
import secrets

if not secrets.compare_digest(received_secret, settings.telegram_secret_token):
    raise HTTPException(status_code=403, detail="Forbidden")
```

### Generic production error response
```python
raise HTTPException(status_code=500, detail="Internal server error")
```

### Settings-based secret loading
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_secret_token: str
    vk_access_token: str
    vk_secret: str
    qdrant_api_key: str | None = None
```

---

## Do not

- Do not trust external input by default.
- Do not skip webhook secret validation.
- Do not expose debug information in production.
- Do not log secrets or sensitive user content carelessly.
- Do not deploy public expensive endpoints without rate limiting or abuse controls.
