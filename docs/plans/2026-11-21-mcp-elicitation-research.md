# Secret Drop: MCP elicitation and inline confirmation — research plan

**Date:** 2026-11-21. **Owner:** [shzk/secret-drop](https://github.com/shzk/secret-drop), **branch:** `research/mcp-elicitation-20261121`, isolated worktree `~/Developer/Codex/secret-drop-elicitation-research`.
**TickTick task:** `6b01a4b48f0887ff0a4c82e8`. **Existing accepted release:** Codex adapter v0.6.0 on `main` — DO NOT MODIFY or re-accept it.
**Input:** Owner observed a native inline question dialog in ChatGPT/Codex, and authorized research in a *separate* Git branch.

## Goal
Determine if native client questions / MCP Elicitation / MCP Apps can improve **request metadata and destination confirmation** while preserving the approved value-intake security boundary: secrets never travel through model-visible form content or tool arguments. Produce a source-backed feasibility and trust-boundary decision, plus a bounded no-secret protocol fixture only if useful.

## Scope
1. Verify current published MCP 2026-07-28 Form vs URL Elicitation requirements, Codex app-server/client routing, ChatGPT MCP Apps UI, version/feature/approval constraints. Distinguish source capability from installed Codex Desktop and ChatGPT Web E2E.
2. Compare three options: (A) preserve local native AppKit value dialog while using in-chat *non-secret* confirmation, (B) URL-mode credential entry with a verified HTTPS/OAuth server, (C) MCP Apps custom embedded UI. Include negative-path, phishing, model-visible data and authorization risks.
3. Optionally add **offline synthetic only** protocol fixtures/tests demonstrating the message shape and fail-closed behavior. No secret value, credential store, hosted URL, network listener, new permanent service, plugin deployment or production changes.
4. Commit and push branch-only research report and evidence. Do not merge, install or update marketplace; do not send unrelated changes to upstream PR #2.

## Verification / stop
- Research report cites precise upstream specs and official OpenAI Codex/Plugins docs, lists known/unknown runtime support and concrete next acceptance gate.
- `git diff --check`, synthetic tests (if fixture added), clean isolated worktree after commit, remote branch readback.
- STOP if UI needs unverified private APIs, secret capture in MCP Form Elicitation, new public credential service, actual keys, production, paid fallback or a material architecture change. In those cases document proposed requirements; get separate implementation approval.
- Explicitly identify **Form Elicitation cannot collect API keys**. Keep human confirmation distinct from model-provided text and verify URL domain/identity in any future flow.

## Output
- `docs/research/2026-11-21-mcp-elicitation-feasibility.md`: source-backed findings, comparison, threat model, recommendation and exact next test.
- Optional `research/elicitation-fixture/` with no-secret, offline protocol test(s) and run receipt.
- **No accepted release changes**. If a proof proves only protocol syntax, do **not** claim Codex Desktop or ChatGPT Web render support.
