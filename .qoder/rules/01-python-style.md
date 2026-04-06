---
trigger: glob
glob: app/**/*.py, scripts/**/*.py, tests/**/*.py
---
# Python Style


## Rules
- Use Python 3.11+ features and modern typing syntax.
- Use pydantic v2 for request and response schemas.
- Prefer explicit imports and small functions.
- Prefer composition over large god classes.
- Prefer composition of async functions over large monolithic coroutines.
- Build async workflows from small awaitable steps with explicit inputs, outputs, and side effects.
- Keep async boundaries explicit for API and I/O code.
- Use `asyncio.gather` or `TaskGroup` only for independent I/O-bound work.
- Use `asyncio.create_task()` only for explicit background work with clear lifecycle, cancellation, and error handling.
- Keep pure business logic separate from async transport and storage adapters.
- Avoid files longer than 300–400 lines unless there is a strong reason.
- Keep business logic testable outside FastAPI request handlers.


## Code style
- Use clear names over abbreviations.
- Prefer deterministic behavior for core service logic.
- Return structured results instead of loosely shaped dicts when practical.
- Extract reusable logic instead of duplicating code across adapters.
- Make async return types explicit and stable so async steps compose predictably.
- Prefer small orchestrator functions that compose focused async helpers.
- Prefer named tasks and explicit ownership for long-lived background work.


## Do not
- Do not introduce unnecessary abstractions for tiny modules.
- Do not create framework-heavy patterns unless they simplify maintenance.
- Do not hide side effects inside utility helpers.
- Do not mix unrelated I/O, validation, parsing, and business decisions inside one large coroutine.
- Do not introduce concurrency when steps depend on each other or when failure handling becomes unclear.
- Do not use `asyncio.create_task()` as a shortcut for avoiding proper awaiting.
- Do not spawn background tasks without explicit error handling, cancellation strategy, or ownership.
- Do not use request-scoped background tasks for critical work that must complete before returning success.


## Example
Good:
- Compose async workflows from small functions such as `load_user()`, `load_permissions()`, and `build_profile()`.
- Run independent reads concurrently with `TaskGroup` or `gather`.
- Use `asyncio.create_task()` only for intentionally detached background work that is supervised.
- Keep validation and business rules reusable outside FastAPI handlers and infrastructure adapters.

Avoid:
- One large async function that fetches data, validates input, applies business rules, logs, retries, and formats the response inline.
- Fire-and-forget `create_task()` calls with no ownership, cancellation, or error observation.


# Note
Secret management and environment configuration rules → see `09-security.md`.