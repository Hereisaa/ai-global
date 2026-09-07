---
name: ai-global
description: ai-global 全域 AI 環境的完整生命週期——新機器首次部署、另一台改了之後更新、漂移檢查、EDITED 裁決、第三方 skills/plugins 與 settings 共用項對帳、制度檔靜態檢查。使用者說「部署 ai-global」「把這台接上」「安裝全域設定」「同步一下」「sync check」「對帳 AI 環境」「另一台改了」「全域設定怎麼不對」時使用。預設唯讀；明確要求同步／部署／修復才動檔案。
---

# ai-global — 全域 AI 環境的部署與同步

## 架構（先懂這個）
- **clone 是 git 正本**，位置隨機器（本機路徑見 `~/.ai-global/.deploy-state.json` 的 `source_repo`）。
- `~/.ai-global/governance/`、`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.claude/{hooks,statusline.sh,skills/<repo 自製>}` 都是**部署出來的實體副本**，不是連結。會漂移，靠腳本的 `check` 抓。
- `manifest/` 只在 clone 裡（第三方能力清單與 settings 共用基準），不部署；本 skill 直接讀 clone 的版本。
- 被取代的檔一律進 `~/.ai-trash/<時間戳>/`，全程無刪除。

**原則**：比對交給 git 與腳本等確定性工具，你只負責解讀結果、補裝、把需要裁決的差異問清楚。**任何刪除一律走 trash 且先問使用者。** 授權依 `governance/20-judgment.md`，安全依 `governance/50-safety.md`。

## 先辨識要求（決定要不要動檔案）
| 使用者說的 | 你做的 |
|---|---|
| 「檢查」「對帳」「看一下有沒有漂移」 | **只做唯讀**：第 0、2（只跑 check）、3、4 步的比對，回報差異。不 pull、不 install、不補裝、不改設定。 |
| 「同步」「更新」「另一台改了」 | 第 1 步 pull → 第 2 步 check → 裁決 → install → 第 3、4 步；補裝與設定合併仍逐項確認。 |
| 「部署」「把這台接上」「安裝」 | 首次部署模式（第 0 步判定）→ 第 2 步 → 第 3、4 步。 |
| 「修復 X」「補裝 Y」 | 只處理指定範圍，先比對再套用。 |

具體授權在同一對話仍有效就不重問；但調整權限、模型或安裝第三方能力，不能只憑「有差異」推定獲准。

## 0. 找 clone、判斷模式
1. 讀 `~/.ai-global/.deploy-state.json`。存在 → `<repo>` = `source_repo`，進入**更新模式**。
2. 不存在 → 這台從沒部署過。clone 路徑問使用者，或依慣例找（macOS `~/Developer/GitHub/ai-global`、Windows `D:\GitHub\ai-global`）；都沒有就請使用者先 `git clone git@github.com:Hereisaa/ai-global.git`。進入**首次部署模式**：跳過第 1 步的 pull（剛 clone 的已是最新），直接做第 2 步。

以下 `<repo>` 代表 clone 路徑。部署腳本：
- macOS/Linux：`bash <repo>/setup/install.sh [check]`
- Windows：`powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1 [-Mode check]`

## 1. 拉最新（更新模式）
先確認目前分支、遠端與工作樹：有本地未 commit 的變更 → 停下來列給使用者，問要 commit、放棄還是先不同步，不要自行 stash 後忘掉。乾淨才 `git -C <repo> pull --ff-only`；不能快轉時保留現況回報，不自行 rebase 或推送。

## 2. check → 裁決 → install → 再 check
先跑 `check`（唯讀，不動任何檔；exit 1 代表有事要處理），逐個狀態碼處置：

| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 部署端與 repo 一致 | 無事 |
| `MISSING` | 還沒部署 | 跑 install |
| `STALE` | 舊版留下的斷鏈 | 跑 install（腳本會自行清掉連結） |
| `BEHIND` | repo 有新內容，部署端停在上次部署的版本 | 跑 install |
| `EXTRA` | 部署端有 repo 已移除／改名的檔或 skill | 跑 install（舊檔進 trash） |
| `EDITED` | 部署端被人**在 repo 外**改過 | **停下來問使用者**，見下 |

`EDITED` 是唯一不能自動處理的：先 `git diff --no-index <repo>/<對應檔> <部署端檔>` 把差異列給使用者，問「這些改動要回寫進 repo（我幫你搬回 clone 再 commit），還是丟掉改回 repo 版本？」。丟掉也不會真的消失——install 會把舊檔放進 `~/.ai-trash/`。

**首次部署且目標位置已有使用者自己的 `CLAUDE.md`／`AGENTS.md`** 也會報 `EDITED`：這時要特別明講「你原本的 system prompt 會被取代，原檔會在 trash」，得到同意再 install。

裁決完跑 install（不帶 check 參數），然後**再跑一次 check 確認全部 `OK`**。install 的輸出裡 `WARN`／`DROP` 行和結尾的 `NOTE` 要原樣轉述給使用者——那是「哪些東西被換掉、放在哪」的唯一紀錄。

同時在 `<repo>` 跑 `python setup/check_governance.py`（唯讀）：兩個 router 節次對齊與各自前綴、制度路由、相對連結、manifest 結構。FAIL 代表 repo 本身有問題，要先修 clone 再部署，不是部署端的漂移。加 `--local` 可額外比對副本內容與白名單設定欄位（Codex TOML 需 Python 3.11+，舊版會明列跳過）。

## 3. 第三方能力對帳（`<repo>/manifest/skills.json`）
- `type: skill` → 對照 `ls ~/.claude/skills/`。缺 → 從 `source` 標的 GitHub repo 抓對應目錄（有 `path` 欄位就抓那個子目錄）裝回 `~/.claude/skills/<name>/`；裝不回來就回報，不要硬湊替代品。
- `type: plugin` → 對照 `~/.claude/plugins/installed_plugins.json`。缺 → 引導使用者用 `/plugin` 從 manifest 記載的 marketplace 安裝。
- `type: command` → 核對 `target` 檔案存在。
- 反向檢查：本機有、manifest 沒有的第三方 skill/plugin → 列出來問使用者「要納入 manifest（兩台都裝）還是本機獨有？」。使用者已說過「本機獨有」的，記進 auto-memory，下次別再問。

## 4. settings 共用項（`<repo>/manifest/settings.json`）
- `claude_settings` 的結構化區塊（`permissions`、`statusLine`、`enabledPlugins`、`extraKnownMarketplaces`）：與 `~/.claude/settings.json` 對應區塊做深度比對，manifest 是共用基準。本機缺漏 → 先把 settings.json 複製一份進 `~/.ai-trash/`，再把 manifest 版本合併進去（保留本機獨有的其他 key，例如 Windows 的 `hooks`）。本機多出或值不同 → 列給使用者裁決：更新 manifest（改共用基準）還是改回本機。
- `codex_config` 的 key：逐項比對 `~/.codex/config.toml`，同樣缺補、異問。
- 只輸出差異的欄位名稱與影響，不貼原始設定或秘密值。這兩個檔由工具自己回寫，永遠不部署、只對帳。

## 5. 回報
結論先行（「已部署」／「已同步」／「補了 N 項」／「M 項差異待裁決」），再逐項列動作與證據（指令輸出關鍵行）；已檢查、已修復、未驗證分開講。若這次有改到 `<repo>` 的內容，提醒使用者 commit；push 須使用者對具體遠端／分支明確授權，未 push 另一台拿不到。

## Codex 側
本 skill 是 Claude Code 的。Codex 使用者請照 `<repo>/README.md` 的「給 AI agent 的指引」手動走同樣步驟；步驟 3–4 的對帳在 Codex 裡用一般檔案讀取與比對完成即可。
