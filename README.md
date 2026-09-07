# ai-global

把兩台機器（macOS 主力、Windows 副機）上給 AI 工具的**使用者全域層**集中在一個 private repo：router、憲法、自製能力、第三方清單、部署工具。

| 層 | 內容 | 給誰讀 |
|---|---|---|
| **Router**（入口） | `claude/CLAUDE.md`、`codex/AGENTS.md` | Claude Code／Cowork、Codex 每個 session 自動載入 |
| **憲法**（governance） | 10 委派、20 判斷、30 模板、40 維護、50 安全、60 起手式、70 行為契約、80 工程 | 模型按 router 的路由按需讀 |
| **能力** | skill `ai-global`、3 支 hooks、statusline | Claude Code |
| **清單**（manifest） | 第三方 skills／plugins／commands 名單、settings 共用基準 | 對帳用，不部署 |
| **工具**（setup） | 部署腳本 ×2、治理 checker＋測試、記憶體回收排程安裝器 ×2 | 人與 agent |
| **參考**（docs/reference） | 各工具官方載入／權限機制、治理驗收情境 | 人與 agent |

## 核心設計：三個決策

**1. 部署是複製，不是連結。**
`setup/install.*` 把 repo 內容**複製**到工具讀的固定位置。clone 在哪都行、可以搬、甚至刪掉，機器上的全域設定不受影響。（舊的 symlink 模型在 Windows 上因為 clone 換槽整條斷過好幾週，而 Claude／Codex 沒有任何錯誤訊息。）

**2. 副本會漂移，所以用狀態檔抓。**
`~/.ai-global/.deploy-state.json` 記 `source_repo`（clone 在哪）、`files`（每檔部署時的 blob hash）、`managed`（逐一部署了哪些 skill／command／agent）。`check` 據此分六種狀態：

| 狀態 | 意思 | 處置 |
|---|---|---|
| `OK` | 一致 | — |
| `MISSING` | 還沒部署 | install |
| `STALE` | 舊版留下的斷鏈 | install（自動清） |
| `BEHIND` | repo 前進了，部署端沒人動過 | install |
| `EXTRA` | repo 已移除／改名的東西還在 | install（收進 trash） |
| `EDITED` | 部署端被人在 repo 外改過 | **先看 diff，人裁決** |

BEHIND／EDITED 靠 hash 不靠 commit，所以從未 commit 的工作樹部署也判得準。所有取代都 `mv` 進 `~/.ai-trash/<時間戳>/`，零刪除。

**3. 兩個 router 平行但不逐字相同。**
節次刻意對齊，只在工具能力處分歧：分支前綴 `claude/` vs `codex/`、`/ai-global` 只有 Claude Code 能跑、子代理機制。`setup/check_governance.py` 把「節次不對齊」與「照抄對面前綴」直接判 FAIL，CI 每次都跑。

## 資料流

```
你在 clone 改檔 ──install──▶ ~/.ai-global/governance/          ← router 指向的 SSOT
                          ├─▶ ~/.claude/CLAUDE.md、hooks/、statusline.sh、skills/ai-global/
                          └─▶ ~/.codex/AGENTS.md
                ──commit──▶ 本機 git ──push（需授權）──▶ origin ──pull──▶ 另一台 clone ──install──▶ …
```

不在這條線上的：`~/.claude/settings.json`、`~/.codex/config.toml` 由工具自己回寫，只用 `manifest/settings.json` 對帳；`manifest/` 整個只留在 clone。`git pull` 不會自動改全域——腳本裝的 `post-merge`／`post-rewrite` hook 只提醒你跑 check。

## 日常操作

| 情境 | 指令 |
|---|---|
| 看有沒有漂移 | `/ai-global check`（唯讀） |
| 另一台改了 | `/ai-global sync`（pull → check → 裁決 → install → 對帳） |
| 新機器／重裝 | `/ai-global deploy`；沒 Claude 時直接跑 `setup/install.*` |
| 改完 router／制度檔 | `/ai-global govcheck` 或 `python setup/check_governance.py` |
| 補一個第三方能力 | `/ai-global install <name>` |
| 手動 | macOS `bash setup/install.sh [check]`；Windows `powershell -ExecutionPolicy Bypass -File setup\install.ps1 [-Mode check]` |

`/ai-global` 不帶參數會列選單。`check` 唯讀；install 輸出的 `WARN`／`DROP`／`NOTE` 是「哪些東西被換掉、放在哪」的唯一紀錄。

