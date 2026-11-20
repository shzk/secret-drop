# Secret Drop for Codex (experimental adapter)

Upstream: [aislam23/secret-drop](https://github.com/aislam23/secret-drop), MIT license, commit `a54d43a`, Claude plugin `0.2.2`.

This is an independent, narrower Codex adapter; it is **not** a copy of Claude's masked composer UI. It provides a `UserPromptSubmit` pattern guard and a local interactive terminal helper. GitHub Secrets is strictly opt-in. Neither a regex guard nor a plugin promises perfect data-loss prevention.

## Installation

1. `codex plugin marketplace add shzk/secret-drop --ref feat/codex-secret-drop`
2. `codex plugin add secret-drop-codex@secret-drop-tkrv`
3. Open Codex and review/trust the hook using `/hooks`; do not bypass hook trust.

## Saving secrets

In your own local interactive terminal, from the intended project root:

- `python3 PATH_TO_PLUGIN/bin/secret_drop.py set OPENAI_API_KEY`: write protected `.env`
- `python3 PATH_TO_PLUGIN/bin/secret_drop.py set OPENAI_API_KEY --github owner/repo`: `.env` and GitHub Actions Secrets
- `python3 PATH_TO_PLUGIN/bin/secret_drop.py set OPENAI_API_KEY --github owner/repo --no-env`: GitHub Actions Secrets only

The helper refuses non-interactive input, symlink/committed `.env`, and multiline values. It is never called by an agent. The agent must not read the resulting secret file. Codex CLI/Desktop trust/load readback and local terminal test are separate verification gates. ChatGPT Web cannot intercept its composer using a local hook.
