# Secret Drop MCP URL-mode pilot plan

Owner: shzk/secret-drop. Branch: research/mcp-url-mode-pilot, based on research/mcp-elicitation-20261121.
Baseline: accepted Secret Drop 0.6.0. Related completed Form investigation: TickTick 6b01a4b48f0887ff0a4c82e8.

1. Add an isolated stdio fixture for MCP 2025-11-25 URL elicitation and a disposable loopback page. The page contains a button for a fixed public marker. The MCP response contains state only. Keep the existing Form probe and production plugin out of this change.
2. Exercise a synthetic client over stdio and real HTTP. Check capability rejection, consent before browser action, cancel, one completed write, and rejection of replay. Run existing impacted research tests.
3. Try routing on an available Codex app-server. Keep client/protocol evidence distinct from Desktop and Work UI evidence. Record environment blockers with the reproduction command.
4. Verify branch content in GitHub. Document the remaining Desktop and Work acceptance gates alongside the fixture.

The pilot accepts no user text or credentials and creates no persistent service, global configuration, or user-workspace file. A live host must show the URL and obtain consent before opening it. A tool result reporting a write must follow a successful write by the fixture, not mere URL acceptance.
