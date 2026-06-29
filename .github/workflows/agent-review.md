---
description: |
  Reviews agent-generated pull requests with Codex and submits inline or summary
  feedback for the implementation agent.

on:
  pull_request:
    types: [opened, synchronize, ready_for_review]

if: "startsWith(github.event.pull_request.title, '[agent]')"

permissions:
  contents: read
  pull-requests: read
  actions: read
  copilot-requests: write

engine:
  id: copilot
  model: gpt-4o-mini
network: defaults

tools:
  github:
    toolsets: [pull_requests, repos]
    min-integrity: none
  bash: true

safe-outputs:
  create-pull-request-review-comment:
    max: 10
    side: "RIGHT"
  submit-pull-request-review:
    max: 1
    allowed-events: [COMMENT, REQUEST_CHANGES]
    footer: "always"
  add-comment:
    max: 1
    footer: false

timeout-minutes: 18
---

# CenEMS Agent PR Reviewer

You are the automatic code reviewer for agent-generated PR
#${{ github.event.pull_request.number }}.

## Review Scope

Focus on correctness, tests, maintainability, and whether the PR satisfies the
linked issue and agent plan. Prioritize actionable feedback over style opinions.

## Steps

1. Read the pull request, changed files, linked issue, and existing comments.
2. Inspect the diff and, if useful, run `python -m unittest discover`.
3. Leave inline review comments for concrete issues on changed lines.
4. Submit a consolidated review.
5. If there are correctness, testing, or maintainability issues that should be
   fixed before merge, use `REQUEST_CHANGES`; otherwise use `COMMENT`.
6. Add a PR conversation comment ending with:

```markdown
Maintainers: comment `/agent-fix` to let the implementation agent address this feedback.
```

Do not approve the PR. Do not modify code.
