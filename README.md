# kronny

**Time-limited auto-approve windows for Claude Code.**

Claude Code asks permission for every tool call it isn't pre-authorized to make. That's the right default — but when you're babysitting a long refactor or a batch of `gh` commands, you end up pressing "yes" forty times in a row. The usual escape hatches are blunt: `--dangerously-skip-permissions` turns checks off for the whole session, and editing `settings.json` allowlists is permanent and fiddly.

Kronny is the middle ground: **approve everything (or just commands matching a glob) for the next N minutes, in this project only, then automatically go back to asking.** No restart, no permanent config change, no "oops, that flag was still on."

<!-- demo gif goes here -->

## Usage

```
/kronny              # approve everything for 5 minutes
/kronny 15           # approve everything for 15 minutes
/kronny 15 "gh *"    # approve only bash commands matching "gh *" for 15 minutes
/kronny -1           # approve everything for 24 hours (the maximum)
/kronny off          # cancel the window early
/kronny status       # what's active and how long is left
```

When the window expires, Claude is notified once and permission prompts resume.

## Install

Requires Claude Code and `python3`.

```bash
git clone https://github.com/jayf0x/kronny.git
cd kronny
./install.sh
```

Restart Claude Code, then run `/kronny` in any session.

To remove: `./uninstall.sh` (cleanly unregisters the hook and deletes the command and skill).

## How it works

`/kronny` writes a tiny state file (`~/.claude/kronny/state.json`) with an expiry timestamp, a command pattern, and the project directory it was set in. A [PreToolUse hook](hooks/kronny-hook.py) reads that file on every tool call and emits `{"decision": "approve"}` only while all three match. No daemon, no background process — about 100 lines of dependency-free Python.

## Security

Auto-approving tool calls is inherently a sharp tool. Kronny keeps the blast radius small:

- **Project-scoped by default.** A window set in `~/projects/foo` only approves tool calls from sessions working inside that directory. Use `--global` to opt out, explicitly.
- **Always time-limited.** Windows cap at 24 hours and expire on their own. There is no "permanently on" mode.
- **Easy to revoke.** `/kronny off` kills the window instantly; so does deleting the state file.
- **Claude can't grant itself a window** — the skill instructs it to only set windows when you explicitly ask, and the `/kronny` command itself goes through a normal permission prompt unless a window is already active.
- **Fail-closed.** Missing, expired, or corrupt state means no approval and a normal prompt.

It does not protect you from yourself: `/kronny -1` with the default `*` pattern means *anything* Claude tries in that project for 24 hours is approved. Prefer short windows and command globs.

## Tests

```bash
python3 tests/test_kronny.py
```

## License

[MIT](LICENSE)
