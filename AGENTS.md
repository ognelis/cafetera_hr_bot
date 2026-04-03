# AGENTS.md

## Goal
This repository uses agentic coding for implementation assistance, but architecture, invariants, and acceptance are human-led.

## Core workflow
1. First inspect relevant files and existing patterns.
2. Then produce a short implementation plan.
3. Do not start coding until the plan is coherent with repository conventions.
4. Implement in small, reviewable changes.
5. After implementation, run validation commands.
6. Report what changed, what was verified, and what remains risky.

## Hard constraints
- Do not introduce new dependencies unless explicitly requested.
- Do not modify public contracts unless explicitly requested.
- Do not change database schema, infra config, or CI unless explicitly requested.
- Do not touch files outside the stated scope.
- Reuse existing patterns before inventing new abstractions.
- Prefer minimal diff over broad refactoring.
- Stop and ask if requirements conflict with codebase conventions.

## Code quality
- Follow existing architecture and naming.
- Prefer explicitness over cleverness.
- Keep functions small and readable.
- Add or update tests for any non-trivial behavior change.
- Preserve backward compatibility unless the task explicitly allows breaking changes.

## Validation
Before finishing, always:
- run tests relevant to changed code,
- run linters/formatters if configured,
- check for compile errors,
- summarize validation status.

## Final response format
Return:
1. Files changed
2. Why each change was made
3. Validation performed
4. Remaining risks or assumptions
