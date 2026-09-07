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
~/.ai-global/                ← 機器上的部署端，兩平台同一個路徑，整個目錄由腳本擁有
  ├── governance/            ← 制度規則 SSOT，兩個 router 都指向這裡
  └── .deploy-state.json     ← 這台從哪個 clone 部署、每個檔部署時的雜湊、管理了哪些項目
~/.claude/CLAUDE.md          ← 實體檔案（Claude Code / Cowork 讀）
~/.codex/AGENTS.md           ← 實體檔案（Codex 讀）
~/.claude/{hooks,statusline.sh,skills/<自製>,commands/<自製>,agents/<自製>}
~/.ai-trash/                 ← 被取代的檔全部進這裡（加時間戳），全程沒有刪除
```

三件事說明為什麼這樣設計：

1. **部署端是複製，不是連結。** 連結一斷（clone 搬家、換槽、被刪），Claude／Codex 會安靜地載不到任何全域指令，而且沒有任何錯誤訊息。實體檔案不會有這個失效模式。
2. **代價是副本會漂移**，所以腳本有 `check` 模式：逐檔比對，並用 `.deploy-state.json` 記的**檔案雜湊**分辨「repo 往前走了」（`BEHIND`，直接更新即可）跟「有人改了部署端」（`EDITED`，要人裁決）。靠雜湊而不是 commit，所以從未 commit 的工作樹部署也判得準。
3. **`git pull` 不會自動改全域。** pull 後跑一次 `check` 自己決定要不要部署。腳本會裝 `post-merge`／`post-rewrite` 兩個 git hook，pull（含 `--rebase`）完提醒你。

`~/.ai-global` 在新機器上本來就不存在——它由 `setup/install.*` 建立。

## 倉庫結構

```
claude/
  CLAUDE.md            Claude Code 全域 router（部署到 ~/.claude/CLAUDE.md）
  statusline.sh        狀態列（repo·worktree、分支、模型、context、額度、token）
  hooks/               cleanup-orphans.{sh,ps1}（記憶體回收）、stop-typecheck.sh
  skills/ai-global/    部署／同步／對帳的 skill（見下）
  commands/ agents/    自製 slash command 與 agent（目前空）
codex/
  AGENTS.md            Codex 全域 router，內容與 CLAUDE.md 對等、節次對齊，只在工具能力處分歧
governance/            制度規則本體（10 委派、20 判斷、30 模板、40 維護、50 安全、60 起手式、70 行為契約、80 工程）
manifest/
  skills.json          每台機器該有的第三方 skills／plugins／commands（名稱＋來源＋版本），不部署
  settings.json        ~/.claude/settings.json 與 ~/.codex/config.toml 該有的共用 key，不部署、只對帳
setup/
  install.sh / install.ps1            部署與檢查（兩支語意完全相同）
  install-cleanup-agent.sh            macOS launchd agent（記憶體回收排程）
  install-cleanup-task.ps1            Windows 排程工作（同上）
