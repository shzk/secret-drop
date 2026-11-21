# Codex one-card Secret Drop — current implementable options, private-channel hypothesis, and decision gates

**Date:** 2026-11-21. **Status:** Research decision, **not** release approval. **Owner:** [shzk/secret-drop](https://github.com/shzk/secret-drop), branch `research/mcp-elicitation-20261121`; TickTick `6b01dc458f08fe236af6b521`.
**Earlier investigations:** [Claude Code Mods vs Codex](2026-11-21-claude-mods-vs-codex-secure-input.md), [Codex Form UI PASS](2026-11-21-codex-form-host-pilot.md), [public marker vs safe intake](2026-11-21-public-marker-vs-secure-intake.md).
**Authoritative baseline:** the reviewed `secret-drop-codex@secret-drop-tkrv` `0.6.0` in fork `main` and the installed Mac app/CLI; do not edit, install, merge, or expose real secrets during this research.

## Executive conclusion — updated since earlier Claude comparison

1. **Claude Code Mod's exact API remains unavailable to third-party Codex plugins:** Claude implements `ui.render / AbovePrompt / Input onInput` inside the client and a `prompt.fill` method. Codex has no documented equivalent open composer-render callback for a general plugin.
2. **But Codex is not entirely without third-party inline UI.** The upstream Codex runtime already recognizes MCP Apps `ui://` resources, `mcpAppResourceUri` and `mcpAppUi { resourceUri, preferredModelDisplayMode: inline|fullscreen }`. The feature flag `enable_mcp_apps` exists. This **could** show a single inline widget next to a tool result, although it would not be Claude's `AbovePrompt` band.
3. **The critical missing proof is a trusted private delivery path for the typed credential**, not rendering a masked input. Standard MCP Form returns data through the client/tool and is normatively forbidden for API keys/passwords. MCP Apps HTML can host an `<input type=password>` as ordinary web UI, but sending it via `app.callServerTool`, `tools/call`, `ui/update-model-context` or a standard Form **does not establish non-exposure to the host, logs or model**.
4. **Best candidate for a one-card UI on this Mac:** conditional experimental MCP Apps iframe + browser-side `fetch` directly to a short-lived, authenticated, **loopback-only** endpoint owned by the existing Secret Drop local process and audited writer. The value must never become an MCP tool argument or model-visible response. This is a **design hypothesis** that requires explicit testing of Codex Desktop support, iframe CSP/CORS/loopback permissions and lifecycle. It is not yet supported/secure by evidence.
5. **Recommended product decision now:** keep the accepted standalone AppKit UI; do not ship or merge the iframe design until all specific no-key and fake-key gates below are observed, then reviewed independently. There is no justification for an always-on service, database, remote endpoint, or a second confirmation window.

## Evidence levels and current installed environment

| Finding | Evidence level | What it actually establishes |
| --- | --- | --- |
| Claude supports a mod-owned `AbovePrompt` with `Input` and direct edit callback | **Source + Claude official API** | [upstream register.tsx](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx#L495), [Claude Mods reference](https://code.claude.com/docs/en/plugins/mods/reference). Mod receives user input in its runtime; the model gets saved-status only |
| Codex plugin manifest supports skills/MCP/apps/hooks/interface | **Codex source** | [manifest parser](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manifest.rs); no general `AbovePrompt` render hook is declared |
| Codex core extracts MCP Apps display metadata | **Codex source** | [MCP tool metadata](https://github.com/openai/codex/blob/main/codex-rs/core/src/mcp_tool_call.rs) and [McpAppUi type](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/items.rs) understand `inline` / `fullscreen` preferences |
| Codex feature `enable_mcp_apps` exists but defaults off and is under development | **Source + real Mac readback** | [feature registry](https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs). `codex features list` on local CLI `0.163.0`: `enable_mcp_apps = false`, `credential_masking = false`, `mcp_2026_07_28 = false`. Do **not** infer the Codex Desktop app's own build/enablement from the CLI; its bundle version was not read back |
| Third-party Codex Desktop inline MCP Apps rendered for at least one user | **External user report, not our host acceptance** | [openai/codex issue #55167](https://github.com/openai/codex/issues/55167), opened 2026-10-19, reports working iframe UI on Desktop 26.1013.40934 while **app-provided tools** were not model-discoverable. Conversely [issue #21019](https://github.com/openai/codex/issues/21019) documents older non-rendering Desktop builds. Product behavior appears version/flag-dependent |
| Inline nonsecret MCP Form works for the owner | **Our actual Desktop screenshot + app-server test** | Successfully rendered and accepted fake destination, but this is **Form Elicitation**, not MCP Apps. It does not prove the new iframe or loopback path |
| MCP Form content is not a secret channel | **Normative protocol + reproducible local marker test** | [MCP spec](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation), [TS SDK warning](https://ts.sdk.modelcontextprotocol.io/v2/servers/elicitation); our public synthetic marker returned in MCP tool output |
| Custom MCP Apps iframe can make browser-side requests with CSP | **MCP Apps reference and standards, not Codex-local E2E** | [MCP Apps CSP/CORS](https://github.com/modelcontextprotocol/ext-apps/blob/main/docs/csp-cors.md) documents `connectDomains` and CORS, including localhost during development; [OpenAI UI docs](https://developers.openai.com/plugins/build/chatgpt-ui) document optional UI **in ChatGPT**, across compatible hosts. **Does not prove loopback requests are allowed in Codex Desktop** |
| Browser isolation may block iframe → loopback | **Chromium guidance; Codex host not verified** | [Chrome Local Network Access](https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access): `loopback-network` permissions and cross-origin iframe delegation can be required. Distinguish generic Chromium policy from actual Codex Desktop WebView |
| `credential_masking` exists in Codex | **Source + installed flag false** | [feature registry](https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs), [network proxy credential broker](https://github.com/openai/codex/blob/main/codex-rs/network-proxy/src/credential_broker.rs), [provider config](https://github.com/openai/codex/blob/main/codex-rs/network-proxy/src/credential_broker/provider_config.rs) mask recognized environment credentials and inject approved headers to configured URL prefixes; they do **not** create an embedded user input UI |
| Privileged `openai/userVerification` exists | **Codex source / restricted authorization** | [user verification routing](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/user_verification_elicitation.rs) permits only **host-owned Apps** source; an arbitrary third-party MCP cannot trigger it merely by copying metadata |

**Version caveat:** The actual installed Mac CLI is `codex-cli 0.163.0`. Its generated app-server protocol schema includes references to `McpAppUi`, but **the installed desktop renderer has not been separately tested for MCP Apps**. The current public repo main may contain newer source than the installed binary. Keep this distinction in future claims.

## Candidate design A — one inline MCP Apps form, private local submission

*This is our only promising route to the user-desired **single in-chat input** without modifying Codex Desktop. It is not proven yet.*

```text
Agent asks: TEST_SECRET_ALPHA + nonsecret proposed destination
                       |
       MCP tool advertises _meta.ui.resourceUri
                       |
          Codex Desktop renders MCP App
      (masked input, target, consent in ONE inline card)
                       |
 User clicks Save; JS sends value via direct fetch, NOT MCP bridge
                       |
   ephemeral 127.0.0.1:<random-port> endpoint
         owned by existing local Secret Drop process
                       |
 trusted native writer validates destination, owner, 0600, git ignore
                       |
        MCP tool result to model: NAME + STATUS only
```

### What must be reused, what is genuinely new

- **Reuse:** the accepted `request_secret` input validation, canonical-project and `env_file` constraints, gitignore checks, atomic writer and post-write verification in v0.6.0. No reimplementation of dotenv/GitHub saving.
- **Reuse:** existing plugin/MCP registration and user-visible result/status semantics. The existing AppKit remains fallback, not a second stage.
- **New minimum mechanism:** a UI resource that renders inline and a **short-lived, local-only** receive endpoint, preferably owned by the same local MCP process and started only during this request. Browsers cannot send HTTP directly to a subprocess's stdin; without the endpoint they would have to use the MCP bridge and lose the desired boundary.
- **Do not add:** persistent daemon, hosted portal, cloud sync, new database, separate service/API product, web tunnel, Keychain-vault project, paid model or another agent orchestrator.

### Security preconditions — fail closed

1. **Codex host must render this exact `ui://` resource** with a protected DOM in a new chat, at the supported host build/version, without accessibility overlays or internal app binary patches. Source recognition alone is insufficient.
2. **Iframe local network must work:** exact `connectDomains` whitelist (specific loopback origin/port), CORS and required browser Local Network Access permission. Verify if the actual Codex embedded browser honors or denies it. No wildcard CSP/CORS and no sending credentials over mixed public endpoints.
3. **Trusted local destination:** bind only `127.0.0.1` or `[::1]`, require exact Host and Origin checks, resist DNS rebinding and CSRF, no token in URLs, and short session TTL with a one-time request identity. A nonce embedded in an MCP-readable UI resource is **not by itself** a sound protection against a model that can read that resource; apply local human confirmation, authority-bound session binding and strict destination allowlist.
4. **No raw secret through the MCP host bridge:** no `callServerTool(secret)`, `tools/call(value)`, `app.sendMessage(secret)`, `ui/update-model-context(secret)`, telemetry, console logging, analytics, localStorage, URL query parameters or GitHub PRs. The iframe's JS and direct request necessarily handle the plaintext in the local UI/web process; do not claim host-process-level zero knowledge without audit.
5. **Model may still read a saved file through other tools** unless separately restricted. This design prevents planned ingestion of the key via conversation / tool results, **not all filesystem exfiltration**. Credentials should never be exposed to plugin authors not trusted by the user.
6. **Cancellation and failures:** always close endpoint and erase references; no stored value after rejection or cancel; timeout and stale/hijacked port fail closed. GitHub external destination still requires separate actual human authorization.
7. **Signing/dependencies:** pinned UI scripts/assets, CSP without arbitrary external JS, reproducible code, security review, no untrusted modifications of the resource between user review and submission.

### Important feasibility unknowns

- Current Mac Codex CLI has `enable_mcp_apps = false`; changing a process-scoped CLI flag is **not proof** that the graphical Desktop will render the UI. An experimental Desktop flag may be absent/unavailable or only effective on its own app-server.
- A sandboxed MCP App iframe may not have permission to reach `127.0.0.1` or may lack a stable origin for CORS, even when `connectDomains` declares that address.
- The iframe may only be able to use the MCP Apps bridge in this host, which is disallowed for actual key bytes under the desired privacy boundary.
- An unsupported MCP UI renderer or an un-auditable host may render a preview but not provide a trustworthy private-channel contract.
- The owner would still have to trust the plugin's own frontend HTML and JavaScript, just as in Claude Mods. "No model value" is narrower than "not accessible to the app host."

## Candidate designs B–G: decisive comparisons

| Candidate | One in-chat field? | Can deliver actual values outside ordinary MCP responses? | Current verdict |
| --- | --- | --- | --- |
| **A. MCP Apps iframe + direct local receive endpoint** | **Potentially yes** (inline tool result, not above composer) | **Potentially** using direct browser fetch, subject to host/CSP/loopback and audit | **RESEARCH PRIORITY #1**: prove UI and direct network with public dummy first |
| **B. Claude's exact `ui.render/AbovePrompt` API in Codex** | Not available to third-party plugins | Not applicable | No documented equivalent; cannot port host API by copying TypeScript |
| **C. Native Codex `tool/requestUserInput`** | Built-in question, not arbitrary editor | Answer flows through Codex app-server and model/tool control | Does not solve secure key input; not a public password-input plugin API |
| **D. Standard MCP Form with `type=password` or masking** | Yes, but **unsuitable** | **No**: content is ordinary elicitation data | **REJECT** (normative prohibition and local observed marker path) |
| **E. MCP URL Elicitation** | No, opens external browser/site | Yes, if correctly designed out of band | Standards-supported; adds external UX/identity/HTTPS service; not user goal |
| **F. AppKit v0.6.0** | No, separate macOS dialog | **Yes**, local process and private pipe | **KEEP / PRODUCTION BASELINE** |
| **G. Codex browser-auth/userVerification** | Host-defined confirmation/identity | Protected for **host-owned** Apps only | **NOT FOR US**; source explicitly cancels non-host-owned attempts |
| **H. Codex `credential_masking` broker** | No | Intended to protect downstream network usage of existing env credentials | Under development/off; **complementary** to secret intake, not replacement |
| **I. CLI custom statusline** | Footer only, no password entry | Not relevant | **REJECT for Desktop UX** |
| **J. Accessibility overlay, plugin UI injection, patched Desktop binary** | Visually imitate | Unstable; worsens host trust/audit | **REJECT**, violates accepted maintainability/security boundaries |

**MCP Apps app-provided tools:** [issue #55167](https://github.com/openai/codex/issues/55167) reports a working iframe but app-provided tools not discoverable by the model. That is not a blocker for a fully direct browser-to-local value submission (which must **not** become a model tool call), but it reinforces that host support is incomplete/version-specific.

### A second possible product gain: credential use, not collection

Codex's future `credential_masking` network proxy broker supports declarative providers with environment names/patterns and URL prefix binding. If deployed and independently verified, it could reduce raw credential exposure to shell/network workflows **after** Secret Drop's intake. It cannot place an inline input in the GUI; it is currently under development and off on this Mac. Do not enable as a hidden dependency of a Secret Drop UI update.

## Minimal next investigation if owner explicitly approves implementation/testing

**Do not start a long project to find out whether the idea is even feasible.** Reuse this research branch. Four strict gates, stopping at the first failure:

| Gate | Tiny observable test, only public dummy values | Success evidence / stop |
| --- | --- | --- |
| **1. Renderer** | Separate synthetic MCP Apps tool advertises `ui://secret-drop-probe/index.html` with inline preferred mode; one static HTML card, no input of real keys | Actual **Codex Desktop screenshot** of the rendered custom iframe. Source reading or app-server metadata alone = insufficient. If `enable_mcp_apps` needs changing user's global settings or unstable Desktop flags, get explicit approval + reversible backup; otherwise STOP |
| **2. Local browser connection** | UI button makes a **single harmless health request** to an ephemeral `127.0.0.1:<port>` endpoint with exact CSP/CORS. No value at all | Observe request in both browser UI and local listener, no external network or prompt injection; if iframe loopback blocked/host denies permission, STOP |
| **3. Dummy secret boundary** | Locally entered **public fake string**, direct `fetch` to endpoint; trusted writer into **disposable project** only | Local readback `0600` and status; the fake literal must be absent from Codex model-visible tool args/results, transcript and accessible app logs in the tested host. No actual secret |
| **4. Acceptance** | Cancel/decline, expired/mismatched session, malicious origin, path substitution and port reuse; independent security review | Evidence-based PASS, otherwise fallback to existing v0.6 AppKit and decline merge; no production rollout or host patch |

**One actual user interaction only if Gate 1 is ready:** a screenshot of the static MCP Apps inline card in Codex Desktop. Avoid asking for repeated experiments with Form Elicitation; its limits are already measured. Do not conflate conditional browser UI with guaranteed Codex support.

## Final implementation recommendation

- **Now:** do nothing to accepted Secret Drop `0.6.0`. The existing AppKit already solves secure human input without a server.
- **Research candidate worth one bounded test:** native **MCP Apps inline UI**. If current Codex Desktop can render it, then evaluate one minimal private local transfer mechanism. The critical learning is that **MCP Apps web UI and MCP Form Elicitation are different protocols/trust boundaries**.
- **If Gate 1 or 2 fails:** do not add multiple popups, overlays, a cloud service, or a Keychain wrapper merely to approximate the target UI. Preserve failure in this branch and revisit when Codex supports a verified trusted UI host.
- **If Gates 1–4 pass:** propose a separate reviewed Codex adapter feature PR based on the already-owned server/writer with optional fallback to AppKit; do not merge the research tests themselves into production without accepted code review.

## Primary public sources

1. [Codex plugin architecture and optional MCP Apps UI](https://developers.openai.com/plugins/concepts/plugins); [OpenAI MCP UI guide](https://developers.openai.com/plugins/build/chatgpt-ui), [quickstart](https://developers.openai.com/plugins/build/app-quickstart)
2. [Codex MCP tool metadata](https://github.com/openai/codex/blob/main/codex-rs/core/src/mcp_tool_call.rs); [MCP app display type](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/items.rs); [app-server event metadata](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
3. [Codex feature flags](https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs) (`enable_mcp_apps`/`credential_masking` under development and disabled by default)
4. [Codex user-verification routing](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/user_verification_elicitation.rs), [privileged form test](https://github.com/openai/codex/blob/main/codex-rs/core/tests/suite/mcp_subagent_elicitation.rs)
5. [MCP Apps spec](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx); [CSP/CORS](https://github.com/modelcontextprotocol/ext-apps/blob/main/docs/csp-cors.md)
6. [Chromium Local Network Access and cross-origin iframe delegation](https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access) (generic Chromium, not verified in Codex Desktop)
7. [MCP Elicitation security rule](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation); [SDK warning](https://ts.sdk.modelcontextprotocol.io/v2/servers/elicitation)
8. [Codex GUI issue #21019](https://github.com/openai/codex/issues/21019) (older non-rendering app version) and [#55167](https://github.com/openai/codex/issues/55167) (Oct 2026 reporter had working iframe but app-provided tools unavailable)
9. [Codex experimental credential broker](https://github.com/openai/codex/blob/main/codex-rs/network-proxy/src/credential_broker.rs) and [provider config](https://github.com/openai/codex/blob/main/codex-rs/network-proxy/src/credential_broker/provider_config.rs)
10. [Claude Mods reference](https://code.claude.com/docs/en/plugins/mods/reference) and [original Secret Drop](https://github.com/aislam23/secret-drop/blob/main/hooks/register.tsx)

**Disposition:** source research complete; current feature flags read-only; no user-global config changed; no model, real keys, external service, app bundle mutation, host flag change or release/merge. All feature and security claims for the proposed iframe path remain **conditional until actual host evidence**.
