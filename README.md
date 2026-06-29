# CenEMS Agent Testing

Pilot repository for testing GitHub Agentic Workflows with a human-approved AI
issue-to-PR loop.

## Pilot Flow

1. Open an issue with the `automation` label.
2. The issue planning workflow comments with an implementation plan and applies
   `agent-plan-ready`.
3. The Slack workflow posts the plan-ready issue to the configured webhook.
4. A human reviews the plan and applies `agent-approved`.
5. The implementation workflow creates a pull request using GitHub Agentic
   Workflows safe outputs.
6. The PR review workflow comments on the PR.
7. A maintainer can comment `/agent-fix` on the PR to let the agent update the
   PR branch based on review feedback.

## Local Checks

```bash
python -m unittest discover
```

## Demo App

The app exposes a tiny unit conversion library. The first pilot issue asks the
agent to add Fahrenheit support while preserving Celsius and Kelvin behavior.
