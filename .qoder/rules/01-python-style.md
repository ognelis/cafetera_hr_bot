---
trigger: glob
glob: packages/**/*.py, scripts/**/*.py, tests/**/*.py
---
# Python Style


## Rules
- Use Python 3.13 features and modern typing syntax.
- Use pydantic v2 for request and response schemas.
- Prefer explicit imports and small functions.
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


## OOP vs Functional style

Default to functions. Use plain `def` or `async def` for data transformations,
business rules, validation, and async workflow steps. Prefer a module of focused
functions over a class with methods when no persistent state is involved.

Use a class when:
- You need mutable state shared across multiple methods with a clear lifecycle
  (e.g. `QdrantRepository`, `RedisClient`, `S3Adapter`).
- Implementing a Protocol, ABC, or framework interface that requires a class.
- Grouping I/O operations that share initialization config or a connection
  object — repository, adapter, or external client wrapper.
- Modeling structured data — always use Pydantic `BaseModel` or `dataclass`,
  never a plain class with `__init__` and loose attributes.

Do not:
- Do not wrap a single function in a class — use a plain function or module instead.
- Do not use inheritance deeper than one level — prefer Protocol + composition.
- Do not create `@staticmethod`-only classes — that is a module, not a class.
- Do not put business logic inside class methods — keep it in standalone
  functions that are testable without instantiation.

Good: standalone functions for business logic, classes for I/O adapters with connection state, Pydantic `BaseModel` for structured data.
Avoid: single-function wrapper classes, business logic inside class methods, `@staticmethod`-only classes.


## Do not
- Do not introduce unnecessary abstractions for tiny modules.
- Do not create framework-heavy patterns unless they simplify maintenance.
- Do not hide side effects inside utility helpers.
- Do not mix unrelated I/O, validation, parsing, and business decisions inside one large coroutine.
- Do not introduce concurrency when steps depend on each other or when failure handling becomes unclear.
- Do not use `asyncio.create_task()` as a shortcut for avoiding proper awaiting.
- Do not spawn background tasks without explicit error handling, cancellation strategy, or ownership.
- Do not use request-scoped background tasks for critical work that must complete before returning success.


## Linting (ruff)

Config: `line-length = 100`, `target-version = "py313"`, `select = ["E", "F", "I", "UP", "B"]`.

- **E** (pycodestyle): line length ≤100, no trailing whitespace, correct indentation, no bare `except`.
- **F** (pyflakes): no unused imports, no undefined names, no redefined-unused variables, no `import *`.
- **I** (isort): imports sorted by stdlib → third-party → local, separated by blank lines.
- **UP** (pyupgrade): use modern Python 3.13 syntax — `X | Y` instead of `Union[X, Y]`, `list[T]` instead of `List[T]`, f-strings over `.format()`, `type X = ...` where applicable.
- **B** (flake8-bugbear): no mutable default args, no `except Exception:` without re-raise, no `assert False`, no redundant `list()`/`tuple()` calls, `raise` from inside `except` must chain with `from`.

Run: `uv run ruff check .` — all violations must be resolved before committing.

# Note
Secret management and environment configuration rules → see `09-security.md`.