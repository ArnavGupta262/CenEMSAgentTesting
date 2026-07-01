# CenEMS Migration Plan — Bringing the Claude Issue-to-PR Loop into Production

**Status:** Proposed — for CenEMS platform/application team review.
**Scope:** Migrate the validated pilot (`ArnavGupta262/CenEMSAgentTesting`) into
the `Central-EMS` organization as a production, human-gated, Claude-powered
issue → plan → approve → PR → review → fix loop.
**Companion docs (pilot repo `docs/`):** `approaches-evaluation.md` (why these
choices), `decision-record.md` (D1–D16, every decision), `secrets-and-setup.md`
(credential mechanics). This document is the **executable migration plan** and
supersedes the earlier high-level `cenems-integration-plan.md`.

---

## 0. What "all of this" is (the thing being migrated)

A gh-aw (GitHub Agentic Workflows) system of four agents, **proven end-to-end in
the pilot on Claude Haiku 4.5**:

| Agent | Trigger | Engine | Action (gh-aw safe-output) |
|-------|---------|--------|-----------------------------|
| **Planning** (`issue-triage`) | issue opened/reopened w/ `automation` | Claude | comments a plan, labels `agent-plan-ready`, Slack ping |
| **Implementation** (`agent-implement`) | label `agent-approved` | Claude | writes code + tests in-runner, opens **draft** PR (`create-pull-request`) |
| **Review** (`agent-review`) | PR opened/updated | Claude *(→ Codex)* | inline + summary review (`submit-pull-request-review`) |
| **Fix** (`agent-fix`) | `/agent-fix` comment | Claude | applies feedback, pushes to PR branch (`push-to-pull-request-branch`) |

**Validated in the pilot:** issue #15 → plan → `agent-approved` → draft PR #16
(+81/−0, only `src/**`+`tests/**`) → review → `/agent-fix` → tests green. Serving
model confirmed `claude-haiku-4-5-20251001` on all agent runs.

**Non-negotiable properties to preserve in production:** egress firewall,
read-only agent jobs with writes isolated in safe-output jobs, pinned action
SHAs, new-secret/new-action approval gate, `protected-files`, spend/turn caps,
label-based human approval (Slack is notification, not authority).

---

## 1. Current CenEMS state (what we build on / must reconcile)

| Artifact | Location | Notes |
|----------|----------|-------|
| Dispatch bridge | `cenems/.github/workflows/trigger-issue-automation.yml` | On `automation`-labeled issue, `repository_dispatch` → `Central-EMS/automation-repo` (`issue_to_review_requested`), auth `AUTOMATION_REPO_DISPATCH_TOKEN`, passes `config_path: .agents/codex-agent.yml` |
| Automation hub | `Central-EMS/automation-repo` (private) | Python framework: `prompts/ schemas/ templates/ scripts/ tests/ pyproject.toml`; default branch `main` |
| Policy config | `cenems/.agents/codex-agent.yml` | write allow `*`; **block** `.github/** infra/** auth/** secrets/**`; `payments/**` → human review; **validation = `npm` (WRONG: CenEMS is a Python monorepo)**; PR draft + labels `[automation, needs-review]`; review owners `team-platform`, `team-application` |
| Mandatory eng rules | `cenems/AGENTS.md` | NATS/event code MUST use `contracts_sdk` (Registry/Validator/Logger); events carry `contract_name`/`contract_version`; DLQ on terminal validation failure; tech-debt-issue policy; Alembic bulk-migration rules |
| Guardrail CI | `cenems/.github/workflows/agent-contracts-guardrails.yaml` | `scripts/contracts/lint_nats_contract_sdk_usage.py` + guardrail tests |
| Delivery CI | `build-and-deploy.yaml`, `helm-validation.yaml`, `alembic-*`, `test-unit/integration/e2e`, `promote-image.yaml` | GitOps: build-once on `dev` → promote same SHA to `staging`/`main`; ArgoCD deploy; Python 3.11/3.12 |

