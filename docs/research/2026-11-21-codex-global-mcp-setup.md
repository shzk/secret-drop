# Temporary user-scoped MCP test for Codex Desktop UI

**Date:** 2026-11-21. **Experiment:** [Secret Drop form-host pilot](2026-11-21-codex-form-host-pilot.md), task TickTick `6b01b31d8f08fe236af1f47b`.
**User authorization:** explicitly agreed to a **temporary global MCP** test with backup and mandatory rollback, clarified that the desired manual UI is the **Codex Desktop application**, not ChatGPT Web.

## Baseline and why

- Previous **two** Desktop tests returned `MCP_NOT_VISIBLE` with the research probe registered **project-only**, even though the project was trusted, CLI discovered it, and a custom Codex app-server test confirmed MCP Elicitation routing.
- To test whether **global server discovery** is the missing layer, the existing **non-secret** `secret_drop_form_probe` was registered temporarily using standard `codex mcp add`. No real Secret Drop code or auth was touched.

## Actual global config readback

- Existing `~/.codex/config.toml`: owner-owned, mode `0600`, had no research probe; the existing MCP names were `computer-use`, `node_repl`, `playwright`. The full config was **not printed** and no secrets read.
- A private byte-identical backup was made at `~/.codex/.secret-drop-elicitation-20261121-backup/config.toml` (directory `0700`, file `0600`), with hashes stored within that private backup directory.
- User-global test entry added:
  - name `secret_drop_form_probe`;
  - stdio executable `/opt/homebrew/bin/python3`;
  - args `-I` and absolute research source `/Users/shzk/Developer/Codex/secret-drop-elicitation-research/research/elicitation-host-pilot/stdio_probe.py`.
- A post-add diff detected an **unexpected Codex CLI normalization of the existing `node_repl.args`** (the property was dropped). The original args array was restored from the private backup **without outputting its contents**. Semantic TOML readback confirmed that **every preexisting setting exactly equals the baseline after excluding the one test MCP entry**.
- Final CLI readback from the **ordinary** `secret-drop` project (not the research worktree): `secret_drop_form_probe` is now **enabled and visible globally**. Accepted `secret-drop-codex@secret-drop-tkrv` remains installed/enabled v0.6.0.
- A private `after.sha256` was recorded to permit an exact rollback if config bytes are unchanged. If the user or another agent edits Codex settings before cleanup, do **not** overwrite their newer changes from the old backup; remove only the test entry and reconcile remaining settings.

## Open Codex Desktop UI gate — DO NOT claim PASS yet

Codex official documentation provides an MCP add/manage UI: Settings → MCP servers → Add server, or Settings → Plugins → MCPs → Add → Add MCP server depending on client build. **Do not create a duplicate**: the test entry has already been added through the supported CLI and uses the same shared configuration. Inspect it in UI and start a **new** Codex Desktop chat:

```
Call the MCP tool secret_drop_form_probe.probe_confirmation once, using no arguments.
Only test NON-SECRET confirmation metadata. Do not call ordinary Secret Drop, read a
saved key, enter credentials or write a file. If a native confirmation form appears,
select config/.env.local and confirm, then report the tool status.
```

Only an actual Desktop event/screenshot or exact error settles this host UI gate. Previous app-server form routing PASS is preserved, but is not a Desktop UI PASS.

## Mandatory rollback — OPEN while user performs one UI check

After the one user-side Desktop test, remove **only `secret_drop_form_probe`** from user-global Codex MCP; verify that the other servers still work and that other user config values match their pretest baseline. A complete restore of `config.toml` bytes from backup is safe **only when its live SHA matches the recorded post-add SHA**; otherwise preserve intervening user changes and remove just the probe. Delete private duplicate backup after successful rollback with an explicit, exact rollback readback.

**Important:** The temporary global test is presently ACTIVE and therefore visible to all local Codex sessions until rollback. It never requests a value and never writes a file or calls a remote endpoint. No new GitHub PR, no modification of accepted `main` or installed Secret Drop v0.6.0.
