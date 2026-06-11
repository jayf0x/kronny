---
description: Set a time-limited auto-approve window so Claude can run tools without permission prompts. Scoped to the current project by default. Pattern defaults to * (all tools); pass a bash glob to restrict to matching commands. Subcommands: off, status.
---

Run this command via the Bash tool, passing the user's arguments through verbatim:

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/kronny.py" $ARGUMENTS

Show the user the output line from the command (it describes what was set and until when).
Do not add explanation unless the command errors.

Usage reference:

    /kronny              — allow everything for 5 minutes, scoped to this project
    /kronny 5            — same
    /kronny 15 "gh *"    — allow bash commands matching "gh *" for 15 minutes
    /kronny -1           — allow everything for 24 hours
    /kronny 15 --global  — window valid in any directory
    /kronny off          — cancel the active window
    /kronny status       — show the active window
