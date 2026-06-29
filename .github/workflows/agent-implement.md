---
description: |
  Assigns an approved automation issue to the GitHub Copilot cloud agent so it
  can implement the task and open a pull request.

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
  model: gpt-4o-mini
network: defaults

tools:
  github:
    toolsets: [issues, repos]
    min-integrity: none

safe-outputs:
  assign-to-agent:
    name: "copilot"
    allowed: [copilot]
    max: 1
    target: "triggering"
    target-repo: "ArnavGupta262/CenEMSAgentTesting"
    pull-request-repo: "ArnavGupta262/CenEMSAgentTesting"
    base-branch: "main"
    custom-instructions: |
      Implement the approved issue in this repository. Follow AGENTS.md.
      Limit code changes to src/** and tests/**. Add or update tests, run
      python -m unittest discover, and open a pull request when complete.
      Keep the change small and include the issue link and test result in the
      pull request body.
    github-token: ${{ secrets.GH_AW_AGENT_TOKEN }}
  add-comment:
    max: 1
    footer: false

imports:
  - shared/slack-notify.md

timeout-minutes: 12
---

# CenEMS Copilot Assignment Agent

You are the assignment agent for approved issue
#${{ github.event.issue.number }}.

## Guardrails

- Only act after the `agent-approved` label is present.
- Read the issue and the `<!-- agent-plan -->` comment.
- Do not modify repository files yourself.
- Use `assign-to-agent` to assign the triggering issue to the `copilot` agent.
- Use `add-comment` to tell maintainers that Copilot cloud agent was assigned,
  or explain why assignment was unsafe.
- Call `slack-notify` with a short message including the issue URL.

## Steps

1. Read issue #${{ github.event.issue.number }}, its labels, and comments.
2. Confirm the issue still has `automation`, `agent-plan-ready`, and
   `agent-approved`.
3. If the issue is approved and suitable, use `assign-to-agent` for the
   triggering issue.
4. Use `add-comment` with a concise status update.
5. Call `slack-notify` saying the approved issue was delegated to Copilot cloud
   agent.
