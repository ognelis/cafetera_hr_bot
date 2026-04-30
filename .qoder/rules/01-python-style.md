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

Default to functions. Use `def` / `async def` for data transformations, business
rules, validation, and workflow steps. Prefer a module of focused functions over
a class when no persistent state is involved.

Use a class only for:
- Stateful I/O adapters with a connection lifecycle (`RAGClient`, `S3Storage`, `QdrantRepository`).
- Protocol / ABC implementations required by a framework.
- Structured data — always via Pydantic `BaseModel` or `dataclass`.

Do not:
- Wrap a single function in a class — use a plain function or module.
- Inherit deeper than one level — prefer Protocol + composition.
- Create `@staticmethod`-only classes — that is a module.
- Put pure business logic inside class methods — keep it in standalone functions.


## Responsibility assignment (GRASP)

Apply these principles when deciding where new code belongs.

- **Information Expert** — assign behaviour to the module that owns the data.
  `QAService` owns the retriever and LLM, so it owns query execution.
- **Creator** — complex object assembly lives in dedicated factories.
  `build_resources()` / `build_rag_resources()` wire up all dependencies.
- **Controller** — transport handlers stay thin and delegate immediately.
  FastAPI routes delegate to `DocumentService`; VK handlers delegate to `RAGClient`.
- **Low Coupling** — packages communicate through narrow interfaces.
  Admin and VK bot reach RAG only via `RAGClient`, never by importing `rag_service`.
- **High Cohesion** — each service handles one concern.
  `DocumentService` = doc lifecycle, `QAService` = Q&A, `S3Storage` = file I/O.
- **Indirection** — introduce a mediator to decouple consumers from providers.
  `RAGClient` shields callers from HTTP details of the RAG service API.
- **Pure Fabrication** — invent service objects when no domain entity fits.
  `RAGClient`, `QAService`, `DocumentService` are fabricated to keep cohesion high.
- **Protected Variations** — isolate what changes behind a stable interface.
  If the RAG service API changes, only `RAGClient` is updated — callers are unaffected.
- **Polymorphism** — rarely needed here; the project prefers functions and
  composition over class hierarchies. Use Protocol when you genuinely need
  interchangeable implementations.


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