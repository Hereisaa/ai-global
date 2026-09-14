#!/usr/bin/env bash
# ai-global deploy script (macOS/Linux).
#
# Copies this clone's global AI config into the paths the tools actually read.
# Everything deployed is a REAL FILE - no symlinks - so moving or deleting this
# clone can never leave the machine with a dangling global config.
#
#   repo/governance   -> ~/.ai-global/governance   (rules SSOT the routers point at)
#   repo/claude/*     -> ~/.claude/*
#   repo/codex/*      -> ~/.codex/*
#
# Usage: install.sh [install|check]
#   install  deploy (idempotent; anything replaced is kept in trash)
#   check    report drift, change nothing (exit 1 if anything needs attention)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-install}"
TARGET_HOME="${AI_GLOBAL_TARGET_HOME:-$HOME}"
GLOBAL="$TARGET_HOME/.ai-global"
STATE="$GLOBAL/.deploy-state.json"
TRASH="$TARGET_HOME/.ai-trash/ai-global-deploy-$(date +%Y%m%d-%H%M%S)-$$"
FAIL=0

case "$MODE" in
  install|check) ;;
  *) echo "usage: install.sh [install|check]" >&2; exit 2 ;;
esac

# State from the previous deploy on this machine (~/.ai-global/.deploy-state.json):
#   files    blob hash of every file as deployed. A deployed file that still
#            matches its recorded hash was not touched since -> BEHIND (safe to
#            update); anything else -> EDITED (needs a human). Hashes rather
#            than a commit, so deploying from a dirty worktree stays accurate.
#   managed  repo-relative paths of the item-level deploys (skills, commands,
#            agents). An item the repo no longer has must be removed, or the
#            tool keeps loading a skill that no longer exists upstream.
#   commit   informational only.
PREV_COMMIT=""
PREV_MANAGED=""
if [ -f "$STATE" ]; then
  PREV_COMMIT="$(sed -n 's/.*"commit"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$STATE" | head -1)"
  PREV_MANAGED="$(sed -n '/"managed"/,/\]/p' "$STATE" | grep -o '"claude/[^"]*"' | tr -d '"' || true)"
fi
MANAGED=""
FILES=""

prev_hash() { # prev_hash <repo-rel> -> blob hash recorded at the last deploy, or ""
  [ -f "$STATE" ] || return 0
  grep -F "\"$1\":" "$STATE" | sed -n 's/.*:[[:space:]]*"\([0-9a-f]*\)".*/\1/p' | head -1
}

backup() { # backup <path> - never delete, park in trash keeping the structure
  local p="$1" label="${1#"$TARGET_HOME"/}"
  mkdir -p "$TRASH/$(dirname "$label")"
  if [ -e "$TRASH/$label" ] || [ -L "$TRASH/$label" ]; then echo "trash destination exists" >&2; exit 1; fi
  mv "$p" "$TRASH/$label"
}

classify() { # classify <repo-rel> <dst> -> OK | MISSING | STALE | BEHIND | EDITED
  local rel="$1" dst="$2" prev dst_blob
  # Nothing deployed is ever a link, so any link here is left over from an
  # older install - dangling or not.
  if [ -L "$dst" ]; then echo STALE; return; fi
  if [ ! -e "$dst" ]; then echo MISSING; return; fi
  if [ -f "$dst" ] && cmp -s "$REPO/$rel" "$dst"; then echo OK; return; fi
  if [ -f "$dst" ]; then
    prev="$(prev_hash "$rel")"
    dst_blob="$(git -C "$REPO" hash-object "$dst" 2>/dev/null || true)"
    if [ -n "$prev" ] && [ "$prev" = "$dst_blob" ]; then echo BEHIND; return; fi
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
  # Record what is deployed after this run, whether or not we had to copy.
  FILES="$FILES"$'\n'"$rel|$(git -C "$REPO" hash-object "$REPO/$rel")"
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
  if [ "$MODE" != check ]; then
    # A directory left as a symlink by an older install must go first, otherwise
    # every copy below would be written straight back into the repo.
    if [ -L "$dst" ]; then
      echo "UNLINK  $dst (link left by an older install)"
      backup "$dst"
    elif [ -e "$dst" ] && [ ! -d "$dst" ]; then
      echo "WARN    $dst is a file where a directory belongs; the old copy goes to trash"
      backup "$dst"
    fi
  fi
  while IFS= read -r f; do
    put "$rel/$f" "$dst/$f"
  done < <(cd "$REPO/$rel" && find . -type f | sed 's|^\./||' | sort)
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

manage() { # manage <repo-rel> - record an item-level deploy for the next run
  MANAGED="$MANAGED"$'\n'"$1"
}

echo "repo:   $REPO"
echo "target: $GLOBAL + ~/.claude + ~/.codex"
echo

put_dir "governance"            "$GLOBAL/governance"

# ~/.ai-global is owned by this script outright, so anything at its top level
# that this version does not deploy is a leftover from an older layout.
if [ -d "$GLOBAL" ]; then
  for e in "$GLOBAL"/* "$GLOBAL"/.[!.]*; do
    [ -e "$e" ] || [ -L "$e" ] || continue
    case "$(basename "$e")" in governance|.deploy-state.json) continue ;; esac
    if [ "$MODE" = check ]; then
      echo "EXTRA   $e - no longer deployed here"; FAIL=1
    else
      backup "$e"
      echo "DROP    $e -> trash"
    fi
  done
fi

put_dir "claude/hooks"          "$TARGET_HOME/.claude/hooks"
put     "claude/CLAUDE.md"      "$TARGET_HOME/.claude/CLAUDE.md"
put     "claude/statusline.sh"  "$TARGET_HOME/.claude/statusline.sh"
put     "codex/AGENTS.md"       "$TARGET_HOME/.codex/AGENTS.md"

# Repo-owned skills/commands/agents are deployed item by item so third-party
# installs keep coexisting in the same parent directories.
for d in "$REPO"/claude/skills/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  if [ -e "$TARGET_HOME/.claude/ai-global-disabled/skills/$n" ]; then
    echo "DISABLED claude/skills/$n - preserving local choice"
    put_dir "claude/skills/$n" "$TARGET_HOME/.claude/ai-global-disabled/skills/$n"
  else
    put_dir "claude/skills/$n" "$TARGET_HOME/.claude/skills/$n"
  fi
  manage "claude/skills/$n"
done
for f in "$REPO"/claude/commands/*; do
  [ -f "$f" ] || continue
  n="$(basename "$f")"
  if [ "$n" = .gitkeep ]; then continue; fi
  if [ -e "$TARGET_HOME/.claude/ai-global-disabled/commands/$n" ]; then
    echo "DISABLED claude/commands/$n - preserving local choice"
    put "claude/commands/$n" "$TARGET_HOME/.claude/ai-global-disabled/commands/$n"
  else
    put "claude/commands/$n" "$TARGET_HOME/.claude/commands/$n"
  fi
  manage "claude/commands/$n"
done
for f in "$REPO"/claude/agents/*; do
  [ -f "$f" ] || continue
  n="$(basename "$f")"
  if [ "$n" = .gitkeep ]; then continue; fi
  put "claude/agents/$n" "$TARGET_HOME/.claude/agents/$n"
  manage "claude/agents/$n"
done

# Items deployed last time that the repo no longer has (a renamed or removed
# skill, command or agent).
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  case $'\n'"$MANAGED"$'\n' in *$'\n'"$rel"$'\n'*) continue ;; esac
  dst="$TARGET_HOME/.claude/${rel#claude/}"
  if [ ! -e "$dst" ] && [ ! -L "$dst" ]; then continue; fi
  if [ "$MODE" = check ]; then
    echo "EXTRA   $dst - no longer in repo"; FAIL=1
  else
    backup "$dst"
    echo "DROP    $dst -> trash"
  fi
done <<< "$PREV_MANAGED"

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

managed_json=""
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  if [ -n "$managed_json" ]; then managed_json="$managed_json,"$'\n'; fi
  managed_json="$managed_json    \"$rel\""
done <<< "$MANAGED"
files_json=""
while IFS= read -r entry; do
  [ -n "$entry" ] || continue
  if [ -n "$files_json" ]; then files_json="$files_json,"$'\n'; fi
  files_json="$files_json    \"${entry%%|*}\": \"${entry#*|}\""
done <<< "$FILES"

mkdir -p "$GLOBAL"
cat > "$STATE" <<JSON
{
  "source_repo": "$REPO",
  "commit": "$HEAD_COMMIT",
  "branch": "$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platform": "$(uname -s)",
  "managed": [
$managed_json
  ],
  "files": {
$files_json
  }
}
JSON
echo "STATE   $STATE -> ${HEAD_COMMIT:0:9}"

# Remind after a pull. Deliberately does not auto-deploy, so a pull can never
# silently overwrite something that was edited on this machine. post-merge
# covers plain/ff pulls, post-rewrite covers `pull --rebase`.
if [ -d "$REPO/.git/hooks" ]; then
  if [ ! -e "$REPO/.git/hooks/post-merge" ] && [ ! -L "$REPO/.git/hooks/post-merge" ]; then
  cat > "$REPO/.git/hooks/post-merge" <<'HOOK'
#!/bin/sh
echo "ai-global: pull done -> run setup/install.sh check (or /ai-global in Claude Code)"
HOOK
  chmod +x "$REPO/.git/hooks/post-merge"
  fi
  if [ ! -e "$REPO/.git/hooks/post-rewrite" ] && [ ! -L "$REPO/.git/hooks/post-rewrite" ]; then
  cat > "$REPO/.git/hooks/post-rewrite" <<'HOOK'
#!/bin/sh
[ "$1" = rebase ] && echo "ai-global: pull --rebase done -> run setup/install.sh check (or /ai-global in Claude Code)"
exit 0
HOOK
  chmod +x "$REPO/.git/hooks/post-rewrite"
  fi
fi

if [ -d "$TRASH" ]; then
  echo
  echo "NOTE: replaced items are in $TRASH (confirm, then empty manually)"
fi
echo "deploy complete"
