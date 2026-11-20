---
name: secret-drop-codex
description: Use when one or multiple credentials must be entered privately into a project .env or explicitly approved GitHub Actions Secrets from Codex on macOS.
---

# Secret Drop for Codex

**Call `secret-drop-local.request_secret`.** Never ask the human to paste a secret in conversation, terminal commands, tool arguments or an agent message. Use `name` for a single variable (legacy), or `secrets: [{name: "TEST_ONE"}, {name: "TEST_TWO"}]` for multiple values in one native macOS modal. Each variable is displayed in **burgundy monospaced type on the left**, with a separate **masked field on the right**. Pass the actual existing canonical absolute `project_dir`; never invent a different target directory.

**Partial entry is supported.** The person may fill only some fields and click Save. Entered variables are written in one atomic `.env` update (0600), while blank fields are skipped and explicitly named in the returned status. Existing saved values for skipped variables remain unchanged. All blank fields or Cancel create no writes. Do not treat `skipped` as proof the variable is absent from an existing file. Never read/print a value to verify it.

Default `destination: "env"`; `"github"` or `"both"` must include a known `github_repo` and receive separate authorization. GitHub secrets are saved individually; observe possible mixed outcomes and report the exact model-safe status. The MCP tool sends **only variable names, destination and save/skip/error statuses** to the model.

**UI boundary:** The native dialog is separate from Codex Desktop, **not inside/above its composer**. No public API has been verified that permits mounting a secret-entry field into the Codex composer; do not fake that with Accessibility overlays or private APIs. The `UserPromptSubmit` hook separately blocks some recognized accidental pastes only once trusted by the user, and is not complete DLP.

If the tool is unavailable, do not ask for credentials in chat. Agent filesystem permissions can still expose existing `.env`; protect real credentials using OS/filesystem access policies. Use only synthetic keys during tests.
