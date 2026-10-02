# ai-global

## 專案目的

ai-global 是我個人使用 **Claude Code 與 Codex 程式 Agent 的共用設定倉庫**。把工作規則、工具設定與選配能力放在同一份 Git 正本中，讓不同工具與電腦有一致的工作方式，也能追蹤修改和回復版本。

目前用途是我與 Agent 一起寫程式、修問題、看程式碼及維護專案。專案重點是讓這個日常環境容易管理；各應用專案自己的建置、測試與發布流程仍由該專案設定。

## 能做什麼、幫助什麼

| 能力 | 對日常開發的幫助 |
|---|---|
| 共用工作規則 | Agent 使用繁體中文、保留既有修改、在授權範圍內持續完成工作，交付時說清楚驗證與限制 |
| 操作安全原則 | 工作檔案採可回復處理、秘密不輸出；push、發布等對外操作依明確授權執行 |
| 設定部署與漂移檢查 | 不必逐台手動複製入口文件；能分辨未部署、正本更新與部署端被另外改過 |
| 基本與選配能力管理 | 查看 skills／plugins 是否已裝、是否啟用；同步保留本機選擇，常用能力可持續開啟 |
| Claude 輔助工具 | 提供狀態列、啟動時部署檢查及刪除指令攔截 hook；是否掛載由本機設定決定 |
| 維護檢查與紀錄 | 檢查規則連結及腳本行為，保留修改歷史；工具升級或出現問題時再核對受影響來源 |

基本預設包含 ai-global 維護入口（Claude）及 context7 文件查詢；前端設計、動畫、知識庫與額外維護能力屬選配。需要時可請 Agent 開啟指定能力，或使用 `capabilities.py`；停用後仍保留安裝內容，通常需新對話確認載入。詳見[能力選配指南](docs/reference/capability-guide.md)。

文字規則提供工作約定，真正的執行限制取決於工具權限、sandbox 與已生效的 hooks。檔案比對通過只代表部署內容一致，不代表當次對話已載入或所有操作都受保護。

## 怎麼辦到的

共用設定分成四層：

| 層次 | 是什麼 | 放在哪裡 |
|---|---|---|
| 入口（router） | Claude 的 `CLAUDE.md`、Codex 的 `AGENTS.md`，摘要基本規則並依任務指向相關文件 | 部署到 `~/.claude/`、`~/.codex/` |
| 工作規則（governance） | 授權、安全、工程及維護規則，需要時才讀；[索引](governance/README.md)與[使用者手冊](governance/USER-GUIDE.md)提供導航 | 部署到 `~/.ai-global/governance/` |
| 輔助工具 | `/ai-global` skill、hooks 與 statusline；Python 腳本負責部署、對帳、安裝及明確開關 | Claude 檔案部署到 `~/.claude/`；Python 腳本留在正本 |
| 清單（manifest） | 基本／選配能力、共用設定參考及外部核對來源 | 留在正本，供腳本與維護流程讀取 |

```text
Git 正本：入口、規則、輔助工具與清單
    │
    ├─ deploy：複製 repo 管理的檔案，保留被取代內容
    │      ├─ ~/.codex/AGENTS.md
    │      ├─ ~/.claude/CLAUDE.md、skills、hooks、statusline
    │      └─ ~/.ai-global/governance/ 與部署狀態
    │
    ├─ check：比對目前內容與上次部署紀錄，回報漂移
    └─ align：同步正本、部署、補裝基本缺項，明確處理衝突
```

另一台電腦取得已發布的 Git 版本後再執行 align，才會更新那台的部署。能力開關保留在各機器，align 不重設；部署與設定修改的備份放在 `~/.ai-trash/`。

本倉庫已有 [GitHub Actions workflow](.github/workflows/governance.yml)，在 push／PR 時於 Linux、macOS、Windows 跑治理檢查與腳本測試。PR review bot 可另外在 GitHub 設定；ai-global 本身不提供 review bot。其他應用專案的 CI/CD 放在各自倉庫。

