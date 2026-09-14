# ai-global

把兩台機器（macOS 主力、Windows 副機）上給 AI 工具的**使用者全域層**集中在一個 private repo：router、憲法、自製能力、第三方清單、部署工具。

| 層 | 內容 | 給誰讀 |
|---|---|---|
| **Router**（入口） | `claude/CLAUDE.md`、`codex/AGENTS.md` | Claude Code／Cowork、Codex 每個 session 自動載入 |
| **憲法**（governance） | 10 委派、20 判斷、30 模板、40 維護、50 安全、60 起手式、70 行為契約、80 工程 | 模型按 router 的路由按需讀 |
| **能力** | skill `ai-global`、3 支 hooks、statusline | Claude Code |
| **清單**（manifest） | 第三方 skills／plugins／commands 名單、settings 共用基準 | 對帳用，不部署 |
| **工具**（setup） | 部署、對齊、能力、安裝、治理 checker（全部 Python）＋測試、記憶體回收排程安裝器 ×2 | 人與 agent |
| **參考**（docs/reference） | 各工具官方載入／權限機制、治理驗收情境 | 人與 agent |

## 核心設計：三個決策

**1. 部署是複製，不是連結。**
`setup/deploy.py` 把 repo 內容**複製**到工具讀的固定位置。clone 在哪都行、可以搬、甚至刪掉，機器上的全域設定不受影響。（舊的 symlink 模型在 Windows 上因為 clone 換槽整條斷過好幾週，而 Claude／Codex 沒有任何錯誤訊息。）

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
| 新機器／重裝 | `/ai-global align`（pull＋部署＋補裝＋衝突選單）；沒 Claude 時直接跑 `python setup/align.py` |
| 只重新部署 repo 自己的檔 | `/ai-global deploy` 或 `python setup/deploy.py` |
| 改完 router／制度檔 | `/ai-global govcheck` 或 `python setup/check_governance.py` |
| 查看專案預設／本機既有及開關 | `/ai-global capabilities` 或 `python setup/capabilities.py list` |
| 模型／工具改版後看 harness 哪裡過時 | `/ai-global evolve`：核對 `manifest/sources.json` 列的官方文件與 marketplace，寫 `docs/reports/harness-review-<日期>.md`；只產報告，不自動改 |
| 補一個第三方能力 | `/ai-global install <name>` |
| 手動（任一 OS） | `python setup/deploy.py [install|check]`、`python setup/align.py [--plan|--yes]`、`python setup/capabilities.py list` |

`/ai-global` 可依明確自然語言分派；沒有參數或可判斷意圖才列選單。`check` 唯讀；install 輸出的 `WARN`／`DROP`／`NOTE` 是「哪些東西被換掉、放在哪」的唯一紀錄。

改東西的節奏：**改 clone → install → 驗證 → commit；push 依授權**（憲法 40）。

## 指令與腳本總表

### `/ai-global` 的 8 個指令（`claude/skills/ai-global/commands/`）

| 指令 | 用途 | 動檔案？ |
|---|---|---|
| `check` | 唯讀對帳：部署漂移、治理、能力、settings 共用項 | 否 |
| `sync` | pull → check → 必要裁決 → 部署 → 對帳 | 是 |
| `deploy` | 只重新部署 repo 自己的檔（governance、router、hooks、ai-global skill），不 pull | 是 |
| `govcheck` | 治理結構檢查：router 節次、路由、連結、manifest、sources 過期 | 否 |
| `capabilities` | 列專案預設／本機既有能力與開關；可指定開關或開互動選單 | 只改指定項 |
| `install <name>` | 補裝 manifest 中指定的一項（＝`align.py --only`） | 只該項 |
| `align` | 一鍵對齊：pull → 部署 → 補裝缺項 → 衝突裁決（終端 TUI／Claude Code 對話）→ 對帳 | 自動項直接做；衝突只依使用者選擇 |
| `evolve [source-id]` | 核對官方文件／changelog／marketplace 是否有變，寫 `docs/reports/harness-review-<日期>.md` | 只寫報告與核對日期 |

`common.md` 是各指令共用的背景，不是指令。slash command 屬 Claude Code；Codex 直接跑下表同一套腳本。

### `setup/` 腳本（Python 3.11+，任一 OS 同一指令）

