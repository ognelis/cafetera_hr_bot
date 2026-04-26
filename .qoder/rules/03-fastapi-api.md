---
trigger: glob
glob: packages/admin/src/cafetera_admin/**/*.py, packages/core/src/cafetera_core/config.py
---
# FastAPI API

## Rules
- Keep endpoints thin: validate input, call service, return response.
- Use pydantic schemas for API contracts.
- Put application settings in a dedicated settings module.
- Keep webhook endpoints idempotent where possible.
- Separate HTTP transport concerns from domain logic.

## Settings
- Use `pydantic-settings` for environment-based configuration.
- Read configuration from `.env` for local development.
- Settings use inheritance: `CoreSettings` (shared) is extended by `AdminSettings` and `VKSettings`. Each package imports its own settings class.

## Route design
- Use `/health` for health checks.
- Put application endpoints under `/api` when appropriate.
- Keep Telegram and VK webhook routes separate.
- Normalize incoming payloads before passing to domain services.
- Admin server entry point: `scripts/admin_server.py` → `cafetera_admin.server` (Hypercorn, port 8000).
- Use `AppResources` factory from `cafetera_core.resources` for resource initialization in lifespan.

## Do not
- Do not place business rules in routers.
- Do not return ad hoc JSON shapes if a schema already exists.

# Notes
- Lifespan, client initialization, and resource teardown → see `08-resource-safety.md`.
- Secret validation and security headers → see `09-security.md`.

Reference: https://fastapi.tiangolo.com/tutorial/bigger-applications/