**Key facts:** org `Central-EMS`; product default branch **`dev`** (not `main`);
build-once-promote release model; contracts-as-source-of-truth culture.

---

## 2. Gap analysis — pilot (personal) → CenEMS (org)

Every difference that must be closed before go-live:

| # | Dimension | Pilot today | CenEMS target | Action |
|---|-----------|-------------|---------------|--------|
| G1 | Repo/owner | `ArnavGupta262/CenEMSAgentTesting` | `Central-EMS/*` | Re-home workflows; set `target-repo`/`allowed-repos` |
| G2 | Base branch | `main` | **`dev`** | Set PR base to `dev` (D10) |
| G3 | Identity/auth | fine-grained PAT (`GH_AW_AGENT_TOKEN`) | **GitHub App** installation token | Create + install App; replace PAT |
| G4 | Topology | self-contained, issue-triggered | in-repo first → **hub-and-spoke** | See §4 |
| G5 | Model | Haiku (tier-limited key) | Haiku triage + **Sonnet** implement/review on an org-tier account | §6 |
| G6 | Review engine | Claude (interim) | **Codex** (`engine.id: codex` + `OPENAI_API_KEY`) | D3/D7 |
| G7 | Policy validation | demo `python -m unittest` | real CenEMS checks (pytest, contracts lint, helm, alembic) | Fix `codex-agent.yml` (§7) |
| G8 | Eng-standards awareness | none needed (toy app) | agent MUST honor `contracts_sdk`/AGENTS.md | Feed `AGENTS.md` to agents; reviewer checks compliance (§8) |
| G9 | Secrets | repo-level, personal | **org-level** secrets/vars + environments | §5 |
| G10 | Approvers | repo owner | `team-platform`/`team-application` w/ write | §9 |
| G11 | Guardrails | instruction + `min-integrity` default | + **`protected-files`** hard block matching `blocked_paths` | §8 |
| G12 | Scope | any `automation` issue | eligible labels/paths only; **`payments/**` excluded** | §10 |
| G13 | Observability/cost | gh-aw daily credit cap | org budget, dashboards, alerting, quotas | §11 |
| G14 | Rollback | delete key | documented kill-switch runbook | §12 |

---

## 3. Recommended sequencing (de-risked)

Two viable topologies (full analysis in `approaches-evaluation.md` §Layer 4).
Recommendation: **earn trust in-repo, then centralize.**

- **Phase A — in-repo (T1):** run the four gh-aw workflows *inside* `cenems`,
  issue-triggered, exactly like the proven pilot. Fastest path to production
  value; smallest change from the validated design; no cross-repo auth yet.
- **Phase B — hub-and-spoke (T2):** consolidate workflows into
  `Central-EMS/automation-repo`; product repos only keep the thin
  `trigger-issue-automation.yml` dispatch + `.agents` policy. Best at CenEMS's
  service count; one place for secrets, budget, allowlists, audit.

This lets us validate on real CenEMS issues without first solving cross-repo
dispatch + cross-repo PR creation, then evolve to the hub the org already
stubbed.

---

## 4. Target architecture

### 4.1 Phase A (in-repo)
Copy the four `.md` workflows + `shared/slack-notify.md` into
`cenems/.github/workflows/`, recompile locks, and change only what G1/G2 require:
- triggers stay `on: issues` / `on: pull_request` / `slash_command`;
- `create-pull-request`/`push-to-pull-request-branch` base = `dev`;
- `github-token` = GitHub App token (§ G3).
Temporarily disable or narrow `trigger-issue-automation.yml` so an issue isn't
*both* dispatched to the hub and handled in-repo (avoid double-processing).

