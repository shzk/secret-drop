#!/usr/bin/env python3
"""Research-only MCP 2025-11-25 URL probe. Accepts no credentials."""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from uuid import uuid4

PROTOCOL = "2025-11-25"
MARKER = b"PUBLIC_SECRET_DROP_URL_PILOT\n"
PAGE = b"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Secret Drop URL pilot</title>
<h1>Secret Drop URL pilot</h1>
<p>This test writes a fixed public marker in a temporary directory.</p>
<form method="post"><button type="submit">Write public marker</button></form>
"""


def result(request_id, payload):
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def tool_result(request_id, state, *, error=False):
    return result(request_id, {
        "content": [{"type": "text", "text": state}],
        "isError": error,
    })


class Probe:
    def __init__(self, target):
        self.target = target
        self.pending = None
        self.supported = False
        self.state = "idle"
        self.lock = Lock()
        self.path = "/pilot/" + uuid4().hex
        self.http = HTTPServer(("127.0.0.1", 0), self.handler())
        self.host = f"127.0.0.1:{self.http.server_port}"
        self.origin = "http://" + self.host

    def handler(self):
        probe = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def respond(self, code, body):
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy",
                                 "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def valid_target(self):
                return self.path == probe.path and self.headers.get("Host") == probe.host

            def do_GET(self):
                if not self.valid_target():
                    self.respond(404, b"Unknown test page")
                    return
                self.respond(200, PAGE)

            def do_POST(self):
                if (not self.valid_target() or self.headers.get("Origin") != probe.origin
                        or self.headers.get("Content-Length") != "0"
                        or self.headers.get("Transfer-Encoding") is not None):
                    self.respond(403, b"Unexpected test request")
                    return
                with probe.lock:
                    if probe.state != "awaiting_browser":
                        self.respond(409, b"No pending write")
                        return
                    try:
                        with probe.target.open("xb") as marker:
                            marker.write(MARKER)
                    except OSError:
                        probe.state = "write_failed"
                        self.respond(500, b"Test write failed")
                        return
                    probe.state = "saved"
                self.respond(200, b"<h1>Public marker saved</h1>")

        return Handler

    def handle(self, msg):
        method = msg.get("method")
        request_id = msg.get("id")
        params = msg.get("params") or {}
        if method == "initialize":
            capabilities = params.get("capabilities", {}).get("elicitation", {})
            # The client proposes a version. The server selects PROTOCOL below,
            # so use the advertised mode once the client continues to tools/call.
            self.supported = isinstance(capabilities.get("url"), dict)
            return result(request_id, {
                "protocolVersion": PROTOCOL,
                "serverInfo": {"name": "secret-drop-url-fixture", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            })
        if method == "ping":
            return result(request_id, {})
        if method == "tools/list":
            return result(request_id, {"tools": [
                {"name": name, "description": description, "inputSchema": {
                    "type": "object", "properties": {}, "additionalProperties": False,
                }}
                for name, description in [
                    ("probe_url", "Request a browser visit for a public-marker pilot. "
                                  "No input or credential is accepted."),
                    ("probe_status", "Check the disposable pilot's write status only."),
                ]
            ]})
        if method == "tools/call":
            if params.get("arguments", {}) != {}:
                return tool_result(request_id, "unexpected_arguments", error=True)
            with self.lock:
                if params.get("name") == "probe_status":
                    return tool_result(request_id, self.state)
                if params.get("name") != "probe_url":
                    return tool_result(request_id, "unknown_tool", error=True)
                if not self.supported:
                    return tool_result(request_id, "url_not_advertised", error=True)
                if self.state != "idle":
                    return tool_result(request_id, self.state)
                self.pending = request_id
                self.state = "awaiting_consent"
                return {"jsonrpc": "2.0", "id": "url-pilot", "method": "elicitation/create",
                        "params": {
                            "mode": "url",
                            "elicitationId": "secret-drop-public-pilot",
                            "url": self.origin + self.path,
                            "message": "Open a loopback page to write a fixed public test marker.",
                        }}
        if method is None and request_id == "url-pilot" and self.pending is not None:
            with self.lock:
                answer = msg.get("result") or {}
                action = answer.get("action")
                if action == "accept" and answer.get("content") is None:
                    self.state = "awaiting_browser"
                elif action in ("cancel", "decline"):
                    self.state = "cancelled"
                else:
                    self.state = "invalid_response"
                response = tool_result(self.pending, self.state)
                self.pending = None
                return response
        if request_id is not None and method is not None:
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": -32601, "message": "Unknown method"}}
        return None


def main():
    with TemporaryDirectory(prefix="secret-drop-url-pilot-") as directory:
        probe = Probe(Path(directory) / "public-marker.txt")
        worker = Thread(target=probe.http.serve_forever, daemon=True)
        worker.start()
        try:
            for line in sys.stdin:
                try:
                    response = probe.handle(json.loads(line))
                except (ValueError, AttributeError, TypeError):
                    continue
                if response is not None:
                    print(json.dumps(response), flush=True)
        finally:
            probe.http.shutdown()
            probe.http.server_close()
            worker.join()


if __name__ == "__main__":
    main()
