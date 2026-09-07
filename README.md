# ai-global — AI 全域環境同步倉庫

跨機器（macOS ↔ Windows）同步 AI 工具的**使用者全域層**：system prompt（CLAUDE.md／AGENTS.md）、制度規則（governance）、自製 skills／commands／agents、hooks，以及第三方能力的安裝清單。

## 核心模型（先懂這個，其他都是細節）

```
<clone 在哪都行>            ← 你在這裡編輯，這裡是 git 正本
  D:\GitHub\ai-global            (Windows)
  ~/Developer/GitHub/ai-global   (macOS)
        │  setup/install.sh  |  setup\install.ps1
        │  （複製，全部是實體檔案，沒有任何 symlink／junction）
        ▼
~/.ai-global/                ← 機器上的部署端，兩平台同一個路徑
  ├── governance/            ← 制度規則 SSOT，兩個 router 都指向這裡
  └── .deploy-state.json     ← 記著這台是從哪個 clone、哪個 commit 部署的
~/.claude/CLAUDE.md          ← 實體檔案（Claude Code / Cowork 讀）
~/.codex/AGENTS.md           ← 實體檔案（Codex 讀）
~/.claude/{hooks,statusline.sh,skills,commands,agents}
```

三件事說明為什麼這樣設計：

1. **部署端是複製，不是連結。** 連結一斷（clone 搬家、換槽、被刪），Claude／Codex 會安靜地載不到任何全域指令，而且沒有任何錯誤訊息。實體檔案不會有這個失效模式。
2. **代價是副本會漂移**，所以腳本有 `check` 模式：逐檔比對，並用 `.deploy-state.json` 記的 commit 分辨「repo 往前走了」（`BEHIND`，直接更新即可）跟「有人改了部署端」（`EDITED`，要人裁決）。
3. **`git pull` 不會自動改全域。** pull 後跑一次 `check` 自己決定要不要部署。腳本會裝一個 `post-merge` git hook，pull 完提醒你。

`~/.ai-global` 在新機器上本來就不存在——它由 `setup/install.*` 建立。

## 給 AI agent 的指引（讀到這裡的模型，照此執行）

**如果你被要求「設置／接上這台機器」，依序執行**：
1. 判斷 OS，跑對應腳本（冪等，可重複執行；不刪檔，被取代的既有檔移入 `~/.ai-trash/`）：
   - macOS/Linux：`bash setup/install.sh`
   - Windows：`powershell -ExecutionPolicy Bypass -File setup\install.ps1`
2. 照 `manifest/skills.json` 補裝第三方能力：`type: plugin` 引導使用者用 `/plugin` 安裝；`type: skill` 從 `source` 標的 GitHub repo 抓對應目錄放入 `~/.claude/skills/<name>/`；`type: command` 放入 `target` 路徑。
3. 照 `manifest/settings.json` 核對本機 `~/.claude/settings.json` 與 `~/.codex/config.toml` 的共用 key，缺漏回報使用者裁決後補上。
4. 完成後逐項回報 PASS/FAIL 附證據。（Claude Code 裝好後，第 2–3 步可直接用 `/ai-global` skill 執行。）

**如果你被要求「同步／對帳」**：`git pull --ff-only`，再跑 check（macOS `bash setup/install.sh check`；Windows `powershell -ExecutionPolicy Bypass -File setup\install.ps1 -Mode check`），照下表處置，最後做上面第 2–4 步。

