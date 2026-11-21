# Why Secret Drop can embed a secure-entry band in Claude Code but not Codex Desktop

**Research date:** 2026-11-21. **Status:** source-backed feasibility analysis; **not an implementation request or release change**.
**Owning source:** [shzk/secret-drop](https://github.com/shzk/secret-drop), research branch `research/mcp-elicitation-20261121`.
**Installed Mac clients read back in this research:** Claude Code `2.1.329`; Codex CLI `0.163.0`. A separately observed Codex Desktop GUI E2E proved non-secret MCP Form Elicitation, not secure inline credential entry.
**Accepted baseline:** Secret Drop Codex `0.6.0` on `main`; no source, marketplace, global MCP configuration, production or real credential is changed by this analysis.

## Executive decision

**The deciding difference is the host-supported UI extension API, not the language model or the MCP protocol.** Original Secret Drop is a **Claude Code Mod**: it directly hooks the Claude client's `ui.render` lifecycle at `AbovePrompt` and receives interactive `Input` events inside its own plugin module. Codex's documented third-party plugin interface provides **skills, MCP tools, lifecycle command hooks, plugin metadata and certain optional UI resources**, but **does not expose a supported equivalent to Claude's generic `ui.render/AbovePrompt` and `$.prompt.fill` bridge to a Codex Desktop plugin** in the sources inspected. These are statements about documented/inspected APIs **as of the stated date**, not a proof that an unavailable or future internal API cannot exist.

**Do not use MCP Form Elicitation for actual credentials.** Official MCP 2026-07-28 prohibits requesting passwords/API keys/access tokens via Form. Existing Codex native AppKit Secret Drop is a supported out-of-band local alternative; migrating secret values into ordinary Form would violate the boundary rather than improve it.

**Recommended action:** keep accepted v0.6.0; preserve this branch as research; do not merge a two-window workaround into `main`. Reassess only upon an official Codex trusted secret-input UI API or an explicitly approved and audited out-of-band secure flow.

## 1. Claude Code: actual working mechanism (source, not analogy)

The original [aislam23/secret-drop](https://github.com/aislam23/secret-drop) is version `0.2.2` (upstream base `a54d43a7eeab25cde884e5e9236b36f66ee760d9`). Its [hooks/hooks.json](https://github.com/aislam23/secret-drop/blob/main/hooks/hooks.json) loads a module, and [hooks/register.tsx](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx) imports `atom/read/update` and `EngineInterface/Register` from `claude-code`. It installs these handlers:

| Extension | Exact source behavior | Why it matters |
| --- | --- | --- |
| `session.start` | `$.tool.register` exposes `request_secret`; `$.command.register` exposes `/secret` | Model or human initiates a secret request without supplying a value in the model tool arguments |
| `tool.call` for `mcp__secret-drop__request_secret` | Creates plugin-side request state and **returns immediately** telling the model to end its turn | User can complete the UI asynchronously; a later non-secret status is submitted to the conversation |
| `ui.render`, component `AbovePrompt` | Returns a render tree made of `Box/Text/Button/Input` and `Svg` for the desktop | The control is drawn by the **Claude host** directly next to its composer, not by an MCP client-side form |
| `Input onInput/onSubmit` | Receives edits in the mod callback; keeps raw typed text in module-side `buffer` / `values`; renders `DOT.repeat(buffer.length)` unless Reveal is selected | The mod, not the model, receives the entry; masking is implemented in module/UI logic |
| `prompt.submit` | Detects apparent secrets from human-origin prompts and returns `{drop: reason}`; uses `$.prompt.fill` to restore a sanitized draft | Claude offers pre-model interruption **and editable composer restoration** |
| `$.fs.write` / `$.process.run` | Saves to dotenv or calls `gh secret set` via stdin; sends only names, lengths and status through `$.prompt.submit` / `$.session.append` | Secret does not intentionally enter model messages; a separate local process/tool may still access the resulting dotenv |

See [actual rendering code (register.tsx lines 495+)](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx#L495), [prompt hook around line 475](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx#L475), [model request around line 396](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx#L396), and [mod tests](https://github.com/aislam23/secret-drop/blob/main/tests/secret-drop.test.tsx).

This is not an undocumented visual trick: [official Claude Code Mods Reference](https://code.claude.com/docs/en/plugins/mods/reference) explicitly lists `ui.render`, `AbovePrompt` for Terminal/Desktop, `Input` with `onInput/onSubmit`, the `$.ui.resolve` element table, `$.tool.register`, `$.command.register` and `$.prompt.fill`. [Official getting-started guide](https://claude.dev/blog/getting-started-with-claude-code-mods/) explains persistent sandboxed mods versus ordinary shell-based settings hooks.

**Security precision:** "the model does not receive the key" is supported by the code path and tests, but "the Claude host never sees the key" or "all memory copies are cryptographically wiped" is **not** established. A UI host handles input events, and the JavaScript module keeps string values until clearing references; no secure zeroization is demonstrated. The Claude Docs say `$.fs.write` **is not atomic**, and the upstream saves the dotenv before checking/updating effective Git ignore. This is **not the same hardening** as our Codex v0.6.0 writer (canonical path/ancestry, no-follow, hardlink, owner, `0600` and Git ignore checks). The accepted Codex adapter remains preferable on some filesystem threat-model dimensions; these findings are source observations, not a full new exploit assessment.

## 2. Codex: supported extension surface and negative evidence

Official [OpenAI Plugin Architecture](https://developers.openai.com/plugins/concepts/plugins) describes packages with skills, MCP servers, command lifecycle hooks and optional UI resources. The [package reference](https://developers.openai.com/plugins/build/plugins) maps plugin metadata and OpenAI extensions. Actual [Codex manifest parser](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manifest.rs) handles name/version/description/keywords, skills, MCP servers, apps, hooks, interface and generic extension metadata; it contains no Claude-like `ui.render/AbovePrompt` contract.

A Codex [UserPromptSubmit hook](https://github.com/openai/codex/blob/main/codex-rs/hooks/src/events/user_prompt_submit.rs) takes a prompt and can stop/block it or append model context. Official [Codex Hooks guide](https://learn.chatgpt.com/docs/hooks) documents `decision: block` / `additionalContext`. **It is not a composer UI widget API**, and it has no published callback equivalent of `$.ui.resolve(Input)` or `$.prompt.fill` for restoring an edited draft. Hook trust is a separate prerequisite.

There *are* native Codex questions: [Codex App Server protocol](https://learn.chatgpt.com/docs/app-server) includes experimental `tool/requestUserInput` and `mcpServer/elicitation/request`, but the former is a **client/server tool prompt for Codex**, not a documented callable renderer for arbitrary plugin-created password controls. The latter is normal MCP Elicitation, governed by its security rules.

The repo's CLI [custom statusline provider](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/create-statusline/SKILL.md) can render a **terminal footer** UI tree, but no general editable or secure field in Codex Desktop is documented for that provider. Do not equate "some custom UI is possible" with "third-party inline credential input exists."

**Scope of negative evidence:** no matching `AbovePrompt` API was found in the Codex plugin manifest, official Plugin UI docs or indexed `openai/codex` source search as of this research. This supports "not publicly documented/supported in the inspected version", **not** absolute technical impossibility. Desktop may contain non-public internal components that plugins may not use.

### Additional separate credential-settings gap

[openai/codex issue #36854](https://github.com/openai/codex/issues/36854), opened Aug 2026 and reported Open in the inspected public source, asks for a supported plugin manifest mechanism to request sensitive configuration on installation and store it securely. This is **a community request**, not an implemented capability. The current manifest parser above does not declare a comparable portable credential prompt. An installation-time settings prompt (if adopted) would also solve a **different workflow** from Secret Drop's dynamic per-task `.env` targets.

## 3. MCP Form Elicitation — the boundary we tested, not conjecture

[MCP Elicitation 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) distinguishes:

- **Form mode**: structured response travels through MCP client, with content available to tools and potentially a model. Servers **MUST NOT** request credentials such as passwords, API keys or access tokens in this mode. See also [MCP SDK Elicitation](https://ts.sdk.modelcontextprotocol.io/v2/servers/elicitation): "Keep secrets out of forms".
- **URL mode**: external browser/out-of-band interaction. The MCP client sees URL/consent but does not receive form fields; server identity, user-session binding, anti-phishing, CSRF, host trust, secure storage and result reconciliation are implementation responsibilities. "Accept" is not proof of successful key storage.

**Our direct observations** are captured in the branch [Desktop Form E2E report](2026-11-21-codex-form-host-pilot.md) and [synthetic marker vs native handoff](2026-11-21-public-marker-vs-secure-intake.md):

- Mac Codex `0.163.0` app-server: server emitted `mcpServer/elicitation/request` and synthetic client accepted only destination metadata, full tool call returned. **Host protocol PASS**.
- Owner saw a real **Codex Desktop inline MCP Form** and completed the fake destination confirmation after temporary user-global MCP registration. **Non-secret GUI E2E PASS**; temporary global registration was backed up, removed, and original config verified byte-identical and original other MCP preserved.
- In a separate app-server test, the strictly public marker `PUBLIC_SYNTHETIC_DEMO_123` entered via Form appeared in an MCP tool result. **This demonstrates the in-band data path**, not that a real model consumed that public marker; no model generation was invoked.
- A synthetic two-stage test used Form **only for a destination**, then a **mocked native AppKit response** fed a fake value into the existing trusted Secret Drop writer. File `0600` and status-only output passed. **This was not a real two-window Desktop E2E**, and does not satisfy the user's goal of one integrated protected field.

The tested forms cannot simply be reclassified as "password input" by masking the characters: masking affects presentation, not whether submitted content passes through the MCP client/host.

## 4. Other UI proposals and why they do not close the gap yet

| Candidate | Native user experience | Secret isolation | Verified availability / verdict |
| --- | --- | --- | --- |
| **Claude Mods `ui.render/AbovePrompt`** | Single in-composer masked band in Claude Code | Mod handles raw entry, model receives only status if implemented correctly | **SUPPORTED in Claude**. Cannot copy the mod engine API into an unmodified Codex host |
| **Codex plugin + current AppKit** | Single separate masked macOS window | Local private child-process/writer, status-only MCP result | **OWNER-ACCEPTED Codex v0.6.0**, keep as baseline |
| **Codex `UserPromptSubmit`** | Can block bad prompt | Cannot create an inline safe entry control or restore draft via a public host UI API | **PARTIAL hook only**, not an answer to requested UX |
| **Codex MCP Form Elicitation** | Inline structured question (actual owner E2E) | In-band content available to client/tool/model | **SUPPORTED for nonsecret fields, PROHIBITED for real keys** |
| **MCP URL Elicitation** | Opens a trusted browser URL, no in-composer entry | Potentially out-of-band if properly authenticated and configured | Standards-supported; **no local/ChatGPT host implementation or trusted URL endpoint approved**. More complexity and another surface, not Claude-like UX |
| **MCP Apps iframe + direct backend HTTPS** | Optional inline UI in **ChatGPT**; other compatible hosts vary | Must explicitly audit whether bridge, telemetry, CSP, backend, auth and model context can access inputs; direct browser → controlled backend is a distinct channel | [OpenAI UI docs](https://developers.openai.com/plugins/build/chatgpt-ui) and [Quickstart](https://developers.openai.com/plugins/build/app-quickstart) document optional **ChatGPT iframe**. **No verified equivalent Codex Desktop composer widget**; not proven safe for credentials |
| **OpenAI Plugin Extensions: extended forms** | Structured forms in **ChatGPT** | Responses returned to tool; cannot assume secure storage/isolation | [Extensions docs](https://developers.openai.com/plugins/build/extensions) are scoped to ChatGPT; not a proved Codex password-input API |
| **Custom Codex CLI statusline** | Read-only-ish status/footer in **terminal** | No documented secure editable field | Not suitable for Codex Desktop secret entry |
| **OS Keychain / separate protected native AppKit panel** | Separate system-controlled step | Can avoid MCP tool argument exposure when written carefully | OS mechanisms possible; not inside composer. Existing AppKit already solves local capture |
| **Accessibility overlay, injection, patched binaries, fake prompt controls** | Could mimic inline UI visually | Host focus, clipboard and arbitrary app-input risks; unstable unsupported private integration | **REJECT** under accepted security/maintainability boundaries; visual imitation not equivalent to a trusted host extension |

MCP Apps UI is a promising *ChatGPT Web* product surface but **must be evaluated separately from Codex Desktop**. A bridge call that forwards `value` through `tools/call` or `ui/update-model-context` loses the desired no-model/no-client boundary. Direct browser-side HTTPS entry, if ever authorized, would need a fully reviewed server identity/session model and cannot be treated as secure merely because it is in an iframe.

## 5. Precise capability that is missing in Codex

The desired feature is **a host-rendered, plugin-owned, secure input control** in or immediately above the Codex Desktop composer, with semantics comparable to:

1. The model requests only the variable name, purpose, and *proposed* destination.
2. The host verifies the plugin's trusted identity and opens a masked secure-control component without embedding typed characters in the conversation or model tool arguments.
3. The control delivers the raw value **only** through a documented private local IPC/callback to an authorized plugin runtime; the host/extension does not place the raw data in transcript, general MCP Form results, telemetry or model-visible state.
4. The trusted writer verifies the canonical target, permission and Git tracking rules and safely stores the credential locally or after explicit separately authorized remote delivery.
5. The assistant receives name/status only, with explicit failure/cancel/skip results. A documented prompt guard can optionally block/rewrite a draft **before** model submission.

This is a **host/API feature request**, not a plugin-side patch that the currently documented APIs already implement. Privacy behavior would need explicit host-side validation, including no secret exposure in logs, accessibility caches, event traces, or model context. Requiring a non-secret approval Form first is not a substitute; it adds extra steps and does not give in-composer secret entry.

### Feasibility of implementing inside our own fork

We control the **MCP server, local writer, AppKit UI and skill**, not Codex Desktop's internal frontend event hooks. Without a documented trusted host extension point, a plugin cannot make the Codex composer render its own arbitrary secure control. Changing our MCP server or styling code does not grant that authority. The source and approved plugin runtime can be updated after an official API is available; adding a new web service or unsafe UI injection now would violate the agreed minimum-mechanism approach.

## 6. Recommendations and evidence gates

**P0 — DO NOT IMPLEMENT:** password/API-key input through MCP Form or an equivalent ordinary value-bearing MCP tool argument. This fails the normative protocol rule and the actual observed visibility test.

**P1 — KEEP:** existing `secret-drop-codex@secret-drop-tkrv` v0.6.0 AppKit, no upgrade, no model, no new service. It is already accepted and has independently stronger tested local-writer controls than the original Claude mod in several threat-model areas.

**P2 — WATCH AS A CAPABILITY GATE, not a new engineering epic:** official Codex support for a trusted plugin-provided secure inline user-input component with a private callback/channel and pre-model draft handling. Evidence threshold: public spec/API + exact host version + isolated dummy-key E2E with no model-visible bytes + independent security review. An issue/request could describe this API contract, but no issue/PR was opened by this research.

**P3 — SEPARATE IF EVER REQUESTED:** ChatGPT Web MCP Apps secure-out-of-band design, where the user has explicitly accepted a web-hosted component and an identity-bound backend. It is not current scope and is not proven equivalent to Claude Code.

## Primary sources

1. [Claude Code Mods reference — UI render sites, input controls, prompt and filesystem APIs](https://code.claude.com/docs/en/plugins/mods/reference)
2. [Claude Code Mods — official getting started](https://claude.dev/blog/getting-started-with-claude-code-mods/)
3. [Upstream Secret Drop register.tsx](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx) and [tests](https://github.com/aislam23/secret-drop/blob/main/tests/secret-drop.test.tsx)
4. [Codex plugin parser — raw manifest](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manifest.rs)
5. [Codex UserPromptSubmit hook implementation](https://github.com/openai/codex/blob/main/codex-rs/hooks/src/events/user_prompt_submit.rs), [Hooks docs](https://learn.chatgpt.com/docs/hooks)
6. [Codex App Server and Elicitation](https://learn.chatgpt.com/docs/app-server), [MCP elicitation.rs](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/elicitation.rs)
7. [OpenAI Plugins architecture](https://developers.openai.com/plugins/concepts/plugins), [MCP Apps UI](https://developers.openai.com/plugins/build/chatgpt-ui), [Extensions](https://developers.openai.com/plugins/build/extensions)
8. [MCP Elicitation 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation), [MCP SDK warnings](https://ts.sdk.modelcontextprotocol.io/v2/servers/elicitation)
9. [Codex plugin credential-config feature request #36854](https://github.com/openai/codex/issues/36854) (issue evidence, **not** a shipped feature)
10. [Codex CLI statusline sample](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/create-statusline/SKILL.md)

**Disposition:** Research completed, no accepted code change, no deployment. Do not claim that Codex cannot possibly render such a control; claim only that no *currently documented, trusted third-party mechanism matching the Claude Mods API* was found in the checked surfaces. Preserve this research in the branch, do not merge until a distinct implementation/design approval.