## 專案樹狀結構

下圖列主要檔案；commands、測試與報告以用途合併顯示，完整檔案可直接查看對應目錄。

```text
ai-global/
├── README.md                         專案介紹與操作方式
├── .github/
│   └── workflows/
│       └── governance.yml            GitHub Actions 跨平台檢查
├── codex/
│   └── AGENTS.md                     Codex 全域入口
├── claude/
│   ├── CLAUDE.md                     Claude 全域入口
│   ├── statusline.sh                 Claude 狀態列
│   ├── hooks/
│   │   ├── guard-delete.sh           刪除指令攔截
│   │   ├── ai-global-check.sh        啟動時檢查部署漂移
│   │   ├── cleanup-orphans.sh        macOS 背景程序清理
│   │   └── cleanup-orphans.ps1       Windows 清理工具
│   └── skills/ai-global/
│       ├── SKILL.md                  /ai-global 維護入口
│       └── commands/                check、align、deploy、能力管理等流程
├── governance/
│   ├── README.md                     工作規則索引
│   ├── USER-GUIDE.md                 給使用者的說明
│   ├── 10-dispatch.md                委派與獨立審查
│   ├── 20-judgment.md                授權、風險與完成判斷
│   ├── 30-templates.md               派工與審查模板
│   ├── 40-maintenance.md             設定與規則維護
│   ├── 50-safety.md                  工作檔案、秘密與對外操作
│   ├── 60-project-bootstrap.md       新專案與文件慣例
│   ├── 70-behavior-contract.md       工作與溝通方式
│   └── 80-engineering.md             工程原則與交付
├── manifest/
│   ├── skills.json                   基本／選配能力清單
│   ├── settings.json                 共用設定與 hook 掛載參考
│   └── sources.json                  工具改版時的核對來源
├── setup/
│   ├── align.py                      同步、部署、補裝與衝突處理
│   ├── deploy.py                     部署檔案與內容比對
│   ├── capabilities.py               能力清單、分組與開關
│   ├── capabilities_tui.py           終端互動選單
│   ├── installers.py                 指定能力的安裝處理
│   ├── govcheck.py                   規則、路由與連結檢查
│   ├── requirements-tui.txt          互動選單依賴
│   └── test_*.py                     腳本與 hook 測試
└── docs/
    ├── CHANGELOG.md                  兩工具入口變更紀錄
    ├── reference/
    │   ├── capability-guide.md       能力選配指南
    │   ├── agent-runtime.md          工具載入與權限機制
    │   ├── environment-maintenance.md 機器維護備忘
    │   ├── governance-evaluation.md  規則驗收情境
    │   └── harness-eval-method.md    模型行為評估設計
    └── reports/                      歷次核對、審查與優化紀錄
```

---

## 環境需求

| 需要 | 說明 |
|---|---|
| git | clone、同步 |
| **Python 3.11 以上** | 先確認 Python 版本達 3.11；macOS 可用 `brew install python@3.12`，之後用 `python3.12`。Windows 可從 python.org 安裝 |
| `claude`／`codex` CLI | 只在補裝第三方 plugin 時用到；沒裝的話那幾項會標 FAIL，其他照常 |

互動選單用的套件（prompt_toolkit）**不用自己裝**，第一次 `align` 會問你要不要建 `.venv`，按 Enter 就好。

---

## 新電腦：三步

```bash
# macOS / Linux
git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
cd ~/Developer/GitHub/ai-global
python3.12 setup/align.py
```

```powershell
# Windows
git clone git@github.com:Hereisaa/ai-global.git D:\GitHub\ai-global
cd D:\GitHub\ai-global
python setup\align.py
```

第一次 `align` 會自己做這些，不用先準備：