### 4.2 Phase B (hub-and-spoke)
```
 cenems (spoke)                       Central-EMS/automation-repo (hub)
 ─ issue labeled 'automation'         ─ on: repository_dispatch
   → trigger-issue-automation.yml       [issue_to_review_requested]
     → repository_dispatch ───────────►  read client_payload (issue #, title, body, repo)
                                         triage(Claude) → plan/label/slack (cross-repo)
                                         implement(Claude) → create-pull-request
                                           target-repo: <spoke>, base: dev
                                         review(Codex) on the spoke PR
                                         fix(Claude) → push-to-pull-request-branch
 human approves label / merges  ◄──────  (writes via GitHub App token, both repos)
```
Porting deltas for the hub (vs pilot):
- **Triggers:** `on: issues`→`on: repository_dispatch: types:[issue_to_review_requested]`;
  read issue via `client_payload` instead of `github.event.issue`.
- **Safe-outputs cross-repo:** set `target-repo` (+ `allowed-repos`) on
  `add-comment`, `add-labels`, `create-pull-request`, `submit-pull-request-review`,
  `push-to-pull-request-branch`.
- **Approval loop:** `agent-approved` label + `/agent-fix` live on the *spoke*
  PR/issue; the hub must watch those (either spoke re-dispatches on label, or the
  hub polls — prefer spoke re-dispatch for the same auth model).

---

## 5. Identity, secrets & config

### 5.1 GitHub App (replaces all PATs) — do this first
Create `CenEMS Automation Agent` (org-owned):
- **Repository permissions (least privilege):** Contents RW, Pull requests RW,
  Issues RW, Metadata R. (Add Actions R only if cache write is desired.)
- **No** org-admin, no members, no secrets permissions.
- Install on **only** the repos in scope (start: a scratch repo, then `cenems`).
- Store `APP_ID` + `APP_PRIVATE_KEY` as org/hub secrets; mint installation
  tokens at runtime (e.g. `actions/create-github-app-token`) and pass as the
  `github-token` on safe-outputs.
Why: no user binding (kills the ToastyPencil-class attribution problem
permanently), short-lived tokens, scoped, rotatable, auditable — the correct
production identity (D6).

### 5.2 Secret inventory
| Secret | Level | Purpose | Rotation |
|--------|-------|---------|----------|
| `ANTHROPIC_API_KEY` | org/hub | Claude engine | dedicated workspace, spend cap, rotate quarterly |
| `OPENAI_API_KEY` | org/hub | Codex review | project-scoped, budget cap |
| `APP_ID`, `APP_PRIVATE_KEY` | org/hub | App auth | rotate private key on schedule |
| `SLACK_WEBHOOK_URL` | org/hub | review channel | dedicated `#cenems-agent` channel |
| `AUTOMATION_REPO_DISPATCH_TOKEN` | spoke | dispatch → hub (Phase B) | migrate to App if possible |

All are GitHub Actions secrets referenced by name — **never committed** (extend
the existing `helm-validation` "hardcoded secrets" scanning discipline).

---

## 6. Model & cost strategy

**Lesson from the pilot (D14):** gh-aw's Claude default is **Opus**, which 429'd
on a new key's 10k input-tokens/min limit; a single agentic request (system
prompt + ~30 tool schemas) exceeds 10k tokens, so it can never start under that
cap. Pinning `claude-haiku-4-5-20251001` fixed it and served every run.

Production plan:
- **Account tier:** ensure the org Anthropic (and OpenAI) accounts are on a tier
  whose input-tokens/min comfortably exceeds a single request (target ≥ 30k ITPM;
  budget for growth). This is a prerequisite, not optional (open decision #5 in
  the integration plan is now concrete).
- **Model per agent:** triage → **Haiku** (cheap, light); implement/fix →
  **Sonnet** (code quality); review → **Codex** (independent vendor). Pin exact
  dated model ids to defeat proxy steering.
- **Cost envelope (order-of-magnitude):** a full Haiku loop was pennies; Sonnet
  implementation runs are ~cents–low-dollars each. Set a monthly budget +
  per-workflow `max-turns`/`timeout-minutes` + gh-aw daily AI-credit cap; alert
  at 70% of budget.
- **Alternative hosting:** Amazon Bedrock / Google Vertex for Claude (approach
  A3) removes per-account Anthropic tier ceilings and keeps model traffic inside
  an existing cloud contract — evaluate for compliance/data-residency.

