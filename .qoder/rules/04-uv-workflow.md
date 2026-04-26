---
trigger: always_on
---
# uv Workflow

## Rules
- This project uses `uv`, not Poetry and not plain pip workflow.
- Dependency management must be based on `pyproject.toml` and `uv.lock`.
- Use `.venv` as the project virtual environment.
- Prefer `uv run` for local commands.
- Prefer `uv sync` to align the environment with the project dependencies.
- Assume local development is done inside a uv-managed environment.

## Standard commands
- `uv venv`
- `uv sync` — install all workspace packages and dependencies.
- `uv run pytest`

## Local development
- `uv run python scripts/admin_server.py` — run admin server locally (Hypercorn, port 8000).
- `uv run python scripts/polling_vk.py` — run VK bot in Long Poll mode locally.
- `uv run python scripts/polling.py` — run Telegram bot in polling mode locally (Post-MVP).

## Do not
- Do not introduce `poetry.lock`, `Pipfile`, or pip-tools workflow unless explicitly requested.
- Do not add `requirements.txt` by default unless explicitly requested.
- Do not suggest `pip install ...` commands unless explicitly requested.
- Do not assume global Python packages are available.