| 腳本 | 用途 |
|---|---|
| `deploy.py` | 部署／檢查（`install`｜`check`）：把 repo 檔複製到 `~/.ai-global`、`~/.claude`、`~/.codex`，記 state，舊檔進 trash |
| `align.py` | 一鍵對齊主流程；`--plan` 唯讀、`--yes` 只套自動項、`--resolve KEY=ACTION`、`--only ID`、`--no-pull`、`--no-venv`；Python 太舊會明講，缺 prompt_toolkit 會問要不要建 `.venv` 再自動重跑 |
| `installers.py` | 依 manifest `source` 安裝單項：plugin 走 `claude`／`codex` CLI，`github:` 淺 clone 複製並寫 `.ai-global.json` |
| `capabilities.py` | 能力清單（manifest vs 本機、兩個工具）與 `enable`／`disable`；Claude plugin 以 CLI 交叉驗證 |
| `capabilities_tui.py` | prompt_toolkit 互動介面：能力開關選單、align 衝突選單（`requirements-tui.txt`；align 會自動建 `.venv` 裝好） |
| `check_governance.py` | 治理靜態檢查＋`--local` 本機對帳；含 `manifest/sources.json` 過期提醒 |
| `install-cleanup-agent.sh`／`install-cleanup-task.ps1` | 記憶體回收排程安裝器（launchd／schtasks，平台專屬故維持 sh/ps1） |
| `test_*.py` | 測試：align、installers、deploy_controls、capabilities、capabilities_tui、check_governance、hooks |

### align 的衝突類型與預設

| 類型 | 意思 | 可選處置 | 預設 |
|---|---|---|---|
| `edited` | 部署檔在 repo 外被改過 | 以 repo 覆蓋／回寫 repo／保留 | 覆蓋（先於部署決定，「保留」不會被蓋） |
| `extra` | 本機有、manifest 沒有 | 保留／停用／trash | 保留 |
| `duplicate` | 獨立 skill 與 plugin 內同名 | trash／停用／保留 | trash |
| `switch` | 本機開關與 manifest 建議相反 | 開／關／維持 | 維持本機選擇 |
| `version` | 安裝版本與 manifest 不同 | 更新／維持 | 更新 |
| `hook` | settings.json 指向不存在的 hook 腳本 | 保留／移除 | 保留 |

### manifest 納管的第三方能力（不在 repo 內；`align` 補裝）

| 工具 | 能力 |
|---|---|
| Claude | `kb-retriever`、`web-design-guidelines`、`frontend-design`、`ui-ux-pro-max`、`gsap-skills`、`typescript-lsp`、`context7`、`hookify`、`claude-md-management` |
| Codex | `kb-retriever`、`web-design-guidelines`、`frontend-design`、`ui-ux-pro-max`、`gsap-skills`、`context7` |

Claude 獨有的三個（`typescript-lsp`、`hookify`、`claude-md-management`）分別因 Codex 無 LSP plugin、hook schema 不同、目標檔是 CLAUDE.md 而不設 Codex 條目。正本以 `manifest/skills.json` 為準。

## 新機器上手

只需要兩樣東西：**git** 和 **Python 3.11 以上**。clone 位置隨你，腳本會自己算出來並記進 state。

```bash
# macOS：先確認版本；系統內建的 /usr/bin/python3 是 3.9，太舊
python3 --version || true
brew install python@3.12          # 沒有 3.11+ 才需要；之後用 python3.12 這個指令

git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
python3.12 ~/Developer/GitHub/ai-global/setup/align.py      # pull → 部署 → 補裝 manifest 缺項 → 衝突選單
```

```powershell
# Windows（不需要開發人員模式或系統管理員）；python 指 3.11+，沒有就先從 python.org 裝
git clone git@github.com:Hereisaa/ai-global.git D:\GitHub\ai-global
python D:\GitHub\ai-global\setup\align.py
```

第一次跑 `align` 會發生的事，都不用你先準備：

1. Python 太舊 → 直接停下並告訴你版本與怎麼裝，不會噴一串 `ModuleNotFoundError`。
2. 缺互動選單套件（prompt_toolkit）→ 問一句「建立 .venv 並安裝？[Y/n]」；按 Enter 就在專案底下建 `.venv`、裝好、用它重新執行自己。`.venv` 只影響這個資料夾、已在 `.gitignore`，刪掉就還原。之後不管你用 `python3.12 setup/align.py` 還是 `.venv/bin/python setup/align.py`，都會自動走 `.venv` 開選單。
3. 有衝突 → 互動選單逐項選 keep／disable／trash；沒有衝突就直接結束。

