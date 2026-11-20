# Secret Drop for Codex — native multi-key macOS dialog

**Version 0.3.0 (E2E acceptance pending).** Original project: [aislam23/secret-drop](https://github.com/aislam23/secret-drop), MIT, upstream commit `a54d43a`, Claude plugin `0.2.2`. Our fork keeps the original Claude plugin separate.

## Behavior

- Codex calls local MCP tool `secret-drop-local.request_secret` with either `name` (one variable) or `secrets` (1–12 entries with `name` and optional short `hint`), plus an existing canonical `project_dir`.
- **One native AppKit dialog** shows each variable name as a **highlighted monospaced label** and its own `NSSecureTextField`. The dialog supports Cancel/Save and scrolls for longer lists.
- The model **never** receives secret values or needs the user to run a terminal command. Values travel only through a local child process pipe and are atomically stored in a `0600` project `.env` (or explicitly requested GitHub Actions Secrets via `gh secret set` stdin).
- If any variable is empty or the user cancels, nothing is stored; GitHub multi-save is not atomic, and failures return status without values.
- Supports the previous single-secret `name` call. The optional `UserPromptSubmit` hook is independently trusted and is only heuristic protection.

## Limitation vs Claude

**This is not an in-composer UI.** Claude Code supports the author's `AbovePrompt` extension surface; the public Codex Desktop plugin API does not establish an equivalent composer-adjacent custom view. We do not modify/bypass the native Codex UI or use accessibility/window spoofing. The dialog is an independent macOS window.

## Installation / upgrading

```sh
codex plugin marketplace add shzk/secret-drop --ref feat/codex-secret-drop
codex plugin marketplace upgrade secret-drop-tkrv
codex plugin remove secret-drop-codex@secret-drop-tkrv
codex plugin add secret-drop-codex@secret-drop-tkrv
```

Run a **fresh Codex Desktop** session and ask for two test variables, e.g. `DEMO_ALPHA` and `DEMO_BETA`, with destination `.env` in a throwaway test project. The plugin includes a local stdio MCP server, built-in Python and AppKit Swift code. It compiles the native dialog once per source SHA to a user-private cache under `~/.cache/secret-drop-codex-dialog`. No server/tunnel/public listener or paid API is introduced.

Tested source checks and actual Desktop acceptance have **different** evidence levels; see the canonical Engineering Knowledge receipt. Never test with actual credentials or print `.env` values. ChatGPT Web does not use this local dialog.
