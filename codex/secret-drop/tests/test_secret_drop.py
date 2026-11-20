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
    def _fake_home(self, root):
        return mock.patch.object(server.Path, "home", return_value=root.parent)

    def test_single_masked_gui_alias_saves_without_exposing_value(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with self._fake_home(root), \
                 mock.patch.object(server, "native_dialog",
                     return_value={"TEST_SECRET_DROP": "Fixture-Only-98765"}) as modal:
                result = server.request_secret({"name": "TEST_SECRET_DROP", "project_dir": str(root)})
            self.assertFalse(result["isError"])
            self.assertEqual(modal.call_args.args[0][0]["name"], "TEST_SECRET_DROP")
            self.assertIn(str(root / ".env"), modal.call_args.args[1])
            self.assertNotIn("Fixture-Only-98765", json.dumps(result))
            self.assertEqual((root / ".env").read_text(), "TEST_SECRET_DROP=Fixture-Only-98765\n")
            self.assertEqual(stat.S_IMODE((root / ".env").stat().st_mode), 0o600)

    def test_two_secrets_one_dialog_and_atomic_env(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            fields = [{"name": "APP_KEY", "hint": "For test app"}, {"name": "SERVICE_TOKEN"}]
            values = {"APP_KEY": "FakeValue12", "SERVICE_TOKEN": "TestOnly345"}
            with self._fake_home(root), \
                 mock.patch.object(server, "native_dialog", return_value=values) as modal:
                result = server.request_secret({"secrets": fields, "project_dir": str(root)})
            self.assertFalse(result["isError"])
            modal.assert_called_once()
            self.assertEqual(len(modal.call_args.args[0]), 2)
            self.assertEqual((root / ".env").read_text(), "APP_KEY=FakeValue12\nSERVICE_TOKEN=TestOnly345\n")
            self.assertEqual(stat.S_IMODE((root / ".env").stat().st_mode), 0o600)
            self.assertIn("APP_KEY, SERVICE_TOKEN", json.dumps(result))
            for value in values.values():
                self.assertNotIn(value, json.dumps(result))

    def test_batch_validation_failure_makes_no_partial_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            file = root / ".env"
            file.write_text("KEEP=original\n")
            with self.assertRaises(ValueError):
                helper.write_env_batch(root, {"A": "Valid123", "B": "newline\nunsafe"})
            self.assertEqual(file.read_text(), "KEEP=original\n")

    def test_cancel_does_not_touch_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with self._fake_home(root), \
                 mock.patch.object(server, "native_dialog", side_effect=server.Cancelled):
                result = server.request_secret({"secrets": [{"name": "ONE"}, {"name": "TWO"}],
                                                "project_dir": str(root)})
            self.assertTrue(result["isError"])
            self.assertFalse((root / ".env").exists())

    def test_rejects_values_duplicate_names_and_conflicting_shapes_without_gui(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            bad_payloads = [
                {"name": "A", "value": "FAKE_NOT_ALLOWED"},
                {"secrets": [{"name": "A", "value": "FAKE_NOT_ALLOWED"}]},
                {"secrets": [{"name": "A"}, {"name": "A"}]},
                {"secrets": [{"name": "A"}], "name": "B"},
                {"secrets": []},
                {"secrets": [{"name": "A"}] * 13},
            ]
            with self._fake_home(root), mock.patch.object(server, "native_dialog") as modal:
                for req in bad_payloads:
                    result = server.request_secret({**req, "project_dir": str(root)})
                    self.assertTrue(result["isError"], req)
                    self.assertNotIn("FAKE_NOT_ALLOWED", json.dumps(result))
                modal.assert_not_called()
            self.assertFalse((root / ".env").exists())

    def test_swift_gui_receives_only_variable_names_in_stdin_and_returns_values_locally(self):
        synthetic = {"status": "entered", "values": {"EXAMPLE_KEY": "FixtureOnly456", "SECOND": "AnotherFake99"}}
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(synthetic), stderr="")
        with mock.patch.object(server.platform, "system", return_value="Darwin"), \
             mock.patch.object(server, "dialog_binary", return_value=Path("/fake/native-dialog")), \
             mock.patch.object(server.subprocess, "run", return_value=proc) as runner:
            values = server.native_dialog([{"name": "EXAMPLE_KEY"}, {"name": "SECOND"}], "/tmp/test/.env")
        self.assertEqual(values, synthetic["values"])
        args, kwargs = runner.call_args
        self.assertEqual(args[0][0], "/fake/native-dialog")
        self.assertEqual(json.loads(kwargs["input"])["fields"][0]["name"], "EXAMPLE_KEY")
        self.assertNotIn("FixtureOnly456", json.dumps(args[0]))
        self.assertNotIn("FixtureOnly456", kwargs["input"])
        self.assertTrue(kwargs["capture_output"])

    def test_mcp_stdio_handshake_and_multi_schema(self):
        payload = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "synthetic-test", "version": "1.0"}
            }},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        reply = subprocess.run(
            [sys.executable, "-I", str(ROOT / "server" / "mcp_server.py")],
            input="\n".join(json.dumps(msg) for msg in payload) + "\n",
            capture_output=True, text=True, check=True, timeout=5,
        )
        lines = [json.loads(line) for line in reply.stdout.splitlines()]
        self.assertEqual(len(lines), 2, reply)
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], "secret-drop-local")
        self.assertEqual(lines[0]["result"]["serverInfo"]["version"], "0.3.0")
        schema = lines[1]["result"]["tools"][0]["inputSchema"]
        self.assertIn("secrets", schema["properties"])
        self.assertEqual(schema["properties"]["secrets"]["maxItems"], 12)
        self.assertNotIn("value", schema["properties"])
        self.assertEqual(reply.stderr, "")

    def test_github_only_multi_opt_in_does_not_write_env_or_leak(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            fake_values = {"DEMO_KEY": "FakeNoNetwork123", "SECOND": "AnotherFixture456"}
            with self._fake_home(root), \
                 mock.patch.object(server, "native_dialog", return_value=fake_values), \
                 mock.patch.object(server, "write_github", return_value=True) as gh:
                result = server.request_secret({
                    "secrets": [{"name": "DEMO_KEY"}, {"name": "SECOND"}],
                    "project_dir": str(root),
                    "destination": "github", "github_repo": "example/demo",
                })
            self.assertFalse(result["isError"])
            self.assertFalse((root / ".env").exists())
            self.assertEqual(gh.call_count, 2)
            self.assertEqual(gh.call_args_list[0].args[:2], ("DEMO_KEY", "example/demo"))
            for value in fake_values.values():
                self.assertNotIn(value, json.dumps(result))


    def test_partial_save_reports_each_unfilled_name(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            fields = [{"name": "TEST_ONE"}, {"name": "TEST_TWO"}, {"name": "TEST_THREE"}]
            fake = "Dummy-Only-111"
            with self._fake_home(root), mock.patch.object(
                server, "native_dialog", return_value={"TEST_TWO": fake}
            ):
                output = server.request_secret({"secrets": fields, "project_dir": str(root)})
            self.assertFalse(output["isError"], output)
            self.assertEqual((root / ".env").read_text(), "TEST_TWO=Dummy-Only-111\n")
            self.assertEqual(stat.S_IMODE((root / ".env").stat().st_mode), 0o600)
            report = json.dumps(output)
            self.assertIn("TEST_TWO", report)
            self.assertIn("TEST_ONE", report)
            self.assertIn("TEST_THREE", report)
            self.assertIn("Skipped", report)
            self.assertNotIn(fake, report)

    def test_partial_save_preserves_previous_env_and_skipped_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            (root / ".env").write_text("TEST_TWO=previous-fixture\nKEEP=untouched\n")
            with self._fake_home(root), mock.patch.object(
                server, "native_dialog", return_value={"TEST_ONE": "New-Fake-123"}
            ):
                output = server.request_secret({
                    "secrets": [{"name": "TEST_ONE"}, {"name": "TEST_TWO"}],
                    "project_dir": str(root),
                })
            self.assertFalse(output["isError"])
            self.assertEqual(
                (root / ".env").read_text(),
                "TEST_TWO=previous-fixture\nKEEP=untouched\nTEST_ONE=New-Fake-123\n",
            )
            self.assertIn("TEST_TWO", json.dumps(output))
            self.assertIn("Skipped", json.dumps(output))

    def test_all_fields_left_blank_reports_no_save(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with self._fake_home(root), mock.patch.object(
                server, "native_dialog", return_value={}
            ):
                output = server.request_secret({
                    "secrets": [{"name": "TEST_ONE"}, {"name": "TEST_TWO"}],
                    "project_dir": str(root),
                })
            self.assertTrue(output["isError"])
            self.assertFalse((root / ".env").exists())
            self.assertIn("No values", json.dumps(output))
            self.assertIn("TEST_ONE", json.dumps(output))
            self.assertIn("TEST_TWO", json.dumps(output))

    def test_native_dialog_accepts_partial_subset_of_requested_fields(self):
        response = {"status": "entered", "values": {"TEST_TWO": "Only-Dummy-987"}}
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(response), stderr="")
        fields = [{"name": "TEST_ONE"}, {"name": "TEST_TWO"}]
        with mock.patch.object(server.platform, "system", return_value="Darwin"), \
             mock.patch.object(server, "dialog_binary", return_value=Path("/fake/native-dialog")), \
             mock.patch.object(server.subprocess, "run", return_value=proc):
            values = server.native_dialog(fields, "/tmp/test/.env")
        self.assertEqual(values, {"TEST_TWO": "Only-Dummy-987"})

    def test_native_dialog_rejects_unrequested_variable(self):
        response = {"status": "entered", "values": {"EVIL": "Only-Dummy-987"}}
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(response), stderr="")
        fields = [{"name": "TEST_ONE"}, {"name": "TEST_TWO"}]
        with mock.patch.object(server.platform, "system", return_value="Darwin"), \
             mock.patch.object(server, "dialog_binary", return_value=Path("/fake/native-dialog")), \
             mock.patch.object(server.subprocess, "run", return_value=proc):
            with self.assertRaises(server.Cancelled):
                server.native_dialog(fields, "/tmp/test/.env")

    def test_github_partial_save_skips_empty_fields_without_external_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with self._fake_home(root), \
                 mock.patch.object(server, "native_dialog", return_value={"TEST_ONE": "DummyOnly321"}), \
                 mock.patch.object(server, "write_github", return_value=True) as gh:
                output = server.request_secret({
                    "secrets": [{"name": "TEST_ONE"}, {"name": "TEST_TWO"}],
                    "project_dir": str(root),
                    "destination": "github", "github_repo": "example/demo",
                })
            self.assertFalse(output["isError"])
            self.assertEqual(gh.call_count, 1)
            self.assertEqual(gh.call_args.args[:2], ("TEST_ONE", "example/demo"))
            self.assertIn("TEST_TWO", json.dumps(output))
            self.assertIn("Skipped", json.dumps(output))
            self.assertFalse((root / ".env").exists())
            self.assertNotIn("DummyOnly321", json.dumps(output))


if __name__ == "__main__":
    unittest.main()
