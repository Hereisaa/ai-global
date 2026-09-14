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

不在這條線上的：`~/.claude/settings.json`、`~/.codex/config.toml` 由工具自己回寫，一般共用項只用 `manifest/settings.json` 對帳；能力開關由 `setup/capabilities.py` 按指定項更新並保留其他設定；`manifest/` 整個只留在 clone。`git pull` 不會自動改全域——腳本只在不存在時建立 `post-merge`／`post-rewrite` 提醒 hook，不覆蓋既有 hook。

## 日常操作

| 情境 | 指令 |
|---|---|
| 看有沒有漂移 | `/ai-global check`（唯讀） |
| 另一台改了 | `/ai-global sync`（pull → check → 裁決 → install → 對帳） |
| 新機器／重裝 | `/ai-global deploy`；沒 Claude 時直接跑 `setup/install.*` |
| 改完 router／制度檔 | `/ai-global govcheck` 或 `python setup/check_governance.py` |
| 查看專案預設／本機既有及開關 | `/ai-global capabilities` 或 `python setup/capabilities.py list` |
| 補一個第三方能力 | `/ai-global install <name>` |
| 手動 | macOS `bash setup/install.sh [check]`；Windows `powershell -ExecutionPolicy Bypass -File setup\install.ps1 [-Mode check]` |

`/ai-global` 可依明確自然語言分派；沒有參數或可判斷意圖才列選單。`check` 唯讀；install 輸出的 `WARN`／`DROP`／`NOTE` 是「哪些東西被換掉、放在哪」的唯一紀錄。

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

裝完跑 `/ai-global check` 或 `python setup/capabilities.py list`，查看專案預設與本機既有能力。缺項只回報，由使用者決定是否安裝；既有開關不因部署或 sync 重設。

### 從 symlink 時代升級（2026-09-07 前裝的機器，一次性）

`git pull` 後直接 `install`：symlink 會報 `STALE` 並被連結本身搬進 trash（指向的檔還在 clone）、舊 `~/.ai-global/manifest/` 自動收掉、`~/Developer/agent-governance` 不再使用（可自行搬進 `~/.ai-trash/`）。唯一手動步驟：舊的 `sync-check` skill 是在管理清單機制之前部署的，請 `mv ~/.claude/skills/sync-check ~/.ai-trash/`。

## 倉庫結構

```
claude/
  CLAUDE.md                  Claude Code router → ~/.claude/CLAUDE.md
  statusline.sh              狀態列：repo·worktree、分支、模型、context、5h/7d 額度、token
  hooks/                     cleanup-orphans.{sh,ps1}、stop-typecheck.sh → ~/.claude/hooks/（整目錄鏡像）
  skills/ai-global/          按需分派器 + commands/{check,sync,deploy,govcheck,capabilities,install,common}.md
  commands/ agents/          自製 slash command 與 agent（目前空；逐一部署）
codex/AGENTS.md              Codex router → ~/.codex/AGENTS.md
governance/                  憲法本體 → ~/.ai-global/governance/（整目錄鏡像；backups/ 不部署）
manifest/skills.json         第三方能力清單（名稱＋來源＋版本）
manifest/settings.json       settings 共用基準（Claude 四個區塊；Codex 只有 personality）
setup/install.sh|.ps1        部署與檢查，兩支語意完全相同
setup/check_governance.py    治理靜態檢查與本機對帳
setup/capabilities.py        能力來源、狀態清單及本機開關
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
| 測試 | `unittest`，隔離 fixture | 驗證治理、部署與能力開關行為 |
| skill | Claude Code skill，`$ARGUMENTS` 分派 | 按需載入命令，已有意圖不重問 |
| 記憶體回收 | macOS bash＋launchd；Windows PowerShell 手動 | 同語意同 log |
| 行尾 | `.gitattributes` 強制 LF | macOS 的 shebang 需要 |

## 給 AI agent 的指引

**Claude Code 已部署過的機器**：用 `/ai-global`。

**全新機器（skill 還不存在）或 Codex**：
1. 確認 OS 與 clone，先跑治理 checker 及 `setup/install.* check`；看清既有 router 差異。需要取代且既有授權未涵蓋時，告知影響與備份位置後取得同意。
2. 在授權內執行部署並 check 驗證；被取代內容保留至 `~/.ai-trash/`，不自動安裝第三方。
3. 跑 `python setup/capabilities.py list`，列專案預設與本機既有能力及啟用狀態。共用設定按需對帳，不自動覆寫本機選擇。
4. 回報變更、證據、限制與分支。第三方安裝、敏感設定或未涵蓋的衝突才另行彙整裁決。

### 互動式能力設定（TUI）

互動介面使用 [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html)，支援 Windows 與 macOS 終端。Python 3.11+；一般 list／enable／disable 不需要這個額外套件。

第一次在專案目錄準備環境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r setup/requirements-tui.txt
.\.venv\Scripts\python.exe setup/capabilities.py manage --demo
```

macOS 使用 `.venv/bin/python` 取代 `.\.venv\Scripts\python.exe`。`--demo` 使用示範資料，不讀寫本機能力設定；去掉 `--demo` 就是實際管理。已啟用此虛擬環境時，也可直接執行 `python setup/capabilities.py manage`。支援 `--tool codex`、`--kind plugin` 等既有篩選。