改東西的節奏：**改 clone → install → 驗證 → commit；push 依授權**（憲法 40）。

## 新機器上手

clone 位置隨你，腳本會自己算出來並記進 state。

```bash
# macOS / Linux
git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
bash ~/Developer/GitHub/ai-global/setup/install.sh
bash ~/Developer/GitHub/ai-global/setup/install.sh check   # 應該全部 OK
```
```powershell
# Windows（不需要開發人員模式或系統管理員——沒有 symlink 就沒有權限問題）
git clone git@github.com:Hereisaa/ai-global.git D:\GitHub\ai-global
powershell -ExecutionPolicy Bypass -File D:\GitHub\ai-global\setup\install.ps1
powershell -ExecutionPolicy Bypass -File D:\GitHub\ai-global\setup\install.ps1 -Mode check
```

目標位置若已有你自己的 `CLAUDE.md`／`AGENTS.md`：先跑 `check` 會報 `EDITED`；install 會取代它並把原檔放進 `~/.ai-trash/`。

裝完開一個 Claude Code session 跑 `/ai-global check`，補齊第三方能力與 settings 共用項。

### 從 symlink 時代升級（2026-09-07 前裝的機器，一次性）

`git pull` 後直接 `install`：symlink 會報 `STALE` 並被連結本身搬進 trash（指向的檔還在 clone）、舊 `~/.ai-global/manifest/` 自動收掉、`~/Developer/agent-governance` 不再使用（可自行搬進 `~/.ai-trash/`）。唯一手動步驟：舊的 `sync-check` skill 是在管理清單機制之前部署的，請 `mv ~/.claude/skills/sync-check ~/.ai-trash/`。

## 倉庫結構

```
claude/
  CLAUDE.md                  Claude Code router → ~/.claude/CLAUDE.md
  statusline.sh              狀態列：repo·worktree、分支、模型、context、5h/7d 額度、token
  hooks/                     cleanup-orphans.{sh,ps1}、stop-typecheck.sh → ~/.claude/hooks/（整目錄鏡像）
  skills/ai-global/          20 行分派器 + commands/{check,sync,deploy,govcheck,install,common}.md
  commands/ agents/          自製 slash command 與 agent（目前空；逐一部署）
codex/AGENTS.md              Codex router → ~/.codex/AGENTS.md
governance/                  憲法本體 → ~/.ai-global/governance/（整目錄鏡像；backups/ 不部署）
manifest/skills.json         第三方能力清單（名稱＋來源＋版本）
manifest/settings.json       settings 共用基準（Claude 四個區塊；Codex 只有 personality）
setup/install.sh|.ps1        部署與檢查，兩支語意完全相同
setup/check_governance.py    治理靜態檢查（+ test_check_governance.py，35 個測試）
setup/install-cleanup-*.{sh,ps1}  記憶體回收排程安裝器
docs/reference/              agent-runtime.md（工具機制）、governance-evaluation.md（驗收情境）
.github/workflows/governance.yml  三 OS 跑 checker 與測試
```

`~/.ai-global/` 頂層只允許 `governance/` 與 `.deploy-state.json`，其他一律視為舊版殘留收進 trash。`~/.claude/skills|commands|agents` 底下只動 repo 自己的項目，第三方的原地不碰。

## 技術棧

| 元件 | 技術 | 為何 |
|---|---|---|
| `install.sh` | bash，macOS 3.2 相容 | macOS／Linux／Git Bash 通用 |
| `install.ps1` | PowerShell 5.1，純 .NET 不用 cmdlet | 從 Git Bash 啟動的 PS 叫不到 `Get-FileHash`／`ConvertFrom-Json` |
| 比對 | 位元組比對；hash 用 `git hash-object` | 兩平台語意一致，和 git blob 對得上 |
| 狀態檔 | 手寫 JSON，一行一 key | bash 端用 sed 就讀得動 |
| checker | Python 3.9+ 標準庫；`tomllib`（3.11+）讀 Codex config | 三 OS CI 零依賴 |
| 測試 | `unittest` 記憶體 fixture，不碰磁碟 | 0.04 秒跑完 |
| skill | Claude Code skill，`$ARGUMENTS` 分派 | 無參數只載 20 行就彈選單 |
| 記憶體回收 | macOS bash＋launchd；Windows PowerShell＋Task Scheduler | 同語意同 log |
| 行尾 | `.gitattributes` 強制 LF | macOS 的 shebang 需要 |

## 給 AI agent 的指引