1. Python 太舊 → 停下來告訴你版本和怎麼裝。
2. 缺選單套件 → 問「建立 .venv 並安裝？[Y/n]」，Enter 就建好、裝好、重新執行自己。`.venv` 只在這個資料夾，不用時依安全流程移到 trash。
3. 部署 router、憲法、hooks、skill 到上表的位置。
4. 只補裝基本能力；frontend、research、maintenance 等選配列出供按需安裝。
5. 有衝突（本機多出來的、版本不同的、重複的）就開選單讓你逐項選；沒有就結束。

> 電腦上本來就有自己的 `CLAUDE.md`／`AGENTS.md`？它會列成 `edited` 衝突讓你選「用 repo 的／把我的寫回 repo／先保留」，原檔一定先進 `~/.ai-trash/`。

---

## 平常怎麼用

常用動作，**在 Claude Code 裡說 `/ai-global <動作>`，或自己在終端跑同名腳本**，名字一樣、做的事一樣：

| 動作 | 做什麼 | Claude Code | 終端 |
|---|---|---|---|
| `check` | 看看有沒有漂移，不動檔 | `/ai-global check` | `python setup/align.py --plan` |
| `align` | 同步：pull → 部署 → 補裝 → 衝突裁決 | `/ai-global align` | `python setup/align.py` |
| `align --only <id>` | 只補裝一項 | `/ai-global align --only context7@claude-plugins-official` | `python setup/align.py --only context7@claude-plugins-official` |
| `deploy` | 只重新部署 repo 自己的檔，不碰第三方 | `/ai-global deploy` | `python setup/deploy.py` |
| `govcheck` | 改了 router／憲法後檢查格式與連結 | `/ai-global govcheck` | `python setup/govcheck.py` |
| `capabilities` | 看有哪些能力、開了沒；開關某一項 | `/ai-global capabilities` | `python setup/capabilities.py list` |
| `evolve` | 工具改版後，看 harness 哪裡過時（只產報告） | `/ai-global evolve` | —（只有 skill 版） |

差別只有一個：終端會開互動選單讓你選；Claude Code 沒有 TTY，改在對話裡問你。`/ai-global` 後面講白話也行（「幫我同步」「列一下能力」）。Codex 沒有這個 skill，直接跑腳本。

### 改設定的節奏

```
改 clone 裡的檔 → python setup/deploy.py → git commit → git push（另一台才拿得到）→ 另一台 align
```

三條不要踩：

- **不要直接改** `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/` 底下的檔。下次 check 會標 `EDITED`，再下次部署會被蓋掉（原檔進 trash）。
- 改 `governance/` 或 router 前先讀 `governance/40-maintenance.md`，改完跑 `govcheck`。
- `git pull` **不會**自動更新全域，pull 完要跑 `align`（或至少 `check`）。

---

## 腳本參數

在 clone 根目錄跑；`python` 指 3.11+（macOS 用 `python3.12`）。每支都有 `--help`。

### `align.py`

```
python setup/align.py [--plan | --yes] [--no-pull] [--only ID ...] [--resolve KEY=ACTION ...] [--no-venv] [--json]
```

| 參數 | 做什麼 |
|---|---|
| （無） | 全部做，衝突開選單 |
| `--plan` | 唯讀，只列會發生什麼（＝ check） |
| `--yes` | 做自動項，衝突只列不問（給 Claude Code／CI） |
| `--no-pull` | 不 `git pull`（離線或有未提交變更時） |
| `--only ID` | 明確補裝這一項（包含選配），ID 用 manifest 的 `id`；可重複 |
| `--resolve KEY=ACTION` | 指定某個衝突怎麼處理，KEY 和可用 ACTION 都印在 CONFLICT 表；可重複 |
| `--no-venv` | 缺選單套件時不問、不建 `.venv`，直接文字模式 |
| `--json` | 最後多印 JSON 摘要 |

