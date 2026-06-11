#!/usr/bin/env bash
# Install kronny — time-limited auto-approve windows for Claude Code.
# Installs:
#   1. Hook + CLI  → ~/.claude/kronny/
#   2. PreToolUse hook registered in ~/.claude/settings.json
#   3. Slash command → ~/.claude/commands/
#   4. Skill → ~/.claude/skills/kronny/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="$HOME/.claude/kronny"
SETTINGS="$HOME/.claude/settings.json"
COMMANDS_DIR="$HOME/.claude/commands"
SKILLS_DIR="$HOME/.claude/skills/kronny"

echo "Installing kronny..."

# ── 1. State dir + scripts ────────────────────────────────────────────────
mkdir -p "$STATE_DIR"
cp "$SCRIPT_DIR/hooks/kronny-hook.py" "$STATE_DIR/kronny-hook.py"
cp "$SCRIPT_DIR/scripts/kronny.py"   "$STATE_DIR/kronny.py"
chmod +x "$STATE_DIR/kronny-hook.py"
chmod +x "$STATE_DIR/kronny.py"
echo "  Scripts: $STATE_DIR/"

# ── 2. PreToolUse hook ────────────────────────────────────────────────────
if [[ ! -f "$SETTINGS" ]]; then
  printf '{"hooks":{"PreToolUse":[]}}\n' > "$SETTINGS"
fi

if python3 -c "
import json, sys
s = json.load(open('$SETTINGS'))
hooks = s.get('hooks', {}).get('PreToolUse', [])
for h in hooks:
    for entry in h.get('hooks', []):
        if 'kronny-hook.py' in entry.get('command', ''):
            sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
  echo "  Hook already registered in settings.json, skipping"
else
  HOOK_CMD="python3 $STATE_DIR/kronny-hook.py"
  python3 - <<PYEOF
import json

settings_path = '$SETTINGS'
hook_cmd = '$HOOK_CMD'

with open(settings_path) as f:
    s = json.load(f)

s.setdefault('hooks', {}).setdefault('PreToolUse', [])
entry = {'matcher': '.*', 'hooks': [{'type': 'command', 'command': hook_cmd}]}
s['hooks']['PreToolUse'].append(entry)

with open(settings_path, 'w') as f:
    json.dump(s, f, indent=2)
    f.write('\n')
PYEOF
  echo "  Registered PreToolUse hook in settings.json"
fi

# ── 3. Slash command ──────────────────────────────────────────────────────
# The repo copy uses ${CLAUDE_PLUGIN_ROOT} (plugin install); rewrite the CLI
# path to the manual-install location.
mkdir -p "$COMMANDS_DIR"
sed 's|"${CLAUDE_PLUGIN_ROOT}/scripts/kronny.py"|~/.claude/kronny/kronny.py|' \
  "$SCRIPT_DIR/commands/kronny.md" > "$COMMANDS_DIR/kronny.md"
echo "  Command: $COMMANDS_DIR/kronny.md"

# ── 4. Skill ──────────────────────────────────────────────────────────────
mkdir -p "$SKILLS_DIR"
cp "$SCRIPT_DIR/skills/kronny/SKILL.md" "$SKILLS_DIR/SKILL.md"
echo "  Skill:   $SKILLS_DIR/SKILL.md"

echo ""
echo "Done. Restart Claude Code for the hook to take effect."
echo ""
echo "Usage:"
echo "  /kronny              — approve everything for 5 min (this project only)"
echo "  /kronny 15           — approve everything for 15 min"
echo "  /kronny 15 \"gh *\"    — approve bash 'gh *' for 15 min"
echo "  /kronny -1           — approve everything for 24 h"
echo "  /kronny off          — cancel the window"
echo "  /kronny status       — show what's active"