---

## 7. Reconciling `.agents/codex-agent.yml` (tracked tech debt)
Open the `[Medium][Automation]` tech-debt issue (per AGENTS.md policy) and:
- **Fix validation commands** (currently `npm run lint/test/build`) → real CenEMS
  checks, e.g.:
  - `python -m pytest`
  - `python scripts/contracts/lint_nats_contract_sdk_usage.py --apps-path apps`
  - relevant `helm lint`/`helm template` and alembic round-trip where the change
    touches those areas.
- **Encode author≠reviewer:** implementation = Claude, review = Codex.
- **Base branch** → `dev`. **Keep** `blocked_paths` and `payments/** → human`.
- Wire `blocked_paths` into gh-aw **`protected-files`** so it's a hard block, not
  just advisory.

---

## 8. Security & CenEMS-standards compliance
- **Egress:** keep gh-aw firewall; the allowlist already permits
  `api.anthropic.com`; add the OpenAI endpoint when Codex is enabled.
- **Write isolation & least privilege:** agent jobs read-only; writes via
  safe-output jobs using the App token scoped to the target repo only.
- **Hard path guards:** `protected-files` = `.github/** infra/** auth/**
  secrets/**` with fallback-to-issue; `payments/**` requires human review.
- **Prompt-injection containment:** treat issue/PR text as untrusted; never
  expand `${{ github.event.* }}` into a shell; rely on gh-aw input sanitization.
- **Contracts culture:** feed `cenems/AGENTS.md` into every agent's context so
  generated NATS/event code uses `contracts_sdk` (Registry/Validator/Logger,
  `contract_name`/`contract_version`, DLQ). The **reviewer's rubric must include
  contracts-SDK compliance and the Alembic bulk-migration rules**, and agent PRs
  must pass `agent-contracts-guardrails.yaml`.
- **Auditability:** every step is a GitHub event (label/comment/PR/review) with
  identity + timestamp; the hub centralizes run logs.

---

## 9. CI/CD & human-in-the-loop integration
- Agent PRs are ordinary PRs → **all existing checks apply** and are the
  deterministic backstop to the AI review: `test-unit`, `test-integration`,
  `test-e2e`, `agent-contracts-guardrails`, `helm-validation`, alembic round-trip.
- **Branch protection on `dev`:** require the above checks + **≥1 CODEOWNER
  review** before merge; disallow the agent from marking its own PR ready.
- **Approval gate:** `agent-approved` label applied by `team-platform`/
  `team-application`; Slack pings a dedicated `#cenems-agent` channel (notification
  only). Optional later: Slack-interactive approval (needs a signed inbound
  receiver — new attack surface, deferred).
- **Label/CODEOWNERS:** add `agent-generated`, `agent-plan-ready`,
  `agent-approved`, `needs-human-triage`; map guarded paths to CODEOWNERS.

---

## 10. Rollout scope & guardrails
- **Eligible work:** only issues labeled `automation` **and** matching an allowed
  path set (start narrow: docs, tests, small library changes). **Never**
  `payments/**`, `infra/**`, `auth/**`, `secrets/**`, `.github/**`.
- **Repos:** scratch repo → `cenems` (dev only) → widen to other services via the
  hub once stable.
- **Volume caps:** concurrency limits + daily run/credit caps; start with a low
  ceiling and raise on evidence.

---

## 11. Observability, cost & quotas
- Dashboard: runs/day, success rate, human-approval rate, merge rate, time-to-PR,
  spend/day per model, rate-limit incidents.
- Alerts: budget ≥70%, error-rate spike, any `protected-files` violation, any
  auth failure.
- Weekly gh-aw activity report (built-in) filed as an issue for review.

---

## 12. Rollback & kill-switch runbook
1. **Pause:** disable the hub/product workflows (`gh aw disable` or Actions UI).
2. **Revoke model access:** disable the Anthropic/OpenAI keys (agents can't call
   models).
