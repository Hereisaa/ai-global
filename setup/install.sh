#!/usr/bin/env bash
# ai-global deploy script (macOS/Linux).
#
# Copies this clone's global AI config into the paths the tools actually read.
# Everything deployed is a REAL FILE - no symlinks - so moving or deleting this
# clone can never leave the machine with a dangling global config.
#
#   repo/governance   -> ~/.ai-global/governance   (rules SSOT the routers point at)
#   repo/manifest     -> ~/.ai-global/manifest
#   repo/claude/*     -> ~/.claude/*
#   repo/codex/*      -> ~/.codex/*
#
# Usage: install.sh [install|check]
#   install  deploy (idempotent; anything replaced is kept in trash)
#   check    report drift, change nothing (exit 1 if anything needs attention)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-install}"
GLOBAL="$HOME/.ai-global"
STATE="$GLOBAL/.deploy-state.json"
TRASH="$HOME/.ai-trash/ai-global-deploy-$(date +%Y%m%d-%H%M%S)"
FAIL=0

case "$MODE" in
  install|check) ;;
  *) echo "usage: install.sh [install|check]" >&2; exit 2 ;;
esac

# Commit this machine was last deployed from. Lets check tell "the repo moved
# on" (safe to update) apart from "someone edited the deployed copy" (review).
PREV_COMMIT=""
if [ -f "$STATE" ]; then
  PREV_COMMIT="$(sed -n 's/.*"commit"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$STATE" | head -1)"
fi

backup() { # backup <path> - never delete, park in trash keeping the structure
  local p="$1" label="${1#"$HOME"/}"
  mkdir -p "$TRASH/$(dirname "$label")"
  mv "$p" "$TRASH/$label"
}

classify() { # classify <repo-rel> <dst> -> OK | MISSING | STALE | BEHIND | EDITED
  local rel="$1" dst="$2" prev_blob dst_blob
  # Nothing deployed is ever a link, so any link here is left over from an
  # older install - dangling or not.
  if [ -L "$dst" ]; then echo STALE; return; fi
  if [ ! -e "$dst" ]; then echo MISSING; return; fi
  if [ -f "$dst" ] && cmp -s "$REPO/$rel" "$dst"; then echo OK; return; fi
  if [ -n "$PREV_COMMIT" ] && [ -f "$dst" ]; then
    prev_blob="$(git -C "$REPO" rev-parse "$PREV_COMMIT:$rel" 2>/dev/null || true)"
    dst_blob="$(git -C "$REPO" hash-object "$dst" 2>/dev/null || true)"
    if [ -n "$prev_blob" ] && [ "$prev_blob" = "$dst_blob" ]; then echo BEHIND; return; fi
  fi
  echo EDITED
}

put() { # put <repo-rel> <dst> - deploy one file
  local rel="$1" dst="$2" st
  if [ ! -f "$REPO/$rel" ]; then echo "SKIP    $rel missing in repo"; return; fi
  st="$(classify "$rel" "$dst")"
  if [ "$MODE" = check ]; then
    case "$st" in
      OK)      echo "OK      $dst" ;;
      MISSING) echo "MISSING $dst - not deployed yet";                                FAIL=1 ;;
      STALE)   echo "STALE   $dst - dangling link left by an older install";          FAIL=1 ;;
      BEHIND)  echo "BEHIND  $dst - repo moved on, run install to update";            FAIL=1 ;;
      EDITED)  echo "EDITED  $dst - changed outside the repo, review before install"; FAIL=1 ;;
    esac
    return
  fi
  if [ "$st" = OK ]; then return; fi
  if [ "$st" = EDITED ]; then
    echo "WARN    $dst differed from the repo; the old copy goes to trash"
  fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then backup "$dst"; fi
  mkdir -p "$(dirname "$dst")"
  cp "$REPO/$rel" "$dst"
  case "$dst" in *.sh) chmod +x "$dst" ;; esac
  echo "PUT     $dst"
}