```

## 給 AI agent 的指引（讀到這裡的模型，照此執行）

**Claude Code 已部署過的機器**：直接用 `/ai-global` skill——`check`（唯讀對帳）、`sync`（pull → 部署 → 對帳）、`deploy`（首次／重新部署）、`govcheck`（制度靜態檢查）、`install <name>`（補裝一項）；不帶參數會列選單。

**全新機器（skill 還不存在）或 Codex**，依序執行：
1. 判斷 OS，跑對應腳本（冪等，可重複執行；不刪檔，被取代的既有檔移入 `~/.ai-trash/`）：
   - macOS/Linux：`bash setup/install.sh`
   - Windows：`powershell -ExecutionPolicy Bypass -File setup\install.ps1`
   - 目標位置若已有使用者自己的 `CLAUDE.md`／`AGENTS.md`，先跑 `check`（會報 `EDITED`），**明講「原本的會被取代、原檔會在 `~/.ai-trash/`」並取得同意**，再 install。
2. 照 `manifest/skills.json` 補裝第三方能力：`type: plugin` 引導使用者用 `/plugin` 安裝；`type: skill` 從 `source` 標的 GitHub repo 抓對應目錄（有 `path` 就抓該子目錄）放入 `~/.claude/skills/<name>/`；`type: command` 放入 `target` 路徑。
3. 照 `manifest/settings.json` 核對本機 `~/.claude/settings.json` 與 `~/.codex/config.toml` 的共用 key，缺漏回報使用者裁決後補上。
4. 完成後逐項回報 PASS/FAIL 附證據。

**如果你被要求「同步／對帳」**：`git pull --ff-only`，再跑 check（macOS `bash setup/install.sh check`；Windows `powershell -ExecutionPolicy Bypass -File setup\install.ps1 -Mode check`），照下表處置，最後做上面第 2–4 步。

**紅線（對 agent 強制）**：
- 修改本 repo 內容後完成驗證與回報並 commit；**push 須有使用者對具體遠端／分支的明確授權**（依 `governance/40-maintenance.md`）。未推送的變更不會同步到另一台機器。
- **不要直接編輯部署端**（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/**`）。改 clone 內的對應檔，再部署。
- 禁止 `rm`／程式化刪除；移除一律 `mv` 進 `~/.ai-trash/` 加時間戳。
- 任何真實憑證（`.credentials.json`、`auth.json`、環境值、API key）不得進本 repo；無秘密的 `.env.example` 依 `governance/50-safety.md` 檢查後可追蹤。commit 前自查。
- 制度檔（`governance/`）的修改要先讀 `governance/40-maintenance.md`（備份、變更紀錄、權限分級）。

## 部署對照表

| 倉庫路徑 | 部署位置 | 管理方式 |
|---|---|---|
| `governance/` | `~/.ai-global/governance/` | 整個目錄鏡像；`backups/` 不部署 |
| （`~/.ai-global/` 頂層） | | 只允許 `governance/` 與 `.deploy-state.json`，其他一律視為舊版殘留收進 trash |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | 單檔 |
| `codex/AGENTS.md` | `~/.codex/AGENTS.md` | 單檔 |
| `claude/statusline.sh` | `~/.claude/statusline.sh` | 單檔 |
| `claude/hooks/` | `~/.claude/hooks/` | 整個目錄鏡像（repo 移除的檔會進 trash） |
| `claude/skills/<name>/` | `~/.claude/skills/<name>/` | **逐一部署**，第三方 skill 在同一層並存不受影響；repo 改名／移除的，舊副本會自動收進 trash |
| `claude/commands/<name>` | `~/.claude/commands/<name>` | 逐一部署，同上 |
| `claude/agents/<name>` | `~/.claude/agents/<name>` | 逐一部署，同上 |

**不部署、只對帳**：`~/.claude/settings.json` 與 `~/.codex/config.toml`——這兩個檔工具自己會回寫，共用基準記在 `manifest/settings.json`。`manifest/` 整個目錄只留在 clone 裡給 `/ai-global` 讀。
**永不進倉庫**：`settings.local.json`、Codex 的機器路徑設定、任何憑證。

### `.deploy-state.json` 記什麼

| 欄位 | 用途 |
|---|---|
| `source_repo` | 這台的 clone 在哪；skill 與 router 都靠它找到 repo |
| `files` | 每個部署檔的 blob hash（`git hash-object`）。部署端內容 == 記錄的 hash → 沒人動過 → `BEHIND`；否則 `EDITED` |
| `managed` | 這次逐一部署了哪些 skill／command／agent。下次 repo 沒有的 → `EXTRA`，install 時收進 trash |
| `commit`／`branch`／`deployed_at`／`platform` | 顯示用 |

## check 的狀態碼

| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 一致 | 無事 |
| `MISSING` | 還沒部署 | 跑 install |
| `STALE` | 舊版留下的斷鏈 | 跑 install（腳本自行清掉連結） |
| `BEHIND` | repo 有新內容，部署端停在上次部署的版本 | 跑 install |
| `EDITED` | 部署端被人在 repo 外改過 | **先看 diff 再決定**：要嘛把改動搬回 clone commit，要嘛跑 install 蓋掉（舊檔進 trash） |
| `EXTRA` | 部署端有 repo 已移除／改名的檔或項目 | 跑 install（舊檔進 trash） |

`check` 唯讀、exit 1 代表有事要處理。install 輸出裡的 `WARN`／`DROP` 行與結尾的 `NOTE` 是「哪些東西被換掉、放在哪」的唯一紀錄，要看。

## 新機器上手

clone 位置隨你，腳本會自己算出來並記進 `.deploy-state.json`。

### macOS / Linux

```bash
git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
bash ~/Developer/GitHub/ai-global/setup/install.sh
bash ~/Developer/GitHub/ai-global/setup/install.sh check   # 應該全部 OK
```

### Windows

```powershell
git clone git@github.com:Hereisaa/ai-global.git D:\GitHub\ai-global
powershell -ExecutionPolicy Bypass -File D:\GitHub\ai-global\setup\install.ps1
powershell -ExecutionPolicy Bypass -File D:\GitHub\ai-global\setup\install.ps1 -Mode check
```

不需要開發人員模式，也不需要系統管理員——沒有 symlink 就沒有權限問題。Git Bash 下跑 `install.sh` 也可以，兩支語意相同。

### 從 symlink 時代的舊部署升級（2026-09-07 前裝的機器，一次性）

pull 之後直接跑 install：斷鏈會報 `STALE` 並自動清掉，`~/.ai-global` 頂層的舊 `manifest/` 會自動收進 trash，`~/Developer/agent-governance` 不再使用（可自行搬進 `~/.ai-trash/`）。唯一要手動做的：舊的 `sync-check` skill 是在「管理清單」機制之前部署的，腳本不知道它是自己放的，請 `mv ~/.claude/skills/sync-check ~/.ai-trash/`。

### 裝完之後（兩平台相同）

開一個 Claude Code session，執行 `/ai-global`：照 manifest 補裝第三方 skills/plugins、核對 settings 共用項。

### hooks 是機器本地、手動接的

`claude/hooks/` 裡三支腳本會部署到 `~/.claude/hooks/`，但**要不要啟用由各機器的 `~/.claude/settings.json` 決定**，manifest 不管 hooks（兩平台的觸發方式不同）：

| 腳本 | 語言 | 接法 |
|---|---|---|
| `stop-typecheck.sh` | bash | `Stop` hook：`bash ~/.claude/hooks/stop-typecheck.sh`——session 要結束時若有髒的 `.ts/.tsx` 且專案有 `typecheck` script，跑不過就擋下並把錯誤餵回去 |
| `cleanup-orphans.sh` | bash（macOS） | 見下節 |
| `cleanup-orphans.ps1` | PowerShell（Windows） | 見下節 |

原生 Windows 跑 bash 腳本需要 Git Bash。

### 記憶體回收（選用）

長期跑 Claude Code 會留下孤兒程序（MCP server、dev server、模擬器、headless 瀏覽器）與只長不縮的容器 VM。兩平台各一支同語意、同 log 檔（`~/.claude/logs/cleanup.log`）的腳本，兩層觸發；安全規則一致：**絕不殺 `claude` 主程序**（Remote Control 就是長駐的 claude），命令列含 `remote-control` 的整棵子樹跳過；超過 1.5 GB 或 24 小時的 session 只發通知；`--dry-run`／`-DryRun` 可預演。

