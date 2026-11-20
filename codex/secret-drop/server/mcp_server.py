#!/usr/bin/env python3
"""Bundled local MCP server. The only user secret is entered in macOS's hidden-answer dialog.

Nothing secret is written to stdout/stderr; stdout is JSON-RPC only.
"""
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
from secret_drop import NAME, REPO, write_env, write_github, quote_env  # noqa: E402

PROTOCOL = "2025-06-18"
TOOL = {
    "name": "request_secret",
    "description": (
        "Open a native macOS masked modal for a human to enter a credential for a single "
        "environment variable. DO NOT ask for the value in chat or shell. It is stored "
        "locally in project_dir/.env (0600) or optionally GitHub Actions Secrets, and "
        "NEVER returned to the model. Call when the human asks to provide a credential. "
        "The modal shows the variable name and exact destination; user confirms saving."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Environment variable name, e.g. OPENAI_API_KEY. Never its value.",
                "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
            },
            "project_dir": {
                "type": "string",
                "description": "Existing absolute local project directory under the user's home, not a file.",
            },
            "destination": {
                "type": "string",
                "enum": ["env", "github", "both"],
                "default": "env",
                "description": "Save to project .env by default, or explicitly selected GitHub Actions Secrets.",
            },
            "github_repo": {
                "type": "string",
                "description": "Required for github/both: explicitly selected owner/repository.",
            },
        },
        "required": ["name", "project_dir"],
        "additionalProperties": False,
    },
}

# Static AppleScript. Never interpolates secret/variable/path into source or command line.
# The input arrives through a macOS native hidden-answer text field.
MAC_DIALOG = r'''
set keyName to system attribute "SECRET_DROP_VARIABLE_NAME"
set targetName to system attribute "SECRET_DROP_DESTINATION"
set dialogMessage to "Enter secret for " & keyName & return & return & "Save to: " & targetName & return & "The value will NOT be sent to Codex."
set answerDialog to display dialog dialogMessage default answer "" with hidden answer buttons {"Cancel", "Save"} default button "Save" with title "Secret Drop"
return text returned of answerDialog
'''


class Cancelled(Exception):
    pass


def native_dialog(name: str, target: str) -> str:
    if platform.system() != "Darwin":
        raise RuntimeError("native macOS dialog unavailable")
    env = os.environ.copy()
    env["SECRET_DROP_VARIABLE_NAME"] = name
    env["SECRET_DROP_DESTINATION"] = target
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", MAC_DIALOG],
            env=env,
            capture_output=True, text=True, timeout=300, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Cancelled() from None
    if result.returncode != 0:
        # Cancel and AppleScript failures are both fail-closed, no stderr to model.
        raise Cancelled()
    value = result.stdout.removesuffix("\n")
    if not value:
        raise Cancelled()
    return value


def validate(args: object) -> tuple[str, Path, str, str | None, str]:
    if not isinstance(args, dict):
        raise ValueError("invalid parameters")
    name = args.get("name")
    destination = args.get("destination", "env")
    repo = args.get("github_repo")
    raw_root = args.get("project_dir")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("invalid environment variable name")
    if destination not in ("env", "github", "both"):
        raise ValueError("invalid save destination")
    if name.upper().startswith("GITHUB_") and destination in ("github", "both"):
        raise ValueError("GitHub Secrets disallows GITHUB_ prefix")
    if destination in ("github", "both") and (not isinstance(repo, str) or not REPO.fullmatch(repo)):
        raise ValueError("explicit owner/repo is required for GitHub Secrets")
    if destination == "env" and repo is not None:
        raise ValueError("unexpected GitHub repository")
    if not isinstance(raw_root, str) or not raw_root or not Path(raw_root).is_absolute():
        raise ValueError("project_dir must be an absolute path")
    given = Path(raw_root)
    if given.is_symlink() or not given.is_dir() or given.resolve() != given:
        raise ValueError("project_dir must be an existing canonical directory, not a symlink")
    root = given.resolve()
    home = Path.home().resolve()
    if root == home or home not in root.parents:
        raise ValueError("project_dir must be an existing directory within the user's home")
    if destination in ("env", "both"):
        output_file = root / ".env"
        if output_file.is_symlink() or (output_file.exists() and not output_file.is_file()):
            raise ValueError("unsafe .env path")
    if destination == "env":
        target = str(root / ".env")
    elif destination == "github":
        target = "GitHub Actions Secrets: " + repo
    else:
        target = str(root / ".env") + " and GitHub Actions Secrets: " + repo
    return name, root, destination, repo, target


def request_secret(args: object) -> dict:
    try:
        name, root, destination, repo, target = validate(args)
    except (ValueError, OSError):
        return {"content": [{"type": "text", "text": "Secret Drop: invalid or unsafe request; nothing saved."}], "isError": True}
    try:
        value = native_dialog(name, target)
    except Cancelled:
        return {"content": [{"type": "text", "text": "Secret Drop: user cancelled or native dialog unavailable. Nothing saved."}], "isError": True}
    except RuntimeError:
        return {"content": [{"type": "text", "text": "Secret Drop: macOS desktop is required. Nothing saved."}], "isError": True}
    try:
        if destination in ("env", "both"):
            # Check quoting errors before any write or GitHub side effect.
            quote_env(value)
            write_env(root, name, value)
        gh_ok = (destination == "env") or write_github(name, repo, value)
        if not gh_ok:
            text = "Secret Drop: GitHub save failed; local .env " + ("was saved." if destination == "both" else "was not used.")
            return {"content": [{"type": "text", "text": text}], "isError": True}
        text = "Secret Drop: " + name + " saved to " + target + ". Secret value was not sent to the agent."
        return {"content": [{"type": "text", "text": text}], "isError": False}
    except (ValueError, OSError, UnicodeError):
        return {"content": [{"type": "text", "text": "Secret Drop: could not save the secret. Nothing disclosed."}], "isError": True}
    finally:
        value = None


def handle(request: dict) -> dict | None:
    method = request.get("method")
    msg_id = request.get("id")
    if msg_id is None:  # MCP notifications have no response
        return None
    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "secret-drop-local", "version": "0.2.0"},
            "instructions": "Call request_secret to show a native macOS masked modal. Never request, read, or print secret values.",
        }
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        params = request.get("params") or {}
        if params.get("name") != "request_secret":
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Unknown tool"}}
        result = request_secret(params.get("arguments"))
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def main():
    for raw in sys.stdin.buffer:
        try:
            msg = json.loads(raw)
            if not isinstance(msg, dict):
                continue
            response = handle(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except (ValueError, TypeError, json.JSONDecodeError):
            # Do not echo the untrusted request (potential secrets).
            continue


if __name__ == "__main__":
    main()
