"""Offline tests for research-only MCP form elicitation.

No secrets or model/API calls; no server configuration changes.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from stdio_probe import Probe, SCHEMA, TOOL_NAME


def invoke(p: Probe, method: str, msg_id: object, params: dict | None = None):
    return p.handle({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})


def initialized(*, caps: dict | None = None):
    p = Probe()
    p.handle({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-11-25", "capabilities": caps or {}},
    })
    return p


class ElicitationProbeTests(unittest.TestCase):
    def test_absent_capability_fails_closed(self):
        p = initialized()
        reply = invoke(p, "tools/call", 10, {"name": TOOL_NAME})[0]
        self.assertNotIn("method", reply)
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("not advertised", reply["result"]["content"][0]["text"])
        self.assertIsNone(p.pending)

    def test_form_capability_routes_mcp_request(self):
        p = initialized(caps={"elicitation": {"form": {}}})
        reply = invoke(p, "tools/call", 10, {"name": TOOL_NAME})[0]
        self.assertEqual(reply["method"], "elicitation/create")
        self.assertEqual(reply["params"]["mode"], "form")
        self.assertEqual(reply["params"]["requestedSchema"], SCHEMA)
        self.assertEqual(set(SCHEMA["properties"]), {"confirm", "destination"})
        self.assertNotIn("value", reply["params"]["requestedSchema"]["properties"])

    def test_response_accept_has_status_only(self):
        p = initialized(caps={"elicitation": {}})
        call = invoke(p, "tools/call", 10, {"name": TOOL_NAME})[0]
        reply = p.handle({
            "jsonrpc": "2.0", "id": call["id"],
            "result": {"action": "accept", "content": {
                "destination": "config/.env.local", "confirm": True,
            }},
        })[0]
        self.assertEqual(reply["id"], 10)
        self.assertFalse(reply["result"]["isError"])
        self.assertIn("NO FILES WERE WRITTEN", reply["result"]["content"][0]["text"])
        self.assertIsNone(p.pending)

    def test_decline_and_cancel_both_stop(self):
        for action in ("decline", "cancel"):
            with self.subTest(action=action):
                p = initialized(caps={"elicitation": {"form": {}}})
                req = invoke(p, "tools/call", 3, {"name": TOOL_NAME})[0]
                result = p.handle({
                    "jsonrpc": "2.0", "id": req["id"],
                    "result": {"action": action},
                })[0]
                self.assertIn("cancelled", result["result"]["content"][0]["text"])
                self.assertIsNone(p.pending)

    def test_unconfirmed_and_do_not_save_stop(self):
        for dest, confirm in [
            ("config/.env.local", False),
            ("Do not save", True),
        ]:
            p = initialized(caps={"elicitation": {"form": {}}})
            req = invoke(p, "tools/call", 4, {"name": TOOL_NAME})[0]
            result = p.handle({
                "jsonrpc": "2.0", "id": req["id"],
                "result": {"action": "accept", "content": {
                    "destination": dest, "confirm": confirm,
                }},
            })[0]
            self.assertIn("not approved", result["result"]["content"][0]["text"])

    def test_unexpected_secret_bearing_fields_rejected(self):
        p = initialized(caps={"elicitation": {"form": {}}})
        req = invoke(p, "tools/call", 6, {"name": TOOL_NAME})[0]
        bad = p.handle({
            "jsonrpc": "2.0", "id": req["id"],
            "result": {"action": "accept", "content": {
                "destination": "config/.env.local", "confirm": True,
                "api_key": "SYNTHETIC-NEVER-ECHO-123",
            }},
        })[0]
        self.assertTrue(bad["result"]["isError"])
        self.assertNotIn("SYNTHETIC-NEVER-ECHO-123", json.dumps(bad))

    def test_concurrent_request_rejected(self):
        p = initialized(caps={"elicitation": {"form": {}}})
        req = invoke(p, "tools/call", 8, {"name": TOOL_NAME})[0]
        dup = invoke(p, "tools/call", 9, {"name": TOOL_NAME})[0]
        self.assertIn("in progress", dup["result"]["content"][0]["text"])
        self.assertIsNotNone(p.pending)
        p.handle({"jsonrpc": "2.0", "id": req["id"], "error": {
            "code": -32603, "message": "client unsupported",
        }})
        self.assertIsNone(p.pending)

    def test_current_protocol_meta_works_without_init_cap(self):
        p = initialized()
        req = {
            "jsonrpc": "2.0", "id": 12, "method": "tools/call",
            "params": {
                "name": TOOL_NAME,
                "_meta": {
                    "io.modelcontextprotocol/clientCapabilities": {
                        "elicitation": {"form": {}},
                    },
                },
            },
        }
        out = p.handle(req)[0]
        self.assertEqual(out["method"], "elicitation/create")

    def test_malformed_arguments_rejected(self):
        p = initialized(caps={"elicitation": {"form": {}}})
        out = invoke(p, "tools/call", 2, {
            "name": TOOL_NAME, "arguments": {"token": "not-a-real-key"},
        })[0]
        self.assertTrue(out["result"]["isError"])
        self.assertNotIn("not-a-real-key", json.dumps(out))

    def test_real_stdio_handshake_and_unsupported_call(self):
        script = Path(__file__).with_name("stdio_probe.py")
        commands = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-11-25", "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": TOOL_NAME, "arguments": {}}},
        ]
        completed = subprocess.run(
            [sys.executable, "-I", str(script)],
            input="\n".join(json.dumps(c) for c in commands) + "\n",
            text=True, capture_output=True, timeout=5, check=True,
        )
        results = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["result"]["serverInfo"]["name"],
                         "secret-drop-form-research-only")
        self.assertEqual(results[1]["result"]["tools"][0]["name"], TOOL_NAME)
        self.assertTrue(results[2]["result"]["isError"])
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