輸出包含選配清單：`OPTIONAL` 僅列未安裝的選配，不影響完成碼；其餘五張表：`ENV` hooks 執行環境（bash、能跑的 python 及版本，缺什麼印安裝指令）、`DRIFT` 漂移、`DEPLOY` 部署了什麼、`INSTALL` 補裝結果、`CONFLICT` 要你決定的。回傳碼 `0` 完成、`2` 還有衝突、`1` 有失敗。

衝突六種；選單預設值是建議，只有明確選擇才套用。`--yes` 保留未選擇的衝突，不默認覆蓋或移除。本機能力開關不同不算衝突：

| 類型 | 意思 | 可選 | 預設 |
|---|---|---|---|
| `edited` | 部署檔在 repo 外被改過 | overwrite 用 repo 的／writeback 寫回 repo／keep | overwrite |
| `extra` | 本機有、manifest 沒有 | keep／disable／trash | keep |
| `duplicate` | 獨立 skill 和 plugin 裡的同名 | trash／disable／keep | trash |
| `version` | 版本和 manifest 不同 | update／keep | update |
| `hook` | settings.json 指到不存在的 hook 腳本，或掛了只建議在別的平台掛的 hook | keep／unwire | keep |
| `hookmissing` | manifest 建議本平台掛的 hook，settings.json 沒掛 | keep／wire | keep |

### `deploy.py`

```
python setup/deploy.py [install | check]
```

`install`（預設）複製 router、憲法、hooks、statusline、skill 到位並記錄狀態；`check` 只報漂移。檢查分開列出 `CONTENT`（部署檔案內容）、`SOURCE`（記錄的部署分支與 commit）、`HOOKS`（此命令不檢查掛載）、`RUNTIME`（未驗證當次載入與防護）、`REMOTE`（此命令不比對遠端或另一台）。內容一致時即使來源 commit 不同仍可 exit 0；這個成功碼只表示部署檔案比對通過。若部署時有未提交變更，state 會記 `source_dirty`，commit 不能單獨代表其內容。

狀態：`OK`、`MISSING` 還沒部署、`BEHIND` repo 有新版、`EDITED` 部署端被改過、`EXTRA` repo 已移除但本機還在、`STALE` 舊版斷鏈。

### `capabilities.py`

```
python setup/capabilities.py list    [--tool claude|codex] [--kind skill|plugin|command] [--group core|frontend|typescript|research|maintenance|local] [--id ID] [--json]
python setup/capabilities.py manage  [--demo]
python setup/capabilities.py enable  --tool claude|codex --kind skill|plugin|command --id ID
python setup/capabilities.py disable --tool claude|codex --kind skill|plugin|command --id ID
```

**第一個字（動作）一定要給**：

- `list`：表格列出每項能力的工具、種類、ID、來源、有沒有裝、開了沒。後面的 `--tool`／`--kind`／`--group`／`--id` 是篩選，可不給。
- `manage`：方向鍵＋空白鍵勾選、Enter 套用、Esc 放棄的選單。要用 `.venv` 的 Python 跑：`.venv/bin/python setup/capabilities.py manage`（Windows `.venv\Scripts\python`）。`--demo` 用假資料練習。
- `enable`／`disable`：開或關一項，`--tool`、`--kind`、`--id` **三個都要給**，值照 `list` 印的抄。

```bash
python setup/capabilities.py list --tool codex
python setup/capabilities.py disable --tool claude --kind plugin --id ui-ux-pro-max@ui-ux-pro-max-skill
```

開關寫進工具自己的設定檔（Claude：`settings.json` 的 `enabledPlugins`；Codex：`config.toml`），改之前備份到 `~/.ai-trash/`。關掉不等於移除；工具要開新 session 才生效。

### `govcheck.py`

```
python setup/govcheck.py [--local]
```

