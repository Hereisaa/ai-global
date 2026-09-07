---
name: sync-check
description: 對帳 ai-global 倉庫與本機 AI 全域環境：git pull、用部署腳本 check 比對 ~/.ai-global 與兩個 router 是否漂移、核對 manifest 的第三方 skills/plugins/commands 與 settings 共用項；缺漏補裝、差異回報使用者裁決。使用者說「同步檢查」「sync check」「對帳 AI 環境」「另一台改了同步一下」時使用。
---

# sync-check — AI 全域環境對帳

**架構**：ai-global clone 是正本；`~/.ai-global/`（governance＋manifest）、`~/.claude/`、`~/.codex/` 底下的檔案都是部署出來的**實體副本**，不是連結。所以副本會漂移，靠部署腳本的 `check` 抓。

**clone 路徑**：讀 `~/.ai-global/.deploy-state.json` 的 `source_repo`；該檔不存在代表這台從沒部署過，請使用者給 clone 路徑（或依環境慣例找：macOS `~/Developer/GitHub/ai-global`、Windows `D:\GitHub\ai-global`），然後直接跳到第 2 步做首次部署。以下用 `<repo>` 代表它。

**原則**：比對交給 git 與腳本等確定性工具，你只負責解讀結果、補裝、把需要裁決的差異問清楚。**任何刪除一律走 trash 流程且先問使用者。**

依序執行：

## 1. 拉最新
`git -C <repo> pull --ff-only`。
有本地未 commit 的變更 → 停下來列給使用者，問要 commit+push 還是放棄，不要自行 stash 後忘掉。

## 2. 部署健康檢查
先跑 check（唯讀，不動任何檔）：
- macOS/Linux：`bash <repo>/setup/install.sh check`
- Windows：`powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1 -Mode check`

逐個狀態碼的處置：

| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 部署端與 repo 一致 | 無事 |
| `MISSING` | 還沒部署 | 跑 install |
| `STALE` | 舊版留下的斷鏈 | 跑 install（腳本會自行清掉連結） |
| `BEHIND` | repo 有新內容，部署端還停在上次部署的版本 | 跑 install |
| `EDITED` | 部署端被人**在 repo 外**改過 | **停下來問使用者**，見下 |
| `EXTRA` | 部署端有 repo 已移除的檔 | 跑 install（舊檔進 trash） |

`EDITED` 是唯一不能自動處理的：先用 `git diff --no-index <repo>/<對應檔> <部署端檔>` 把差異列給使用者，問「這些改動要回寫進 repo（我幫你搬回 clone 再 commit），還是丟掉改回 repo 版本？」。丟掉也不會真的消失——install 會把舊檔放進 `~/Developer/temp/trash/`。

裁決完再跑一次 install（不帶 check 參數），然後重跑 check 確認全部 `OK`。

## 3. manifest 對帳（`<repo>/manifest/skills.json`）
- `type: skill` → 對照 `ls ~/.claude/skills/`。缺 → 從 `source` 標的 GitHub repo 抓對應目錄裝回 `~/.claude/skills/<name>/`；裝不回來就回報，不要硬湊替代品。
- `type: plugin` → 對照 `~/.claude/plugins/installed_plugins.json`。缺 → 引導使用者用 `/plugin` 從 manifest 記載的 marketplace 安裝。
- `type: command` → 核對 `target` 檔案存在。
- 反向檢查：本機有、manifest 沒有的第三方 skill/plugin → 列出來問使用者「要納入 manifest（兩台都裝）還是本機獨有？」

## 4. settings 共用項（`<repo>/manifest/settings.json`）
- `claude_settings` 的結構化區塊（`permissions`、`statusLine`、`enabledPlugins`、`extraKnownMarketplaces`）：與 `~/.claude/settings.json` 對應區塊做深度比對，manifest 是共用基準。本機缺漏 → 先備份 settings.json，再把 manifest 版本合併進去（保留本機獨有的其他 key）。本機多出或值不同 → 列給使用者裁決：要更新 manifest（改共用基準並 push）還是改回本機。
- `codex_config` 的 key：逐項比對 `~/.codex/config.toml`，同樣缺補、異問。
- 這兩個檔由工具自己回寫，所以永遠不部署、只對帳。

## 5. 回報
結論先行（「已同步」／「補了 N 項」／「M 項差異待裁決」），再逐項列動作與證據（指令輸出關鍵行）。若這次有改到 `<repo>` 的內容，提醒使用者 `git commit && git push`，否則另一台拿不到。
