# Decision Record — CenEMS AI Agent Workflow Pilot

ADR-style log of **every** decision made while fixing this pilot and designing
the CenEMS integration, with the reasoning behind each. Format per decision:
Context → Decision → Why → Consequences / alternatives considered.

Legend: **Status** ∈ {Adopted (pilot), Proposed (CenEMS), Interim}.

---

### D1 — Build on gh-aw rather than a bespoke Action or `claude-code-action`
**Status:** Adopted (pilot)
**Context:** The pilot already used gh-aw; we needed to switch it to Claude/Codex.
**Decision:** Keep gh-aw as the orchestration framework.
**Why:** gh-aw gives us, for free, the exact controls a code-writing agent needs:
an egress firewall, read-only agent jobs with writes isolated into
minimally-scoped **safe-output** jobs, pinned action SHAs, a new-secret/new-action
approval gate, `protected-files`, input sanitization, and daily AI-credit caps.
Rebuilding those in a bespoke Action (A4) or bolting them onto
`claude-code-action` (A3) would be strictly more work and more risk. Switching
engines is a one-line change, which is precisely why the pivot was cheap.
**Consequences:** We accept a compile step (`gh aw compile`) and version pinning.
Alternatives in `approaches-evaluation.md` (A3 remains the fallback if CenEMS
mandates Bedrock/Vertex model hosting).

### D2 — Claude writes code in-runner via `create-pull-request` (drop `assign-to-agent: copilot`)
**Status:** Adopted (pilot)
**Context:** "Use Claude over Copilot." The old `agent-implement`/`agent-fix`
delegated implementation to Copilot's cloud agent, which never produced a PR.
**Decision:** Set `engine.id: claude`, enable the `edit` + restricted `bash`
tools, and emit `create-pull-request` (implement) / `push-to-pull-request-branch`
(fix). Claude edits files and runs tests inside the firewalled runner; gh-aw
commits and opens/updates the PR.
**Why:** It is the only way to make Claude — not Copilot — the author, and it
keeps code generation *inside* gh-aw's sandbox instead of an opaque off-runner
service. In-runner also lets the agent run `python -m unittest discover` before
proposing the PR.
**Consequences:** The agent needs repo checkout + `edit`/`bash`; we bound it with
`max-turns: 30` and `timeout-minutes`. Writes are constrained to `src/**` and
`tests/**` by instruction (D12).

### D3 — Two-vendor design: Claude authors, Codex reviews (target)
**Status:** Proposed (CenEMS) / Interim on Claude (pilot)
**Context:** Requirement: "automatic code review via Codex," improving the PR
from that feedback.
**Decision:** The review workflow is engine-swappable; the **target** is
`engine.id: codex`.
**Why:** An independent, different-vendor reviewer catches classes of error the
author model is systematically blind to. Same-vendor review still helps (fresh
context, explicit rubric) but is a weaker check.
**Consequences:** Requires `OPENAI_API_KEY`. See D7 for the pilot interim.

### D4 — Human approval is a GitHub **label gate**; Slack is notification-only
**Status:** Adopted (pilot)
**Context:** "Ping us on Slack; we decide yes/no; if yes the agent PRs."
**Decision:** The planning agent applies `agent-plan-ready` and pings Slack; a
human authorizes by adding the `agent-approved` label, which triggers
implementation. Approval authority lives in GitHub, not Slack.
**Why:** A Slack message is not an authenticated, audited action; a GitHub label
change is (identity, timestamp, permission-checked). This prevents "a Slack
click causes code to be written" from being the security boundary. Slack-button
approval (H2) would need a public inbound receiver + signature verification —
new attack surface, deferred.
**Consequences:** Approvers must have write access to labels. Slack outages never
block or bypass the gate.

### D5 — Centralize Slack in the agent-driven import; delete `slack-human-events.yml`
**Status:** Adopted (pilot)
**Context:** Slack was sent from *two* places: the gh-aw `shared/slack-notify.md`
import (agent-driven) and a separate plain-Actions `slack-human-events.yml`
(event-driven), risking double-posts and drift.
**Decision:** Keep the single `shared/slack-notify.md` import, used by triage
(plan-ready), implement (PR opened), and fix (fix pushed). Remove the standalone
workflow.
**Why:** One source of truth; contextual messages (the agent can summarize
suitability / link the PR); fewer places referencing `SLACK_WEBHOOK_URL`.
**Consequences:** If an agent run fails before emitting Slack, there is no ping —
acceptable because the interesting state changes are produced by the agents
themselves. A deterministic backstop can be re-added later if desired.

### D6 — Fine-grained PAT for PR cascade in the pilot; GitHub App for production
**Status:** Adopted (pilot) / Proposed (CenEMS)
**Context:** The default `GITHUB_TOKEN` cannot trigger the review workflow from a
PR it opens.
**Decision:** Pilot uses `GH_AW_AGENT_TOKEN` (a fine-grained PAT) on
`create-pull-request` and `push-to-pull-request-branch`. Production uses a GitHub
App installation token.
**Why:** A PAT is the fastest revocable "testing" credential and makes the
implement→review→fix cascade work. A GitHub App is the correct production
identity: no user binding, least-privilege, rotatable, auditable — essential for
a shared org hub.
**Consequences:** The PAT must be scoped to this repo with contents/PR/issues
write and a short expiry. See `secrets-and-setup.md`.

