#!/bin/bash
# SessionStart hook (Claude Code). Prints one short drift summary so the model
# knows at the start of every session whether the deployed global config still
# matches the clone. Read-only: it runs `setup/deploy.py check`, never install,
# never pull. Always exits 0 - a missing clone or python must not break sessions.
set -u

state="$HOME/.ai-global/.deploy-state.json"
if [ ! -f "$state" ]; then
  echo "ai-global: 尚未部署（沒有 ${state}）。到 clone 跑 python setup/align.py。"
  exit 0
fi

py=""
for candidate in python3.13 python3.12 python3.11 python3 python py; do
  command -v "$candidate" >/dev/null 2>&1 || continue
  if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    py="$candidate"; break
  fi
done
if [ -z "$py" ]; then
  echo "ai-global: 找不到 Python 3.11+，無法檢查部署漂移。"
  exit 0
fi

repo=$("$py" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8-sig")).get("source_repo", ""))' "$state" 2>/dev/null)
if [ -z "$repo" ] || [ ! -f "$repo/setup/deploy.py" ]; then
  echo "ai-global: state 指向的 clone 不存在（${repo}）。重新 clone 後跑 python setup/align.py。"
  exit 0
fi

output=$("$py" "$repo/setup/deploy.py" check 2>&1)
rc=$?
head=$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)
branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)

# Second axis: is the clone itself current? A quiet fetch (no prompt, short
# timeout) then ahead/behind against upstream; offline just says so.
remote_note=""
if [ "${AI_GLOBAL_CHECK_NO_FETCH:-0}" != "1" ] && git -C "$repo" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  if GIT_TERMINAL_PROMPT=0 git -C "$repo" -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=5 fetch -q origin 2>/dev/null; then
    counts=$(git -C "$repo" rev-list --left-right --count 'HEAD...@{u}' 2>/dev/null)
    ahead=${counts%%[[:space:]]*}; behind=${counts##*[[:space:]]}
    [ "${behind:-0}" -gt 0 ] && remote_note="$remote_note clone 落後 remote ${behind} 個 commit（git pull 後再 align）；"
    [ "${ahead:-0}" -gt 0 ] && remote_note="$remote_note clone 有 ${ahead} 個 commit 未 push（另一台拿不到）；"
  else
    remote_note=" 無法連到 remote，未比對是否落後；"
  fi
elif [ "$branch" != "unknown" ]; then
  remote_note=" 分支沒有 upstream，未比對 remote；"
fi
if [ "$branch" != "main" ] && [ "$branch" != "unknown" ]; then
  remote_note="$remote_note 部署自分支 ${branch}（尚未在 main）；"
fi

if [ "$rc" -eq 0 ]; then
  if [ -n "$remote_note" ]; then
    echo "ai-global: 部署端與 clone 一致（$branch@${head}），但：${remote_note}"
  else
    echo "ai-global: 全域設定與 clone 同步（main@${head}，與 remote 一致）。"
  fi
  exit 0
fi
drift=$(printf '%s\n' "$output" | grep -E '^(MISSING|STALE|BEHIND|EDITED|EXTRA) ' | sed 's/ - .*//')
count=$(printf '%s\n' "$drift" | grep -c . || true)
if [ "$count" -eq 0 ]; then
  # check failed without reporting drift: deploy.py itself broke. Show why.
  echo "ai-global: 部署檢查本身失敗（exit ${rc}，clone $branch@${head}），無法判斷是否同步："
  printf '%s\n' "$output" | tail -n 5
  exit 0
fi
echo "ai-global: 全域設定與 clone 不同步（$count 項，clone $branch@${head}）。先在 Claude Code 跑 /ai-global check 看細節，再決定 align／deploy；不要直接改部署端。"
printf '%s\n' "$drift" | head -n 8
[ "$count" -gt 8 ] && echo "…（其餘 $((count - 8)) 項略）"
exit 0
