---
name: sync-check
description: 對帳 ai-global 同步倉庫與本機 AI 全域環境：git pull、檢查 symlink/junction 部署、比對 manifest 的第三方 skills/plugins/commands 與 settings 共用項；缺漏補裝、差異回報使用者裁決。使用者說「同步檢查」「sync check」「對帳 AI 環境」「另一台改了同步一下」時使用。
---

# sync-check — AI 全域環境對帳

倉庫位置：`~/Developer/GitHub/ai-global`（Windows 原生為 `%USERPROFILE%\Developer\GitHub\ai-global`）。
原則：比對交給 git 與腳本等確定性工具，你只負責解讀結果、補裝、和把需要裁決的差異問清楚。**任何刪除一律走 trash 流程且先問使用者。**

依序執行：

## 1. 拉最新
`git -C ~/Developer/GitHub/ai-global pull --ff-only`。
有本地未 commit 的變更 → 停下來列給使用者，問要 commit+push 還是放棄，不要自行 stash 後忘掉。

## 2. 連結健康檢查
- macOS/Linux：`bash ~/Developer/GitHub/ai-global/setup/install.sh check`；出現 DRIFT → 跑一次 `install.sh` 修復（冪等、不刪檔，被取代的實體進 trash）。
- Windows 原生：重跑 `install.ps1`（冪等）。若部署時退回過 COPY 模式，用 `git diff --no-index` 比對 repo 檔與部署副本，不一致列給使用者裁決方向。

## 3. manifest 對帳（`manifest/skills.json`）
- `type: skill` → 對照 `ls ~/.claude/skills/`。缺 → 從 `source` 標的 GitHub repo 抓對應目錄裝回 `~/.claude/skills/<name>/`；裝不回來就回報，不要硬湊替代品。
- `type: plugin` → 對照 `~/.claude/plugins/installed_plugins.json`。缺 → 引導使用者用 `/plugin` 從 manifest 記載的 marketplace 安裝。
- `type: command` → 核對 `target` 檔案存在。
- 反向檢查：本機有、manifest 沒有的第三方 skill/plugin → 列出來問使用者「要納入 manifest（兩台都裝）還是本機獨有？」

## 4. settings 共用項（`manifest/settings.json`）
逐 key 比對 `~/.claude/settings.json` 與 `~/.codex/config.toml`。缺項或值不同 → 列表回報並問以哪邊為準；要改本機檔案時先備份再改。

## 5. 回報
結論先行（「已同步」／「補了 N 項」／「M 項差異待裁決」），再逐項列動作與證據（指令輸出關鍵行）。
