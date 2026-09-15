#!/bin/bash
# PreToolUse hook for the Bash tool (Claude Code). Enforces governance/50-safety:
# no rm / rmdir / unlink / shred / find -delete / PowerShell Remove-Item, even
# inside a compound command ("cd x && rm -rf y", "xargs rm", "$(rm ...)").
# The permissions deny list only matches a command's prefix; this looks at the
# whole line. Exit 2 blocks the call and hands the reason back to the model.
#
# Reads the hook JSON on stdin. Anything that is not a Bash tool call, or that
# cannot be parsed, is allowed (exit 0) so a broken hook never locks the user out.
set -u

py=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1; then py="$candidate"; break; fi
done
if [ -z "$py" ]; then
  # Fail open, but say so: the model must not assume this guard is active.
  echo "ai-global guard-delete: 找不到 python，本次未檢查刪除指令（hook 失效，紅線仍然有效）。" >&2
  exit 0
fi

# The heredoc below takes over stdin, so the hook payload is captured first
# and handed to the script as its only argument.
payload=$(cat)

"$py" - "$payload" <<'PY'
import json, re, sys

try:
    # A BOM sneaks in when the payload comes through a PowerShell pipe.
    event = json.loads(sys.argv[1].lstrip("\ufeff"))
except (IndexError, ValueError):
    sys.stderr.write("ai-global guard-delete: hook 輸入不是 JSON，本次未檢查刪除指令（紅線仍然有效）。\n")
    sys.exit(0)
if not isinstance(event, dict):
    sys.exit(0)
if event.get("tool_name") != "Bash":
    sys.exit(0)
command = event.get("tool_input", {}).get("command", "")
if not isinstance(command, str):
    sys.exit(0)

# A delete verb counts only at the start of a (sub)command - after a separator,
# a keyword such as do/then/else, or inside sudo/xargs/exec/env - so "npm rm pkg"
# and "git rm --cached" stay allowed. A quote counts as a start only right after
# an interpreter flag (-c, -e, -Command), so grep 'rm -rf' is not a hit.
LEAD = (r"(?:^|[;&|(`{]|\$\(|\bsudo\s+(?:-\S+\s+)*|\bxargs\s+(?:-\S+\s+)*|\bexec\s+|\bcommand\s+"
        r"|\bnohup\s+|\benv\s+(?:\w+=\S*\s+)*|\b(?:do|then|else)\s+|-(?:c|e|Command)\s*[\"'])\s*")
VERB = r"(?:\\|/\S*/)?"   # \rm and /bin/rm are still rm
PATTERNS = [
    re.compile(LEAD + VERB + r"(?:rm|rmdir|unlink|shred)\b"),
    re.compile(r"\bfind\b[^;&|]*\s-delete\b"),
    re.compile(LEAD + r"(?:Remove-Item|ri|rd|del|erase)\b(?![-\w.])", re.I),
    re.compile(LEAD + r"git\s+clean\b(?=[^;&|]*\s-[a-zA-Z]*f)"),
    re.compile(LEAD + r"(?:npx\s+)?(?:rimraf|trash-put)\b"),
    re.compile(r"\brsync\b[^;&|]*\s--delete\b"),
    # Programmatic deletes run through an interpreter one-liner.
    re.compile(r"\b(?:shutil\.rmtree|os\.(?:remove|unlink|rmdir|removedirs)|\.unlink|unlinkSync|rmSync"
               r"|fs\.(?:unlink|rm|rmdir))\s*\("),
]

for line in command.splitlines():
    stripped = line.strip()
    if stripped.startswith("#"):
        continue
    for pattern in PATTERNS:
        hit = pattern.search(line)
        if hit:
            snippet = line.strip()
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            sys.stderr.write(
                "ai-global guard-delete: 擋下刪除指令 `" + snippet + "`。\n"
                "依 ~/.ai-global/governance/50-safety.md：不用 rm／rmdir／find -delete／Remove-Item，"
                "改用 mv 搬到 ~/.ai-trash/<用途>-<時間戳>/ 並保留來源路徑。\n")
            sys.exit(2)
sys.exit(0)
PY
