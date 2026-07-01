# CenEMS Agent Testing

Pilot repository for testing GitHub Agentic Workflows (gh-aw) with a
human-approved, **Claude-powered** issue-to-PR loop.

## Pilot Flow

1. Open an issue with the `automation` label.
2. **Planning** (`issue-triage`, Claude): comments an implementation plan and
   applies `agent-plan-ready`, then posts the plan to Slack for review.
3. A human reviews the plan and applies the `agent-approved` label to authorize
   the change.
4. **Implementation** (`agent-implement`, Claude): writes the code and tests
   *in the Actions runner*, runs the test suite, and opens a **draft** pull
   request (`create-pull-request`). No work is delegated to any cloud agent.
5. **Review** (`agent-review`): reviews the PR and posts inline + summary
   feedback. Runs on Claude for the pilot; a one-line change switches it to
   Codex (see `docs/decision-record.md`, D7).
6. A maintainer comments `/agent-fix` to let the implementation agent address
   the review feedback.
7. **Fix** (`agent-fix`, Claude): edits the code and pushes to the PR branch
   (`push-to-pull-request-branch`), which re-triggers review.
8. A human does the final review and merges.

## Documentation

- `docs/approaches-evaluation.md` — every integration approach considered, with
  trade-offs and the recommendation.
- `docs/decision-record.md` — an ADR-style log of every decision and its
  justification.
- `docs/cenems-integration-plan.md` — the full plan to roll this into CenEMS.
- `docs/secrets-and-setup.md` — exactly which keys/tokens/secrets are needed and
  how to create them safely.

## Secrets

This pilot needs `ANTHROPIC_API_KEY` (Claude), `GH_AW_AGENT_TOKEN` (a scoped
token so agent PRs trigger review), and `SLACK_WEBHOOK_URL`. Adding
`OPENAI_API_KEY` enables the Codex review path. **Never commit secrets.** See
`docs/secrets-and-setup.md`.

## Local Checks

```bash
python -m unittest discover
```

After editing any `.github/workflows/*.md`, recompile the generated workflows:

```bash
gh aw compile
```

## Demo App

The app exposes a tiny unit conversion library. The first pilot issue asks the
agent to add Fahrenheit support while preserving Celsius and Kelvin behavior.
