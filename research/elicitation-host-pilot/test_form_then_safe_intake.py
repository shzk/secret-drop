"""Synthetic two-stage route: MCP nonsecret confirmation -> audited native intake.

The native AppKit dialog is mocked by a LOCAL fixture, never by an MCP form.
Real key values are NEVER used; the fake value is verified only in temporary
on-disk test data, and must not appear in the tool result. Not a GUI host E2E.
"""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from stdio_probe import Probe, TOOL_NAME

ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER_SOURCE = ROOT / "codex" / "secret-drop" / "server" / "mcp_server.py"
SPEC = importlib.util.spec_from_file_location("test_canonical_secret_drop_mcp", MCP_SERVER_SOURCE)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)

PUBLIC_FAKE_VALUE = "FAKE_LOCAL_FIXTURE_ONLY_2026"


def form_approve():
    p = Probe()
    p.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {"elicitation": {"form": {}}},
    }})
    request = p.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": TOOL_NAME, "arguments": {}}})[0]
    assert request["method"] == "elicitation/create"
    returned = p.handle({"jsonrpc": "2.0", "id": request["id"], "result": {
        "action": "accept",
        "content": {"destination": "config/.env.local", "confirm": True},
    }})[0]
    assert not returned["result"]["isError"]
    return returned


class SyntheticSafeHandoff(unittest.TestCase):
    def test_confirm_then_native_helper_saves_fake_value_but_model_gets_status_only(self):
        confirm = form_approve()
        self.assertNotIn(PUBLIC_FAKE_VALUE, json.dumps(confirm))
        with tempfile.TemporaryDirectory() as td:
            home = Path(td).resolve() / "home"
            root = home / "project"
            root.mkdir(parents=True, mode=0o700)
            home.chmod(0o700)
            root.chmod(0o700)
            (root / "config").mkdir(mode=0o700)
            # This response models the accepted LOCAL AppKit UI. It does not
            # represent a form reply and is never included in any MCP argument.
            with mock.patch.object(server.Path, "home", return_value=home), \
                 mock.patch.object(
                     server, "native_dialog",
                     return_value=server.NativeResponse(
                         values={"TEST_SECRET_ALPHA": PUBLIC_FAKE_VALUE},
                         destination_confirmed=True,
                         github_confirmed=False,
                     ),
                 ) as local_dialog:
                response = server.request_secret({
                    "name": "TEST_SECRET_ALPHA",
                    "project_dir": str(root),
                    "env_file": "config/.env.local",
                    "reason": "synthetic-only test, no real service",
                })
            self.assertFalse(response["isError"], response)
            self.assertEqual(local_dialog.call_count, 1)
            target = root / "config" / ".env.local"
            self.assertEqual(target.read_text(), "TEST_SECRET_ALPHA=" + PUBLIC_FAKE_VALUE + "\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertIn("TEST_SECRET_ALPHA", json.dumps(response))
            self.assertNotIn(PUBLIC_FAKE_VALUE, json.dumps(response))
            self.assertNotIn(PUBLIC_FAKE_VALUE, json.dumps(confirm))

    def test_cancelled_form_stops_before_any_local_write(self):
        p = Probe()
        p.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {"elicitation": {"form": {}}},
        }})
        q = p.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": TOOL_NAME, "arguments": {}}})[0]
        result = p.handle({"jsonrpc": "2.0", "id": q["id"],
                           "result": {"action": "decline"}})[0]
        self.assertFalse(result["result"]["isError"])
        self.assertIn("cancelled", json.dumps(result))
        self.assertNotIn("saved locally", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
