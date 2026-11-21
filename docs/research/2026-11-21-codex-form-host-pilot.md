# Pilot: native Codex MCP Form Elicitation routing

**Date:** 2026-11-21. **Status:** **app-server protocol E2E PASS; Codex Desktop visual UI E2E OPEN**.
**Owner:** [shzk/secret-drop](https://github.com/shzk/secret-drop), research branch `research/mcp-elicitation-20261121`.
**Task:** TickTick `6b01b31d8f08fe236af1f47b`.
**Plan:** [separate saved pilot plan](../plans/2026-11-21-mcp-form-host-pilot.md).
**Baseline:** approved `secret-drop-codex@secret-drop-tkrv` v0.6.0 on `main`; this research must not alter it.

## Tested setup

- Mac Codex CLI/app-server `0.163.0`, user-authenticated local runtime, **no language-model turn** initiated during the test.
- Isolated Python stdio server [`stdio_probe.py`](../../research/elicitation-host-pilot/stdio_probe.py), with only the **non-secret** MCP tool `probe_confirmation`.
- Its `elicitation/create` form contains exactly two metadata properties: `destination` (dummy `config/.env.local` vs `Do not save`) and `confirm` (boolean), plus explicit “DO NOT enter an API key” wording. It has **no password, key, value, credential, file write, authentication or network listener**.
- Standalone [app-server smoke client](../../research/elicitation-host-pilot/codex_appserver_smoke.py) launches `codex app-server --stdio` with process-scoped MCP overrides, starts an isolated Codex thread, then directly calls `mcpServer/tool/call` for `secret_drop_form_probe.probe_confirmation`. It answers a form event with **dummy metadata** only; no model inference used.
- The Codex-generated schema for `McpServerToolCallParams` requires `server`, `tool`, and `threadId`. Initial payload incorrectly used `serverName`/`toolName` and was rejected with `missing field server`; corrected against the actual generated schema. With `approvalPolicy=never`, the host **automatically cancelled** the form and emitted no client event. With `approvalPolicy=on-request`, it routed correctly.

## Actual local results (no inference)

```text
INIT_ACK=yes
THREAD_STARTED=yes
MCP_STATUS_RECEIVED=yes
ELICITATION_EVENT=yes
ELICITATION_MODE=form
ELICITATION_SERVER_MATCH=True
TOOL_CALL_RESULT=Form pilot: dummy destination confirmed: config/.env.local; NO FILES WERE WRITTEN
INIT_OK=True
CALL_STARTED=True
FORM_ROUTED=True
CALL_RETURNED=True
EXIT=0
```

- **10/10** separate pilot Python unit tests PASS: absent client capability fail-closed, form request, status-only accept, cancel/decline, unchecked destination, unknown content rejection (even if a secret-looking field is injected), no duplicate in-flight calls, schema metadata capability and direct stdio handshake.
- Previously committed protocol fixture **7/7** passed. `git diff --check` verification is part of branch closeout.
- Local research-only `.codex/config.toml` was created at `~/Developer/Codex/secret-drop-elicitation-research/.codex/config.toml`, permission **0600**, containing `approval_policy = "on-request"` and the `secret_drop_form_probe` stdio command with an absolute path to this branch's test script. It is intentionally ignored via this **worktree's** `.git/info/exclude`, and **not in Git** or user-global Codex settings.
- `codex mcp list --json` from the **research worktree** showed `secret_drop_form_probe` enabled; running it in the accepted original fork directory showed the probe **absent**. The installed `secret-drop-codex@secret-drop-tkrv` stayed enabled at **v0.6.0**, with marketplace/main unchanged.
- There is **no separate web or production MCP**, remote URL, real credentials, OAuth integration or model-visible key; app-server client acted as the synthetic non-secret confirmer.

## What this proves — and what it does not

**Proved:** an MCP stdio tool can trigger form elicitation **through a real Codex app-server**, which raises a `mcpServer/elicitation/request` event and routes an accepted structured response back to the source MCP tool when the interactive approval policy permits it.

**Not yet proved:** whether **Codex Desktop** renders this event as the exact inline question card shown in the owner's ChatGPT screenshot (the screenshot alone does not identify the RPC), whether project trust needs user action in the Desktop host, and what the visual Cancel/Decline controls look like. This requires the owner to observe the native UI in a **new Codex Desktop chat** opened at the research worktree; do not infer a GUI PASS from an app-server event.

**Security:** The Form payload carries only nonsecret destination metadata and an approval boolean. API keys, passwords and tokens **MUST NOT** be placed in MCP Form Elicitation under the [MCP 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) spec; for sensitive external workflows it mandates URL mode. The existing local AppKit remains the only accepted key-value intake in Codex v0.6.0.

## Desktop visual verification instruction

1. In **Codex Desktop** open project `/Users/shzk/Developer/Codex/secret-drop-elicitation-research`, not the regular `secret-drop` project, and start a **new** chat. If prompted, review and trust only this test project's local `.codex/config.toml` (contains one Python stdio probe and no external endpoint).
2. Message: “Call the research-only MCP tool `secret_drop_form_probe.probe_confirmation` once. It is a test of a native inline confirmation form, **not** a request for a key. Do not call the real Secret Drop tool or enter any API key. If a confirmation appears, select `config/.env.local`, set `Confirm destination` to true, and submit. Report only the tool result.”
3. Observe whether the form is embedded in the conversation, separate, cancelled, or not shown; send screenshot/response with **no real secrets**. If no form appears, check the project trust and the stated `approval_policy`; do **not** grant extra permissions or use Accessibility/private APIs.
4. After visual evidence, record `Desktop inline FORM PASS` or exact mismatch, then decide whether to propose a separate implementation PR for **non-secret** confirmation. Never merge this research pilot into the accepted plugin without a separately reviewed design and explicit owner approval.


## Desktop admission follow-up (2026-11-21)

The owner attempted the tool from Codex Desktop and received **tool not available**; no form opened. The project is already trusted and the probe is present in project-scoped CLI MCP discovery, while the Desktop thread omitted it. The isolated local config was corrected to explicit absolute Python executable and project `cwd`; CLI and direct stdio probe readbacks passed, but **a new Desktop retest has not yet occurred**. This is an **OPEN host-discovery gate**, not evidence that Elicitation itself failed.

[Detailed diagnostics and single retest procedure](2026-11-21-codex-desktop-mcp-discovery.md). No changes to accepted Secret Drop 0.6.0, user-global Codex config, or production. If project-scoped admission remains absent after new chat, stop and request separate permission before any temporary global-config workaround.

## Official documentation

- [MCP Form/URL Elicitation 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
- [MCP Elicitation 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Codex app-server protocol (elicitation route)](https://learn.chatgpt.com/docs/app-server)
- [Codex project-scoped configuration and trust](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Codex config reference: `approval_policy.granular.mcp_elicitations`](https://learn.chatgpt.com/docs/config-file/config-reference)

**Release boundary:** Only the research branch contains this server/client; approved `main`/installed v0.6.0 is untouched. No upgrade, merge or upstream PR update was performed for this pilot.
