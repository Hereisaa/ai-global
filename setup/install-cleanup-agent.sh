#!/bin/bash
# Register (or remove) the launchd agent that runs
# ~/.claude/hooks/cleanup-orphans.sh --scope global every N hours and at load.
#
#   bash setup/install-cleanup-agent.sh
#   bash setup/install-cleanup-agent.sh --interval-hours 4
#   bash setup/install-cleanup-agent.sh --uninstall

set -eu

LABEL="com.claude.orphan-cleanup"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SCRIPT="$HOME/.claude/hooks/cleanup-orphans.sh"
INTERVAL_HOURS=2
UNINSTALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --interval-hours) INTERVAL_HOURS="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

domain="gui/$(id -u)"

if [ "$UNINSTALL" = 1 ]; then
  launchctl bootout "$domain/$LABEL" 2>/dev/null || true
  if [ -f "$PLIST" ]; then
    trash="$HOME/.ai-trash"
    mkdir -p "$trash"
    mv "$PLIST" "$trash/$LABEL.plist.$(date '+%Y%m%d-%H%M%S')"
  fi
  echo "Removed launchd agent $LABEL"
  exit 0
fi

[ -x "$SCRIPT" ] || { echo "Script not found or not executable: $SCRIPT (run setup/install.sh first)" >&2; exit 1; }

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.claude/logs"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SCRIPT</string>
    <string>--scope</string>
    <string>global</string>
  </array>
  <key>StartInterval</key><integer>$((INTERVAL_HOURS * 3600))</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardErrorPath</key><string>$HOME/.claude/logs/cleanup-agent.err</string>
</dict>
</plist>
PLIST_EOF

launchctl bootout "$domain/$LABEL" 2>/dev/null || true
launchctl bootstrap "$domain" "$PLIST"
echo "Registered $LABEL : every ${INTERVAL_HOURS}h + at load -> $SCRIPT"
echo "Log: $HOME/.claude/logs/cleanup.log"
