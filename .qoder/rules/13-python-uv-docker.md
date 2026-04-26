---
trigger: glob
glob: **/pyproject.toml, **/uv.lock, **/Dockerfile, **/*.py
---

For uv-based Python projects, always generate a production-ready Docker setup.

- Use a multi-stage Dockerfile with separate builder and runtime stages.
- Copy only `pyproject.toml` and `uv.lock` before installing dependencies; copy application source code only after the dependency layer.
- Use `uv sync --locked`; for production always use `--no-dev`, use `--no-install-project` where appropriate, and use `--no-editable` for the final install.
- If the base image already provides Python, set `UV_PYTHON_DOWNLOADS=never`.
- Set `UV_LINK_MODE=copy`; enable `UV_COMPILE_BYTECODE=1` when appropriate.
- Prefer a minimal pinned Python base image and copy the `uv` binary from the official uv image; if a digest is not pinned, add a TODO comment.
- Keep the runtime image minimal: no build tools, no dev dependencies, no uv cache, and no unnecessary system packages.
- Never run the container as root; create a dedicated non-root system user for runtime.
- Always create a `.dockerignore` file and exclude `.venv`, `__pycache__`, `.git`, test artifacts, local env files, caches, and build outputs.
- Do not allow these anti-patterns: `COPY . .` before dependency installation, root runtime, dev dependencies in production, unpinned `latest`, shell-form `CMD`, host `.venv` inside the image, or development servers in production.
- Use an absolute `WORKDIR`, cache-friendly layers, and JSON exec-form for `CMD` or `ENTRYPOINT`.
- If the project is a web API, include `EXPOSE`.
- For monorepo/workspace projects, use `uv export --package <name>` to generate per-package requirements for Docker builds.
- Pre-download ML models (Docling, tokenizer, embedding caches) during Docker build to avoid runtime network calls. Cache them in dedicated directories and set environment variables pointing to those caches.
- If the entrypoint, module path, app object, or port is unknown, do not invent values; leave explicit TODO markers.
- Always output: `Dockerfile`, `.dockerignore`, brief explanations, build and run commands, and a short list of manual replacements.
