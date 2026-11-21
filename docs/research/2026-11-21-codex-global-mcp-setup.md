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

## Codex Desktop embedded Form Elicitation — OWNER-OBSERVED PASS

Codex official documentation provides an MCP add/manage UI: Settings → MCP servers → Add server, or Settings → Plugins → MCPs → Add → Add MCP server depending on client build. **Do not create a duplicate**: the test entry has already been added through the supported CLI and uses the same shared configuration. Inspect it in UI and start a **new** Codex Desktop chat:

```
Call the MCP tool secret_drop_form_probe.probe_confirmation once, using no arguments.
Only test NON-SECRET confirmation metadata. Do not call ordinary Secret Drop, read a
saved key, enter credentials or write a file. If a native confirmation form appears,
select config/.env.local and confirm, then report the tool status.
```

**Owner-observed actual Codex Desktop result (2026-11-21, screenshot in the original chat):** In a new Codex conversation, the first request still displayed `MCP_NOT_VISIBLE`, but a second request exposed `secret_drop_form_probe.probe_confirmation`. Codex displayed an **inline form in the conversation** with `Confirm destination`, the fake destination options `config/.env.local` / `Do not save` and visible **Decline / Accept** controls. The owner accepted the selected fake target and reported Codex's result: the tool was called once with `{}`, returned confirmation of `config/.env.local`, requested no keys and wrote no files. This establishes **Codex Desktop UI E2E PASS for non-secret MCP Form Elicitation**, not proof of a secure credential-value intake form.

**Discovery boundary:** project-local registration alone yielded repeated `MCP_NOT_VISIBLE`; temporary global registration enabled subsequent discovery **within the same Desktop conversation**, without changing the accepted Secret Drop plugin. The first global-scope attempt still returning `MCP_NOT_VISIBLE` prevents attributing the outcome to a single definite trigger or guaranteeing instantaneous discovery. In particular, do not claim that simply registering any project MCP will always make it available to Codex Desktop.

## Mandatory rollback — COMPLETED and independently read back

After the owner confirmed the Desktop form, the current global `~/.codex/config.toml` SHA-256 **exactly matched the recorded post-add fingerprint**, and parsing it without the temporary `secret_drop_form_probe` record produced the identical pretest TOML mapping. Therefore the original byte-identical `config.toml` was restored atomically from the private backup and mode `0600` re-established. **Readback: restored configuration SHA-256 `e0b1588437088c2edf67d6524489ddbe1436ccfc1c3ef0700e77969fc3fe9ea1`; backup bytes identical; no global test probe; `computer-use`, `node_repl`, `playwright`, `secret-drop-local` all still enabled; installed Secret Drop plugin `0.6.0` unchanged.** The deleted `node_repl.args` side-effect caused earlier by the Codex CLI was also fully restored with the original byte-identical config. After final check, the private duplicate backup directory and its temporary fingerprint files were deleted successfully. No backup or secrets were committed to Git.

**Final status:** the temporary global test is **NOT active**. The research-only stdio probe source remains in the isolated research branch; no public MCP server, model-visible key, new GitHub PR or accepted `main` change was introduced. Any future product integration requires its own design/security acceptance and must keep credential values outside MCP Form Elicitation.