檢查工具前綴、路由、連結與 manifest 格式。入口結構差異只提醒；來源超過 45 天未核對只提供資訊，工具升級或出現問題再按需 evolve。`--local` 多對帳本機部署副本。CI 在 push／PR 時於三個 OS 跑。

### 模型行為評測（eval）

規則是否讓AI更可靠、更少停頓，須用真實任務比較；腳本測試不代表模型通過。[方法與首輪規格](docs/reference/harness-eval-method.md) 包含八題、兩版本比較、分層評分與隔離要求；目前是方法設計，尚未啟動模型行為測試。

### 測試

```bash
python -m unittest discover -s setup -p 'test_*.py'
```

---

## 它怎麼運作

**部署是複製，不是連結。** clone 在哪都行、可以搬、可以刪，電腦上的設定不受影響。（以前用 symlink，Windows 上 clone 換槽整條斷了好幾週，工具一聲不吭。）

**用狀態檔抓漂移。** `~/.ai-global/.deploy-state.json` 記 clone 在哪、每個檔部署時的 hash、部署了哪些項目。`BEHIND`／`EDITED` 靠 hash 判斷，所以沒 commit 的改動也判得準。

**兩個 router 平行但不逐字相同。** 入口結構可依工具需要調整，例如分支前綴 `claude/` vs `codex/`、`/ai-global` 只有 Claude Code 能跑。`govcheck` 提醒結構差異；錯誤的工具前綴與失效路由仍判 FAIL。

```
你在 clone 改檔 ──deploy──▶ ~/.ai-global/governance/、~/.claude/…、~/.codex/AGENTS.md
               ──commit──▶ git ──push──▶ origin ──pull──▶ 另一台 clone ──align──▶ …
```

`~/.claude/settings.json`、`~/.codex/config.toml` 是工具自己寫的，不在這條線上；只用 `manifest/settings.json` 對帳共用項，能力開關由 `capabilities.py` 逐項改、其他設定不動。

### manifest 納管的第三方能力

| 工具 | 能力 |
|---|---|
| Claude | `kb-retriever`、`web-design-guidelines`、`frontend-design`、`ui-ux-pro-max`、`gsap-skills`、`typescript-lsp`、`context7`、`hookify`、`claude-md-management` |
| Codex | `kb-retriever`、`web-design-guidelines`、`frontend-design`、`ui-ux-pro-max`、`gsap-skills`、`context7` |

基本預設只有維護入口與 context7。其餘按 frontend、typescript、research、maintenance 分組選配；`default_enabled` 表示新環境是否自動補裝，不覆蓋已安裝能力的本機開關。一般 `align` 不裝選配，可用 `--only ID` 指定。詳見[能力選配與工作環境指南](docs/reference/capability-guide.md)。

正本是 `manifest/skills.json`。`typescript-lsp` 另需 `npm install -g typescript-language-server typescript`。

`~/.ai-global/` 頂層只會有 `governance/` 和 `.deploy-state.json`，其他一律當舊版殘留收進 trash。`~/.claude/skills|commands|agents` 只動 repo 自己的項目，第三方的不碰。

---

## hooks

`claude/hooks/` 底下的腳本都會部署到 `~/.claude/hooks/`，但**要不要啟用由各機器自己的 `settings.json` 決定**，部署不會幫你掛。`manifest/settings.json` 的 `hooks` 區塊是建議接法：`align` 發現建議的 hook 沒掛會列成 `hookmissing` 衝突，選 `wire` 才掛（新 session 生效）；指到不存在腳本的 hook 列成 `hook`，選 `unwire` 才移除。

