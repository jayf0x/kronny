<div align="center">

# ⏱️ kronny

**Time-limited auto-approve windows for Claude Code.**

Stop pressing "yes" 40 times — without turning permissions off forever.

</div>

---

```
/kronny              # approve everything for 5 min
/kronny 15 "gh *"    # approve only "gh *" bash commands for 15 min
/kronny -1           # approve everything for 24h (max)
/kronny off          # cancel early
/kronny status       # what's active?
```

When the window expires, prompts come back automatically. No restart, no permanent config change, no "oops, that flag was still on."

<!-- demo gif goes here -->

## 🚀 Install

Requires Claude Code + `python3`.

```bash
claude plugin marketplace add jayf0x/kronny
claude plugin install kronny@kronny
```

Or from inside Claude Code: `/plugin marketplace add jayf0x/kronny`, then `/plugin install kronny@kronny`.

Restart Claude Code, then run `/kronny`. Remove with `claude plugin uninstall kronny@kronny`.

<details>
<summary>Manual install (no plugin system)</summary>

```bash
git clone https://github.com/jayf0x/kronny.git
cd kronny && ./install.sh
```

Remove with `./uninstall.sh`.

</details>

## ⚙️ How it works

`/kronny` writes a tiny state file with an expiry, a command pattern, and the project directory. A [PreToolUse hook](hooks/kronny-hook.py) checks it on every tool call and approves only while all three match. No daemon, no dependencies — ~100 lines of Python.

## 🔒 Security

- **Project-scoped by default** — a window only works in the directory it was set in (`--global` to opt out)
- **Always expires** — hard cap at 24h, no "permanently on" mode
- **Instant revoke** — `/kronny off`
- **Claude can't grant itself a window** — only you can, explicitly
- **Fail-closed** — missing or corrupt state means normal prompts

⚠️ Still a sharp tool: `/kronny -1` approves *everything* in that project for a day. Prefer short windows and command globs.

## License

[MIT](LICENSE)
