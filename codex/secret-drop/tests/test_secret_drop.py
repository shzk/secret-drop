"""Safe fixture tests. Never use real credentials or GitHub network."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

guard = load("secret_drop_guard", ROOT / "hooks" / "prompt_guard.py")
helper = load("secret_drop_helper", ROOT / "bin" / "secret_drop.py")
server = load("secret_drop_mcp", ROOT / "server" / "mcp_server.py")


class GuardTests(unittest.TestCase):
    def test_recognizes_fake_formats(self):
        self.assertTrue(guard.contains_secret("key sk-proj-" + "x" * 40))
        self.assertTrue(guard.contains_secret("token: Zq81kLm02XpR7tYv9wQe"))
        self.assertTrue(guard.contains_secret("1234567890:AA" + "y" * 33))
        self.assertTrue(guard.contains_secret("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----"))

    def test_ordinary_metadata_is_not_secret(self):
        for prompt in (
            "Use env var OPENAI_API_KEY without printing it",
            "key commit " + "3f2a9c1e5b7d4f6a8c0e2b4d6f8a1c3e5b7d9f0a",
            "voice uuAEb8aX4QXTwh8CAexT, key is in .env",
            "Search https://example.com/docs/api/key",
        ):
            self.assertFalse(guard.contains_secret(prompt))

    def test_hook_block_does_not_echo_secret(self):
        fake = "sk-ant-" + "a" * 35
        p = subprocess.run(
            [sys.executable, "-I", str(ROOT / "hooks" / "prompt_guard.py")],
            input=json.dumps({"prompt": "here: " + fake}),
            text=True, capture_output=True, check=True,
        )
        output = json.loads(p.stdout)
        self.assertEqual(output["decision"], "block")
        self.assertNotIn(fake, p.stdout + p.stderr)

    def test_hook_invalid_data_blocks(self):
        p = subprocess.run(
            [sys.executable, "-I", str(ROOT / "hooks" / "prompt_guard.py")],
            input="broken", text=True, capture_output=True, check=True,
        )
        self.assertEqual(json.loads(p.stdout)["decision"], "block")


class WriterTests(unittest.TestCase):
    def test_shell_env_quote_and_update(self):
        got = helper.patched_env("export DEMO=old\nOTHER=1\n", "DEMO", "abc$def")
        self.assertEqual(got, "export DEMO='abc$def'\nOTHER=1\n")
        with self.assertRaises(ValueError):
            helper.quote_env("two\nlines")
        with self.assertRaises(ValueError):
            helper.quote_env("a'b")

    def test_atomic_mode_and_no_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            helper.write_env(root, "FAKE_TOKEN", "Fixture1234")
            env = root / ".env"
            self.assertEqual(env.read_text(), "FAKE_TOKEN=Fixture1234\n")
            self.assertEqual(stat.S_IMODE(env.stat().st_mode), 0o600)
            helper.write_env(root, "FAKE_TOKEN", "UpdatedFake987")
            self.assertEqual(env.read_text(), "FAKE_TOKEN=UpdatedFake987\n")
            env.unlink()
            target = root / "target"
            target.write_text("keep")
            env.symlink_to(target)
            with self.assertRaises(ValueError):
                helper.write_env(root, "FAKE_TOKEN", "NOTWRITTEN")
            self.assertEqual(target.read_text(), "keep")

    def test_refuses_tracked_env(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".env").write_text("FAKE_KEY=old\n")
            subprocess.run(["git", "-C", str(root), "add", ".env"], check=True)
            with self.assertRaises(ValueError):
                helper.write_env(root, "FAKE_KEY", "NEWFAKE")
            self.assertEqual((root / ".env").read_text(), "FAKE_KEY=old\n")


class NativeMcpTests(unittest.TestCase):
    def test_local_masked_gui_saves_without_exposing_value(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with mock.patch.object(server.Path, "home", return_value=root.parent), \
                 mock.patch.object(server, "native_dialog", return_value="Fixture-Only-98765") as modal:
                result = server.request_secret({"name": "TEST_SECRET_DROP", "project_dir": str(root)})
            self.assertEqual(result["isError"], False, result)
            self.assertEqual(modal.call_args.args[0], "TEST_SECRET_DROP")
            self.assertIn(str(root / ".env"), modal.call_args.args[1])
            serialized = json.dumps(result)
            self.assertNotIn("Fixture-Only-98765", serialized)
            self.assertEqual((root / ".env").read_text(), "TEST_SECRET_DROP=Fixture-Only-98765\n")
            self.assertEqual(stat.S_IMODE((root / ".env").stat().st_mode), 0o600)

    def test_cancel_does_not_touch_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with mock.patch.object(server.Path, "home", return_value=root.parent), \
                 mock.patch.object(server, "native_dialog", side_effect=server.Cancelled):
                result = server.request_secret({"name": "FAKE_KEY", "project_dir": str(root)})
            self.assertTrue(result["isError"])
            self.assertFalse((root / ".env").exists())

    def test_rejects_unexpected_value_input_without_opening_gui(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with mock.patch.object(server.Path, "home", return_value=root.parent), \
                 mock.patch.object(server, "native_dialog") as modal:
                result = server.request_secret({
                    "name": "FAKE_KEY", "project_dir": str(root), "value": "FAKE_NOT_ALLOWED"
                })
            self.assertTrue(result["isError"])
            modal.assert_not_called()
            self.assertNotIn("FAKE_NOT_ALLOWED", json.dumps(result))

    def test_only_mac_script_receives_nonsecret_metadata(self):
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="FixtureOnly456\n", stderr="")
        with mock.patch.object(server.platform, "system", return_value="Darwin"), \
             mock.patch.object(server.subprocess, "run", return_value=proc) as runner:
            value = server.native_dialog("EXAMPLE_KEY", "/tmp/test/.env")
        self.assertEqual(value, "FixtureOnly456")
        args, kwargs = runner.call_args
        self.assertEqual(args[0][0], "/usr/bin/osascript")
        self.assertIn("with hidden answer", args[0][2])
        self.assertNotIn("FixtureOnly456", json.dumps(args[0]))
        self.assertEqual(kwargs["env"]["SECRET_DROP_VARIABLE_NAME"], "EXAMPLE_KEY")
        self.assertTrue(kwargs["capture_output"])

    def test_mcp_stdio_handshake_and_tool_without_secret_value_field(self):
        payload = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "synthetic-test", "version": "1.0"}
            }},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        ]
        reply = subprocess.run(
            [sys.executable, "-I", str(ROOT / "server" / "mcp_server.py")],
            input="\n".join(json.dumps(msg) for msg in payload) + "\n",
            capture_output=True, text=True, check=True, timeout=5,
        )
        lines = [json.loads(line) for line in reply.stdout.splitlines()]
        self.assertEqual(len(lines), 2, reply)
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], "secret-drop-local")
        tool = lines[1]["result"]["tools"][0]
        self.assertEqual(tool["name"], "request_secret")
        self.assertNotIn("value", tool["inputSchema"]["properties"])
        self.assertEqual(reply.stderr, "")

    def test_github_only_opt_in_does_not_write_env_or_leak(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with mock.patch.object(server.Path, "home", return_value=root.parent), \
                 mock.patch.object(server, "native_dialog", return_value="FakeNoNetwork123"), \
                 mock.patch.object(server, "write_github", return_value=True) as gh:
                result = server.request_secret({
                    "name": "DEMO_KEY", "project_dir": str(root),
                    "destination": "github", "github_repo": "example/demo",
                })
            self.assertFalse(result["isError"])
            self.assertFalse((root / ".env").exists())
            self.assertEqual(gh.call_args.args[:2], ("DEMO_KEY", "example/demo"))
            self.assertNotIn("FakeNoNetwork123", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
