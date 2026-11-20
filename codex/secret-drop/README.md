# Secret Drop for Codex — native macOS dialog adapter

**Version 0.2.0 (under test)**. Upstream: [aislam23/secret-drop](https://github.com/aislam23/secret-drop), MIT, upstream `a54d43a`, Claude plugin `0.2.2`. This is an independent Codex implementation, **not** the original Claude UI.

## Workflow

1. Codex discovers local MCP tool `secret-drop-local.request_secret`.
2. When the user wants to enter a credential, Codex invokes `request_secret` with its **variable name, actual project path and optional destination**. It never sends the value.
3. A native macOS `display dialog … with hidden answer` window opens. The window shows the variable name and exact destination, with Cancel/Save.
4. The helper writes `.env` locally with `0600` permissions (refuses symlinks, tracked Git files, invalid paths) or sends the secret to GitHub Actions via `gh secret set` standard input when explicitly requested. Tool output gives only name and save status.

No terminal command or chat key entry is necessary. `UserPromptSubmit` hook remains an optional second line of defense against accidental pastes and must be trusted by the user via `/hooks`. Detection is heuristic, not perfect.

## Install / update (Codex Desktop / CLI on macOS)

```sh
codex plugin marketplace add shzk/secret-drop --ref feat/codex-secret-drop
codex plugin add secret-drop-codex@secret-drop-tkrv
```

The portable root `mcp.json` bundles a local stdio process and needs only system Python 3.10+, `osascript` (macOS), and optionally authenticated `gh` for GitHub saves. No long-running public service is introduced. Install/enable this plugin in **Codex desktop** on the same Mac where the dialog should appear; remote/headless execution cannot display the window. After upgrading an installed plugin, check `codex plugin list` for version 0.2.0 and start a new Codex session so MCP discovery refreshes.

## Security and limitations

- The GUI value travels from the OS dialog's `osascript` stdout **into the local MCP process's private pipe**, not its protocol stdout; neither the prompt text nor any key bytes are returned as tool content or printed to logs by this implementation.
- The agent might still read `.env` through unrestricted filesystem tools; use a protected store or restrict agent filesystem access for real credentials. Never ask the agent to print or verify the key.
- Invalid project paths, modal cancellation and all failed writes return a value-free error. The tool refuses secret values in its input schema.
- macOS system dialogs may require an interactive GUI session and proper OS permissions. CLI and Desktop E2E require separate checks. Unsupported hosts cannot use this dialog.
- The plugin code is public, and no actual secrets or real credentials are committed or used in tests.
