# Codex Desktop project MCP discovery: failed host test and bounded diagnostics

**Date:** 2026-11-21. **Scope:** existing [Secret Drop MCP Form pilot](2026-11-21-codex-form-host-pilot.md), branch `research/mcp-elicitation-20261121`, TickTick `6b01b31d8f08fe236af1f47b`. **Status:** **Codex Desktop UI E2E BLOCKED / NOT VERIFIED**. Accepted `main` Secret Drop plugin v0.6.0 is unchanged.

## Direct user observation

The owner followed the pilot test in Codex Desktop. The agent reported:

> `secret_drop_form_probe.probe_confirmation` is missing from available MCP tools; it cannot call it. No form opened, no tool result. It did not call regular Secret Drop, request keys or write anything.

This is **not** a negative test of MCP Elicitation itself: the host never admitted the probe tool.

## Verified on the same Mac

1. The project `/Users/shzk/Developer/Codex/secret-drop-elicitation-research` is marked **trusted** in `~/.codex/config.toml` (only trust metadata was inspected; no secrets read).
2. A **research worktree-only**, `0600`, ignored `.codex/config.toml` registers `secret_drop_form_probe`. `codex mcp list` / `codex mcp get` from that folder report `enabled=true`; from the accepted original fork folder the probe is **absent**.
3. Initial `codex mcp get` showed `cwd=null` and `command=python3`. As a bounded targeted compatibility check, updated only that ignored project-local config to `command="/opt/homebrew/bin/python3"` and `cwd="/Users/shzk/Developer/Codex/secret-drop-elicitation-research"`. Readback confirms the exact effective command and cwd, enabled=true, while the source worktree remains clean.
4. Running the **test stdio tool itself** via the explicit absolute Python path produced `initialize` / `tools/list` response with `probe_confirmation`, exit 0 and empty stderr.
5. The separate earlier isolated Codex **app-server** simulation with process-scoped MCP overrides successfully emitted `mcpServer/elicitation/request` and received a dummy form response, exit 0. This proves the transport route, not the Desktop's project-config loader.
6. **OWNER RETEST RESULT — 2026-11-21:** after the explicit Python command and project `cwd` correction, the owner restarted/opened the research project in a new Codex Desktop chat and received **`MCP_NOT_VISIBLE`** again. The test MCP tool was absent; no Form was opened, no tool was called and no value was entered. This is the **second bounded Desktop discovery failure**, so further project-local configuration variations are stopped.

## Relevant public issue evidence, not a verified root-cause attribution

- [openai/codex#13025](https://github.com/openai/codex/issues/13025): reproductions where Codex Desktop ignores trusted project `.codex/config.toml` MCP entries while user-global configuration works.
- [openai/codex#10499](https://github.com/openai/codex/issues/10499): project MCP tools visible in CLI / Settings but not injected into Desktop thread.
- [openai/codex#14449](https://github.com/openai/codex/issues/14449): a report of Desktop admission improving after setting a project MCP `cwd`.
- [openai/codex#20605](https://github.com/openai/codex/issues/20605): existing Desktop threads can keep stale tool catalogs after config changes.

These are GitHub issue reports from other environments. Do not claim our exact issue has been fixed or that those reports establish a definitive cause.

## Decision after second Desktop failure — BLOCKED

**STOP** project-scoped configuration attempts and repeated user UI tests. Codex Desktop did not expose the research tool even after project trust, explicit Python executable, explicit cwd, and a fresh Desktop attempt. The root cause within the Desktop client has **not** been proven. The existing app-server protocol E2E remains PASS; Desktop Form UI E2E remains **NOT TESTED** because tool discovery fails first.

**Optional next route — requires separate explicit user approval:** temporarily register *only the non-secret test probe* under user-global `~/.codex/config.toml`, after backing up the exact file; verify readback, run one new Desktop chat, then restore prior configuration and verify clean rollback. A global entry may affect other Codex sessions, so do not apply it under the existing research authorization. No real key may be entered, no current Secret Drop plugin may be modified. If the user does not approve the global experiment, leave the research branch and ticket BLOCKED without extra testing.

## Outcome boundary

**Existing probe:** stdio PASS, Codex app-server routing PASS, **Codex Desktop tool discovery FAIL x2 (including after cwd correction)**. Local source and CLI checks PASS; actual Desktop inline Form UI remains **UNVERIFIED**. Follow-up requires an explicitly approved reversible global-config test, not further project-local retries. No accepted Secret Drop source, marketplace or `main` files changed. No real credentials, public endpoint, network listener, GitHub write or metered API spend.
