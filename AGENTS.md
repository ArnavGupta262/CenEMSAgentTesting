# AGENTS.md

## Scope

These instructions apply to the whole repository. They are read by the
Claude-powered agents in `.github/workflows/` (planning, implementation,
review, and fix).

## Pilot Safety Rules

- Keep generated code changes focused on `src/` and `tests/`.
- Do not modify `.github/`, `AGENTS.md`, or anything secret-related from an
  agent run. The implementation and fix agents edit code directly in the runner,
  so this boundary is enforced by instruction and by review — respect it.
- Run `python -m unittest discover` before proposing or updating a PR, and only
  proceed when it passes.
- Generated PRs must be opened as **draft** and stay draft until a human
  maintainer marks them ready.
- Prefer small, reviewable changes with clear tests.
- Never print, echo, or commit secrets (API keys, tokens, webhook URLs).
