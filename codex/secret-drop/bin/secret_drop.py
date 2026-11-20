#!/usr/bin/env python3
"""Internal secure local .env/GitHub writer. Imported by the macOS GUI MCP tool."""
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
BARE = re.compile(r"[A-Za-z0-9_./:@%+=,-]+\Z")


def quote_env(value: str) -> str:
    """Conservative shell/dotenv-compatible representation, never shell-expand secrets."""
    if "\n" in value or "\r" in value or "\0" in value:
        raise ValueError("multiline/NUL values cannot be saved to .env")
    if BARE.fullmatch(value):
        return value
    if "'" in value:
        raise ValueError("complex quoted value: use a secret manager or --no-env --github")
    return "'" + value + "'"


def patched_env(original: str, name: str, value: str) -> str:
    lines = original.splitlines()
    expr = re.compile(r"^(\s*)(export\s+)?(" + re.escape(name) + r")\s*=")
    found = [i for i, line in enumerate(lines) if expr.match(line)]
    if len(found) > 1:
        raise ValueError("duplicate variable definitions; resolve manually")
    representation = quote_env(value)
    if found:
        i = found[0]
        match = expr.match(lines[i])
        lines[i] = match.group(1) + (match.group(2) or "") + name + "=" + representation
    else:
        lines.append(name + "=" + representation)
    return "\n".join(lines) + "\n"


def git_command(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def prepare_git(root: Path) -> None:
    probe = git_command(root, "rev-parse", "--show-toplevel")
    if probe.returncode != 0:
        return
    if Path(probe.stdout.strip()).resolve() != root:
        raise ValueError("run this helper at the Git repository root")
    if git_command(root, "ls-files", "--error-unmatch", "--", ".env").returncode == 0:
        raise ValueError(".env is tracked by Git: untrack it and rotate old credentials first")
    if git_command(root, "check-ignore", "-q", "--", ".env").returncode == 0:
        return
    ignore = root / ".gitignore"
    if ignore.is_symlink() or (ignore.exists() and not ignore.is_file()):
        raise ValueError(".gitignore is not a regular file")
    old = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    with ignore.open("a", encoding="utf-8") as stream:
        if old and not old.endswith("\n"):
            stream.write("\n")
        stream.write("/.env\n")


def write_env_batch(root: Path, values: dict[str, str]) -> None:
    """Validate all values, then atomically update one .env file."""
    if not values:
        raise ValueError("no variables to save")
    env = root / ".env"
    if env.is_symlink() or (env.exists() and not env.is_file()):
        raise ValueError(".env is not a regular file")
    old = env.read_text(encoding="utf-8") if env.exists() else ""
    updated = old
    for name, value in values.items():
        if not NAME.fullmatch(name):
            raise ValueError("invalid environment variable name")
        quote_env(value)  # Validate before changing project files.
        updated = patched_env(updated, name, value)
    prepare_git(root)
    fd, path = tempfile.mkstemp(prefix=".secret-drop-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(path, env)
    finally:
        if os.path.exists(path):
            os.unlink(path)



def verify_env_written(root: Path, values: dict[str, str]) -> dict[str, bool]:
    """Post-write on-disk readback, LOCAL ONLY. Never return or log secret bytes.

    The agent receives only per-variable booleans. Verification compares the
    exact serialized values held by this process with saved file contents,
    checks owner/mode 0600, and rejects symlinks/hardlinks or unbounded files.
    This establishes persistence, NOT external API credential validity.
    """
    verified = {name: False for name in values}
    if not values:
        return verified
    fd = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(root / ".env", flags)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 1048576):
            return verified
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = None
            content = stream.read(1048577)
        if len(content) > 1048576:
            return verified
        lines = content.splitlines()
        for name, value in values.items():
            matcher = re.compile(r"^\s*(?:export\s+)?" + re.escape(name) + r"\s*=")
            matches = [line for line in lines if matcher.match(line)]
            verified[name] = (
                len(matches) == 1
                and matches[0].split("=", 1)[1] == quote_env(value)
            )
        return verified
    except (OSError, UnicodeError, ValueError):
        return verified
    finally:
        if fd is not None:
            os.close(fd)


def write_env(root: Path, name: str, value: str) -> None:
    """Compatibility wrapper for the single-secret API."""
    write_env_batch(root, {name: value})


def write_github(name: str, repo: str, value: str) -> bool:
    # No shell interpolation and no secret in argv. Suppress all gh output.
    try:
        p = subprocess.run(
            ["gh", "secret", "set", name, "--repo", repo],
            input=value,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
