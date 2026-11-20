---
name: secret-drop-codex
description: Use when one or multiple credentials must be entered securely into a local project .env or explicitly approved GitHub Actions Secrets via Codex on macOS.
---

# Secret Drop for Codex

**Invoke `secret-drop-local.request_secret`** with a single `name`, or multiple `secrets: [{name: "TEST_ONE"}, {name: "TEST_TWO"}]`, and the canonical existing absolute `project_dir`. Never request a secret value through conversation, terminal commands, MCP arguments or another agent. The user gets a compact native macOS AppKit modal with **burgundy monospaced centered variable chips on the left** and **masked fields on the right**. The dialog is separate from Codex's composer.

**Partial entry:** only populated fields are saved. Each blank field is reported as `Skipped (not entered)`; existing previous values in the file may still exist and are not touched. All blank or Cancel means no write. Project `.env` writes are atomic with mode `0600`.

**Verification:** after writing `.env`, the trusted local helper reads the file **inside its own process only** to check that the exact entered values persisted and that owner, file type and permissions are correct. The model receives **only per-name saved/verified, skipped and error statuses**, never the secret bytes. `Saved and verified locally` confirms persistence; **it does not mean a remote API key is valid**. If verification returns `NOT VERIFIED`, report this accurately; do not use the credential as ready or ask the user to expose it for diagnosis.

Optional GitHub Secrets output must be explicitly authorized and accompanied by `github_repo`; remote CLI write success is separate from remote credential validity and GitHub multi-write may partly fail. Do not treat `Skipped` as proof an existing variable is absent.

The `UserPromptSubmit` guard heuristically blocks some accidental pastes **after user trust** and is not comprehensive DLP. A running agent with filesystem access might still read `.env`; prohibit that separately. Do not ask the agent to open or print the file. On non-macOS or no MCP tool, report unsupported secure entry rather than requesting a key in chat.

Codex Desktop currently has **no verified supported plugin API to mount this UI next to the composer**. Do not imitate Claude's `AbovePrompt` using Accessibility overlays, private APIs or modifications of Codex. Use only synthetic keys for acceptance.
