---
name: ai-global
description: ai-global 全域 AI 環境的完整生命週期——唯讀對帳、同步更新、首次／重新部署、制度檔靜態檢查、補裝第三方能力。使用者說「ai-global」「部署」「同步」「對帳 AI 環境」「全域設定怎麼不對」時使用。不帶參數會先列指令清單讓使用者選，不靠字眼猜意圖。
argument-hint: "[check | sync | deploy | govcheck | install <name>]"
---

# ai-global — 全域 AI 環境的部署與同步

## 指令（先看 `$ARGUMENTS`）

| 指令 | 做什麼 | 會不會動檔案 |
|---|---|---|
| `check` | 唯讀對帳：部署漂移、治理靜態檢查、第三方能力、settings 共用項，只回報 | 否 |
| `sync` | 另一台改了：`pull --ff-only` → check → 裁決 → install → 對帳 | 是（每步確認） |
| `deploy` | 首次部署或重新部署這台（不 pull）：check → 裁決 → install | 是 |
| `govcheck` | 只跑 `check_governance.py`：改完 router／制度檔後用 | 否 |
| `install <name>` | 補裝 manifest 裡指定的 skill／plugin／command | 是（只該項） |

- **`$ARGUMENTS` 為空** → 用 AskUserQuestion 列出前四項讓使用者選（每項附上表中的「做什麼」），並提醒 `install <name>` 要用參數形式。**不要靠使用者的字眼猜意圖。**
- 有參數 → 直接執行對應流程；不認得的參數 → 列出清單請使用者重選。
- 具體授權在同一對話仍有效就不重問；但調整權限、模型或安裝第三方能力，不能只憑「有差異」推定獲准。

## 架構（先懂這個）
- **clone 是 git 正本**，位置隨機器（本機路徑見 `~/.ai-global/.deploy-state.json` 的 `source_repo`）。
- `~/.ai-global/governance/`、`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.claude/{hooks,statusline.sh,skills/<repo 自製>}` 都是**部署出來的實體副本**，不是連結。會漂移，靠腳本的 `check` 抓。
- `manifest/` 只在 clone 裡（第三方能力清單與 settings 共用基準），不部署；本 skill 直接讀 clone 的版本。
- 被取代的檔一律進 `~/.ai-trash/<時間戳>/`，全程無刪除。

**原則**：比對交給 git 與腳本等確定性工具，你只負責解讀結果、補裝、把需要裁決的差異問清楚。**任何刪除一律走 trash 且先問使用者。** 授權依 `governance/20-judgment.md`，安全依 `governance/50-safety.md`。

## 各指令的流程

### 共同前置：找 clone
1. 讀 `~/.ai-global/.deploy-state.json`。存在 → `<repo>` = `source_repo`。
2. 不存在 → 這台從沒部署過。clone 路徑問使用者，或依慣例找（macOS `~/Developer/GitHub/ai-global`、Windows `D:\GitHub\ai-global`）；都沒有就請使用者先 `git clone git@github.com:Hereisaa/ai-global.git`。此時只有 `deploy` 有意義，其他指令改建議 `deploy`。

部署腳本：
- macOS/Linux：`bash <repo>/setup/install.sh [check]`
- Windows：`powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1 [-Mode check]`

### `check`（唯讀）
1. `git -C <repo> fetch` 後報 branch、ahead/behind、未 commit 數——**不 pull**。
2. 跑部署腳本 `check`，列非 `OK` 的狀態碼（表見下）。
3. 跑 `python <repo>/setup/check_governance.py --local`，列 FAIL 與非固定免責的 WARN。
4. 做「第三方能力對帳」與「settings 共用項對帳」（見下），只回報差異。
5. 回報格式見「回報」。差異需要動作時，建議對應指令（`sync`／`deploy`／`install <name>`），不自行執行。

### `sync`
1. 確認工作樹：有未 commit 變更 → 停下來列給使用者，問要 commit、放棄還是先不同步，不要自行 stash 後忘掉。乾淨才 `git -C <repo> pull --ff-only`；不能快轉時保留現況回報，不自行 rebase 或推送。
2. 接 `deploy` 的 2–4 步。
3. 接「第三方能力對帳」「settings 共用項對帳」，缺漏逐項確認後補。

### `deploy`
1. 跑 `check`（腳本），逐個狀態碼處置：

| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 部署端與 repo 一致 | 無事 |
| `MISSING` | 還沒部署 | 跑 install |
| `STALE` | 舊版留下的斷鏈 | 跑 install（腳本會自行清掉連結） |
| `BEHIND` | repo 有新內容，部署端停在上次部署的版本 | 跑 install |
| `EXTRA` | 部署端有 repo 已移除／改名的檔或 skill | 跑 install（舊檔進 trash） |
| `EDITED` | 部署端被人**在 repo 外**改過 | **停下來問使用者**，見下 |

2. `EDITED` 是唯一不能自動處理的：先 `git diff --no-index <repo>/<對應檔> <部署端檔>` 把差異列給使用者，問「這些改動要回寫進 repo（我幫你搬回 clone 再 commit），還是丟掉改回 repo 版本？」。丟掉也不會真的消失——install 會把舊檔放進 `~/.ai-trash/`。**首次部署且目標位置已有使用者自己的 `CLAUDE.md`／`AGENTS.md`** 也會報 `EDITED`：要特別明講「你原本的 system prompt 會被取代，原檔會在 trash」，得到同意再 install。
3. 裁決完跑 install（不帶 check 參數），然後**再跑一次 check 確認全部 `OK`**。install 輸出裡的 `WARN`／`DROP` 行和結尾的 `NOTE` 要原樣轉述——那是「哪些東西被換掉、放在哪」的唯一紀錄。
4. 跑 `python <repo>/setup/check_governance.py`。FAIL 代表 repo 本身有問題，要先修 clone，不是部署端的漂移。

### `govcheck`（唯讀）
在 `<repo>` 跑 `python setup/check_governance.py`（加 `--local` 可比對副本內容與白名單設定；Codex TOML 需 Python 3.11+，舊版會明列跳過）。檢查項：兩個 router `##` 節次對齊（Cowork 為 Claude 專屬例外）、各自含本工具分支前綴且沒照抄對面的、制度目錄路徑與逐檔路由、相對連結、manifest 結構。逐條解釋 FAIL 的修法，不自行改制度檔（改制度依 `40-maintenance.md`）。

### `install <name>`
在 `<repo>/manifest/skills.json` 找 `<name>`：找不到 → 列出清單請使用者重選。
- `type: skill` → 從 `source` 標的 GitHub repo 抓對應目錄（有 `path` 欄位就抓那個子目錄）裝回 `~/.claude/skills/<name>/`；裝不回來就回報，不要硬湊替代品。
- `type: plugin` → 引導使用者用 `/plugin` 從 manifest 記載的 marketplace 安裝。
- `type: command` → 放到 `target` 路徑。
裝完核對存在與版本，回報。

## 第三方能力對帳（`check`／`sync` 用；讀 `<repo>/manifest/skills.json`）
- `type: skill` → 對照 `ls ~/.claude/skills/`；`type: plugin` → 對照 `~/.claude/plugins/installed_plugins.json`；`type: command` → 核對 `target` 存在。
- 反向檢查：本機有、manifest 沒有的第三方 skill/plugin → 列出來問「要納入 manifest（兩台都裝）還是本機獨有？」。使用者已說過「本機獨有」的，記進 auto-memory，下次別再問。

## settings 共用項對帳（`check`／`sync` 用；讀 `<repo>/manifest/settings.json`）
- `claude_settings` 的結構化區塊（`permissions`、`statusLine`、`enabledPlugins`、`extraKnownMarketplaces`）：與 `~/.claude/settings.json` 對應區塊做深度比對，manifest 是共用基準。本機缺漏 → 先把 settings.json 複製一份進 `~/.ai-trash/`，再把 manifest 版本合併進去（保留本機獨有的其他 key，例如 Windows 的 `hooks`）。本機多出或值不同 → 列給使用者裁決：更新 manifest（改共用基準）還是改回本機。
- `codex_config` 只比 manifest 列出的 key（目前只有 `personality`；`model`／`model_reasoning_effort` 是本機獨有，不比）。
- 只輸出差異的欄位名稱與影響，不貼原始設定或秘密值。這兩個檔由工具自己回寫，永遠不部署、只對帳。

## 回報
結論先行（「已同步」／「已部署」／「補了 N 項」／「M 項差異待裁決」），再逐項列動作與證據（指令輸出關鍵行）；已檢查、已修復、未驗證分開講。若這次有改到 `<repo>` 的內容，提醒使用者 commit；push 須使用者對具體遠端／分支明確授權，未 push 另一台拿不到。

## Codex 側
本 skill 是 Claude Code 的。Codex 使用者請照 `<repo>/README.md` 的「給 AI agent 的指引」手動走同樣步驟。