- ↑／↓ 選取，PageUp／PageDown 翻頁，空白鍵切換預定開關；再按一次空白鍵可還原。
- `[x]` 預定啟用、`[ ]` 預定停用、`[-]` 無法切換、`*` 有待套用變更；未安裝或開關未知的項目會說明原因。
- Enter 套用並離開；Esc／Ctrl+C 放棄全部預選且不寫入。表格欄位對齊，窄終端省略長 ID，選取項目的 ID 在下方獨立顯示，←／→ 可橫向捲動查看完整內容，不擠掉狀態與提示。
- 套用前檢查能力狀態是否被其他工作階段改變；逐項套用並回報結果，發生失敗即停止，不把已完成部分當作全部成功，也不自動回復其他人的變更。
- 不支援輸入／輸出重新導向；請在真正的互動 Terminal 執行。切換後需重新載入或重啟工具確認當次效果。

驗證方式：先開 demo，選第二項、按空白鍵確認出現 `*` 與預定「開」；按 Esc 應顯示未寫入。再開 demo 重做並按 Enter，應回報示範預選數。實際模式可預選後按 Esc，接著用 list 確認原狀態未改。

### 能力選項

清單涵蓋使用者全域層，不含專案或系統層。`manifest/skills.json` 以 `tool`、`id`、`default_enabled` 描述專案建議；預設值不強制覆寫本機。插件附帶的 skills 由所屬插件開關。Codex 插件目前只能確認本機開關設定，沒有可靠安裝登錄時安裝狀態顯示未知。

```bash
python setup/capabilities.py list
python setup/capabilities.py disable --tool codex --kind plugin --id <ID>
python setup/capabilities.py enable --tool claude --kind skill --id <ID>
```

使用 list 提供的工具、種類與精確 ID。清單區分專案預設與本機既有，並列出安裝及啟用狀態；未列管項目保留，不代表需要刪除或納管。明確要求某項開關即可執行，不再次確認。切換使用原生設定或可逆停用方式，保留其他設定與本機偏好，sync 不重設它們。list 唯讀；開關不下載、不卸載、不變更 manifest。未支援或無法判斷的狀態明示限制，設定驗證不代表現有工作階段已重新載入。

**紅線（對 agent 強制）**：不直接編輯部署端（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/**`）；禁止 `rm`／程式化刪除，一律 `mv` 進 `~/.ai-trash/`；push 須使用者對具體遠端／分支明確授權；任何真實憑證不進 repo；改 `governance/` 先讀 `governance/40-maintenance.md`。

開關的保存位置：Claude 插件使用 `settings.json` 的 `enabledPlugins`；Codex 使用 `config.toml` 的插件設定與 `skills.config`（需 Python 3.11+）。Claude 獨立 skill／command 停用時移入 `~/.claude/ai-global-disabled/{skills,commands}/<name>`，部署會保留停用狀態。設定修改前備份到 `~/.ai-trash/ai-global-settings-<唯一值>/`，不輸出秘密。

## hooks 與記憶體回收（機器本地、手動接）

`claude/hooks/` 會部署到 `~/.claude/hooks/`，但**要不要啟用由各機器的 `~/.claude/settings.json` 決定**，manifest 不管 hooks。

| 腳本 | 接法 |
|---|---|
| `stop-typecheck.sh` | 舊入口已退役為不執行檢查；必要 typecheck 由任務驗收依專案套件管理器執行，避免其他 session 的髒檔觸發重跑 |
| `cleanup-orphans.sh`（macOS） | `SessionEnd`：`bash ~/.claude/hooks/cleanup-orphans.sh --scope session`；排程：`bash setup/install-cleanup-agent.sh`（launchd，每 2h；`--interval-hours N`、`--uninstall`） |
| `cleanup-orphans.ps1`（Windows） | 自 2026-09-08 改為手動：桌面「Claude 清理背景程序.cmd」或 `~/.claude/hooks/cleanup-orphans.ps1 -Scope global`；既有排程工作 `ClaudeCodeOrphanCleanup` 與失效的 SessionEnd hook 已移除，不因部署重新掛載 |

清理腳本的 global 模式只回報候選程序與 VM，不因名稱相似或父程序消失就終止程序。session 模式只處理可證明屬於該 session 的後代輔助程序，逐候選排除 `remote-control`；主程序不清理。查詢失敗時保留現況，不能當成「沒有工作」。支援 `--dry-run`／`-DryRun`，log 在 `~/.claude/logs/cleanup.log`。Windows 採手動是因先前 hook 的 `%USERPROFILE%` 未展開、長期沒有有效執行紀錄；排程安裝器保留為手動工具，部署不啟用它。實際掛載仍屬各機器設定。

## 治理檢查

```bash
python setup/check_governance.py --local    # 已包含離線檢查；只驗 repo 時省略 --local
python -m unittest discover -s setup -p 'test_*.py'
```

離線 checker 需 Python 3.9+；能力 CLI、完整測試套件及 `--local` 的 Codex TOML 對帳需 Python 3.11+。CI（`.github/workflows/governance.yml`）在 push／PR 於三個 OS 跑離線 checker 與測試——工作流程存在不等於分支保護已設。這些檢查驗結構與連結，**不證明模型遵循**；真正的強制在 sandbox／permissions／hooks／CI。完整部署對帳仍以 `setup/install.* check` 與 `/ai-global` 為準。[驗收情境](docs/reference/governance-evaluation.md)、[執行環境參考](docs/reference/agent-runtime.md)。

## 已知邊界

- Markdown 是行為約定，不是隔離：checker 與 `--local` 只驗「檔在、內容對」，不驗「當次 session 真的載入或遵循」。
- 工具產生的能力清單只涵蓋可辨識的本機來源與設定；未知狀態不能當成已啟用或停用。
- manifest 的 `codex_config` 只共用 `personality`；`model`／`model_reasoning_effort` 是各機器本機獨有（使用者裁決）。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、真實 `.env`、API key）**永不進本倉庫**；無秘密的 `.env.example` 依 `governance/50-safety.md` 檢查後可追蹤。
- 本倉庫必須保持 **private**。