**Claude Code 已部署過的機器**：用 `/ai-global`。

**全新機器（skill 還不存在）或 Codex**：
1. 判斷 OS，跑對應 `setup/install.*`（冪等；被取代的既有檔移入 `~/.ai-trash/`）。目標位置已有使用者自己的 router 時，先 `check`、**明講會被取代並取得同意**，再 install。
2. 照 `manifest/skills.json` 補裝：`plugin` 引導用 `/plugin`；`skill` 從 `source`（有 `path` 就抓該子目錄）放入 `~/.claude/skills/<name>/`；`command` 放入 `target`。
3. 照 `manifest/settings.json` 核對本機 `~/.claude/settings.json` 與 `~/.codex/config.toml` 的共用 key，缺漏回報使用者裁決後補上。
4. 逐項回報 PASS/FAIL 附證據。

**紅線（對 agent 強制）**：不直接編輯部署端（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/**`）；禁止 `rm`／程式化刪除，一律 `mv` 進 `~/.ai-trash/`；push 須使用者對具體遠端／分支明確授權；任何真實憑證不進 repo；改 `governance/` 先讀 `governance/40-maintenance.md`。

## hooks 與記憶體回收（機器本地、手動接）

`claude/hooks/` 會部署到 `~/.claude/hooks/`，但**要不要啟用由各機器的 `~/.claude/settings.json` 決定**，manifest 不管 hooks。

| 腳本 | 接法 |
|---|---|
| `stop-typecheck.sh` | `Stop` hook：`bash ~/.claude/hooks/stop-typecheck.sh`——有髒的 `.ts/.tsx` 且專案有 `typecheck` script 時跑，失敗就擋下並把錯誤餵回去 |
| `cleanup-orphans.sh`（macOS） | `SessionEnd`：`bash ~/.claude/hooks/cleanup-orphans.sh --scope session`；排程：`bash setup/install-cleanup-agent.sh`（launchd，每 2h；`--interval-hours N`、`--uninstall`） |
| `cleanup-orphans.ps1`（Windows） | `SessionEnd`：`powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\hooks\cleanup-orphans.ps1" -Scope session`；排程：`setup\install-cleanup-task.ps1`（每 2h；`-IntervalHours N`、`-Uninstall`） |

記憶體回收清的是孤兒程序（MCP server、dev server、模擬器、headless 瀏覽器）與只長不縮的容器 VM（Windows vmmem；macOS Colima／lima）。安全規則：**絕不殺 `claude` 主程序**，命令列含 `remote-control` 的整棵子樹跳過；超過 1.5 GB 或 24 小時的 session 只發通知；`--dry-run`／`-DryRun` 預演；log 在 `~/.claude/logs/cleanup.log`。macOS 差異：只看自己 uid、`launchctl list` 裡的 PID 一律跳過、`~/.claude/cleanup-protect.txt` 可加保護 regex；`colima stop` 後 launchd 不會自動拉回，log 附重啟指令。原生 Windows 跑 bash 腳本需 Git Bash。

## 治理檢查

```bash
python setup/check_governance.py            # 離線：router 節次對齊與各自前綴、制度路由、相對連結、manifest 結構
python -m unittest discover -s setup -p 'test_*.py'
python setup/check_governance.py --local    # 加本機副本內容與白名單設定欄位
```

離線檢查 Python 3.9+；`--local` 的 Codex TOML 對帳需 3.11+。CI（`.github/workflows/governance.yml`）在 push／PR 於三個 OS 跑前兩項——工作流程存在不等於分支保護已設。這些檢查驗結構與連結，**不證明模型遵循**；真正的強制在 sandbox／permissions／hooks／CI。完整部署對帳仍以 `setup/install.* check` 與 `/ai-global` 為準。[驗收情境](docs/reference/governance-evaluation.md)、[執行環境參考](docs/reference/agent-runtime.md)。

## 已知邊界

- Markdown 是行為約定，不是隔離：checker 與 `--local` 只驗「檔在、內容對」，不驗「當次 session 真的載入或遵循」。
- `/ai-global` 彈選單仍是一次模型回合，快不到 shell alias。
- manifest 的 `codex_config` 只共用 `personality`；`model`／`model_reasoning_effort` 是各機器本機獨有（使用者裁決）。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、真實 `.env`、API key）**永不進本倉庫**；無秘密的 `.env.example` 依 `governance/50-safety.md` 檢查後可追蹤。
- 本倉庫必須保持 **private**。
