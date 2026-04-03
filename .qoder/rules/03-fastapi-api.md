---
trigger: glob
glob: app/api/**/*.py, app/main.py, app/core/**/*.py
---
# FastAPI API

## Rules
- Use FastAPI lifespan for startup and shutdown initialization.
- Keep endpoints thin: validate input, call service, return response.
- Use pydantic schemas for API contracts.
- Put application settings in a dedicated settings module.
- Initialize reusable clients once when practical.
- Keep webhook endpoints idempotent where possible.
- Separate HTTP transport concerns from domain logic.

## Settings
- Use `pydantic-settings` for environment-based configuration.
- Read configuration from `.env` for local development.
- Keep all environment variables centralized in one settings class.

## Route design
- Use `/health` for health checks.
- Put application endpoints under `/api` when appropriate.
- Keep Telegram and VK webhook routes separate.
- Normalize incoming payloads before passing to domain services.

## Do not
- Do not create heavy provider clients inside every route call unless necessary.
- Do not place business rules in routers.
- Do not return ad hoc JSON shapes if a schema already exists.