put_dir() { # put_dir <repo-rel-dir> <dst-dir> - mirror a repo-owned directory
  local rel="$1" dst="$2" f
  if [ ! -d "$REPO/$rel" ]; then echo "SKIP    $rel missing in repo"; return; fi
  # A directory left as a symlink by an older install must go first, otherwise
  # every copy below would be written straight back into the repo.
  if [ "$MODE" != check ] && [ -L "$dst" ]; then
    echo "UNLINK  $dst (link left by an older install)"
    backup "$dst"
  fi
  while IFS= read -r f; do
    put "$rel/$f" "$dst/$f"
  done < <(cd "$REPO/$rel" && find . -type f ! -name .gitkeep ! -path './backups/*' | sed 's|^\./||' | sort)
  # Skip the extras scan while the destination is still a link: install already
  # unlinked it above, and in check mode every file under it is reported anyway.
  if [ -L "$dst" ] || [ ! -d "$dst" ]; then return; fi
  # files that no longer exist in the repo
  while IFS= read -r f; do
    if [ -e "$REPO/$rel/$f" ]; then continue; fi
    if [ "$MODE" = check ]; then
      echo "EXTRA   $dst/$f - no longer in repo"; FAIL=1
    else
      backup "$dst/$f"
      echo "DROP    $dst/$f -> trash"
    fi
  done < <(cd "$dst" && find . -type f | sed 's|^\./||' | sort)
}

echo "repo:   $REPO"
echo "target: $GLOBAL + ~/.claude + ~/.codex"
echo

put_dir "governance"            "$GLOBAL/governance"
put_dir "manifest"              "$GLOBAL/manifest"
put_dir "claude/hooks"          "$HOME/.claude/hooks"
put     "claude/CLAUDE.md"      "$HOME/.claude/CLAUDE.md"
put     "claude/statusline.sh"  "$HOME/.claude/statusline.sh"
put     "codex/AGENTS.md"       "$HOME/.codex/AGENTS.md"

# Repo-owned skills/commands/agents are deployed item by item so third-party
# installs keep coexisting in the same parent directories.
for d in "$REPO"/claude/skills/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  put_dir "claude/skills/$n" "$HOME/.claude/skills/$n"
done
for f in "$REPO"/claude/commands/*; do
  [ -f "$f" ] || continue
  n="$(basename "$f")"
  if [ "$n" = .gitkeep ]; then continue; fi
  put "claude/commands/$n" "$HOME/.claude/commands/$n"
done
for f in "$REPO"/claude/agents/*; do
  [ -f "$f" ] || continue
  n="$(basename "$f")"
  if [ "$n" = .gitkeep ]; then continue; fi
  put "claude/agents/$n" "$HOME/.claude/agents/$n"
done

HEAD_COMMIT="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"

if [ "$MODE" = check ]; then
  echo
  if [ -z "$PREV_COMMIT" ]; then
    echo "STATE   never deployed on this machine"
  elif [ "$PREV_COMMIT" != "$HEAD_COMMIT" ]; then
    echo "STATE   deployed from ${PREV_COMMIT:0:9}, repo HEAD is ${HEAD_COMMIT:0:9}"
  else
    echo "STATE   deployed from ${PREV_COMMIT:0:9} (current)"
  fi
  if [ "$FAIL" -eq 0 ]; then
    echo "global deployment is in sync"
  else
    echo "out of sync - run: bash $REPO/setup/install.sh"
    exit 1
  fi
  exit 0
fi

mkdir -p "$GLOBAL"
cat > "$STATE" <<JSON
{
  "source_repo": "$REPO",
  "commit": "$HEAD_COMMIT",
  "branch": "$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platform": "$(uname -s)"
}
JSON
echo "STATE   $STATE -> ${HEAD_COMMIT:0:9}"

# Remind after a pull. Deliberately does not auto-deploy, so a pull can never
# silently overwrite something that was edited on this machine.
if [ -d "$REPO/.git/hooks" ]; then
  cat > "$REPO/.git/hooks/post-merge" <<'HOOK'
#!/bin/sh
echo "ai-global: pull 完成 -> 跑 setup/install.sh check 看全域部署要不要更新"
HOOK
  chmod +x "$REPO/.git/hooks/post-merge"
fi

if [ -d "$TRASH" ]; then
  echo
  echo "NOTE: replaced items are in $TRASH (confirm, then empty manually)"
fi
echo "deploy complete"
