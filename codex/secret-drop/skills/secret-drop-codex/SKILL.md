---
name: secret-drop-codex
description: Use when Codex needs an API key, token, password, or GitHub Actions secret without receiving its value in chat.
---

# Secret Drop for Codex

This plugin blocks some recognizable credentials in **user prompts** through a Codex UserPromptSubmit hook, if and only if that hook is enabled and trusted. It is not a complete DLP, credential manager, or the original Claude inline masked-input UI.

When a credential is needed, ask the human to run the bundled `bin/secret_drop.py` helper **from their own interactive local terminal** in the intended project root. Never ask the human to paste a credential into a Codex prompt, tool argument, shell command, Git or an agent message. The helper uses local masked input (Python getpass), writes a protected local `.env` if selected, and optionally writes a GitHub Actions secret when `--github owner/repo` is expressly supplied. **Do not invoke this helper on behalf of the model** or inspect the saved secret.

The human must review/trust bundled hooks through Codex `/hooks` before relying on the prompt guard. An installed plugin does not prove the guard ran. Pattern matching is incomplete; false negatives and positives are possible.

**Security boundaries:** An agent with ordinary filesystem access might read `.env`; model/tool permissions and OS ACLs are separate defenses. Never verify by printing a real key. Use fake credentials for tests. ChatGPT Web does not run this local hook.
