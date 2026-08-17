#!/usr/bin/env bash
# ai-global deploy script (macOS/Linux).
# Links global AI config from this repo into the locations the tools read.
# Never deletes: pre-existing real files/dirs are moved to ~/Developer/temp/trash/.
# Usage: install.sh [install|check]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-install}"
TRASH="$HOME/Developer/temp/trash/ai-global-install-$(date +%Y%m%d-%H%M%S)"
FAIL=0

link() { # link <source-in-repo> <link-path>
  local src="$1" dst="$2"
  if [ "$MODE" = "check" ]; then
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ] && [ -e "$dst" ]; then
      echo "OK    $dst"
    else
      echo "DRIFT $dst (expected -> $src)"
      FAIL=1
    fi
    return
  fi
  if [ ! -e "$src" ]; then
    echo "SKIP  $src missing in repo"
    return
  fi
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    return
  fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    mkdir -p "$TRASH"
    mv "$dst" "$TRASH/$(basename "$dst")"
    echo "MOVED $dst -> trash"
  fi
  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  echo "LINK  $dst -> $src"
}

link "$REPO/governance"           "$HOME/Developer/agent-governance"
link "$REPO/claude/CLAUDE.md"     "$HOME/.claude/CLAUDE.md"
link "$REPO/claude/statusline.sh" "$HOME/.claude/statusline.sh"
link "$REPO/claude/hooks"         "$HOME/.claude/hooks"
link "$REPO/codex/AGENTS.md"      "$HOME/.codex/AGENTS.md"

# Repo-owned skills/commands/agents are linked item-by-item so third-party
# installs can coexist in the same parent directories.
for d in "$REPO"/claude/skills/*/; do
  [ -d "$d" ] || continue
  link "${d%/}" "$HOME/.claude/skills/$(basename "$d")"
done
for f in "$REPO"/claude/commands/*; do
  { [ -f "$f" ] && [ "$(basename "$f")" != ".gitkeep" ]; } || continue
  link "$f" "$HOME/.claude/commands/$(basename "$f")"
done
for f in "$REPO"/claude/agents/*; do
  { [ -e "$f" ] && [ "$(basename "$f")" != ".gitkeep" ]; } || continue
  link "$f" "$HOME/.claude/agents/$(basename "$f")"
done

if [ "$MODE" = "check" ]; then
  if [ "$FAIL" -eq 0 ]; then
    echo "all links healthy"
  else
    echo "drift detected — run install.sh to repair"
    exit 1
  fi
else
  [ -d "$TRASH" ] && echo "NOTE: replaced items moved to $TRASH (confirm, then empty manually)"
  echo "deploy complete"
fi