答 `n`（或加 `--no-venv`）就維持文字模式：衝突以 `KEY=ACTION` 列出，用 `--resolve` 指定。`--plan`／`--yes` 與非 TTY（Claude Code、CI）從不觸發這個提問。裝完跑 `python setup/deploy.py check` 應全部 OK；只想部署 repo 自己的檔、不碰第三方用 `python setup/deploy.py`。

目標位置若已有你自己的 `CLAUDE.md`／`AGENTS.md`：先跑 `check` 會報 `EDITED`；install 會取代它並把原檔放進 `~/.ai-trash/`。

裝完跑 `/ai-global check` 或 `python setup/capabilities.py list`，查看專案預設與本機既有能力。缺項只回報，由使用者決定是否安裝；既有開關不因部署或 sync 重設。

### 從 symlink 時代升級（2026-09-07 前裝的機器，一次性）

`git pull` 後直接 `install`：symlink 會報 `STALE` 並被連結本身搬進 trash（指向的檔還在 clone）、舊 `~/.ai-global/manifest/` 自動收掉、`~/Developer/agent-governance` 不再使用（可自行搬進 `~/.ai-trash/`）。唯一手動步驟：舊的 `sync-check` skill 是在管理清單機制之前部署的，請 `mv ~/.claude/skills/sync-check ~/.ai-trash/`。

## 倉庫結構

```
claude/
  CLAUDE.md                  Claude Code router → ~/.claude/CLAUDE.md
  statusline.sh              狀態列：repo·worktree、分支、模型、context、5h/7d 額度、token
  hooks/                     cleanup-orphans.{sh,ps1} → ~/.claude/hooks/（整目錄鏡像）
  skills/ai-global/          按需分派器 + commands/{check,sync,deploy,govcheck,capabilities,install,align,evolve,common}.md
  commands/ agents/          自製 slash command 與 agent（需要時再建目錄；逐一部署）
codex/AGENTS.md              Codex router → ~/.codex/AGENTS.md
governance/                  憲法本體 → ~/.ai-global/governance/（整目錄鏡像）
manifest/skills.json         第三方能力清單（名稱＋來源＋版本）
manifest/settings.json       settings 共用基準（Claude 四個區塊；Codex 只有 personality）
manifest/sources.json        evolve 的核對來源（官方文件、changelog、marketplace；記上次核對日期）
docs/reports/                evolve 產出的 harness 審查報告（依日期）
setup/deploy.py              部署與檢查（install|check），跨平台單一實作
setup/align.py               一鍵對齊：pull → deploy → 補裝缺項 → 衝突（TUI 或 --resolve）
setup/installers.py          依 manifest 來源型別安裝單項（tool CLI 或 git checkout）
setup/check_governance.py    治理靜態檢查與本機對帳
setup/capabilities.py        能力來源、狀態清單及本機開關（capabilities_tui.py 為互動介面）
setup/install-cleanup-*.{sh,ps1}  記憶體回收排程安裝器
docs/reference/              agent-runtime.md（工具機制）、governance-evaluation.md（驗收情境）
.github/workflows/governance.yml  三 OS 跑 checker 與測試
```

`~/.ai-global/` 頂層只允許 `governance/` 與 `.deploy-state.json`，其他一律視為舊版殘留收進 trash。`~/.claude/skills|commands|agents` 底下只動 repo 自己的項目，第三方的原地不碰。

## 技術棧

| 元件 | 技術 | 為何 |
|---|---|---|
| `deploy.py`／`align.py`／`installers.py` | Python 3.11+ 標準庫 | 一份實作三 OS 通用；可被彼此 import，不靠解析 stdout |
| 比對 | 位元組比對；hash 自算 git blob sha1 | 和 git blob 對得上，不依賴 git 執行檔 |
| 互動選單 | prompt_toolkit（專案 `.venv`） | 能力開關與對齊衝突共用；align 在終端缺它時問一句就自動建 `.venv`，拒絕或非 TTY 退回 `--resolve` |
| checker | Python 3.9+ 標準庫；`tomllib`（3.11+）讀 Codex config | 三 OS CI 零依賴 |
| 測試 | `unittest`，隔離 fixture | 驗證治理、部署與能力開關行為 |
| skill | Claude Code skill，`$ARGUMENTS` 分派 | 按需載入命令，已有意圖不重問 |
| 記憶體回收 | macOS bash＋launchd；Windows PowerShell 手動 | 同語意同 log |
| 行尾 | `.gitattributes` 強制 LF | macOS 的 shebang 需要 |