**紅線（對 agent 強制）**：
- 修改本 repo 內容後必須 `git commit && git push`，否則另一台機器拿不到。
- **不要直接編輯部署端**（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/**`）。改 clone 內的對應檔，再部署。
- 禁止 `rm`／程式化刪除；移除一律 `mv` 進 `~/.ai-trash/` 加時間戳。
- 任何憑證（`.credentials.json`、`auth.json`、`.env*`、API key）不得進本 repo；commit 前自查。
- 制度檔（`governance/`）的修改要先讀 `governance/40-maintenance.md`（備份、變更紀錄、權限分級）。

## 部署對照表

| 倉庫路徑 | 部署位置 | 備註 |
|---|---|---|
| `governance/` | `~/.ai-global/governance/` | 制度規則 SSOT；`backups/` 不部署 |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | Claude Code / Cowork 全域指令 |
| `codex/AGENTS.md` | `~/.codex/AGENTS.md` | Codex 全域指令 |
| `claude/statusline.sh` | `~/.claude/statusline.sh` | |
| `claude/hooks/` | `~/.claude/hooks/` | 整個目錄鏡像（repo 移除的檔會進 trash） |
| `claude/skills/<name>/` | `~/.claude/skills/<name>/` | **逐一部署**，讓第三方 skill 能在同一層並存 |
| `claude/commands/<name>` | `~/.claude/commands/<name>` | 逐一部署 |
| `claude/agents/<name>` | `~/.claude/agents/<name>` | 逐一部署 |

**不部署、只對帳**：`~/.claude/settings.json` 與 `~/.codex/config.toml`——這兩個檔工具自己會回寫，共用基準記在 `manifest/settings.json`。`manifest/` 整個目錄只留在 clone 裡給 `/ai-global` 讀，不部署。
**永不進倉庫**：`settings.local.json`、Codex 的機器路徑設定、任何憑證。

## check 的狀態碼

| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 一致 | 無事 |
| `MISSING` | 還沒部署 | 跑 install |
| `STALE` | 舊版留下的斷鏈 | 跑 install（腳本自行清掉連結） |
| `BEHIND` | repo 有新內容，部署端停在上次部署的版本 | 跑 install |
| `EDITED` | 部署端被人在 repo 外改過 | **先看 diff 再決定**：要嘛把改動搬回 clone commit，要嘛跑 install 蓋掉（舊檔進 trash） |
| `EXTRA` | 部署端有 repo 已移除的檔 | 跑 install（舊檔進 trash） |

## 新機器上手

clone 位置隨你，腳本會自己算出來並記進 `.deploy-state.json`。

### macOS / Linux

```bash
git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
bash ~/Developer/GitHub/ai-global/setup/install.sh
bash ~/Developer/GitHub/ai-global/setup/install.sh check   # 應該全部 OK
```

### macOS 記憶體回收（選用）

`claude/hooks/cleanup-orphans.sh`，與 Windows 版同語意、同 log 檔，兩層觸發：

- `SessionEnd` hook（寫在 `~/.claude/settings.json`，機器本地，手動加）：
  `bash ~/.claude/hooks/cleanup-orphans.sh --scope session` — 只清該 session 自己的子孫。
- launchd agent：`bash setup/install-cleanup-agent.sh`（每 2 小時＋載入時；`--interval-hours N` 調整、`--uninstall` 移除）。
- macOS 與 Windows 的差異（因為孤兒在 macOS 是被 launchd 收養成 ppid=1，不是失去父程序）：只看自己 uid 的程序；`launchctl list` 裡的 PID 一律跳過（那是使用者自己註冊的服務，例如 dev server、gateway）；`~/.claude/cleanup-protect.txt` 可加自訂保護 regex（一行一條）。
- 容器 VM 對應 Windows 的 vmmem：Colima／lima。VM >3 GB 且無執行中容器時 `colima stop`。實測：Homebrew 版 colima 的 launchd job 雖設 `KeepAlive`，但 `colima start -f` 這個監管程序在 VM 停止後不會結束，所以 launchd 不會把 VM 拉回來——停了就是停了，log 會附上重啟指令 `launchctl kickstart -k gui/$(id -u)/homebrew.mxcl.colima`。另外偵測到 Docker Desktop 與非 Desktop context 並存時會提醒關掉。
- 安全規則與 Windows 版一致：**絕不殺 `claude` 主程序**，命令列含 `remote-control` 的整棵子樹跳過；超過 1.5 GB 或 24 小時的 session 只發通知。紀錄在 `~/.claude/logs/cleanup.log`；`--dry-run` 可預演。

### Windows

```powershell
git clone git@github.com:Hereisaa/ai-global.git D:\GitHub\ai-global
powershell -ExecutionPolicy Bypass -File D:\GitHub\ai-global\setup\install.ps1
powershell -ExecutionPolicy Bypass -File D:\GitHub\ai-global\setup\install.ps1 -Mode check
```

不需要開發人員模式，也不需要系統管理員——沒有 symlink 就沒有權限問題。

注意：`claude/hooks/` 裡三支腳本並存，由各平台的 `settings.json` 各自指名——`stop-typecheck.sh` 與 `cleanup-orphans.sh` 是 bash（原生 Windows 要有 Git Bash 才跑得動），`cleanup-orphans.ps1` 是 PowerShell。

### Windows 記憶體回收（選用）

長期跑 Claude Code 會留下孤兒程序（MCP server、dev server、模擬器、headless 瀏覽器）與只長不縮的 WSL vmmem。`claude/hooks/cleanup-orphans.ps1` 負責清理，兩層觸發：

- `SessionEnd` hook（寫在 `~/.claude/settings.json`，機器本地，手動加）：
  `powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\hooks\cleanup-orphans.ps1" -Scope session` — 只清該 session 自己的子孫。
- 排程工作：`powershell -ExecutionPolicy Bypass -File setup\install-cleanup-task.ps1`（每 2 小時＋登入；`-IntervalHours N` 調整、`-Uninstall` 移除）— 清父程序已消失的孤兒、Docker 閒置且 vmmem >3 GB 時 `wsl --shutdown`。
- 安全規則：**絕不殺 `claude` 主程序**（Remote Control 就是長駐的 claude），命令列含 `remote-control` 的整棵子樹一律跳過；超過 1.5 GB 或 24 小時的 session 只發 toast 提醒。紀錄在 `~/.claude/logs/cleanup.log`；`-DryRun` 可預演。

### 裝完之後（兩平台相同）

開一個 Claude Code session，執行 `/ai-global`：照 manifest 補裝第三方 skills/plugins、核對 settings 共用項。

## 日常工作流

- 改了 CLAUDE.md／制度檔／自製 skill → 在 clone 內改 → 跑 install 部署 → `git commit && git push`。
- 換到另一台開工前 → `git pull` → 跑 `check` → 需要就 install。（或直接 `/ai-global`，它包含 pull、check 與 manifest 對帳。）
- 裝了新的第三方 skill 且想要兩台都有 → 把它記進 `manifest/skills.json` 再 push。
- 制度檔的修改規範（備份、變更紀錄、權限分級）照 `governance/40-maintenance.md`；git 歷史是第二層回滾機制。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、`.env`、API key）**永不進本倉庫**。commit 前發現疑似金鑰，停下來處理。
- 本倉庫必須保持 **private**。
