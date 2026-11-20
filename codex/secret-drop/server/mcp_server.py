#!/usr/bin/env python3
"""Local Codex MCP: secure native macOS multi-secret prompt, status-only results.

MCP stdout is JSON-RPC only. Secret values pass solely from the short-lived
local AppKit child process through a private pipe to the local writer.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
from secret_drop import NAME, REPO, write_env_batch, write_github, quote_env  # noqa: E402

PROTOCOL = "2025-06-18"
TOOL = {
    "name": "request_secret",
    "description": (
        "Ask the human for one OR MULTIPLE credentials in ONE native macOS masked "
        "input window. Use 'secrets': [{name:'OPENAI_API_KEY'}, {name:'SERVICE_TOKEN'}] "
        "for multiple variables, or legacy 'name' for one. Names use a monospaced "
        "font; each value has its own masked input. DO NOT request or supply the "
        "values in chat, shell, or MCP arguments. Store in project_dir/.env (0600) "
        "and optionally explicitly authorized GitHub Actions Secrets. The model "
        "receives ONLY variable names and save status. The window is a separate "
        "native macOS modal, not an overlay attached to Codex composer."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "For ONE key only; e.g. OPENAI_API_KEY (NOT its value).",
                "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
            },
            "secrets": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "description": "For MULTIPLE keys in one dialog. Pass names and optional short non-secret hints only.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
                        "hint": {"type": "string", "maxLength": 120},
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
            },
            "project_dir": {
                "type": "string",
                "description": "Existing canonical absolute local project directory inside user's home.",
            },
            "destination": {
                "type": "string",
                "enum": ["env", "github", "both"],
                "default": "env",
                "description": "Local .env by default; GitHub Secrets ONLY with explicit user authorization.",
            },
            "github_repo": {
                "type": "string",
                "description": "Required for GitHub destinations, explicit owner/repository.",
            },
        },
        "required": ["project_dir"],
        "additionalProperties": False,
    },
}


class Cancelled(Exception):
    pass


def validate(args: object) -> tuple[list[dict[str, str]], Path, str, str | None, str]:
    if not isinstance(args, dict) or set(args) - {
        "name", "secrets", "project_dir", "destination", "github_repo"
    }:
        raise ValueError("invalid parameters; do not include secret values")
    if ("name" in args) == ("secrets" in args):
        raise ValueError("provide exactly one of name or secrets")
    raw = ([{"name": args["name"]}] if "name" in args else args["secrets"])
    if not isinstance(raw, list) or not 1 <= len(raw) <= 12:
        raise ValueError("invalid variable count")
    fields: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) - {"name", "hint"}:
            raise ValueError("invalid secret field; values are forbidden")
        name = item.get("name")
        hint = item.get("hint", "")
        if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 128:
            raise ValueError("invalid variable name")
        if not isinstance(hint, str) or len(hint) > 120:
            raise ValueError("invalid hint")
        if name in seen:
            raise ValueError("duplicate variable name")
        seen.add(name)
        fields.append({"name": name, "hint": hint})
    destination = args.get("destination", "env")
    repo = args.get("github_repo")
    if destination not in ("env", "github", "both"):
        raise ValueError("invalid save destination")
    if destination in ("github", "both"):
        if not isinstance(repo, str) or not REPO.fullmatch(repo):
            raise ValueError("explicit owner/repo is required for GitHub Secrets")
        if any(f["name"].upper().startswith("GITHUB_") for f in fields):
            raise ValueError("GitHub Secrets disallows GITHUB_ prefix")
    elif repo is not None:
        raise ValueError("unexpected GitHub repository")
    raw_root = args.get("project_dir")
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
        target_file = root / ".env"
        if target_file.is_symlink() or (target_file.exists() and not target_file.is_file()):
            raise ValueError("unsafe .env path")
    if destination == "env":
        target = str(root / ".env")
    elif destination == "github":
        target = "GitHub Actions Secrets: " + repo
    else:
        target = str(root / ".env") + " and GitHub Actions Secrets: " + repo
    return fields, root, destination, repo, target


def dialog_binary() -> Path:
    """Compile the audited local Swift source once per source hash; no network."""
    source = Path(__file__).resolve().parent.parent / "gui" / "SecretDropDialog.swift"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:20]
    cache = Path.home() / ".cache" / "secret-drop-codex-dialog"
    if cache.is_symlink():
        raise RuntimeError("unsafe GUI cache")
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    executable = cache / ("secret-drop-dialog-" + digest)
    if executable.is_file() and not executable.is_symlink() and os.access(executable, os.X_OK):
        return executable
    temp = cache / (".building-" + str(os.getpid()))
    try:
        compiled = subprocess.run(
            ["/usr/bin/swiftc", "-o", str(temp), str(source)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=120,
        )
        if compiled.returncode != 0:
            raise RuntimeError("native dialog compilation failed")
        os.chmod(temp, 0o700)
        os.replace(temp, executable)
    finally:
        if temp.exists():
            temp.unlink()
    return executable


def native_dialog(fields: list[dict[str, str]], target: str) -> dict[str, str]:
    if platform.system() != "Darwin":
        raise RuntimeError("native macOS dialog unavailable")
    executable = dialog_binary()
    try:
        proc = subprocess.run(
            [str(executable)],
            input=json.dumps({"fields": fields, "destination": target}),
            capture_output=True, text=True, check=False, timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Cancelled() from None
    if proc.returncode != 0 or not proc.stdout:
        raise Cancelled()
    try:
        response = json.loads(proc.stdout)
        if response.get("status") != "entered":
            raise Cancelled()
        values = response["values"]
        expected = {f["name"] for f in fields}
        if not isinstance(values, dict) or set(values) != expected:
            raise Cancelled()
        if any(not isinstance(v, str) or not v for v in values.values()):
            raise Cancelled()
        return values
    except (ValueError, KeyError, TypeError):
        raise Cancelled() from None


def result(text: str, error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def request_secret(args: object) -> dict:
    try:
        fields, root, destination, repo, target = validate(args)
    except (ValueError, OSError):
        return result("Secret Drop: invalid or unsafe request. Nothing saved.", True)
    try:
        values = native_dialog(fields, target)
    except (Cancelled, RuntimeError, OSError):
        return result("Secret Drop: cancelled or native dialog unavailable. Nothing saved.", True)
    try:
        # All values validated BEFORE writing or sending anything.
        if destination in ("env", "both"):
            for value in values.values():
                quote_env(value)
            write_env_batch(root, values)
        saved = []
        failed = []
        if destination in ("github", "both"):
            for name, value in values.items():
                if write_github(name, repo, value):
                    saved.append(name)
                else:
                    failed.append(name)
        names = ", ".join(values)
        if failed:
            return result(
                "Secret Drop: local .env " +
                ("saved. " if destination == "both" else "not used. ") +
                "GitHub save failed for: " + ", ".join(failed) +
                "; succeeded for: " + ", ".join(saved) +
                ". No secret values returned.", True
            )
        return result(
            "Secret Drop: " + names + " saved to " + target +
            ". No secret values returned to the agent."
        )
    except (ValueError, OSError, UnicodeError):
        return result("Secret Drop: could not save the requested values. Nothing disclosed.", True)
    finally:
        values.clear()


def handle(request: dict) -> dict | None:
    method = request.get("method")
    msg_id = request.get("id")
    if msg_id is None:
        return None
    if method == "initialize":
        payload = {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "secret-drop-local", "version": "0.3.0"},
            "instructions": (
                "Call request_secret with ONE 'name' or MULTIPLE 'secrets' entries; "
                "a single native masked macOS window collects values. Never ask for, "
                "read, print or pass secret values through agent messages."
            ),
        }
    elif method == "tools/list":
        payload = {"tools": [TOOL]}
    elif method == "tools/call":
        params = request.get("params") or {}
        if params.get("name") != "request_secret":
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Unknown tool"}}
        payload = request_secret(params.get("arguments"))
    elif method == "ping":
        payload = {}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": payload}


def main():
    for raw in sys.stdin.buffer:
        try:
            request = json.loads(raw)
            if not isinstance(request, dict):
                continue
            response = handle(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except (ValueError, TypeError, json.JSONDecodeError):
            # Never echo input, which may contain a sensitive value.
            continue


if __name__ == "__main__":
    main()
