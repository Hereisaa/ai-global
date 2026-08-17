#!/bin/bash
# Stop hook: when the session tries to end its turn with modified .ts/.tsx files
# in a repo that has a "typecheck" script, run it. On failure, block the stop
# and feed the errors back to Claude so it must fix them before finishing.

input=$(cat)

# Loop guard: if we already blocked once in this stop chain, let it through.
if echo "$input" | jq -e '.stop_hook_active == true' >/dev/null 2>&1; then
  exit 0
fi

# Run in the session's project directory when provided.
dir=$(echo "$input" | jq -r '.cwd // empty' 2>/dev/null)
if [ -n "$dir" ] && [ -d "$dir" ]; then
  cd "$dir" || exit 0
fi

# Applicability gates: git repo, package.json with a typecheck script.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
[ -f package.json ] || exit 0
jq -e '.scripts.typecheck' package.json >/dev/null 2>&1 || exit 0

# Only act when TypeScript files are actually dirty (modified/staged/untracked).
git status --porcelain 2>/dev/null | grep -qE '\.(ts|tsx)$' || exit 0

out=$(npm run typecheck 2>&1)
status=$?
[ $status -eq 0 ] && exit 0

tail_out=$(echo "$out" | tail -30)
jq -n --arg reason "Stop hook: 'npm run typecheck' failed. Fix these errors before finishing:
$tail_out" '{"decision":"block","reason":$reason}'
exit 0
