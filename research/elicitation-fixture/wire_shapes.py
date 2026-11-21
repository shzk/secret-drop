"""Offline wire-shape fixtures only. No MCP server, network listener, or secrets.

This is deliberately not a credential-entry implementation and is NOT a
Codex Desktop/ChatGPT Web compatibility or secure-storage test.
"""
from __future__ import annotations

from urllib.parse import urlsplit


def confirmation_form() -> dict:
    """Return only non-secret destination metadata for MCP form elicitation."""
    return {
        "mode": "form",
        "message": (
            "Secret Drop requests permission to open a protected credential-entry "
            "dialog. No API key or password should be entered here."
        ),
        "requestedSchema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "enum": ["config/.env.local", "GitHub: example/demo (test only)"],
                },
                "confirm": {"type": "boolean"},
            },
            "required": ["destination", "confirm"],
            "additionalProperties": False,
        },
    }


def credential_url_request(url: str, *, protocol: str) -> dict:
    """Generate an OUT-OF-BAND navigation request, never a secret-bearing form.

    HTTPS URL is fictitious; it is not fetched, opened, signed or given a token.
    Extra query/fragment/userinfo restrictions are local conservative policy,
    not a representation of all MCP protocol requirements.
    """
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != "secrets.example.invalid"
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or not parts.path.startswith("/request/")
    ):
        raise ValueError("Unsafe or unapproved URL-mode destination")
    result = {
        "mode": "url",
        "message": "Open verified external secure input in the browser.",
        "url": url,
    }
    if protocol == "2025-11-25":
        result["elicitationId"] = "synthetic-fixture-not-a-real-session"
    elif protocol != "2026-07-28":
        raise ValueError("Unsupported example protocol")
    return result


def capability_advertisement(protocol: str) -> dict:
    """Demonstrate a versioned client capability *shape*, not host support."""
    caps = {"elicitation": {"form": {}, "url": {}}}
    if protocol == "2025-11-25":
        return {"capabilities": caps}
    if protocol == "2026-07-28":
        return {"_meta": {"io.modelcontextprotocol/clientCapabilities": caps}}
    raise ValueError("Unknown example protocol")


def model_visible_result(*, saved: bool, variable_name: str) -> dict:
    """Only local status/name, no value; never inspect any secret storage."""
    if not variable_name.isidentifier():
        raise ValueError("Invalid synthetic variable name")
    return {
        "content": [{
            "type": "text",
            "text": variable_name + (" saved locally" if saved else " not saved"),
        }]
    }
