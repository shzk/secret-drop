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

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

guard = load("secret_drop_guard", ROOT / "hooks" / "prompt_guard.py")
helper = load("secret_drop_helper", ROOT / "bin" / "secret_drop.py")


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


if __name__ == "__main__":
    unittest.main()
