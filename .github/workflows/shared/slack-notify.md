---
safe-outputs:
  jobs:
    slack-notify:
      description: "Send a concise Slack notification to the pilot review channel."
      runs-on: ubuntu-latest
      output: "Slack notification sent."
      inputs:
        message:
          description: "The Slack message text to send."
          required: true
          type: string
      steps:
        - name: Send Slack notification
          env:
            SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          shell: bash
          run: |
            node <<'NODE'
            const fs = require("fs");

            const webhook = process.env.SLACK_WEBHOOK_URL;
            if (!webhook) {
              console.log("SLACK_WEBHOOK_URL secret is not configured; skipping Slack notification.");
              process.exit(0);
            }

            const outputPath = process.env.GH_AW_AGENT_OUTPUT;
            if (!outputPath || !fs.existsSync(outputPath)) {
              throw new Error("GH_AW_AGENT_OUTPUT is missing");
            }

            const output = JSON.parse(fs.readFileSync(outputPath, "utf8"));
            const items = (output.items || []).filter((item) => item.type === "slack_notify");
            if (items.length === 0) {
              console.log("No slack_notify items requested by the agent.");
              process.exit(0);
            }

            for (const item of items) {
              const message = String(item.message || "").trim();
              if (!message) continue;

              const response = await fetch(webhook, {
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify({ text: message }),
              });

              if (!response.ok) {
                const body = await response.text();
                throw new Error(`Slack webhook failed: ${response.status} ${body}`);
              }
            }
            NODE
---
