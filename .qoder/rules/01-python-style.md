***
trigger: glob
glob: app/**/*.py, scripts/**/*.py, tests/**/*.py
***
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

Good:
```python
# Business rule as a standalone function — testable anywhere
def compute_relevance_score(embedding: list[float], threshold: float) -> float:
    ...

# I/O adapter as a class — owns connection and config state
class QdrantRepository:
    def __init__(self, client: QdrantClient, collection: str) -> None:
        self.client = client
        self.collection = collection

    async def search(self, vector: list[float], top_k: int) -> list[ScoredPoint]:
        ...

# Structured result as a Pydantic model
class SearchResult(BaseModel):
    id: str
    score: float
    payload: dict[str, Any]
```

Avoid:
```python
# A class that only wraps one function — use a plain function instead
class RelevanceScorer:
    def compute(self, embedding: list[float]) -> float:
        ...

# Business logic buried in a class method — hard to test in isolation
class SearchService:
    async def handle(self, query: str) -> list[dict]:
        # fetches, scores, filters, formats — all in one method
        ...
```


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