#!/usr/bin/env python3
"""Isolated MCP elicitation probe — metadata only, never a secret entry tool.

No network, filesystem writes, logging or external process execution.
Designed for a disposable research branch, NOT for installed Secret Drop.
"""
from __future__ import annotations

import json
import sys
from typing import Any

MCP_VERSION = "2025-11-25"
TOOL_NAME = "probe_confirmation"
SCHEMA = {
    "type": "object",
    "properties": {
        "destination": {
            "type": "string",
            "title": "Destination",
            "description": "An example only; this tool never writes a file.",
            "enum": ["config/.env.local", "Do not save"],
        },
        "confirm": {
            "type": "boolean",
            "title": "Confirm destination",
            "description": "Approve this simulated destination only; no secret entered.",
            "default": False,
        },
    },
    "required": ["destination", "confirm"],
    "additionalProperties": False,
}
TOOL = {
    "name": TOOL_NAME,
    "description": (
        "TEST-ONLY: ask a human to choose and confirm a dummy destination using "
        "a native MCP form. This tool never accepts or stores keys, API tokens, "
        "passwords, or any secret values. Use only in the isolated research pilot."
    ),
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
}


def jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def supported_form(capabilities: Any) -> bool:
    if not isinstance(capabilities, dict):
        return False
    elicitation = capabilities.get("elicitation")
    return isinstance(elicitation, dict) and (
        not elicitation or isinstance(elicitation.get("form"), dict)
    )


def supported_request(req: dict[str, Any], initialization: dict[str, Any]) -> bool:
    # The 2026-07-28 protocol advertises client capabilities on each request;
    # the 2025-11-25 protocol advertises during initialization.
    meta = req.get("params")
    if isinstance(meta, dict):
        meta = meta.get("_meta")
        if isinstance(meta, dict):
            caps = meta.get("io.modelcontextprotocol/clientCapabilities")
            if isinstance(caps, dict):
                return supported_form(caps)
    return supported_form(initialization)


class Probe:
    def __init__(self) -> None:
        self.client_capabilities: dict[str, Any] = {}
        self.pending: dict[str, Any] | None = None
        self.next_request_id = 1

    def handle(self, msg: dict[str, Any]) -> list[dict[str, Any]]:
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize" and msg_id is not None:
            params = msg.get("params") or {}
            if not isinstance(params, dict):
                params = {}
            self.client_capabilities = params.get("capabilities") or {}
            version = params.get("protocolVersion")
            if version not in ("2025-11-25", "2025-06-18", "2026-07-28"):
                version = "2025-06-18"
            return [jsonrpc_result(msg_id, {
                "protocolVersion": version,
                "serverInfo": {"name": "secret-drop-form-research-only", "version": "0.0.1"},
                "capabilities": {"tools": {"listChanged": False}},
                "instructions": (
                    "Research only; use no real credentials. The tool requests "
                    "confirmation metadata and never writes or saves anything."
                ),
            })]
        if method == "tools/list" and msg_id is not None:
            return [jsonrpc_result(msg_id, {"tools": [TOOL]})]
        if method == "ping" and msg_id is not None:
            return [jsonrpc_result(msg_id, {})]
        if method == "tools/call" and msg_id is not None:
            params = msg.get("params") or {}
            if not isinstance(params, dict) or params.get("name") != TOOL_NAME:
                return [jsonrpc_result(msg_id, self._status("unsupported tool", error=True))]
            args = params.get("arguments", {})
            if args not in ({}, None):
                return [jsonrpc_result(msg_id, self._status("unexpected arguments refused", error=True))]
            if self.pending is not None:
                return [jsonrpc_result(msg_id, self._status("another request in progress", error=True))]
            if not supported_request(msg, self.client_capabilities):
                return [jsonrpc_result(msg_id, self._status(
                    "form not advertised by this MCP client; no request was opened",
                    error=True,
                ))]
            pending_id = "elicitation-" + str(self.next_request_id)
            self.next_request_id += 1
            self.pending = {"request_id": pending_id, "tool_call_id": msg_id}
            return [{
                "jsonrpc": "2.0",
                "id": pending_id,
                "method": "elicitation/create",
                "params": {
                    "mode": "form",
                    "message": (
                        "Secret Drop pilot: confirm a FAKE destination only. "
                        "DO NOT enter an API key, token or password in this form."
                    ),
                    "requestedSchema": SCHEMA,
                },
            }]
        if msg_id is not None and self.pending is not None:
            if msg_id == self.pending["request_id"] and "method" not in msg:
                call_id = self.pending["tool_call_id"]
                self.pending = None
                return [jsonrpc_result(call_id, self._interpret_response(msg))]
        return []

    @staticmethod
    def _status(text: str, *, error: bool = False) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "Form pilot: " + text}], "isError": error}

    def _interpret_response(self, msg: dict[str, Any]) -> dict[str, Any]:
        if "error" in msg:
            return self._status("client rejected/does not support elicitation", error=True)
        result = msg.get("result")
        if not isinstance(result, dict):
            return self._status("invalid response refused", error=True)
        if result.get("action") in ("decline", "cancel"):
            return self._status("user declined or cancelled; nothing saved")
        if result.get("action") != "accept":
            return self._status("unknown action refused", error=True)
        content = result.get("content")
        if (
            not isinstance(content, dict)
            or set(content) != {"destination", "confirm"}
            or content["destination"] not in SCHEMA["properties"]["destination"]["enum"]
            or type(content["confirm"]) is not bool
        ):
            return self._status("unexpected form content refused", error=True)
        if not content["confirm"] or content["destination"] == "Do not save":
            return self._status("not approved; nothing saved")
        return self._status(
            "dummy destination confirmed: config/.env.local; NO FILES WERE WRITTEN"
        )


def main() -> None:
    probe = Probe()
    for raw in sys.stdin.buffer:
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                continue
            for reply in probe.handle(message):
                sys.stdout.write(json.dumps(reply, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except (ValueError, TypeError, UnicodeError):
            # Never reflect the malformed input, which could contain sensitive text.
            continue


if __name__ == "__main__":
    main()