**macOS**：`cleanup-orphans.sh`
- `SessionEnd` hook（`~/.claude/settings.json`）：`bash ~/.claude/hooks/cleanup-orphans.sh --scope session` — 只清該 session 自己的子孫。
- launchd agent：`bash setup/install-cleanup-agent.sh`（每 2 小時＋載入時；`--interval-hours N` 調整、`--uninstall` 移除）。
- 平台差異（孤兒在 macOS 是被 launchd 收養成 ppid=1，不是失去父程序）：只看自己 uid 的程序；`launchctl list` 裡的 PID 一律跳過（使用者自己註冊的服務）；`~/.claude/cleanup-protect.txt` 可加自訂保護 regex（一行一條）。
- 容器 VM：Colima／lima。VM >3 GB 且無執行中容器時 `colima stop`。Homebrew 版 colima 的 launchd job 雖設 `KeepAlive`，但 `colima start -f` 監管程序在 VM 停止後不會結束，所以不會自動拉回來——log 會附重啟指令 `launchctl kickstart -k gui/$(id -u)/homebrew.mxcl.colima`。偵測到 Docker Desktop 與非 Desktop context 並存時會提醒。

**Windows**：`cleanup-orphans.ps1`
- `SessionEnd` hook（`~/.claude/settings.json`）：`powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\hooks\cleanup-orphans.ps1" -Scope session`。
- 排程工作：`powershell -ExecutionPolicy Bypass -File setup\install-cleanup-task.ps1`（每 2 小時＋登入；`-IntervalHours N` 調整、`-Uninstall` 移除）— 清父程序已消失的孤兒、Docker 閒置且 vmmem >3 GB 時 `wsl --shutdown`。

## 日常工作流

- 改了 CLAUDE.md／制度檔／自製 skill → 在 clone 內改 → 跑 install 部署 → 驗證 → commit；push 依授權。
- 換到另一台開工前 → `git pull` → 跑 `check` → 需要就 install。（或直接 `/ai-global`，它包含 pull、check 與 manifest 對帳。）
- 裝了新的第三方 skill 且想要兩台都有 → 把它記進 `manifest/skills.json` 再 push。
- 改 CLAUDE.md 或 AGENTS.md 任一邊 → 順手看另一邊要不要跟；兩邊節次刻意對齊，只在工具能力處分歧（分支前綴 `claude/` vs `codex/`、`/ai-global` 只有 Claude Code 能跑、子代理機制）。
- 制度檔的修改規範（備份、變更紀錄、權限分級）照 `governance/40-maintenance.md`；git 歷史是第二層回滾機制。

## 治理檢查

```bash
python setup/check_governance.py            # 離線：兩個 router 節次對齊與各自前綴、制度路由、相對連結、manifest 結構
python -m unittest discover -s setup -p 'test_*.py'
python setup/check_governance.py --local    # 加上本機副本內容與白名單設定欄位的對帳
```

離線檢查支援 Python 3.9+；`--local` 的 Codex TOML 對帳需 Python 3.11+，舊版跳過時會明列缺口。測試前設 `PYTHONDONTWRITEBYTECODE=1` 避免產生快取。`.github/workflows/governance.yml` 在 push／PR 於三個 OS 跑離線檢查與單元測試——工作流程存在不等於分支保護已設。

- 離線檢查會擋的：兩個 router `##` 節次不對齊（Cowork 為 Claude 專屬例外）、AGENTS.md 抄到 `claude/` 前綴或 CLAUDE.md 抄到 `codex/`、router 缺任一制度檔路由、相對連結斷鏈、manifest 白名單欄位型別錯。行數只是維護預算（WARN）。
- `--local` 只回報漂移不改設定；完整部署對帳仍以 `setup/install.* check` 與 `/ai-global` 為準（含 hooks、skills、EXTRA／BEHIND／EDITED 分類）。
- 這些檢查不會強制模型遵守紅線，也不會自動調整本機 sandbox、權限或 hooks。[驗收情境](docs/reference/governance-evaluation.md) 用於獨立讀回；[執行環境參考](docs/reference/agent-runtime.md) 記錄各工具的載入與權限機制。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、`.env`、API key）**永不進本倉庫**。commit 前發現疑似金鑰，停下來處理。
- 本倉庫必須保持 **private**。
