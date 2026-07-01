# Secrets & Setup Guide

Exactly which keys/tokens/secrets this system needs, how to create each **as a
revocable testing credential**, and how to store them safely. CenEMS rule: **no
secret is ever committed to code** — everything below is a GitHub Actions secret
referenced by name.

> **Never paste a key into a chat, an issue, a PR, a commit, or a log.** Set
> secrets yourself via the GitHub UI or `gh secret set` in your own terminal.

---

## 1. What the pilot needs

| Secret | Needed for the live test? | Used by | Notes |
|--------|:--:|---------|-------|
| `ANTHROPIC_API_KEY` | **Yes** | triage, implement, review (interim), fix | Claude engine auth |
| `GH_AW_AGENT_TOKEN` | **Yes** | implement, fix | Scoped token so agent PRs/pushes trigger the review workflow (the default `GITHUB_TOKEN` can't) |
| `SLACK_WEBHOOK_URL` | Optional | triage, implement, fix | Loop works without it; the notifier skips cleanly if unset |
| `OPENAI_API_KEY` | No (not yet) | review (Codex) | Only when you flip review from Claude to Codex |
| `GITHUB_TOKEN` | Auto | everything | Provided by GitHub Actions automatically — you don't create it |

**Minimum to run the live test now:** `ANTHROPIC_API_KEY` + `GH_AW_AGENT_TOKEN`
(+ `SLACK_WEBHOOK_URL` if you want the pings).

---

## 2. `ANTHROPIC_API_KEY` — a revocable, spend-capped testing key

Create it isolated so you can cancel it without touching anything else:

1. Sign in at **console.anthropic.com**.
2. **Settings → Workspaces → Create Workspace**, name it e.g.
   `cenems-agent-pilot`. A workspace isolates keys, usage, and limits.
3. On that workspace set a **spend limit** (e.g. a small monthly cap) so a
   runaway loop can't cost more than the cap.
4. **API Keys → Create Key**, and make sure the key belongs to the
   `cenems-agent-pilot` workspace. Name it `pilot-testing`.
5. Copy the key **once** (starts with `sk-ant-...`) and store it straight into
   the GitHub secret (§6). Don't save it elsewhere.

**To cancel/rotate:** delete the `pilot-testing` key (instant revoke), or archive
the whole workspace. Because it's a dedicated workspace, this affects nothing
else.

---

## 3. `GH_AW_AGENT_TOKEN` — fine-grained PAT (pilot) 

Needed so PRs the agent opens actually trigger the review workflow.

1. GitHub → **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**.
2. **Resource owner:** your account. **Repository access:** *Only select
   repositories* → `ArnavGupta262/CenEMSAgentTesting` (nothing else).
3. **Repository permissions** (minimum):
   - Contents: **Read and write**
   - Pull requests: **Read and write**
   - Issues: **Read and write**
   - Metadata: Read (auto)
4. **Expiration:** 30 days (short-lived testing credential).
5. Generate, copy once, store into the secret (§6).

**To cancel:** delete the token in the same screen — instant revoke.

> Production (`Central-EMS`): replace this PAT with a **GitHub App** installation
> token (no user binding, least-privilege, auto-rotated, auditable). See the
> Integration Plan §3–4.

---

## 4. `SLACK_WEBHOOK_URL` — new webhook vs. reusing the existing one

**You asked: can I reuse the webhook from another repo, or make a new app?**
**Recommendation: create a new Incoming Webhook pointed at a dedicated channel**
(e.g. `#cenems-agent-pilot`). You do *not* need a whole new Slack *app* — a new
webhook on your existing app is fine — but you *should* have a distinct webhook +
channel because:

- A Slack Incoming Webhook is **bound to one channel**; reusing the other repo's
  webhook would post pilot messages into that repo's channel.
- Separate webhook = **independent revocation** (kill the pilot's pings without
  affecting the other repo) and clean attribution.

Steps:
1. **api.slack.com/apps** → pick your existing app (or Create New App →
   From scratch).
2. **Incoming Webhooks → Activate** (if not already) → **Add New Webhook to
   Workspace** → choose `#cenems-agent-pilot`.
3. Copy the new `https://hooks.slack.com/services/...` URL into the secret (§6).

**To cancel:** delete that webhook in the app's Incoming Webhooks list.

---

## 5. `OPENAI_API_KEY` — for the Codex review (when you're ready)

Not required now (review runs on Claude — see `decision-record.md` D7). When you
switch review to Codex:

1. **platform.openai.com** → **Projects → Create project** `cenems-agent-review`.
2. Set a **budget limit** on the project.
3. **API keys → Create new secret key** *in that project*; copy once.
4. Store as `OPENAI_API_KEY` (§6), then in `agent-review.md` change
   `engine.id: claude` → `codex`, run `gh aw compile`, and push.

**To cancel:** delete the key / archive the project.

---

## 6. Storing the secrets (do this yourself — not through me)

**Option A — GitHub UI:** repo → **Settings → Secrets and variables → Actions →
New repository secret**. Name it exactly (`ANTHROPIC_API_KEY`, etc.), paste the
value, save.

**Option B — `gh` CLI**, in *your own* terminal (it prompts for the value without
echoing it; nothing is written to shell history):

```bash
gh secret set ANTHROPIC_API_KEY  --repo ArnavGupta262/CenEMSAgentTesting
gh secret set GH_AW_AGENT_TOKEN  --repo ArnavGupta262/CenEMSAgentTesting
gh secret set SLACK_WEBHOOK_URL  --repo ArnavGupta262/CenEMSAgentTesting
# later, for Codex review:
gh secret set OPENAI_API_KEY     --repo ArnavGupta262/CenEMSAgentTesting
```

Verify names (values are never shown):

```bash
gh secret list --repo ArnavGupta262/CenEMSAgentTesting
```

---

## 7. Security posture (why this is safe)

- **Isolation:** dedicated Anthropic workspace + repo-scoped PAT + dedicated
  Slack webhook → each is independently revocable and spend-capped.
- **No exfiltration path:** gh-aw runs agents behind an egress firewall (only
  allowlisted domains, incl. `api.anthropic.com`), agent jobs are read-only, and
  all writes go through minimally-scoped safe-output jobs.
- **Least privilege:** the PAT can touch only this repo, only contents/PRs/issues.
- **Bounded spend:** workspace/project caps + gh-aw daily AI-credit guardrail +
  `max-turns`/`timeout-minutes`.
- **Kill switch:** revoke any key (agents can't call the model), delete the PAT
  (agents can't write), or disable the workflows.

---

## 8. Live-test checklist

- [ ] `ANTHROPIC_API_KEY` set (revocable workspace key)
- [ ] `GH_AW_AGENT_TOKEN` set (repo-scoped fine-grained PAT)
- [ ] `SLACK_WEBHOOK_URL` set (optional; dedicated channel)
- [ ] Changes pushed and workflows present on the default branch
- [ ] Open an issue with the `automation` label and watch the Actions tab
