---
description: |
  Applies reviewer feedback to an agent-generated PR when a maintainer comments
  /agent-fix.

on:
  slash_command:
    name: agent-fix
    strategy: centralized
  reaction: "eyes"

permissions: read-all

engine: copilot
network:
  allowed:
    - defaults
    - python

tools:
  github:
    toolsets: [default]
    min-integrity: none
  edit:
  bash: true

safe-outputs:
  push-to-pull-request-branch:
    required-title-prefix: "[agent] "
    required-labels: [agent-generated]
    allowed-files:
      - src/**
      - tests/**
    protected-files: blocked
    github-token-for-extra-empty-commit: ${{ secrets.GH_AW_CI_TRIGGER_TOKEN }}
  add-comment:
    max: 1
    footer: false

imports:
  - shared/slack-notify.md

timeout-minutes: 25
---

# CenEMS Agent Fixer

You are updating an existing agent-generated PR after a maintainer requested
`/agent-fix`.

## Guardrails

- Only change PRs whose title starts with `[agent] ` and that have the
  `agent-generated` label.
- Modify only `src/**` and `tests/**`.
- Do not modify `.github/**`, `AGENTS.md`, `README.md`, dependency manifests, or secrets.
- Address review feedback without broad refactors.

## Steps

1. Read the triggering PR, existing reviews, review comments, PR comments, and
   linked issue.
2. Identify the actionable feedback that should be addressed in code.
3. Make the smallest code and test changes needed.
4. Run `python -m unittest discover`.
5. Use `push-to-pull-request-branch` to update the PR branch.
6. Add a PR comment summarizing which feedback was addressed and the test result.
7. Call `slack-notify` with a short message that the PR was updated from
   `/agent-fix`, including the PR URL.

If no code change is needed, use `add-comment` to explain why and do not push.
