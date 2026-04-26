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
- System prompts must be isolated per context — never share VK bot's `SYSTEM_PROMPT` with admin panel or vice versa.

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

## Key patterns

- Use `secrets.compare_digest()` for webhook secret comparison (timing-safe).
- Settings hierarchy: `CoreSettings` → `AdminSettings` / `VKSettings` in their respective packages.
- Return generic error messages externally; log details internally.

---

## Do not

- Do not trust external input by default.
- Do not skip webhook secret validation.
- Do not expose debug information in production.
- Do not log secrets or sensitive user content carelessly.
- Do not deploy public expensive endpoints without rate limiting or abuse controls.

---

## Input Validation Patterns

- Prefer allowlisting (define what IS permitted) over denylisting (blocking known bad values).
- Apply syntactic validation first (correct format), then semantic validation (business logic correctness — e.g., start_date < end_date, valid status transitions).
- Use strict type conversion with exception handling; rely on pydantic for this where possible.
- For string inputs: enforce minimum and maximum length constraints.
- For numeric inputs: enforce range checks (min/max bounds).
- For discrete value sets: validate against an explicit list of allowed values.
- Anchor regex patterns fully (`^...$`); avoid unbounded `.*` wildcards to prevent ReDoS.
- Server-side validation is mandatory; client-side validation is UX convenience only.
- For free-form Unicode text: normalize before validation to prevent homograph or encoding attacks.
- Apply context-specific output encoding: HTML entity encoding for HTML body, JavaScript encoding for script context, JSON encoding for API responses.

### Do not
- Do not use denylisting as the primary validation strategy.
- Do not write regex patterns without full anchoring and ReDoS review.

---

## Secrets Lifecycle

- Automate secret rotation on a periodic schedule (monthly or quarterly), not only after suspected leaks.
- Use gradual rotation: provision new secret, accept both old and new during transition, then revoke old.
- For webhook secrets (Telegram, VK): support secret versioning so rotation does not cause downtime.
- Log all secret access and rotation events for audit; alert on unusual access patterns.
- Minimize the time window secrets remain in memory; clear variables after use when practical.
- Review third-party dependencies (vkbottle, langchain, httpx) for accidental secret exposure in logs or exceptions.
- When team or infrastructure grows, consider moving from environment variables to a dedicated secrets manager with fine-grained access control per service (admin, VK bot, ingestion).

### Do not
- Do not rely solely on manual rotation triggered by suspected leaks.
- Do not allow all services to share the same secret access scope.

---

## Further reading

- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
