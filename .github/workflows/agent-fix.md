---
description: |
  Applies review feedback to an agent-generated pull request using the Claude
  engine when a maintainer comments /agent-fix, then pushes the fix to the PR
  branch.

on:
  slash_command:
    name: agent-fix
    strategy: centralized
  reaction: "eyes"

permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read

engine:
  id: claude
  # Pinned to Haiku for the pilot (high tokens/min, low cost). Raise to Sonnet
  # for production once the Anthropic tier is lifted (see decision-record.md D14).
  model: claude-haiku-4-5
  max-turns: 30
network: defaults

tools:
  edit:
  bash: ["python*", "python3*"]
  github:
    toolsets: [issues, pull_requests, repos]

safe-outputs:
  push-to-pull-request-branch:
    target: "triggering"
    required-title-prefix: "[agent] "
    # PAT/GitHub App token so the push (synchronize event) re-triggers review.
    github-token: ${{ secrets.GH_AW_AGENT_TOKEN }}
  add-comment:
    max: 1
    footer: false

imports:
  - shared/slack-notify.md

timeout-minutes: 20
---

# CenEMS Feedback-Fix Agent

You are addressing review feedback on the triggering pull request after a
maintainer commented `/agent-fix`. You edit the code yourself in this runner and
push to the existing PR branch; you do **not** delegate to any other agent.

## Guardrails (follow `AGENTS.md`)

- Only act on pull requests titled with the `[agent]` prefix.
- Limit code changes to `src/**` and `tests/**`. Never touch `.github/`,
  `AGENTS.md`, or anything secret-related.
- Keep changes focused on the actionable review feedback.

## Steps

1. Read the triggering pull request, its reviews, review comments, and recent PR
   comments. Identify the actionable feedback.
2. If there is no actionable feedback, add a comment saying so and stop.
3. Make the smallest changes that address the feedback, editing only files under
   `src/**` and `tests/**`.
4. Run `python -m unittest discover` and confirm it passes.
5. Use `push-to-pull-request-branch` to push the fix to the PR branch.
6. Use `add-comment` to summarize which review comments were addressed.
7. Call `slack-notify` with a short message including the PR URL.
