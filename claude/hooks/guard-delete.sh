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
[ -n "$py" ] || exit 0

# The heredoc below takes over stdin, so the hook payload is captured first
# and handed to the script as its only argument.
payload=$(cat)

"$py" - "$payload" <<'PY'
import json, re, sys

try:
    event = json.loads(sys.argv[1])
except (IndexError, ValueError):
    sys.exit(0)
if not isinstance(event, dict):
    sys.exit(0)
if event.get("tool_name") != "Bash":
    sys.exit(0)
command = event.get("tool_input", {}).get("command", "")
if not isinstance(command, str):
    sys.exit(0)

# A delete verb counts only at the start of a (sub)command, or fed through
# sudo/xargs/exec, so "npm rm pkg" and "git rm --cached" stay allowed.
LEAD = r"(?:^|[;&|(`{\"']|\$\(|\bsudo\s+(?:-\S+\s+)*|\bxargs\s+(?:-\S+\s+)*|\bexec\s+|\bcommand\s+|\bnohup\s+)\s*"
PATTERNS = [
    re.compile(LEAD + r"(?:rm|rmdir|unlink|shred)\b"),
    re.compile(r"\bfind\b[^;&|]*\s-delete\b"),
    re.compile(LEAD + r"(?:Remove-Item|ri|rd|del|erase)\b(?![-\w.])", re.I),
    re.compile(LEAD + r"git\s+clean\b(?=[^;&|]*\s-[a-zA-Z]*f)"),
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
