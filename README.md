# ai-global — AI 全域環境同步倉庫

跨機器（macOS ↔ Windows）同步 AI 工具的**使用者全域層**：使用者指令（CLAUDE.md／AGENTS.md）、制度規則（agent-governance）、自製 skills／commands／agents、hooks，以及第三方能力的安裝清單。

## 給 AI agent 的指引（讀到這裡的模型，照此執行）

**這個 repo 是什麼**：使用者 Aaron 的 AI 全域設定「正本」。部署後，`~/.claude/CLAUDE.md`、`~/Developer/agent-governance/`、`~/.claude/hooks/`、`~/.codex/AGENTS.md` 與部分 skills 都是指向本 repo 的連結——**改那些路徑就是改本 repo 的工作區**。

**如果你被要求「設置／接上這台機器」，依序執行**：
1. 判斷 OS，跑對應腳本（冪等，可重複執行；它不刪檔，被取代的既有檔會移入 `~/Developer/temp/trash/`）：
   - macOS/Linux：`bash setup/install.sh`（之後可用 `bash setup/install.sh check` 驗證）
   - Windows 原生：`powershell -ExecutionPolicy Bypass -File setup\install.ps1`（目錄用 Junction；單檔 symlink 建議先開「開發人員模式」，否則退回複製模式）
2. 照 `manifest/skills.json` 補裝第三方能力：`type: plugin` 引導使用者用 `/plugin` 安裝；`type: skill` 從 `source` 標的 GitHub repo 抓對應目錄放入 `~/.claude/skills/<name>/`；`type: command` 放入 `target` 路徑。
3. 照 `manifest/settings.json` 核對本機 `~/.claude/settings.json` 與 `~/.codex/config.toml` 的共用 key，缺漏回報使用者裁決後補上。
4. 完成後逐項回報 PASS/FAIL 附證據。（Claude Code 裝好後，以上第 2–3 步可直接用 `/sync-check` skill 執行。）

**如果你被要求「檢查／對帳」**：只做唯讀連結、內容與 manifest 比對，回報差異；不 pull、補裝或修設定。

**如果你被要求「同步／更新到另一台已發布版本」**：確認目前分支及工作樹可安全更新後 `git pull --ff-only`，再檢查部署。需要修復連結或補裝能力時依本次具體授權處理，保留本機獨有設定；不同步未授權的權限或模型變更。

**安全與授權約定（執行層保護另行驗證）**：
- 修改完成後先驗證與回報；push 須有對具體遠端／分支的明確授權。未推送的變更不會同步到另一台機器。
- 禁止 `rm`／程式化刪除；移除一律 `mv` 進 `~/Developer/temp/trash/` 加時間戳。
- 任何真實憑證（`.credentials.json`、`auth.json`、環境值、API key）不得進本 repo；無秘密的 `.env.example` 依 `governance/50-safety.md` 檢查後可追蹤。
- 制度檔（`governance/`）的修改要先讀 `governance/40-maintenance.md`（備份、變更紀錄、權限分級）。

## 設計原則

- **搬得動的檔案**：正本放本倉庫，各機器用 symlink（macOS/Linux）或 Junction（Windows）鋪回 AI 工具認得的固定位置。同機連結會反映目前工作樹；跨機仍需 Git 同步。Windows 單檔退回複製時需另行比對內容，不能假定不會漂移。
- **搬不動的安裝品**（官方/第三方 skills、plugins）：只記 `manifest/` 清單，各機器用 `/sync-check` 對帳補裝。上游活著的東西不揹拷貝。
- **機器特有的**（`settings.local.json`、Codex 的機器路徑設定、憑證）：留在本機，永不進倉庫。

## 目錄結構與部署對照

| 倉庫路徑 | 部署位置（連結終點 ← 連結來源） |
|---|---|
| `governance/` | ← `~/Developer/agent-governance/`（制度規則單一事實來源） |
| `claude/CLAUDE.md` | ← `~/.claude/CLAUDE.md`（Claude 全域指令） |
| `claude/statusline.sh` | ← `~/.claude/statusline.sh` |
| `claude/hooks/` | ← `~/.claude/hooks/` |
| `claude/skills/<name>/` | ← `~/.claude/skills/<name>/`（**逐一連結**，skills 目錄本體保持實體，讓第三方 skill 能並存） |
| `claude/commands/<name>` | ← `~/.claude/commands/<name>`（逐一連結） |
| `claude/agents/<name>` | ← `~/.claude/agents/<name>`（逐一連結） |
| `codex/AGENTS.md` | ← `~/.codex/AGENTS.md`（Codex 全域指令） |

`manifest/skills.json`：每台機器該有的第三方 skills／plugins／commands 清單（名稱＋來源＋版本）。
`manifest/settings.json`：`~/.claude/settings.json` 與 `~/.codex/config.toml` 裡「應該存在的共用設定項」。這兩個檔案由工具自己回寫，所以不連結、只對帳。

## 新機器上手

### macOS / Linux

```bash
git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
bash ~/Developer/GitHub/ai-global/setup/install.sh
```

