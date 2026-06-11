---
name: kronny
description: >
  Kronny manages time-limited auto-approve windows for Claude Code tool calls.
  Activated via the /kronny slash command. When a window is active, the PreToolUse
  hook auto-approves matching tools so Claude can work without permission prompts.
  Use when the user says /kronny, asks to set an auto-approve window, or wants to
  temporarily allow tools without confirmation.
---

# Kronny — Time-Limited Auto-Approve Windows

Kronny lets the user pre-authorize tool calls for a fixed duration by writing a
state file that the `kronny-hook.py` PreToolUse hook reads on every tool call.

## Slash command

```
/kronny              # allow everything for 5 minutes, scoped to this project
/kronny 5            # same
/kronny 15 "gh *"    # allow bash commands matching "gh *" for 15 minutes
/kronny -1           # allow everything for 24 hours
/kronny 15 --global  # window valid in any directory, not just this project
/kronny off          # cancel the active window
/kronny status       # show what's active and how long is left
```

The command runs `python3 ~/.claude/kronny/kronny.py [args]` via the Bash tool.

## State file

`~/.claude/kronny/state.json`:
```json
{
  "expires_at": 1717500000,
  "pattern": "*",
  "scope": "/path/to/project",
  "notified": false
}
```

- `expires_at` — Unix timestamp when the window closes
- `pattern` — `"*"` approves all tools; any other value is a bash-command glob
  (only matches `Bash` tool calls where the command fits the glob)
- `scope` — directory the window is bound to; only sessions working inside it
  (or a subdirectory) are auto-approved. `null` means any directory.
- `notified` — set to `true` after the expiry notification fires (prevents repeats)

## When invoked

If the user runs `/kronny [args]`, call the CLI via Bash and show the output.
Do not add commentary unless the command fails.

If the user asks "is kronny active?" or "how long is left?", run
`python3 ~/.claude/kronny/kronny.py status` and show the output.

Never set or extend a window on your own initiative — only when the user
explicitly asks for one.
