---
name: secret-drop-codex
description: Use when Codex needs a credential, token, password, or GitHub Actions secret from the user without receiving its value in conversation or tool arguments.
---

# Secret Drop for Codex

**Primary route: call the bundled `secret-drop-local.request_secret` MCP tool**. Pass the variable `name` and exact existing absolute `project_dir`; `destination` is `env` by default. The tool opens a native macOS dialog with a **masked input field** labeled with the variable name and destination, asks the user to enter the secret, writes locally, and returns **only save status**. The user need not run anything in Terminal. Never request the key's value in chat, shell command arguments, tool arguments, or agent messages.

Example call arguments (NO secret values): `{"name":"OPENAI_API_KEY","project_dir":"/Users/<local-user>/project","destination":"env"}`. Resolve `project_dir` from the actual active working directory; never guess or pick a different project. To save GitHub Actions Secrets, explicitly use `destination: "github"` or `"both"` with a known `github_repo`. The macOS modal shows the target; the human must click Save. Do not invoke the old terminal helper.

If the MCP tool is absent, report that the local plugin or MCP connection is not loaded; **do not substitute a chat prompt for the secret or tell the human to type the secret into an agent terminal**. On non-macOS hosts, the native UI is unavailable.

A separate `UserPromptSubmit` pattern guard can block some recognizable credentials accidentally pasted into a Codex prompt, **only after the user trusts/enables it** via `/hooks`. The guard is heuristic and not complete DLP.

**Security boundary:** Codex/other agents with filesystem access can potentially read `.env`. Respect OS permissions and project-scoped tool approvals; never inspect the value for verification. Use fake credentials in tests. ChatGPT Web cannot show this local macOS modal without a connected local runtime.
