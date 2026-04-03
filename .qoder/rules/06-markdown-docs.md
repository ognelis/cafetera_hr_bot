---
trigger: glob
glob: **/*.md, **/*.mdx
---
# Markdown Docs

## Rules
- Keep Markdown concise, readable, and scannable.
- Use clear headings and short bullet lists.
- Prefer fenced code blocks for commands and config.
- Document project setup using `uv` commands only.
- Keep architecture notes aligned with the actual code structure.
- Update docs when changing setup, commands, or major architecture.
- Verify that all external links resolve before committing them to docs.

## Do not
- Do not document Poetry or pip workflows unless explicitly requested.
- Do not leave outdated setup instructions in README files.
- Do not duplicate the same instructions across many files without need.
- Do not add external links without checking they are reachable.