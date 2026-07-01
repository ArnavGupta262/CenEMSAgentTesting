# Approaches Evaluation — AI Agents in GitHub Workflows for CenEMS

**Status:** Pilot (this repo, `ArnavGupta262/CenEMSAgentTesting`)
**Audience:** CenEMS platform + application maintainers
**Goal:** An automated but human-gated loop where an AI agent triages issues,
proposes a plan, pings us on Slack for approval, opens a PR with a fix, gets an
automated code review, improves the PR from that review, and lands a final PR —
using **Claude** as the coding agent and **Codex** as the reviewer.

This document evaluates every approach we considered for each layer of the
system, with trade-offs, security posture, and cost, and states the choice. The
decisions themselves (and *why*) are logged in `decision-record.md`.

---

## The loop, decomposed into decisions

The system is not one choice but five independent ones:

| Layer | Question |
|------|----------|
| 1. Framework | What orchestrates the agents in GitHub Actions? |
| 2. Coding engine | Who writes the code? |
| 3. Review engine | Who reviews the PR? |
| 4. Topology | Where do the agents run relative to the product repo? |
| 5. Human gate + token model | How do humans approve, and what identity opens PRs? |

---

## Layer 1 — Orchestration framework

### A1. GitHub Agentic Workflows (`gh-aw`) — **CHOSEN**
Markdown workflow definitions compiled to hardened GitHub Actions `.lock.yml`.

