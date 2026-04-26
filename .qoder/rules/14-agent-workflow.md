---
trigger: model_decision
description: "Agent workflow patterns: session hygiene, context isolation, verification gates, and investigation discipline."
---
# Agent Workflow

## Session Hygiene

- Treat each session as a bounded resource with limited context window.
- Start a fresh session when switching to an unrelated task or after a long correction loop.
- Summarize key decisions and outcomes before ending a session; carry forward only the summary, not the full history.
- Do not endlessly patch a failing approach in one session — reset and re-plan with a cleaner prompt.

## Explore → Plan → Code Discipline

- Before writing code, always inspect the relevant files and existing patterns first.
- Produce a short implementation plan coherent with repository conventions before coding.
- Do not start coding until the plan accounts for layer boundaries (ref: `00-architecture.md`) and existing patterns.
- For trivial single-file changes, inline exploration is sufficient — skip formal planning.

## Context Isolation

- Keep investigation, implementation, and review in separate mental phases.
- Pass only concise summaries between phases, not raw file dumps or intermediate reasoning.
- When multiple files need analysis, summarize findings per file before making changes.

## Verification as a Gate

- Every non-trivial code change must pass through a verification step before delivery.
- Verification means running actual tools (tests, linters, type checks) — not asserting correctness by inspection alone.
- Reference the validation checklist in `AGENTS.md` for the canonical set of checks.
- If verification fails, fix and re-verify — do not skip the gate.

## Writer / Reviewer Separation

- The agent writing code should not be the sole judge of its correctness.
- For high-impact changes (cross-module, security, data flow), request or perform an independent review pass.
- Architecture decisions and acceptance criteria remain human-led (ref: `AGENTS.md`).

## Tool Selection Order (Investigation)

- Prefer broad-to-narrow: start with codebase search or directory listing, then grep for patterns, then read specific files.
- Do not read entire files when a targeted search would suffice.
- Do not guess file paths — search first.

## Skills as Modular Context

- Specialized, repeatable workflows (e.g., "add a new API endpoint", "add a new VK handler") can be extracted into skill files.
- Skills should be self-contained: include the goal, steps, file paths involved, and verification criteria.
- Keep skills narrow — one skill per workflow, not one skill per domain.

## Do not

- Do not mix exploration, coding, and review in a single undifferentiated pass for complex tasks.
- Do not continue iterating in a degraded context — reset the session.
- Do not skip verification to save time.
- Do not assume file paths or API shapes without checking first.
- Do not duplicate guidance already in existing rule files — reference them.
