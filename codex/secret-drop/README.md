# Secret Drop for Codex — native masked macOS dialog

**Version 0.4.0 (Desktop user acceptance pending).** Upstream: [aislam23/secret-drop](https://github.com/aislam23/secret-drop), MIT, commit `a54d43a`, original Claude plugin `0.2.2`. This is an independent Codex adaptation; the Claude plugin is unchanged.

## Current input workflow

- Codex invokes the bundled local MCP tool `secret-drop-local.request_secret` with either one `name` or a `secrets` array (1–12 names plus optional non-secret hints), an existing canonical `project_dir`, and optional destination.
- One independent **native macOS AppKit dialog** displays each **burgundy-highlighted monospaced name on the LEFT** and an `NSSecureTextField` **on the RIGHT**, in the same row.
- **Save** stores **only fields actually filled in**. Empty or whitespace-only fields are individually **skipped** and named in the status returned to Codex; they do not cancel the others. All blank fields result in no write and an explicit status. **Cancel** writes nothing.
- Entered values are saved together in one atomic update to project `.env`, with mode 0600. Existing entries for skipped names remain unchanged; `skipped` means *not entered in this request*, not *absent in file*.
- GitHub Actions Secrets storage is optional and must be explicitly authorized; it passes each entered value to `gh secret set` on stdin. Multi-key GitHub saves are **not atomic**; per-variable failed/succeeded and skipped names are reported.
- The model receives **names and save/skip/error statuses only**, never the values. No real secrets in tests. The optional Codex `UserPromptSubmit` pattern guard is an independent heuristic defense after user hook trust.

## UI limitation vs original Claude

Claude Code exposes `AbovePrompt`. Codex Desktop has no **verified supported** composer-adjacent custom plugin input surface. The dialog **remains an independent macOS window**; we do not use overlays attached through Accessibility, private API calls, or binary modifications. This is a documented limitation, not an accepted claim of identical UI.

## Installation / upgrade on Mac

```sh
codex plugin marketplace add shzk/secret-drop --ref feat/codex-secret-drop
codex plugin marketplace upgrade secret-drop-tkrv
codex plugin remove secret-drop-codex@secret-drop-tkrv
codex plugin add secret-drop-codex@secret-drop-tkrv
```

Start a fresh Codex Desktop session to refresh MCP discovery. Request `TEST_ONE` and `TEST_TWO` in an isolated test project. To check partial saving, fill only `TEST_ONE`, then Save: it should report `TEST_ONE` saved and `TEST_TWO` skipped without printing dummy values. `stat -f '%Sp' .env` must show `-rw-------`. Do not `cat` real secret files. Cancel test must not modify `.env`.

The local stdio MCP process depends on system Python and macOS Swift/AppKit, with optional authenticated `gh` for explicit GitHub writes. It compiles a SHA-keyed private native dialog executable locally. No public listener/service or paid API is introduced. Tool registration/compile PASS is not a substitute for actual user-side Desktop E2E.