**Pros**
- **Security model is built for this exact risk.** Every run executes behind an
  egress firewall (squid + api-proxy containers) with a domain allowlist;
  writes to GitHub happen only through **safe-outputs** run in separate,
  minimally-scoped jobs — the agent job itself is read-only. It has
  supply-chain guardrails (pinned action SHAs, a "new secret / new action needs
  approval" gate — which fired for us on `ANTHROPIC_API_KEY`), `protected-files`
  enforcement, sanitized inputs, and daily AI-credit caps.
- **Engine-agnostic.** Switching Copilot→Claude and Claude→Codex is a
  one-line `engine.id` change — the reason this pilot could pivot cheaply.
- Native primitives for our loop: `add-comment`, `add-labels`,
  `create-pull-request`, `push-to-pull-request-branch`,
  `submit-pull-request-review`, slash-command routing (`/agent-fix`), and
  reusable imports (our `shared/slack-notify.md`).
- Already the pilot's foundation; already the shape the org's
  `Central-EMS/automation-repo` is trending toward.

**Cons**
- Extra concept to learn; `.md` sources must be recompiled (`gh aw compile`) and
  the `.lock.yml` committed — drift files a "stale lock" issue (it did: pilot
  issue #11).
- It is a `githubnext` project — pin the version (`v0.80.9` here) and treat
  upgrades as reviewed changes.

### A2. GitHub Copilot coding agent via `assign-to-agent` — **REJECTED (current state)**
What the pilot does today: delegate implementation to Copilot's cloud agent.

**Why rejected:** it is fundamentally **not Claude** (Copilot's coding agent is
OpenAI/GitHub-controlled; you cannot point it at Claude), and the pilot's own
history is a graveyard of attempts to make it work — 11 issues across
`gpt-4o-mini`, `gpt-4`, `gpt-5`, and auto-model, **zero PRs produced**, plus
auto-filed "failed" issues. It also hides the actual code generation off-runner,
outside gh-aw's firewall and safe-output controls.

### A3. Anthropic `claude-code-action` (official) — **STRONG ALTERNATIVE**
Anthropic's first-party Action runs Claude Code in the runner, typically
triggered by `@claude` mentions; supports direct API key, Amazon Bedrock, and
Google Vertex auth, and can open PRs.

**Pros:** first-party, direct Claude control, Bedrock/Vertex options (relevant if
CenEMS wants to keep model traffic inside an existing cloud contract).
**Cons:** we would **lose gh-aw's safe-output sandbox, egress firewall,
slash-routing, and Slack import**, and would have to build the Codex review
step, the human-approval gate, and the guardrails ourselves. Best considered if
we later want Bedrock/Vertex hosting — see Integration Plan, "Model hosting."

### A4. Bespoke Actions calling the Anthropic API directly — **REJECTED**
Maximum control, maximum maintenance; reinvents every safety control gh-aw gives
us for free. Only justified if neither A1 nor A3 can meet a hard requirement.

---

## Layer 2 — Coding engine (who writes the code)

| Option | Auth | Verdict |
|--------|------|---------|
| **Claude engine (in-runner + `create-pull-request`)** | `ANTHROPIC_API_KEY` | **CHOSEN.** Matches the explicit "Claude over Copilot" requirement; Claude edits files and runs tests in the firewalled runner; gh-aw commits and opens the draft PR. Supports `max-turns` to bound cost/runaway. |
| Copilot cloud agent | `copilot-requests`/PAT | Rejected — see A2. |
| Codex engine as coder | `OPENAI_API_KEY` | Not chosen for coding; reserved for review. |

---

## Layer 3 — Review engine (who reviews the PR)

| Option | Auth | Verdict |
|--------|------|---------|
| **Codex engine** | `OPENAI_API_KEY` | **TARGET.** The stated requirement: an independent, different-vendor reviewer catches issues the author model is blind to. |
| **Claude engine** | `ANTHROPIC_API_KEY` | **PILOT-NOW.** You currently have only one key path and asked to "use Claude for now," so the review workflow ships on Claude and is a **one-line switch** to Codex once `OPENAI_API_KEY` exists (see `agent-review.md` and `decision-record.md` D7). |
| GitHub-native (CodeQL, branch protections, Copilot review) | — | **COMPLEMENTARY.** Keep CodeQL/required checks as a deterministic backstop; they are not a substitute for a reasoning reviewer, and vice-versa. |

> **Why a *different* vendor reviews the author (long-term):** an author model
> tends to be blind to its own mistakes in the same way twice. A Codex reviewer
> over a Claude author (or vice-versa) is a cheap independence gain. During the
> pilot, same-model review still adds value (fresh context, explicit rubric) but
> should be flagged as an interim compromise.

---

## Layer 4 — Topology (where the agents run)

### T1. Self-contained per-repo (the pilot's shape)
All workflows live in the repo they act on.
**Pros:** simplest; least cross-repo token surface; easy to reason about.
**Cons:** N copies to maintain across CenEMS's many services; per-repo secret
sprawl.

### T2. Hub-and-spoke — **RECOMMENDED for CenEMS**
Product repos (e.g. `Central-EMS/cenems`) **dispatch** issue events to a central
automation repo (`Central-EMS/automation-repo`) that runs the agents and opens
PRs back. **CenEMS already has both halves stubbed:**
`cenems/.github/workflows/trigger-issue-automation.yml` fires a
`repository_dispatch` to `Central-EMS/automation-repo` with
`config_path: .agents/codex-agent.yml`.

**Pros:** one place to maintain workflows, secrets, allowlists, and the model
budget; consistent guardrails across every service; central audit trail.
**Cons:** cross-repo auth (a GitHub App is strongly preferred over a PAT here);
one more moving part; the hub becomes a high-value target and must be locked
down accordingly.

### T3. Hybrid
Lightweight triage in each product repo; heavy implementation centralized. More
moving parts than the value returns for CenEMS today.

> The pilot is T1 for fast iteration. The integration plan promotes the *fixed,
> Claude+Codex* loop into T2, reusing the existing dispatch bridge — details in
> `cenems-integration-plan.md`.

---

## Layer 5 — Human gate + PR identity

### Human approval
- **H1. GitHub-label gate + Slack notification — CHOSEN.** The agent posts a
  plan and Slack pings us; a human authorizes by adding the `agent-approved`
  label (an authenticated, audited GitHub action). Slack is *notification*, not
  *authority* — so a Slack message cannot itself cause code to be written.
- **H2. Slack-interactive approval (buttons).** Nicer UX, but requires a
  public inbound webhook receiver, Slack request-signature verification, and a
  service to translate a click into a labeled GitHub action — new attack surface
  and new infra. Documented as a future enhancement, not pilot scope.

### PR identity / cascade token
The default `GITHUB_TOKEN` **cannot** trigger another workflow with the PRs it
opens (GitHub suppresses that cascade), so a PR opened with it would never fire
the review workflow. Options:

| Token | Cascade? | Verdict |
|-------|----------|---------|
| Default `GITHUB_TOKEN` | No | Fine for comment/label-only steps; breaks the implement→review handoff. |
| **Fine-grained PAT (`GH_AW_AGENT_TOKEN`)** | Yes | **PILOT.** Scope to this repo, minimal write, short expiry, revocable — matches your "testing key we can cancel." |
| **GitHub App installation token** | Yes | **PRODUCTION.** No user binding, least-privilege, rotatable, auditable — the right choice for `Central-EMS`. |

---

## Recommendation summary

| Layer | Pilot (now) | CenEMS production (target) |
|-------|-------------|----------------------------|
| Framework | gh-aw `v0.80.9` | gh-aw, pinned + upgrade-reviewed |
| Coding engine | **Claude** (in-runner PR) | **Claude** |
| Review engine | **Claude** (interim) → **Codex** one-line switch | **Codex** |
| Topology | Self-contained (T1) | **Hub-and-spoke (T2)** via existing dispatch |
| Human gate | Label gate + Slack notify | Same, optionally Slack-interactive later |
| PR token | Fine-grained PAT | **GitHub App** |

---

## Sources
- gh-aw docs: <https://github.github.com/gh-aw/> (engines, safe-outputs, tools).
- Anthropic Claude Code GitHub Action: <https://github.com/anthropics/claude-code-action> (verify latest usage before adopting A3).
- Existing CenEMS stubs: `cenems/.github/workflows/trigger-issue-automation.yml`, `cenems/.agents/codex-agent.yml`.