### D7 — `agent-review` ships on Claude now, one-line switch to Codex
**Status:** Interim (pilot)
**Context:** You have no keys yet and asked to "use Claude for now"; a full live
test needs the review step to run on a key you actually have.
**Decision:** `agent-review.md` uses `engine.id: claude` today. Switching to
Codex is: change `claude`→`codex`, add `OPENAI_API_KEY`, recompile.
**Why:** Lets the entire loop be validated end-to-end on a single Anthropic key,
without blocking on OpenAI procurement, while keeping the Codex target explicit
and cheap to reach.
**Consequences:** Interim same-vendor review; tracked to be flipped to Codex.
This is a deliberate, temporary compromise — see "Tech debt" below.

### D8 — Remove `min-integrity: none` from the github tool
**Status:** Adopted (pilot)
**Context:** Every workflow set `min-integrity: none` (the most permissive tool
filter).
**Decision:** Remove the override and use gh-aw's default.
**Why:** Security-first: don't opt out of a safety filter without a reason. The
agents only need to read issues/PRs/repo contents; the default tier is
sufficient. If a needed tool turns out to be filtered, we add it back
explicitly and document why.
**Consequences:** None observed; all four workflows compiled cleanly.

### D9 — Bound cost/runaway with `max-turns` + `timeout-minutes` + gh-aw credit cap
**Status:** Adopted (pilot)
**Decision:** `max-turns: 30` on implement/fix, existing `timeout-minutes`, and
rely on gh-aw's `GH_AW_MAX_DAILY_AI_CREDITS` (default 5000) guardrail.
**Why:** An agent that writes code and runs tests can loop; these caps bound the
blast radius on both time and spend, which pairs with the revocable testing key.

### D10 — Pilot base branch stays `main`; CenEMS is `dev`
**Status:** Adopted (pilot)
**Decision:** Keep `main` (this repo's default). Note that `Central-EMS/cenems`
defaults to `dev`, so the integration must target `dev`.
**Why:** `create-pull-request` bases on the repo default; matching it avoids
surprises. Recorded so the CenEMS rollout doesn't inherit `main`.

### D11 — Commit regenerated `.lock.yml`; add drift detection in CI (recommended)
**Status:** Adopted (pilot) / Proposed (CenEMS)
**Context:** Pilot issue #11 was an auto-filed "stale lock file" — `.md` edited
without recompiling.
**Decision:** Always `gh aw compile` and commit the locks together. Recommend a
CI check that runs `gh aw compile` and fails if the working tree changes.
**Why:** gh-aw refuses to run stale locks; drift silently breaks the loop.

### D12 — Constrain agent writes to `src/**` and `tests/**`
**Status:** Adopted (pilot) / hardened for CenEMS
**Decision:** `AGENTS.md` forbids touching `.github/`, `AGENTS.md`, and secrets.
For CenEMS, additionally enforce with gh-aw `protected-files` and the
`blocked_paths` already present in `.agents/codex-agent.yml`
(`.github/**`, `infra/**`, `auth/**`, `secrets/**`).
**Why:** Instruction alone is soft; production needs a hard, tool-level block so
a prompt-injected issue cannot make the agent edit CI or secrets.

### D13 — Self-contained topology for the pilot; hub-and-spoke for CenEMS
**Status:** Adopted (pilot) / Proposed (CenEMS)
**Decision:** Keep everything in this repo for the pilot; integrate via the
existing `trigger-issue-automation.yml` → `Central-EMS/automation-repo` dispatch.
**Why:** Fast iteration now; one maintained, auditable hub at scale. Detailed in
`cenems-integration-plan.md`.

### D14 — Omit explicit `model:`; use the engine default now, tune later
**Status:** Adopted (pilot)
**Decision:** Do not pin a model string in the workflows initially.
**Why:** A wrong/aliased model id fails at runtime; the engine default (latest
Claude) is reliable for a first live test. Cost tuning (e.g. a smaller model for
read-only triage, a stronger one for implementation/review) is a documented
follow-up, not a blocker.

### D15 — This session touches the pilot repo only
**Status:** Adopted
**Context:** You chose "pilot repo only." `Central-EMS/cenems` and
`Central-EMS/automation-repo` are production/shared.
**Decision:** All fixes and docs land in `CenEMSAgentTesting`. No changes to
CenEMS or the automation hub; the integration plan describes that rollout for
explicit future approval.
**Why:** Least blast radius; production changes to shared repos deserve their own
reviewed PR.

### D16 — No secrets in code; revocable, spend-capped testing credentials
**Status:** Adopted
**Decision:** All credentials are GitHub Actions secrets referenced by name;
none are committed. The Anthropic key is created in a dedicated, spend-limited
workspace so it can be disabled/rotated independently.
**Why:** CenEMS's stated non-negotiable — no secret leakage. Also lets the pilot
be torn down cleanly.

---

## Tech debt / deliberate compromises tracked

Per CenEMS policy (open a tracked `tech-debt` issue at the moment a trade-off is
made), the following are deliberate and should be filed when this moves into a
CenEMS repo:

1. **[Low][Automation] Interim same-vendor review (D7).** Review runs on Claude
   until `OPENAI_API_KEY` exists; flip to Codex.
2. **[Low][Automation] Model ids unpinned (D14).** Pin per-workflow models once
   cost/quality is measured.
3. **[Medium][Automation] `.agents/codex-agent.yml` validation commands are
   `npm`, but CenEMS is a Python monorepo.** The config's
   `lint/test/build: npm ...` will not validate CenEMS services; must be
   corrected during integration (see `cenems-integration-plan.md`).
4. **[Low][Automation] No lockfile-drift CI check yet (D11).**
