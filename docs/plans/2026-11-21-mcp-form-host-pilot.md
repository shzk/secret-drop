# Secret Drop — Codex MCP Form Elicitation host pilot

**Date:** 2026-11-21. **Task:** TickTick `6b01b31d8f08fe236af1f47b`.
**Owner:** [shzk/secret-drop](https://github.com/shzk/secret-drop), existing branch `research/mcp-elicitation-20261121`, isolated worktree `~/Developer/Codex/secret-drop-elicitation-research`.
**Approved input:** owner said “давай проверять” after reading [feasibility report](../research/2026-11-21-mcp-elicitation-feasibility.md).
**Baseline:** accepted v0.6.0 remains in `main` and the Mac plugin installation; no modification or merge into it.

## Precise hypothesis

An MCP stdio server can issue `elicitation/create` for **non-secret** destination approval during a tool call, and a Codex host with advertised form capability can render/route the request. The question card shown in ChatGPT is not proof that the same UI API is exposed to third-party Codex MCP tools.

## Steps and evidence

| Step | Deliverable | Verification |
| --- | --- | --- |
| 1 | This saved plan and research task | Git fetch and SHA/readback |
| 2 | Separate `research/elicitation-host-pilot/` stdio MCP server, tool `probe_confirmation`, no credential acceptance, no writes | Test initialize capability, form-only schema, accept/decline/cancel, timeout/unavailable fail closed, no secret fields/values |
| 3 | Codex app-server/CLI isolated test using **process-scoped** config or a disposable project; do not edit global `~/.codex` or user hook trust | Capture real client capabilities and routing event; distinguish app-server RPC response from native Desktop window screenshot; no real keys |
| 4 | Research report with exact observed outcome and next host UI gate | `git diff --check`, synthetic tests, pinned branch commit, remote readback; package + current `main` SHA unchanged |

## Safety and STOP

- MCP **Form is forbidden for passwords, API keys or access tokens** (MCP 2026-07-28 / 2025-11-25). The probe only exchanges `destination` and `confirm` with fake labels; no value input, secret storage, GitHub writes, public URL, tunnel, or API integration.
- The server **must not** elicit when client capability is absent; handle decline/cancel and errors with a status-only result. Do not fall back to entering a key in Form or chat.
- No patch to installed v0.6.0, Claude plugin, OpenCode, production, or `main`. No paid API/model fallback or persistent new service. A short-lived local process within the approved test scope is permitted.
- If Codex Desktop cannot present the UI automatically, record **PARTIAL / host UI OPEN** rather than inventing visual evidence; do not bypass via private GUI hooks. If an architecture change/new public endpoint is required, STOP and seek separate approval.
- Avoid creating a new Paseo project or duplicating an existing task. Distinguish synthetic-protocol PASS from actual Codex app-server/desktop observed behavior.
