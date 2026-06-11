#!/usr/bin/env python3
"""Tests for kronny hook and CLI.

Run: python3 tests/test_kronny.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
HOOK = os.path.join(REPO_DIR, "hooks", "kronny-hook.py")
CLI = os.path.join(REPO_DIR, "scripts", "kronny.py")


class TestHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state_file = os.path.join(self.tmp, "state.json")
        self.env = {**os.environ, "KRONNY_STATE_FILE": self.state_file}

    def _run_hook(self, tool_call):
        return subprocess.run(
            [sys.executable, HOOK],
            input=json.dumps(tool_call),
            capture_output=True,
            text=True,
            env=self.env,
        )

    def _write_state(self, state):
        with open(self.state_file, "w") as f:
            json.dump(state, f)

    def _read_state(self):
        with open(self.state_file) as f:
            return json.load(f)

    def _active(self, **overrides):
        state = {
            "expires_at": int(time.time()) + 300,
            "pattern": "*",
            "scope": None,
            "notified": False,
        }
        state.update(overrides)
        return state

    # ── no state ────────────────────────────────────────────────────────────

    def test_no_state_file_exits_zero_no_output(self):
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    # ── active window ────────────────────────────────────────────────────────

    def test_active_window_wildcard_approves_bash(self):
        self._write_state(self._active())
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out.get("decision"), "approve")

    def test_active_window_wildcard_approves_non_bash(self):
        self._write_state(self._active())
        r = self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out.get("decision"), "approve")

    # ── directory scoping ────────────────────────────────────────────────────

    def test_scoped_window_approves_inside_scope(self):
        self._write_state(self._active(scope=self.tmp))
        r = self._run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": self.tmp,
        })
        self.assertEqual(json.loads(r.stdout).get("decision"), "approve")

    def test_scoped_window_approves_subdirectory(self):
        sub = os.path.join(self.tmp, "nested", "deeper")
        os.makedirs(sub)
        self._write_state(self._active(scope=self.tmp))
        r = self._run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": sub,
        })
        self.assertEqual(json.loads(r.stdout).get("decision"), "approve")

    def test_scoped_window_silent_outside_scope(self):
        other = tempfile.mkdtemp()
        self._write_state(self._active(scope=self.tmp))
        r = self._run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": other,
        })
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_scoped_window_silent_on_sibling_prefix_dir(self):
        # /tmp/x must not match scope /tmp/x-evil (prefix but not subpath)
        sibling = self.tmp + "-evil"
        os.makedirs(sibling, exist_ok=True)
        self._write_state(self._active(scope=self.tmp))
        r = self._run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": sibling,
        })
        self.assertEqual(r.stdout.strip(), "")

    def test_scoped_window_silent_when_cwd_missing(self):
        self._write_state(self._active(scope=self.tmp))
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_null_scope_approves_anywhere(self):
        self._write_state(self._active(scope=None))
        r = self._run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": tempfile.mkdtemp(),
        })
        self.assertEqual(json.loads(r.stdout).get("decision"), "approve")

    # ── pattern matching ─────────────────────────────────────────────────────

    def test_pattern_match_approves_matching_bash_command(self):
        self._write_state(self._active(pattern="gh *"))
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "gh repo list"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout).get("decision"), "approve")

    def test_pattern_match_skips_non_matching_bash_command(self):
        self._write_state(self._active(pattern="gh *"))
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_pattern_match_skips_non_bash_tool(self):
        self._write_state(self._active(pattern="gh *"))
        r = self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_glob_star_matches_any_suffix(self):
        self._write_state(self._active(pattern="git *"))
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}})
        self.assertEqual(json.loads(r.stdout).get("decision"), "approve")

    # ── expiry ───────────────────────────────────────────────────────────────

    def test_expired_window_notifies_once_then_silent(self):
        self._write_state(self._active(expires_at=int(time.time()) - 1))

        r1 = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r1.returncode, 0)
        out1 = json.loads(r1.stdout)
        self.assertIn("additionalContext", out1)
        self.assertIn("expired", out1["additionalContext"])

        # State must now have notified=True
        self.assertTrue(self._read_state()["notified"])

        # Second call — silent
        r2 = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r2.stdout.strip(), "")

    def test_expired_already_notified_is_silent(self):
        self._write_state(self._active(expires_at=int(time.time()) - 1, notified=True))
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    # ── resilience ───────────────────────────────────────────────────────────

    def test_bad_json_stdin_exits_zero(self):
        r = subprocess.run(
            [sys.executable, HOOK],
            input="not json !!!",
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(r.returncode, 0)

    def test_empty_stdin_exits_zero(self):
        r = subprocess.run(
            [sys.executable, HOOK],
            input="",
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(r.returncode, 0)

    def test_corrupt_state_file_exits_zero(self):
        with open(self.state_file, "w") as f:
            f.write("{ not valid json")
        r = self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r.returncode, 0)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = {**os.environ, "KRONNY_STATE_DIR": self.tmp}
        self.state_file = os.path.join(self.tmp, "state.json")

    def _run_cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, CLI] + list(args),
            capture_output=True,
            text=True,
            env=self.env,
            cwd=cwd,
        )

    def _read_state(self):
        with open(self.state_file) as f:
            return json.load(f)

    # ── defaults ─────────────────────────────────────────────────────────────

    def test_no_args_defaults_5_minutes_wildcard_scoped(self):
        r = self._run_cli(cwd=self.tmp)
        self.assertEqual(r.returncode, 0)
        state = self._read_state()
        self.assertEqual(state["pattern"], "*")
        self.assertFalse(state["notified"])
        self.assertEqual(os.path.realpath(state["scope"]), os.path.realpath(self.tmp))
        now = int(time.time())
        self.assertAlmostEqual(state["expires_at"], now + 300, delta=5)

    # ── duration variants ────────────────────────────────────────────────────

    def test_explicit_minutes(self):
        r = self._run_cli("15")
        self.assertEqual(r.returncode, 0)
        now = int(time.time())
        self.assertAlmostEqual(self._read_state()["expires_at"], now + 900, delta=5)

    def test_minus_one_means_24h(self):
        r = self._run_cli("-1")
        self.assertEqual(r.returncode, 0)
        now = int(time.time())
        self.assertAlmostEqual(self._read_state()["expires_at"], now + 86400, delta=5)

    def test_over_24h_fails(self):
        r = self._run_cli("1441")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("24 hours", r.stderr)

    # ── scoping ──────────────────────────────────────────────────────────────

    def test_scope_defaults_to_cwd(self):
        self._run_cli("5", cwd=self.tmp)
        self.assertEqual(
            os.path.realpath(self._read_state()["scope"]), os.path.realpath(self.tmp)
        )

    def test_global_flag_disables_scope(self):
        r = self._run_cli("5", "--global", cwd=self.tmp)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(self._read_state()["scope"])

    def test_short_global_flag(self):
        r = self._run_cli("5", "-g", cwd=self.tmp)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(self._read_state()["scope"])

    # ── pattern argument ─────────────────────────────────────────────────────

    def test_custom_pattern_stored(self):
        r = self._run_cli("15", "gh *")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self._read_state()["pattern"], "gh *")

    def test_wildcard_default_when_no_pattern(self):
        r = self._run_cli("10")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self._read_state()["pattern"], "*")

    # ── off / status ─────────────────────────────────────────────────────────

    def test_off_removes_state(self):
        self._run_cli("5")
        self.assertTrue(os.path.exists(self.state_file))
        r = self._run_cli("off")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.state_file))
        self.assertIn("cancelled", r.stdout)

    def test_off_without_window(self):
        r = self._run_cli("off")
        self.assertEqual(r.returncode, 0)
        self.assertIn("No active window", r.stdout)

    def test_status_active(self):
        self._run_cli("5", cwd=self.tmp)
        r = self._run_cli("status")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ALL tools", r.stdout)

    def test_status_no_window(self):
        r = self._run_cli("status")
        self.assertEqual(r.returncode, 0)
        self.assertIn("No active window", r.stdout)

    # ── notified reset ───────────────────────────────────────────────────────

    def test_notified_always_false_on_new_window(self):
        # Pre-write a state with notified=True so we can confirm it's reset.
        with open(self.state_file, "w") as f:
            json.dump({"expires_at": 0, "pattern": "*", "notified": True}, f)
        self._run_cli("5")
        self.assertFalse(self._read_state()["notified"])

    # ── output messages ──────────────────────────────────────────────────────

    def test_output_mentions_all_tools_for_wildcard(self):
        r = self._run_cli("5")
        self.assertIn("ALL tools", r.stdout)

    def test_output_mentions_pattern_for_restricted(self):
        r = self._run_cli("5", "gh *")
        self.assertIn("gh *", r.stdout)

    # ── error cases ──────────────────────────────────────────────────────────

    def test_non_integer_minutes_fails(self):
        r = self._run_cli("notanumber")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Error", r.stderr)

    def test_zero_minutes_fails(self):
        r = self._run_cli("0")
        self.assertNotEqual(r.returncode, 0)

    def test_negative_minutes_other_than_minus1_fails(self):
        r = self._run_cli("-5")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
