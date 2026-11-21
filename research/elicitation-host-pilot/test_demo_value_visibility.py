"""Public dummy text proves why MCP Form must not carry credentials.

All test values are deliberately nonsecret. No network, key or file writes.
"""
import json
import unittest

from stdio_probe import Probe, DEMO_MARKER, DEMO_SCHEMA, DEMO_TOOL_NAME


def new_probe(capabilities=None):
    p = Probe()
    p.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": capabilities if capabilities is not None else {"elicitation": {"form": {}}},
    }})
    return p


def start(p):
    return p.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                     "params": {"name": DEMO_TOOL_NAME, "arguments": {}}})[0]


def answer(p, elicitation_id, content=None, action="accept"):
    return p.handle({"jsonrpc": "2.0", "id": elicitation_id,
                     "result": {"action": action, "content": content}})[0]


class PublicDemoVisibilityTests(unittest.TestCase):
    def test_form_requests_only_enum_restricted_public_marker(self):
        p = new_probe()
        req = start(p)
        self.assertEqual(req["method"], "elicitation/create")
        self.assertEqual(req["params"]["mode"], "form")
        self.assertEqual(req["params"]["requestedSchema"], DEMO_SCHEMA)
        self.assertEqual(set(DEMO_SCHEMA["properties"]), {"demo_text"})
        self.assertEqual(DEMO_SCHEMA["properties"]["demo_text"]["enum"], [DEMO_MARKER])
        self.assertIn("PUBLIC", req["params"]["message"])

    def test_public_marker_is_returned_in_model_visible_tool_result(self):
        p = new_probe()
        req = start(p)
        result = answer(p, req["id"], {"demo_text": DEMO_MARKER})
        text = result["result"]["content"][0]["text"]
        self.assertEqual(result["id"], 2)
        self.assertFalse(result["result"]["isError"])
        self.assertIn(DEMO_MARKER, text)  # Proven client-visible; NOT a secure channel.
        self.assertIsNone(p.pending)

    def test_other_text_rejected_without_echo(self):
        p = new_probe()
        req = start(p)
        result = answer(p, req["id"], {"demo_text": "PRIVATE_LOOKING_BUT_FAKE_999"})
        self.assertTrue(result["result"]["isError"])
        self.assertNotIn("PRIVATE_LOOKING_BUT_FAKE_999", json.dumps(result))

    def test_sensitive_field_rejected_without_echo(self):
        p = new_probe()
        req = start(p)
        result = answer(p, req["id"], {
            "demo_text": DEMO_MARKER, "api_key": "NOT_A_REAL_KEY_999",
        })
        self.assertTrue(result["result"]["isError"])
        self.assertNotIn("NOT_A_REAL_KEY_999", json.dumps(result))

    def test_declined_input_returns_no_marker(self):
        p = new_probe()
        req = start(p)
        result = answer(p, req["id"], action="decline")
        self.assertFalse(result["result"]["isError"])
        self.assertNotIn(DEMO_MARKER, json.dumps(result))

    def test_no_form_support_fails_closed(self):
        p = new_probe(capabilities={})
        response = start(p)
        self.assertNotIn("method", response)
        self.assertTrue(response["result"]["isError"])
        self.assertIsNone(p.pending)


if __name__ == "__main__":
    unittest.main()