| 腳本 | 事件 | 做什麼 |
|---|---|---|
| `guard-delete.sh` | `PreToolUse`（matcher `Bash`） | 整條指令裡出現 `rm`／`rmdir`／`unlink`／`shred`／`find -delete`／`Remove-Item`／`git clean -f`／`shutil.rmtree` 等就擋下（exit 2）並把 50-safety 的替代做法回給模型。permissions 的 deny 只比對指令開頭，`cd x && rm -rf y` 擋不到，這支補上。`npm rm`、`git rm`、`grep 'rm -rf'` 不擋。**純 bash＋grep＋sed，不需要 python**。 |
| `ai-global-check.sh` | `SessionStart` | 跑 `deploy.py check`，在 session 開頭印一行「同步／不同步（N 項）」；唯讀、永遠 exit 0。 |
| `cleanup-orphans.sh` | `SessionEnd`（manifest 標 `platforms: ["macOS"]`，Windows 不建議） | 回收該 session 留下的背景程序，見下節。 |

掛法（`~/.claude/settings.json`）：

```json
"hooks": {
  "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash ~/.claude/hooks/guard-delete.sh"}]}],
  "SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "bash ~/.claude/hooks/ai-global-check.sh", "timeout": 20}]}],
  "SessionEnd": [{"hooks": [{"type": "command", "command": "bash ~/.claude/hooks/cleanup-orphans.sh --scope session"}]}]
}
```

Windows 的 Claude Code 也是用 `bash`（Git Bash）跑這些 `.sh`。`ai-global-check.sh` 需要 bash 裡找得到能執行的 Python 3.11+；Windows 的 Store 別名 `python3` 只是空殼（exit 49、無輸出），hooks 會跳過它。`align` 開頭的 `ENV` 節會檢查 bash 與 python 並印安裝指令，這是新機器最先該看的一節。

### 記憶體回收

- macOS：`SessionEnd` hook 跑 `bash ~/.claude/hooks/cleanup-orphans.sh --scope session`；另有 launchd 每 2 小時跑 `--scope global`（已裝好的機器保留運作，排程安裝器已退役）。
- Windows：手動。桌面「Claude 清理背景程序.cmd」或 `~/.claude/hooks/cleanup-orphans.ps1 -Scope global`。

兩支都支援 `--dry-run`／`-DryRun`，只清可證明屬於該 session 的後代程序，主程序不動；log 在 `~/.claude/logs/cleanup.log`。

---

## 給 AI agent 的指引

**Claude Code 已部署過的機器**：用 `/ai-global`。

**全新機器（skill 還不存在）或 Codex**：
1. 確認 OS 與 clone，先跑 `python setup/govcheck.py` 與 `python setup/align.py --plan`，看清既有 router 差異。要取代且既有授權未涵蓋時，告知影響與備份位置後取得同意。
2. 在授權內跑 `python setup/align.py --yes`，以 `python setup/deploy.py check` 驗證；被取代內容在 `~/.ai-trash/`。
3. 衝突在對話中逐項請使用者決定，再以 `--resolve` 套用；不自動納管本機多出的能力。
4. 回報變更、證據、限制與分支。

**紅線**：不直接編輯部署端（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/**`）；禁止 `rm`／程式化刪除，一律 `mv` 進 `~/.ai-trash/`；push 須使用者對具體遠端／分支明確授權；真實憑證不進 repo；改 `governance/` 先讀 `governance/40-maintenance.md`。

---

## 已知邊界

- Markdown 是約定，不是隔離：`govcheck` 只驗「檔在、內容對」，不驗「這個 session 真的讀了、照做了」。真正的強制在 sandbox／permissions／hooks／CI；見 [驗收情境](docs/reference/governance-evaluation.md)、[執行環境參考](docs/reference/agent-runtime.md)。
- 能力清單只涵蓋認得出來的本機來源；安裝狀態靠 `claude plugin list`／`codex plugin list`，CLI 不在 PATH 上時顯示「未知」。
- manifest 的 Codex 設定只共用 `personality`；`model`／`model_reasoning_effort` 各機器自己決定。

## 紅線

- 憑證（`.credentials.json`、`auth.json`、真實 `.env`、API key）**永不進本倉庫**。
- 本倉庫必須保持 **private**。
