# CenEMS Integration Plan — Claude+Codex Issue-to-PR Automation

**Goal:** Promote the fixed pilot (this repo) into `Central-EMS` as a
production-grade, human-gated loop: triage → Slack approval → **Claude** opens a
PR → **Codex** reviews → Claude improves from the review → human merges — with
CenEMS's security bar (no secret leakage, least privilege, full audit).

This plan is written for review; **nothing here has been applied to any
`Central-EMS` repo** (this session was scoped to the pilot, per D15). Treat it as
the spec/ADR to attach to the integration PR.

---

## 1. What already exists in CenEMS (don't rebuild it)

CenEMS has **both halves of a hub-and-spoke design already stubbed** — the plan
is to converge on it, not invent something new:

- `cenems/.github/workflows/trigger-issue-automation.yml` — on an `automation`-
  labeled issue, sends a `repository_dispatch` (`issue_to_review_requested`) to
  **`Central-EMS/automation-repo`**, passing issue fields +
  `config_path: .agents/codex-agent.yml`, authenticated by
  `secrets.AUTOMATION_REPO_DISPATCH_TOKEN`.
- `cenems/.agents/codex-agent.yml` — a policy config: trigger labels/phrases,
  `write_policy` (allowed `*`; **blocked** `.github/**`, `infra/**`, `auth/**`,
  `secrets/**`; `requires_human_review` `payments/**`), validation commands,
  draft-PR + label defaults, and review owners (`team-platform`,
  `team-application`).
- **`Central-EMS/automation-repo`** — a real private repo with
  `prompts/`, `schemas/`, `templates/`, `scripts/`, `tests/`, `pyproject.toml`.

**Two gaps this plan closes:**
1. The stubbed hub is Codex-oriented (`codex-agent.yml`) but the requirement is
   **Claude authors, Codex reviews**. We reconcile the config to that split.
2. `codex-agent.yml`'s `validation.{lint,test,build}` are `npm` commands — wrong
   for a Python monorepo. Must become the real CenEMS checks (see §6).

---

## 2. Target architecture

```
                 ┌─────────────────────────────────────────────┐
  issue labeled  │  Central-EMS/cenems (spoke)                  │
  'automation'   │  trigger-issue-automation.yml                │
        ─────────┼──►  repository_dispatch ──────────┐          │
                 └───────────────────────────────────┼──────────┘
                                                      ▼
                 ┌─────────────────────────────────────────────┐
                 │  Central-EMS/automation-repo (hub)           │
                 │  gh-aw workflows (pinned):                   │
                 │   • triage   (Claude)  → plan + Slack + label │
                 │   • implement(Claude)  → draft PR back to spoke
                 │   • review   (Codex)   → inline + summary     │
                 │   • fix      (Claude)  → push to PR branch    │
                 │  Auth: GitHub App installation token          │
                 │  Guardrails: egress firewall, safe-outputs,   │
                 │   protected-files, per-repo allowlist         │
                 └─────────────────────────────────────────────┘
                                                      │ PR + reviews
                                                      ▼
                 human approves label / merges in the spoke repo
```

Key point: the **spoke** repos stay thin (one dispatch workflow + one
`.agents` policy file). All agent logic, secrets, and model budget live in the
**hub**, so onboarding a new service is "add the dispatch workflow + policy," not
"copy four workflows and four secrets."

> Alternative if you prefer no hub: run the four gh-aw workflows directly in each
> product repo (topology T1). Simpler per-repo, but N× the secret and
> maintenance surface. The hub is recommended at CenEMS's service count — see
> `approaches-evaluation.md` §Layer 4.

---

## 3. Security model (the non-negotiable part)

| Control | How |
|--------|-----|
| **No secrets in code** | All creds are org/repo Actions secrets referenced by name. Helm `hardcoded secrets` scan pattern already exists in CenEMS CI — extend the same discipline. |
| **Least-privilege identity** | Replace the dispatch PAT and pilot PAT with a **GitHub App** installed on the org, scoped to the specific repos, with only `contents`, `pull_requests`, `issues` (write) + `metadata` (read). Installation tokens are short-lived and auto-rotated. |
| **Egress control** | gh-aw runs every agent behind the squid/api-proxy firewall with a domain allowlist (already includes `api.anthropic.com`; add the OpenAI endpoint when Codex is enabled). No arbitrary network from agent runs. |
| **Write isolation** | Agent jobs are read-only; all GitHub writes go through safe-output jobs with minimal scopes. |
| **Hard path guards** | Enforce `.agents/codex-agent.yml` `blocked_paths` via gh-aw `protected-files` (fallback-to-issue on violation), not just prompt instructions. `payments/**` → `requires_human_review`. |
| **Prompt-injection containment** | Issue/PR text is untrusted input. gh-aw sanitizes inputs; keep the agent read-only + safe-outputs so a malicious issue can't escalate to writing CI or secrets. Never expand `${{ github.event.issue.body }}` into a shell. |
| **Spend + runaway caps** | `max-turns`, `timeout-minutes`, gh-aw daily AI-credit cap; per-workspace spend limit on the API keys. |
| **Auditability** | Every action is a GitHub event (label, comment, PR, review) with identity + timestamp; the hub centralizes run logs. |
| **Kill switch** | Disable the hub's workflows (or `gh aw disable`) and/or revoke the GitHub App installation to stop everything immediately. Document this runbook. |

