#!/usr/bin/env bash
# Uninstall kronny — removes hook, command, and skill. State dir preserved.
set -euo pipefail

STATE_DIR="$HOME/.claude/kronny"
SETTINGS="$HOME/.claude/settings.json"
CMD_DEST="$HOME/.claude/commands/kronny.toml"
SKILLS_DIR="$HOME/.claude/skills/kronny"

echo "Uninstalling kronny..."

# Remove hook scripts
for f in kronny-hook.py kronny.py; do
  if [[ -f "$STATE_DIR/$f" ]]; then
    rm "$STATE_DIR/$f"
    echo "  Removed: $STATE_DIR/$f"
  fi
done

# Remove slash command
if [[ -f "$CMD_DEST" ]]; then
  rm "$CMD_DEST"
  echo "  Removed: $CMD_DEST"
fi

# Remove skill
if [[ -d "$SKILLS_DIR" ]]; then
  rm -rf "$SKILLS_DIR"
  echo "  Removed: $SKILLS_DIR"
fi

# Patch out PreToolUse hook from settings.json
if [[ -f "$SETTINGS" ]]; then
  python3 - <<PYEOF
import json, sys

settings_path = '$SETTINGS'

try:
    with open(settings_path) as f:
        s = json.load(f)
except Exception:
    sys.exit(0)

ptu = s.get('hooks', {}).get('PreToolUse', [])
filtered = [
    h for h in ptu
    if not any('kronny-hook.py' in e.get('command', '') for e in h.get('hooks', []))
]
s.setdefault('hooks', {})['PreToolUse'] = filtered

with open(settings_path, 'w') as f:
    json.dump(s, f, indent=2)
    f.write('\n')

print('  Removed PreToolUse hook from settings.json')
PYEOF
fi

echo ""
echo "Done. State preserved at: $STATE_DIR"
echo "To fully clean up: rm -rf \"$STATE_DIR\""
