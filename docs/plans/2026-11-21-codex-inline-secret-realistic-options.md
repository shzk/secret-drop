# Codex single-inline protected secret entry — deeper feasibility research plan

**Date:** 2026-11-21. **Owner:** `shzk/secret-drop`, branch `research/mcp-elicitation-20261121`.
**Task:** TickTick `6b01dc458f08fe236af6b521`. **Previous result:** [Claude Mods vs Codex](../research/2026-11-21-claude-mods-vs-codex-secure-input.md).
**Owner request:** identify what we can realistically implement in Codex now that the Claude host-specific `ui.render/AbovePrompt` architecture is understood.

## Outcome and evidence

Produce a source-backed **implementation-option decision**, not a product patch:
1. Verify public Codex plugin/App UI feature gates, source parser, actual CLI flag state, host UI reports and third-party constraints; separate Codex CLI from the desktop renderer.
2. Reassess whether an MCP Apps **iframe containing a masked field** can get a dummy value to a trusted local helper via **direct frontend-to-local network** rather than `tools/call`, keeping it out of model-visible MCP values.
3. Evaluate official credential broker/credential masking, host-privileged browser verification, Form/URL Elicitation, native OS/AppKit, in-app browser and unsupported UI injection. Record why each is or is not a fit.
4. Specify a minimal **nonsecret** future feasibility pilot with exact go/no-go gates and a security checklist; no unapproved services, private flags in user global config, real secrets, deployment or installed v0.6 changes.
5. Commit the decision report to **this research branch only**, verify clean diff against `main` and update TickTick to DONE for research-only scope.

## Non-goals and STOP

Do not implement a new production endpoint, issue a hosted URL, edit `~/.codex/config.toml`, enable experimental flags in the user's session, create a user-facing service, patch Desktop binaries, use accessibility overlays, publish screenshots, write actual keys, install another plugin or merge into accepted `main`.

A direct iframe `fetch` is **a conditional hypothesis**, not established host compatibility or security. Require proof of UI rendering, sandbox CSP and CORS, loopback permission, identity/session binding, and no model/tool-log exposure before even testing a dummy value via localhost. If any prerequisite is missing or an architectural decision is necessary, preserve HOLD and request separate implementation approval.
