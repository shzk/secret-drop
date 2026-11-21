# Secret Drop research: demo value through Form vs protected native intake

**Date:** 2026-11-21. **TickTick:** `6b01c4f28f08fe236af3e5e5`.
**Owner:** `shzk/secret-drop`, **isolated branch** `research/mcp-elicitation-20261121`; worktree `~/Developer/Codex/secret-drop-elicitation-research`.
**Approved input:** owner asked to test a secret after a successful Codex Desktop inline nonsecret Form Elicitation E2E and verified rollback of the temporary global MCP.
**Accepted baseline:** `secret-drop-codex@secret-drop-tkrv` v0.6.0 at `main`, unchanged. Historical E2E confirmed native AppKit dummy value write and local readback.

## Purpose and threat boundary

Answer the user's practical question, "Can we use the inline Codex form for secret values?" by observing how a **public, deterministic synthetic marker** travels from MCP Form Elicitation into an MCP tool result through real Codex app-server. **Never request an actual API key/password/token through Form.** Official MCP [2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) forbids it and requires URL mode for sensitive credentials. A dummy marker is **not a secret**; it solely demonstrates observable data flow.

Compare the result against the **existing** approved Secret Drop `request_secret` implementation: private native macOS AppKit entry / local writer / name-only saved-and-verified status. Do not repeat the user-accepted v0.6 GUI host E2E merely to claim it anew. If actual chained Desktop UX is useful, leave that as a separate one-shot visual owner acceptance step, without reintroducing persistent global MCP settings.

## Ordered steps

1. Save plan in Git research branch. Verify file is present and pinned.
2. Add **one separate** test-only tool `probe_demo_value_visibility` to the existing research stdio probe: ask user to choose only predefined literal `PUBLIC_SYNTHETIC_DEMO_123` in a **nonsecret** form field `demo_text`, then deliberately return the literal in the tool result. Validate field/value strictly; never accept arbitrary inputs or actual credentials. Keep original `probe_confirmation` unmodified. Add unit tests for roundtrip, unexpected field/value rejection and missing client support.
3. Extend existing isolated app-server smoke client with a synthetic test of the `probe_demo_value_visibility` path. Observe response event, confirmed dummy marker propagation and model-visible tool result. Use only a process-scoped test MCP override and a dummy form response, not any real secret, global install or model API call.
4. Confirm accepted v0.6 native `request_secret` returns statuses without values from existing tests/source and do **not** claim live GUI E2E from this fixture alone. Record a clear comparison and recommendation: use Form for nonsecret selection, native AppKit or separately approved URL mode for actual key values.
5. Synthetic tests, `git diff --check`, compare with `main` (no accepted plugin source changes), commit and push branch-only evidence. Reconcile this research task.

## STOP / risks

Stop if a live key would be exposed to Form/agent/MCP client, an untrusted URL or new service is required, an accepted user-global config change is needed, or host-only GUI needs unapproved automation. No deployment/merge, production, real credentials, paid model fallback, public endpoint, new auth flow or new plugin registration. A result proving client visibility is **NOT** a demonstration that inline MCP Form can safely accept API keys.