## 給 AI agent 的指引

**Claude Code 已部署過的機器**：用 `/ai-global`。

**全新機器（skill 還不存在）或 Codex**：
1. 確認 OS 與 clone，先跑治理 checker 及 `python setup/deploy.py check`（或 `python setup/align.py --plan`）；看清既有 router 差異。需要取代且既有授權未涵蓋時，告知影響與備份位置後取得同意。
2. 在授權內執行部署並 check 驗證；被取代內容保留至 `~/.ai-trash/`，不自動安裝第三方。
3. 跑 `python setup/capabilities.py list`，列專案預設與本機既有能力及啟用狀態。共用設定按需對帳，不自動覆寫本機選擇。
4. 回報變更、證據、限制與分支。第三方安裝、敏感設定或未涵蓋的衝突才另行彙整裁決。

### 互動式能力設定（TUI）

互動介面使用 [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html)，支援 Windows 與 macOS 終端。Python 3.11+；一般 list／enable／disable 不需要這個額外套件。

`.venv` 通常已由第一次 `align` 建好（見「新機器上手」）。還沒有的話手動建一次：

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

清單涵蓋使用者全域層，不含專案或系統層。`manifest/skills.json` 以 `tool`、`id`、`default_enabled` 描述專案建議；預設值不強制覆寫本機。插件附帶的 skills 由所屬插件開關。Claude 插件的安裝狀態以 `claude plugin list` 交叉驗證登錄檔；Codex 插件目前只能確認本機開關設定，沒有可靠安裝登錄時安裝狀態顯示未知。

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
| `cleanup-orphans.sh`（macOS） | `SessionEnd`：`bash ~/.claude/hooks/cleanup-orphans.sh --scope session`；排程：`bash setup/install-cleanup-agent.sh`（launchd，每 2h；`--interval-hours N`、`--uninstall`） |
| `cleanup-orphans.ps1`（Windows） | 自 2026-09-08 改為手動：桌面「Claude 清理背景程序.cmd」或 `~/.claude/hooks/cleanup-orphans.ps1 -Scope global`；既有排程工作 `ClaudeCodeOrphanCleanup` 與失效的 SessionEnd hook 已移除，不因部署重新掛載 |

清理腳本的 global 模式只回報候選程序與 VM，不因名稱相似或父程序消失就終止程序。session 模式只處理可證明屬於該 session 的後代輔助程序，逐候選排除 `remote-control`；主程序不清理。查詢失敗時保留現況，不能當成「沒有工作」。支援 `--dry-run`／`-DryRun`，log 在 `~/.claude/logs/cleanup.log`。Windows 採手動是因先前 hook 的 `%USERPROFILE%` 未展開、長期沒有有效執行紀錄；排程安裝器保留為手動工具，部署不啟用它。實際掛載仍屬各機器設定。

## 治理檢查

```bash
python setup/check_governance.py --local    # 已包含離線檢查；只驗 repo 時省略 --local
python -m unittest discover -s setup -p 'test_*.py'
```

離線 checker 需 Python 3.9+；能力 CLI、完整測試套件及 `--local` 的 Codex TOML 對帳需 Python 3.11+。CI（`.github/workflows/governance.yml`）在 push／PR 於三個 OS 跑離線 checker 與測試——工作流程存在不等於分支保護已設。這些檢查驗結構與連結，**不證明模型遵循**；真正的強制在 sandbox／permissions／hooks／CI。完整部署對帳仍以 `python setup/deploy.py check` 與 `/ai-global` 為準。[驗收情境](docs/reference/governance-evaluation.md)、[執行環境參考](docs/reference/agent-runtime.md)。

## 已知邊界

- Markdown 是行為約定，不是隔離：checker 與 `--local` 只驗「檔在、內容對」，不驗「當次 session 真的載入或遵循」。
- 工具產生的能力清單只涵蓋可辨識的本機來源與設定；未知狀態不能當成已啟用或停用。
- manifest 的 `codex_config` 只共用 `personality`；`model`／`model_reasoning_effort` 是各機器本機獨有（使用者裁決）。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、真實 `.env`、API key）**永不進本倉庫**；無秘密的 `.env.example` 依 `governance/50-safety.md` 檢查後可追蹤。
- 本倉庫必須保持 **private**。