---

## 4. Secrets required in CenEMS (org or hub-repo level)

See `secrets-and-setup.md` for step-by-step creation. Summary:

| Secret | Where | Purpose |
|--------|-------|---------|
| `ANTHROPIC_API_KEY` | hub repo / org | Claude engine (triage, implement, fix) |
| `OPENAI_API_KEY` | hub repo / org | Codex engine (review) |
| GitHub App creds (`APP_ID`, `APP_PRIVATE_KEY`) | hub repo / org | Cross-repo PR/label/comment identity (replaces PATs) |
| `SLACK_WEBHOOK_URL` | hub repo / org | Review-channel notifications (dedicated channel) |
| `AUTOMATION_REPO_DISPATCH_TOKEN` | each spoke | Already used; migrate to the GitHub App if possible |

---

## 5. Phased rollout

**Phase 0 — Pilot sign-off (this repo).** Validate the Claude loop end-to-end on
one Anthropic key (see `secrets-and-setup.md`). Confirm plan→approve→PR→review→
`/agent-fix`→merge works and Slack pings land. *Exit:* a green run on the
Fahrenheit demo.

**Phase 1 — Stand up the hub with Claude+Codex.** In `Central-EMS/automation-repo`
add the four gh-aw workflows (ported from this repo), the GitHub App auth, and
`OPENAI_API_KEY` so review runs on Codex from day one. Keep it pointed at a
single non-critical CenEMS repo or a scratch repo. *Exit:* hub opens a PR back to
a spoke and Codex reviews it.

**Phase 2 — Wire one real spoke.** Point `cenems`'s existing
`trigger-issue-automation.yml` at the hub's new event, reconcile
`.agents/codex-agent.yml` (§6), set base branch `dev` (D10), restrict to a label
like `automation` + maybe a path allowlist. Run on low-risk issues only. *Exit:*
a real `cenems` issue produces a reviewed draft PR against `dev`.

**Phase 3 — Harden + widen.** Add `protected-files`, CODEOWNERS-based required
review on agent PRs, lockfile-drift CI (D11), dashboards for run
volume/spend/merge-rate, and the kill-switch runbook. Then onboard more spokes by
adding the thin dispatch + policy files. *Exit:* documented SLOs and a
maintainer rota.

**Phase 4 (optional) — Slack-interactive approval (H2)** and **Bedrock/Vertex
model hosting (A3)** if CenEMS wants model traffic inside an existing cloud
contract.

---

## 6. Reconciling `.agents/codex-agent.yml`

Changes needed when integrating (track as the `[Medium][Automation]` tech-debt
item from `decision-record.md`):

- **Validation commands** → real CenEMS checks, e.g.
  `python -m pytest`, the contracts lint
  (`python scripts/contracts/lint_nats_contract_sdk_usage.py --apps-path apps`),
  and Helm/alembic validation where relevant — **not** `npm run {lint,test,build}`.
- **Author vs reviewer** → make explicit that implementation is Claude and review
  is Codex; the file currently reads as a single Codex agent.
- **Blocked paths** → confirm `.github/**`, `infra/**`, `auth/**`, `secrets/**`
  are enforced by gh-aw `protected-files`, and keep `payments/**` as
  human-review-required.
- **Base branch** → `dev`.
- **CenEMS AGENTS.md** → the hub agents must honor the repo's mandatory NATS/
  contracts rules; feed the spoke's `AGENTS.md` into the agent context so
  generated code follows `contracts_sdk` guardrails and the tech-debt policy.

---

## 7. Interaction with existing CenEMS CI

Agent PRs are normal PRs, so existing checks apply and act as a deterministic
backstop to the Codex review: `test-unit`, `test-integration`, `test-e2e`,
`agent-contracts-guardrails`, `helm-validation`, alembic round-trip. Recommended:
require these + at least one CODEOWNER review before an agent PR can merge, and
never let the agent mark its own PR ready-for-review.

---

## 8. Open decisions for the team

1. **Model hosting:** direct Anthropic/OpenAI APIs vs Bedrock/Vertex (data
   residency, existing cloud spend commitments)?
2. **Hub vs per-repo** final call (this plan recommends hub).
3. **Scope of automation:** which issue types/labels/paths are eligible; is
   `payments/**` ever agent-eligible (recommend never)?
4. **Approver group** for the `agent-approved` gate (map to `team-platform` /
   `team-application`).
5. **Budget ceiling** per day/week and alerting threshold.
