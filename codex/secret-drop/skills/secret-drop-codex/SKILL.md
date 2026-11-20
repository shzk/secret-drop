---
name: secret-drop-codex
description: Use when a person needs to provide one or multiple API keys, passwords or tokens to Codex safely through a native masked macOS input dialog.
---

# Secret Drop for Codex

**Call `secret-drop-local.request_secret`**, never ask the human to paste or type a secret into chat or shell. Use `name` for one variable (legacy support) or **`secrets: [{name: "OPENAI_API_KEY"}, {name: "SERVICE_TOKEN"}]`** to collect multiple variables in **one native macOS window**. Optional `hint` is a short non-secret description. Always pass the exact existing canonical absolute `project_dir` for the intended project, not a guessed path. The window displays variable names in highlighted monospaced labels, uses one hidden field per variable, and presents the destination. The user enters secrets and clicks Save; the model receives **only variable names, destination and save status**.

Default `destination: "env"` atomically saves all values into the local project's `.env` with mode `0600`; opt-in `destination: "github"` or `"both"` requires known `github_repo` and explicit permission. A GitHub failure may partially save values, so report the returned status accurately. Never inspect, print, cat, or reproduce any saved secret. Do not use the old manual terminal helper.

**Supported UI boundary:** Codex Desktop currently does not provide a verified public API to mount a third-party secret field inside or above its native composer. The plugin shows a **separate native macOS AppKit dialog**, not the original Claude embedded band. Never manipulate Codex's accessibility/window hierarchy to imitate unsupported UI.

The `UserPromptSubmit` guard heuristically blocks some accidental pastes **after user hook trust**; it is not comprehensive DLP. On a missing MCP tool or a headless/non-macOS host, report that native masked entry is unavailable. Never fall back to asking for a real key via chat. Real keys require restricted project filesystem permissions since an agent with read access might still inspect `.env`.
