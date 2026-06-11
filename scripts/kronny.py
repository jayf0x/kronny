#!/usr/bin/env python3
"""Kronny CLI — set time-limited auto-approve windows for Claude Code.

Usage:
  kronny.py                  # allow everything for 5 minutes, scoped to cwd
  kronny.py 5                # same
  kronny.py 15 "gh *"        # allow bash commands matching "gh *" for 15 minutes
  kronny.py -1               # allow everything for 24 hours
  kronny.py 15 --global      # window valid in any directory (-g works too)
  kronny.py off              # cancel the active window
  kronny.py status           # show the active window, if any

Windows are scoped to the directory they were set in (and its subdirectories)
unless --global is passed. Maximum duration is 24 hours.

State dir: KRONNY_STATE_DIR (env) or ~/.claude/kronny/
"""
import json
import os
import sys
import time
from datetime import datetime

_DEFAULT_STATE_DIR = os.path.expanduser("~/.claude/kronny")
STATE_DIR = os.environ.get("KRONNY_STATE_DIR", _DEFAULT_STATE_DIR)
STATE_FILE = os.path.join(STATE_DIR, "state.json")

MAX_MINUTES = 24 * 60


def _fmt_until(expires_at):
    return datetime.fromtimestamp(expires_at).strftime("%H:%M:%S")


def cmd_off():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("[kronny] Window cancelled.")
    else:
        print("[kronny] No active window.")


def cmd_status():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (OSError, ValueError):
        print("[kronny] No active window.")
        return

    expires_at = int(state.get("expires_at", 0))
    remaining = expires_at - int(time.time())
    if remaining <= 0:
        print("[kronny] No active window (last one expired).")
        return

    pattern = state.get("pattern", "*")
    scope = state.get("scope")
    target = "ALL tools" if pattern == "*" else f"bash '{pattern}'"
    where = scope if scope else "any directory"
    print(
        f"[kronny] Approving {target} until {_fmt_until(expires_at)} "
        f"({remaining // 60}m {remaining % 60}s left), scope: {where}"
    )


def main():
    args = sys.argv[1:]

    if args and args[0] in ("off", "stop", "cancel"):
        cmd_off()
        return
    if args and args[0] == "status":
        cmd_status()
        return

    scoped = True
    if "--global" in args or "-g" in args:
        scoped = False
        args = [a for a in args if a not in ("--global", "-g")]

    minutes = 5
    pattern = "*"

    if args:
        try:
            minutes = int(args[0])
        except ValueError:
            print(
                f"Error: first argument must be an integer (minutes), "
                f"'off', or 'status'; got: {args[0]!r}",
                file=sys.stderr,
            )
            sys.exit(1)
        if len(args) > 1:
            pattern = args[1]

    if minutes == -1:
        minutes = MAX_MINUTES
    elif minutes <= 0:
        print(
            f"Error: minutes must be a positive integer or -1 (24h), got: {minutes}",
            file=sys.stderr,
        )
        sys.exit(1)
    elif minutes > MAX_MINUTES:
        print(
            f"Error: maximum window is 24 hours ({MAX_MINUTES} minutes), got: {minutes}",
            file=sys.stderr,
        )
        sys.exit(1)

    now = int(time.time())
    expires_at = now + minutes * 60
    scope = os.getcwd() if scoped else None

    os.makedirs(STATE_DIR, exist_ok=True)
    state = {
        "expires_at": expires_at,
        "pattern": pattern,
        "scope": scope,
        "notified": False,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

    until = _fmt_until(expires_at)
    target = "ALL tools" if pattern == "*" else f"bash '{pattern}'"
    where = f"in {scope}" if scope else "in any directory"
    print(f"[kronny] Auto-approving {target} until {until} ({minutes}m), {where}.")


if __name__ == "__main__":
    main()
