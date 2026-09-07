# 共用背景（各指令流程檔會引用）

## 架構
- **clone 是 git 正本**，位置隨機器。`<repo>` = `~/.ai-global/.deploy-state.json` 的 `source_repo`；該檔不存在代表這台從沒部署過（見 deploy）。
- `~/.ai-global/governance/`、`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.claude/{hooks,statusline.sh,skills/<repo 自製>}` 都是**部署出來的實體副本**，不是連結。會漂移，靠腳本的 `check` 抓。
- `manifest/` 只在 clone 裡，不部署；直接讀 clone 的版本。
- 被取代的檔一律進 `~/.ai-trash/<時間戳>/`，全程無刪除。

**原則**：比對交給 git 與腳本等確定性工具，你只負責解讀結果、補裝、把需要裁決的差異問清楚。任何刪除一律走 trash 且先問使用者。授權依 `governance/20-judgment.md`，安全依 `governance/50-safety.md`。具體授權在同一對話仍有效就不重問；但調整權限、模型或安裝第三方能力，不能只憑「有差異」推定獲准。

## 部署腳本
- macOS/Linux：`bash <repo>/setup/install.sh [check]`
- Windows：`powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1 [-Mode check]`

## check 的狀態碼
| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 部署端與 repo 一致 | 無事 |
| `MISSING` | 還沒部署 | install |
| `STALE` | 舊版留下的斷鏈 | install（腳本自行清掉連結） |
| `BEHIND` | repo 有新內容，部署端停在上次部署的版本 | install |
| `EXTRA` | 部署端有 repo 已移除／改名的檔或 skill | install（舊檔進 trash） |
| `EDITED` | 部署端被人**在 repo 外**改過 | **停下來問使用者**（見下） |

`EDITED` 處置：先 `git diff --no-index <repo>/<對應檔> <部署端檔>` 列差異，問「回寫進 repo（我搬回 clone 再 commit），還是丟掉改回 repo 版本？」。丟掉也不會消失——install 會把舊檔放進 `~/.ai-trash/`。首次部署且目標位置已有使用者自己的 `CLAUDE.md`／`AGENTS.md` 也會報 `EDITED`：要明講「你原本的 system prompt 會被取代，原檔會在 trash」，得到同意再 install。

install 輸出裡的 `WARN`／`DROP` 行與結尾 `NOTE` 要原樣轉述——那是「哪些東西被換掉、放在哪」的唯一紀錄。

## 第三方能力對帳（讀 `<repo>/manifest/skills.json`）
- `type: skill` → 對照 `ls ~/.claude/skills/`；`type: plugin` → 對照 `~/.claude/plugins/installed_plugins.json`；`type: command` → 核對 `target` 存在。
- 反向：本機有、manifest 沒有的第三方 skill/plugin → 問「納入 manifest（兩台都裝）還是本機獨有？」。已說過「本機獨有」的記進 auto-memory，下次別再問。

## settings 共用項對帳（讀 `<repo>/manifest/settings.json`）
- `claude_settings` 的 `permissions`、`statusLine`、`enabledPlugins`、`extraKnownMarketplaces` 與 `~/.claude/settings.json` 對應區塊深度比對，manifest 是共用基準。本機缺漏 → 先把 settings.json 複製一份進 `~/.ai-trash/` 再合併（保留本機獨有 key，例如 Windows 的 `hooks`）。本機多出或值不同 → 問：更新 manifest 還是改回本機。
- `codex_config` 只比 manifest 列出的 key（目前只有 `personality`；`model`／`model_reasoning_effort` 本機獨有，不比）。
- 只輸出差異的欄位名稱與影響，不貼原始設定或秘密值。這兩個檔永遠不部署、只對帳。

## 回報
結論先行（「已同步」／「已部署」／「補了 N 項」／「M 項差異待裁決」），再逐項列動作與證據；已檢查、已修復、未驗證分開講。若改到 `<repo>`，提醒 commit；push 須使用者對具體遠端／分支明確授權。

## Codex 側
本 skill 是 Claude Code 的。Codex 使用者照 `<repo>/README.md` 的「給 AI agent 的指引」手動走。
