# AGENTS.md

## Scope

These instructions apply to the whole repository.

## Pilot Safety Rules

- Keep generated code changes focused on `src/` and `tests/`.
- Do not modify `.github/`, `AGENTS.md`, or repository secrets from an agent run.
- Run `python -m unittest discover` before proposing or updating a PR.
- Generated PRs should stay draft until a human maintainer marks them ready.
- Prefer small, reviewable changes with clear tests.
