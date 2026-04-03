---
trigger: glob
glob: app/**/*.py, scripts/**/*.py, tests/**/*.py
---
# Python Style

## Rules
- Use Python 3.11+ features and modern typing syntax.
- Use pydantic v2 for request and response schemas.
- Use `pydantic-settings` for application settings.
- Prefer explicit imports and small functions.
- Prefer composition over large god classes.
- Keep async boundaries explicit for API and I/O code.
- Avoid files longer than 300-400 lines unless there is a strong reason.
- Do not hardcode secrets, tokens, URLs, or credentials.
- Keep business logic testable outside FastAPI request handlers.

## Code style
- Use clear names over abbreviations.
- Prefer deterministic behavior for core service logic.
- Return structured results instead of loosely shaped dicts when practical.
- Extract reusable logic instead of duplicating code across adapters.

## Do not
- Do not introduce unnecessary abstractions for tiny modules.
- Do not create framework-heavy patterns unless they simplify maintenance.
- Do not hide side effects inside utility helpers.