3. **Revoke write:** suspend/uninstall the GitHub App (agents can't write).
4. **Contain a bad PR:** it's a draft behind required checks + CODEOWNER review —
   close it; `protected-files` already blocks sensitive paths.
5. **Recover:** all changes are PRs; nothing merges without human review.

---

## 13. Risks & mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Rate-limit/tier too low | Med | Runs fail to start | Provision org tier ≥30k ITPM; pin models (§6) |
| Prompt injection via issue text | Med | Unwanted changes | Read-only agents, safe-outputs, `protected-files`, sanitization |
| Agent violates contracts_sdk rules | Med | Failing/unsafe NATS code | Feed AGENTS.md; reviewer rubric; guardrail CI blocks merge |
| Cross-repo token sprawl (Phase B) | Med | Broad blast radius | GitHub App, per-repo install, least privilege |
| Cost overrun | Low/Med | $$ | Budgets, caps, alerts, Haiku for cheap stages |
| Lockfile drift | Low | Runs blocked | CI check: `gh aw compile` must produce no diff (D11) |
| Author misattribution | Low | Provenance | App identity (no user binding) — fixes the ToastyPencil class of issue |

---

## 14. Phased execution checklist (with entry/exit)

**Phase 0 — Prereqs**
- [ ] Anthropic org account/workspace at target tier (≥30k ITPM) + spend cap
- [ ] OpenAI project for Codex + budget
- [ ] GitHub App created, permissions set, installed on a scratch repo
- [ ] `#cenems-agent` Slack channel + webhook
- *Exit:* secrets set at org level; App mints tokens in a test workflow

**Phase A — in-repo pilot on a scratch repo, then `cenems`**
- [ ] Port 4 workflows + `shared/slack-notify.md`; base=`dev`; App token; pin models
- [ ] `gh aw compile`; commit locks; add drift-check CI
- [ ] Narrow/disable `trigger-issue-automation.yml` to avoid double-processing
- [ ] Run the demo issue end-to-end; confirm required checks gate the PR
- *Exit:* a real `cenems` `automation` issue → reviewed draft PR on `dev`, all checks green, CODEOWNER approval required

**Phase B — hub-and-spoke**
- [ ] Move workflows to `automation-repo`; convert triggers to `repository_dispatch`
- [ ] Cross-repo `target-repo`/`allowed-repos`; App installed on hub + spokes
- [ ] Fix `.agents/codex-agent.yml` (§7); wire `protected-files`
- [ ] Switch review to **Codex**; feed `AGENTS.md` context
- *Exit:* hub opens a Codex-reviewed PR back to a spoke; kill-switch tested

**Phase C — harden & widen**
- [ ] Dashboards, budgets, alerts, weekly activity report
- [ ] Onboard additional service repos via thin dispatch + policy
- *Exit:* documented SLOs, maintainer rota, runbook signed off

---

## 15. Open decisions for the team
1. **Topology:** in-repo-then-hub (recommended) vs hub-first.
2. **Model hosting:** direct Anthropic/OpenAI vs Bedrock/Vertex (residency/spend).
3. **Eligibility:** which labels/paths are agent-eligible; confirm `payments/**`
   never is.
4. **Approver group** for the `agent-approved` gate.
5. **Budget ceiling** and alert thresholds.
6. **Review vendor at GA:** Codex (recommended) vs staying on Claude.

---

## 16. Appendix — pilot → CenEMS frontmatter deltas (quick reference)
```yaml
# implement / fix
safe-outputs:
  create-pull-request:            # (or push-to-pull-request-branch)
    draft: true
    base: dev                     # was: main (G2)
    target-repo: Central-EMS/cenems   # Phase B only (G1/G4)
    labels: [agent-generated, automation, needs-review]
    github-token: ${{ steps.app-token.outputs.token }}   # GitHub App (G3)
engine:
  id: claude
  model: claude-sonnet-4-5-…      # implement/fix (G5); triage stays Haiku
# review
engine:
  id: codex                       # was: claude (G6); needs OPENAI_API_KEY
```
