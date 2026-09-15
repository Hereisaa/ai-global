#!/bin/bash
# PreToolUse hook for the Bash tool (Claude Code). Enforces governance/50-safety:
# no rm / rmdir / unlink / shred / find -delete / PowerShell Remove-Item, even
# inside a compound command ("cd x && rm -rf y", "xargs rm", "$(rm ...)").
# The permissions deny list only matches a command's prefix; this looks at the
# whole line. Exit 2 blocks the call and hands the reason back to the model.
#
# Pure bash + grep + sed on purpose: no python, no perl. On Windows the only
# "python3" on PATH is often the Microsoft Store stub, and a guard that depends
# on an interpreter fails silently exactly where it matters. Claude Code treats
# any exit code other than 0/2 as "non-blocking", so this script must never
# crash: unparseable input is allowed through, but says so on stderr.
set -u

# Whole payload, newlines removed (the JSON is one object; a real newline inside
# the command arrives escaped as \n). A BOM from a PowerShell pipe is dropped.
payload=$(cat | tr -d '\r\n')
payload=${payload#$'\xef\xbb\xbf'}

if ! printf '%s' "$payload" | grep -Eq '"tool_name"[[:space:]]*:[[:space:]]*"Bash"'; then
  exit 0   # not a Bash call (or not JSON at all): nothing to guard
fi

# Extract the "command" string: everything up to the first unescaped quote.
raw=$(printf '%s' "$payload" | sed -En 's/.*"command"[[:space:]]*:[[:space:]]*"((\\.|[^"\\])*)".*/\1/p')
if [ -z "$raw" ] && ! printf '%s' "$payload" | grep -Eq '"command"[[:space:]]*:[[:space:]]*""'; then
  echo "ai-global guard-delete: hook 輸入裡找不到 command 欄位，本次未檢查刪除指令（紅線仍然有效）。" >&2
  exit 0
fi

# Undo JSON escapes with bash expansions only. Escaped backslashes go through a
# placeholder first so "\\n" (backslash + n) is not turned into a newline.
ph=$'\x01'
cmd=${raw//\\\\/$ph}
cmd=${cmd//\\\"/\"}
cmd=${cmd//\\n/$'\n'}
cmd=${cmd//\\t/$'\t'}
cmd=${cmd//\\r/}
cmd=${cmd//\\\//\/}
cmd=${cmd//$ph/\\}

# A delete verb counts only at the start of a (sub)command - after a separator,
# a keyword such as do/then/else, or inside sudo/xargs/exec/env - so "npm rm pkg"
# and "git rm --cached" stay allowed. A quote counts as a start only right after
# an interpreter flag (-c, -e, -Command), so grep 'rm -rf' is not a hit.
# Portable ERE: no \b, \s or lookarounds (BSD grep on macOS, GNU grep in Git Bash).
W='[^[:alnum:]_]'                                   # word boundary substitute
S='[[:space:]]'
LEAD="(^|[;&|(\`{]|\\\$\\(|(^|$W)(sudo|xargs|exec|command|nohup|env|do|then|else)($S+(-[^[:space:]]+|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*))*$S+|-(c|e|Command)$S*[\"'])$S*"
VERB='(\\|/[^[:space:]]*/)?'                       # \rm and /bin/rm are still rm

PATTERNS=(
  "${LEAD}${VERB}(rm|rmdir|unlink|shred)($W|\$)"
  "(^|$W)find$W[^;&|]*$S-delete($W|\$)"
  "${LEAD}git$S+clean[^;&|]*$S-[a-zA-Z]*f"
  "${LEAD}(npx$S+)?(rimraf|trash-put)($W|\$)"
  "(^|$W)rsync$W[^;&|]*$S--delete($W|\$)"
  "(shutil\\.rmtree|os\\.(remove|unlink|rmdir|removedirs)|\\.unlink|unlinkSync|rmSync|fs\\.(unlink|rm|rmdir))$S*\\("
)
PATTERNS_I=(
  "${LEAD}(Remove-Item|ri|rd|del|erase)([^-[:alnum:]_.]|\$)"   # PowerShell / cmd, case-insensitive
)

block() {
  snippet=$(printf '%s' "$1" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
  if [ ${#snippet} -gt 120 ]; then snippet="${snippet:0:117}..."; fi
  printf 'ai-global guard-delete: 擋下刪除指令 `%s`。\n' "$snippet" >&2
  echo "依 ~/.ai-global/governance/50-safety.md：不用 rm／rmdir／find -delete／Remove-Item，改用 mv 搬到 ~/.ai-trash/<用途>-<時間戳>/ 並保留來源路徑。" >&2
  exit 2
}

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    "") continue ;;
  esac
  if printf '%s' "$line" | grep -Eq '^[[:space:]]*#'; then
    continue
  fi
  for pattern in "${PATTERNS[@]}"; do
    if printf '%s' "$line" | grep -Eq -- "$pattern"; then block "$line"; fi
  done
  for pattern in "${PATTERNS_I[@]}"; do
    if printf '%s' "$line" | grep -Eiq -- "$pattern"; then block "$line"; fi
  done
done <<< "$cmd"
exit 0