記憶體回收（macOS 專屬，選用）：`claude/hooks/cleanup-orphans.sh`，與 Windows 版同語意、同 log 檔，兩層觸發：
- `SessionEnd` hook（`~/.claude/settings.json`，機器本地，手動加）：`bash ~/.claude/hooks/cleanup-orphans.sh --scope session` — 只清該 session 自己的子孫。
- launchd agent：`bash setup/install-cleanup-agent.sh`（每 2 小時＋載入時；`--interval-hours N` 調整、`--uninstall` 移除）。
- macOS 與 Windows 的差異（因為孤兒在 macOS 是被 launchd 收養成 ppid=1，不是失去父程序）：只看自己 uid 的程序；`launchctl list` 裡的 PID 一律跳過（那是使用者自己註冊的服務，例如 dev server、gateway）；`~/.claude/cleanup-protect.txt` 可加自訂保護 regex（一行一條）。
- 容器 VM 的清理可能停止 Colima／lima；觸發門檻與自動重啟行為以目前腳本、服務設定及預演為準，不沿用歷史實測作保證。
- 安全規則與 Windows 版一致：**絕不殺 `claude` 主程序**，命令列含 `remote-control` 的整棵子樹跳過；超過 1.5 GB 或 24 小時的 session 只發通知。紀錄在 `~/.claude/logs/cleanup.log`；`--dry-run` 可預演。

### Windows（原生）

1. 一次性設定：開啟「開發人員模式」（設定 → 隱私權與安全性 → 開發人員專用），否則單檔 symlink 需系統管理員權限（腳本會自動退回複製模式並警告）。
2. ```powershell
   git clone git@github.com:Hereisaa/ai-global.git $env:USERPROFILE\Developer\GitHub\ai-global
   powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\Developer\GitHub\ai-global\setup\install.ps1
   ```
3. 注意：`claude/hooks/` 內是 bash 腳本，原生 Windows 需 Git Bash 才能執行；制度路徑統一為 `~/Developer/agent-governance`（install.ps1 會在 `%USERPROFILE%\Developer\` 建 Junction，Git Bash 下 `$HOME/Developer/...` 同樣成立）。
4. 記憶體回收（Windows 專屬，選用；macOS 對應版見上節）：長期跑 Claude Code 會留下孤兒程序（MCP server、dev server、模擬器、headless 瀏覽器）與只長不縮的 WSL vmmem。`claude/hooks/cleanup-orphans.ps1` 負責清理，兩層觸發：
   - `SessionEnd` hook（`~/.claude/settings.json`，機器本地，手動加）：`powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\hooks\cleanup-orphans.ps1" -Scope session` — 只清該 session 自己的子孫。
   - 排程工作：`powershell -ExecutionPolicy Bypass -File setup\install-cleanup-task.ps1`（每 2 小時＋登入；`-IntervalHours N` 調整、`-Uninstall` 移除）— 清父程序已消失的孤兒、Docker 閒置且 vmmem >3 GB 時 `wsl --shutdown`。
   - 安全規則：**絕不殺 `claude` 主程序**（Remote Control 就是長駐的 claude），命令列含 `remote-control` 的整棵子樹一律跳過；超過 1.5 GB 或 24 小時的 session 只發 toast 提醒。紀錄在 `~/.claude/logs/cleanup.log`；`-DryRun` 可預演。

### 裝完之後（兩平台相同）

開一個 Claude Code session，執行 `/sync-check` 做唯讀對帳；要補裝或套用差異時明確指定範圍。

## 日常工作流

- 改了指令／制度檔／自製 skill：完成相關驗證，再提交本次範圍；已獲對外發布授權才 push。
- 換到另一台時先確認工作樹；已要求同步且可安全更新時用 `git pull --ff-only`，再檢查掛載與內容。
- 新第三方能力要跨機共用時，更新 `manifest/skills.json` 並驗證來源；發布與安裝遵守各自授權。
- 制度修改依 `governance/40-maintenance.md`：乾淨且已追蹤的版本用 Git 回復；未提交或未追蹤的重要內容先備份。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、`.env`、API key）**永不進本倉庫**。commit 前發現疑似金鑰，停下來處理。
- 本倉庫必須保持 **private**。


## 治理檢查

```bash
python3 setup/check_governance.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s setup -p 'test_*.py'
python3 setup/check_governance.py --local
```

離線檢查支援 Python 3.9+；本機 Codex TOML 對帳需 Python 3.11+ 的標準函式庫。Windows 可使用 `python`，測試時以環境變數 `PYTHONDONTWRITEBYTECODE=1` 避免產生快取。

- 離線檢查：兩邊入口一致、制度路由與現行相對連結有效、設定白名單結構正確；行數只是維護預算。
- `--local`：另核對本機連結／副本內容及支援的模型設定欄位。漂移只回報，不擅自修設定；不包含完整權限、hooks 或插件對帳。
- `bash setup/install.sh check`：保留原有所有安裝連結檢查，不能替代內容／設定檢查。完整設定對帳仍依 manifest 與 `/sync-check`。
- `.github/workflows/governance.yml` 在 push／PR 執行離線檢查和單元測試。加入工作流程不等於遠端已跑過，也不等於已設成分支保護的必要檢查。
- [驗收情境](docs/reference/governance-evaluation.md) 用於獨立規則讀回及後續各平台行為測試；[平台機制](docs/reference/agent-runtime.md) 記錄資料來源與限制。

這些檢查不會強制模型遵守全部安全紅線，也不會自動調整本機 sandbox、權限或掛載 hooks。
