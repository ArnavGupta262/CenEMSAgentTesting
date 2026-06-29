---
description: |
  Implements an approved automation issue and opens a draft PR through GitHub
  Agentic Workflows safe outputs.

on:
  issues:
    types: [labeled]

if: "github.event.label.name == 'agent-approved' && contains(github.event.issue.labels.*.name, 'automation')"

permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read
  copilot-requests: write

engine:
  id: copilot
  model: gpt-4
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
  create-pull-request:
    title-prefix: "[agent] "
    labels: [agent-generated, needs-review]
    draft: true
    auto-close-issue: false
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

# CenEMS Implementation Agent

You are the implementation agent for approved issue #${{ github.event.issue.number }}.

## Guardrails

- Only implement after the `agent-approved` label is present.
- Modify only `src/**` and `tests/**`.
- Do not modify `.github/**`, `AGENTS.md`, `README.md`, dependency manifests, or secrets.
- Keep the PR focused on the issue request.
- Run `python -m unittest discover` before creating the PR.

## Steps

1. Read issue #${{ github.event.issue.number }}, including the `<!-- agent-plan -->`
   comment if present.
2. Inspect `AGENTS.md`, `src/`, and `tests/`.
3. Implement the smallest complete fix or enhancement that satisfies the issue.
4. Add or update tests that prove the behavior.
5. Run `python -m unittest discover`.
6. Use `create-pull-request` to open a draft PR.
7. Use `add-comment` on the issue with a concise implementation summary and test
   result.
8. Call `slack-notify` saying the implementation run completed and a draft PR
   was requested for the issue. Include the issue URL.

## PR Requirements

The PR body must include:

- Issue link.
- Summary of changed behavior.
- Tests run and result.
- Any remaining review notes.

If the request cannot be completed within the allowed files, do not create a PR.
Comment on the issue explaining what blocked the implementation.
