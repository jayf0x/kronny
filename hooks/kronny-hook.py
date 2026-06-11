#!/usr/bin/env python3
"""Kronny PreToolUse hook — auto-approves tool calls during active windows.

Reads state from KRONNY_STATE_FILE (env) or ~/.claude/kronny/state.json.
State schema:
  {"expires_at": <unix_ts>, "pattern": "<glob>", "scope": "<dir>|null", "notified": <bool>}

A window only approves tool calls from sessions whose working directory is
inside `scope` (set to null by `kronny.py --global` to disable scoping).

Output (stdout, JSON):
  {"decision": "approve"}           — inside active window, scope + pattern matched
  {"additionalContext": "..."}      — window just expired (once only)
  (empty)                           — no active window / scope or pattern mismatch

Always exits 0 — must never crash Claude Code.
"""
import fnmatch
import json
import os
import sys
import time

_DEFAULT_STATE_FILE = os.path.expanduser("~/.claude/kronny/state.json")
STATE_FILE = os.environ.get("KRONNY_STATE_FILE", _DEFAULT_STATE_FILE)


def _load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        return json.load(f)


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def _in_scope(scope, cwd):
    if not scope:
        return True
    if not cwd:
        return False
    scope = os.path.realpath(scope)
    cwd = os.path.realpath(cwd)
    return cwd == scope or cwd.startswith(scope.rstrip(os.sep) + os.sep)


def _matches(pattern, tool_name, tool_input):
    if pattern == "*":
        return True
    # Non-wildcard patterns are bash-command globs — only match the Bash tool.
    if tool_name != "Bash":
        return False
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    return fnmatch.fnmatch(command, pattern)


def main():
    try:
        raw = sys.stdin.read()
        tool_call = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    try:
        state = _load_state()
    except Exception:
        sys.exit(0)

    if state is None:
        sys.exit(0)

    try:
        expires_at = int(state.get("expires_at", 0))
        pattern = state.get("pattern", "*")
        scope = state.get("scope")
        notified = bool(state.get("notified", False))
        now = int(time.time())

        if now >= expires_at:
            if not notified:
                state["notified"] = True
                _save_state(state)
                print(json.dumps({
                    "additionalContext": "[kronny] Auto-approve window expired."
                }))
            sys.exit(0)

        if not _in_scope(scope, tool_call.get("cwd", "")):
            sys.exit(0)

        tool_name = tool_call.get("tool_name", "")
        tool_input = tool_call.get("tool_input", {})

        if _matches(pattern, tool_name, tool_input):
            print(json.dumps({"decision": "approve"}))

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
