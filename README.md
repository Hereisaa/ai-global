# ai-global

給 AI 工具（Claude Code／Cowork、Codex）用的**使用者全域設定**，集中放在這個 private repo，兩台機器（macOS 主力、Windows 副機）共用同一份：

- **router**：`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`，每個 session 自動載入的入口。
- **憲法**（governance）：委派、判斷、安全、工程等規則，router 按情境路由過去讀。
- **自製能力**：`/ai-global` skill、hooks、statusline。
- **第三方清單**（manifest）：該裝哪些 skills／plugins、版本多少；只對帳，不部署。
- **工具**（setup）：一鍵對齊、部署、能力開關、治理檢查，全部 Python，三個 OS 同一指令。

你在 clone 裡改檔，跑一支腳本，它就**複製**到工具讀的位置；另一台 `git pull` 後再跑同一支腳本就同步了。所有被取代的檔都進 `~/.ai-trash/`，不刪東西。

---

## 環境需求

| 需要 | 說明 |
|---|---|
| git | clone 與同步 |
| **Python 3.11 以上** | 腳本只用標準庫；3.11 才有讀 Codex `config.toml` 的 `tomllib`。macOS 內建 `/usr/bin/python3` 是 3.9，太舊，要 `brew install python@3.12` 後用 `python3.12` 指令；Windows 從 python.org 裝 |
| `claude` CLI／`codex` CLI | 只有補裝第三方 plugin 時用到；沒裝的話該項報 FAIL，其他照常 |
| prompt_toolkit（互動選單） | **不用自己裝**：第一次 `align` 會問一句，同意就自動在專案底下建 `.venv` 裝好 |

支援 macOS（Apple Silicon）、Windows 11（PowerShell 或 Git Bash）、Linux。不需要系統管理員或開發人員模式。

---

## 新機器：三步

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

第一次跑 `align` 會自己做這些事，都不用先準備：

1. **Python 太舊** → 停下，印出目前版本與怎麼裝，不會噴一串 `ModuleNotFoundError`。
2. **缺互動選單套件** → 問「建立 .venv 並安裝 prompt_toolkit？[Y/n]」，按 Enter 就建好、裝好、用它重新執行自己。`.venv` 只影響這個資料夾、已在 `.gitignore`，刪掉就還原；之後不管用哪個 python 指令跑都會自動走 `.venv`。
3. **部署**：把 router、憲法、hooks、`/ai-global` skill 複製到 `~/.ai-global`、`~/.claude`、`~/.codex`。
4. **補裝第三方**：manifest 列的 plugins／skills 缺哪個裝哪個（需要的 marketplace 會先自動註冊）。
5. **衝突選單**：本機多出來的、版本不同的、重複的，逐項讓你選 keep／disable／trash；沒衝突就直接結束。

跑完看到每個階段的表格與 `NOTE 被取代的項目在 ~/.ai-trash/...` 就完成了。要確認：`python setup/deploy.py check` 應全部 OK。

> 目標位置若已經有你自己的 `CLAUDE.md`／`AGENTS.md`：`align` 會把它列成 `edited` 衝突讓你選「以 repo 覆蓋／回寫 repo／保留」；覆蓋前原檔會進 `~/.ai-trash/`。

---

## 已裝好的機器：日常怎麼用

兩種入口做同一件事，選順手的：**在 Claude Code 裡用 `/ai-global`**（它會讀 clone、跑腳本、在對話裡問你裁決），或**自己在終端跑腳本**（衝突用互動選單）。

| 情境 | Claude Code 裡 | 自己跑 |
|---|---|---|
| 看看有沒有漂移（不動檔案） | `/ai-global check` | `python setup/align.py --plan` |
| 另一台改了，同步過來 | `/ai-global sync` 或 `/ai-global align` | `python setup/align.py` |
| 只重新部署 repo 自己的檔，不碰第三方 | `/ai-global deploy` | `python setup/deploy.py` |
| 看本機有哪些能力、開了沒 | `/ai-global capabilities` | `python setup/capabilities.py list` |
| 開／關某個 skill 或 plugin | `/ai-global capabilities disable …` | `python setup/capabilities.py disable --tool … --kind … --id …` |
| 用方向鍵勾選開關 | — | `python setup/capabilities.py manage` |
| 補裝清單裡的一項 | `/ai-global install <name>` | `python setup/align.py --only <id>` |
| 改完 router／憲法要檢查 | `/ai-global govcheck` | `python setup/check_governance.py` |
| 模型或工具改版，看 harness 哪裡過時 | `/ai-global evolve` | （只有 skill 版） |

`/ai-global` 後面可以直接用自然語言（「幫我同步」「列一下能力」），它會分派；只有猜不到意圖才列選單。Codex 沒有這個 skill，請直接跑腳本。

### 改設定的節奏

```
改 clone 裡的檔 → python setup/deploy.py → python setup/deploy.py check → git commit → git push（另一台才拿得到）
```

- **不要直接改** `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/` 底下任何檔——下次 check 會標 `EDITED`，下次部署會被覆蓋（舊檔進 trash）。
- 改了 `governance/` 或兩個 router → 先讀 `governance/40-maintenance.md`，改完跑 `python setup/check_governance.py`。
- `git pull` **不會**自動更新全域；pull 完要跑一次 `deploy.py check` 或 `align.py`。

---

## 指令參考

所有腳本在 clone 根目錄執行；`python` 指 3.11+（macOS 用 `python3.12`，或 `.venv/bin/python`）。每支都有 `--help`。

### `setup/align.py`：一鍵對齊（最常用）

```
python setup/align.py [--plan | --yes] [--no-pull] [--only ID ...] [--resolve KEY=ACTION ...] [--no-venv] [--json]
```

流程：`git pull` → 部署 → 補裝 manifest 缺項 → 衝突裁決 → 對帳。輸出分四個表格：`DRIFT`（部署漂移）、`DEPLOY`（部署了什麼）、`INSTALL`（補裝結果）、`CONFLICT`（要你決定的）。

| 參數 | 做什麼 |
|---|---|
| （無） | 全部做；衝突開互動選單（真正的終端才會開） |
| `--plan` | 唯讀：只列會發生什麼，不動任何檔 |
| `--yes` | 做自動項；衝突只列出不問（給 Claude Code／CI 用） |
| `--no-pull` | 不 `git pull`（離線、或工作樹有未提交變更時） |
| `--only ID` | 只（重新）安裝這一項，ID 用 manifest 的 `id`，例如 `context7@claude-plugins-official`；可重複 |
| `--resolve KEY=ACTION` | 指定某個衝突的處置，KEY 與可用 ACTION 都印在 CONFLICT 表；可重複 |
| `--no-venv` | 缺 prompt_toolkit 時不問、不建 `.venv`，直接文字模式 |
| `--json` | 最後多印一段 JSON 摘要 |

回傳碼：`0` 全部完成；`2` 還有衝突沒決定；`1` 有失敗項。

衝突類型與預設處置：

| 類型 | 意思 | 可選 | 預設 |
|---|---|---|---|
| `edited` | 部署檔在 repo 外被改過 | overwrite 以 repo 覆蓋／writeback 回寫 repo／keep 保留 | overwrite |
| `extra` | 本機有、manifest 沒有 | keep／disable／trash | keep |
| `duplicate` | 獨立 skill 與 plugin 內同名 | trash／disable／keep | trash |
| `switch` | 本機開關與 manifest 建議相反 | enable／disable／keep | keep |
| `version` | 安裝版本與 manifest 不同 | update／keep | update |
| `hook` | settings.json 指向不存在的 hook 腳本 | keep／unwire | keep |

範例：

```bash
python setup/align.py --plan                                   # 先看
python setup/align.py --no-pull --only context7@claude-plugins-official
python setup/align.py --no-pull --resolve claude:skill:ui-styling=trash --resolve claude:plugin:x@m=update
```

### `setup/deploy.py`：只部署 repo 自己的檔

```
python setup/deploy.py [install | check]
```

- `install`（預設）：把 governance、router、hooks、statusline、`/ai-global` skill 複製到位，寫 `~/.ai-global/.deploy-state.json`，舊檔進 trash。
- `check`：只報漂移，不動檔。狀態：`OK`／`MISSING` 還沒部署／`BEHIND` repo 前進了／`EDITED` 部署端被改過（人裁決）／`EXTRA` repo 已移除但還在／`STALE` 舊版斷鏈。

### `setup/capabilities.py`：能力清單與開關

```
python setup/capabilities.py list   [--tool claude|codex] [--kind skill|plugin|command] [--id ID] [--json]
python setup/capabilities.py manage [--demo] [--tool …] [--kind …]
python setup/capabilities.py enable  --tool claude|codex --kind skill|plugin|command --id ID
python setup/capabilities.py disable --tool claude|codex --kind skill|plugin|command --id ID
```

**第一個參數（動作）一定要給**，四選一：

| 動作 | 做什麼 | 必填 |
|---|---|---|
| `list` | 表格列出專案預設與本機既有的每一項：工具、種類、ID、來源、安裝、開關 | 無；`--tool`／`--kind`／`--id` 是篩選 |
| `manage` | 方向鍵＋空白鍵勾選開關的互動選單，Enter 套用、Esc 放棄；`--demo` 用假資料練習 | 真正的終端，且要用 `.venv` 的 Python 跑：`.venv/bin/python setup/capabilities.py manage`（Windows `.venv\Scripts\python`）；`.venv` 由第一次 `align` 建好 |
| `enable`／`disable` | 開或關一項 | `--tool`、`--kind`、`--id` **三個都要**，值照 `list` 印出來的填 |

```bash
python setup/capabilities.py list --tool codex
python setup/capabilities.py disable --tool claude --kind plugin --id ui-ux-pro-max@ui-ux-pro-max-skill
```

開關寫在工具原生的設定（Claude 是 `settings.json` 的 `enabledPlugins`；Codex 是 `config.toml`）；Claude 獨立 skill／command 停用是搬到 `~/.claude/ai-global-disabled/`。改之前備份到 `~/.ai-trash/ai-global-settings-*/`。切換不等於卸載，不下載也不改 manifest；工具通常要開新 session 才生效。

### `setup/check_governance.py`：治理檢查

```
python setup/check_governance.py [--local]
```

檢查兩個 router 節次對齊、沒照抄對面前綴、路由與連結有效、manifest 結構、`sources.json` 有沒有超過 45 天沒核對。`--local` 再多對帳本機部署副本與共用設定。CI 在 push／PR 時於三個 OS 跑一次。

### 測試

```bash
python -m unittest discover -s setup -p 'test_*.py'
```

### `setup/install-cleanup-*`：記憶體回收排程（各機器手動接，見下方「hooks 與記憶體回收」）

```bash
bash setup/install-cleanup-agent.sh [--interval-hours N] [--uninstall]   # macOS launchd
setup\install-cleanup-task.ps1 [-IntervalHours N] [-Uninstall]           # Windows schtasks（目前不啟用）
```

### `/ai-global` 的 8 個指令（Claude Code）

| 指令 | 用途 | 動檔案？ |
|---|---|---|
| `check` | 唯讀對帳：部署漂移、治理、能力、settings 共用項 | 否 |
| `sync` | pull → check → 必要裁決 → 部署 → 對帳 | 是 |
| `deploy` | 只重新部署 repo 自己的檔，不 pull | 是 |
| `govcheck` | 治理結構檢查 | 否 |
| `capabilities [list\|manage\|enable\|disable]` | 能力清單與開關 | 只改指定項 |
| `install <name>` | 補裝 manifest 中指定的一項（＝`align.py --only`） | 只該項 |
| `align` | 一鍵對齊；衝突在對話中問你 | 自動項直接做 |
| `evolve [source-id]` | 核對官方文件／marketplace 是否有變，寫 `docs/reports/harness-review-<日期>.md` | 只寫報告 |

流程檔在 `claude/skills/ai-global/commands/`；`common.md` 是共用背景，不是指令。

---

## 它怎麼運作

**部署是複製，不是連結。** `deploy.py` 把 repo 內容複製到工具讀的固定位置，所以 clone 在哪都行、可以搬、甚至刪掉，機器上的全域設定不受影響。（舊的 symlink 模型在 Windows 上因為 clone 換槽整條斷過好幾週，而工具沒有任何錯誤訊息。）

**副本會漂移，用狀態檔抓。** `~/.ai-global/.deploy-state.json` 記 `source_repo`（clone 在哪）、`files`（每檔部署時的 blob hash）、`managed`（逐一部署了哪些 skill／command／agent）。`BEHIND`／`EDITED` 靠 hash 不靠 commit，從未 commit 的工作樹部署也判得準。

**兩個 router 平行但不逐字相同。** 節次刻意對齊，只在工具能力處分歧（分支前綴 `claude/` vs `codex/`、`/ai-global` 只有 Claude Code 能跑、子代理機制）。checker 把「節次不對齊」與「照抄對面前綴」直接判 FAIL。

```
你在 clone 改檔 ──deploy──▶ ~/.ai-global/governance/          ← router 指向的規則本體
                         ├─▶ ~/.claude/CLAUDE.md、hooks/、statusline.sh、skills/ai-global/
                         └─▶ ~/.codex/AGENTS.md
               ──commit──▶ 本機 git ──push──▶ origin ──pull──▶ 另一台 clone ──deploy──▶ …
```

不在這條線上的：`~/.claude/settings.json`、`~/.codex/config.toml` 由工具自己回寫，只用 `manifest/settings.json` 對帳共用項；能力開關由 `capabilities.py` 按指定項更新並保留其他設定；`manifest/` 整個只留在 clone。

### manifest 納管的第三方能力

| 工具 | 能力 |
|---|---|
| Claude | `kb-retriever`、`web-design-guidelines`、`frontend-design`、`ui-ux-pro-max`、`gsap-skills`、`typescript-lsp`、`context7`、`hookify`、`claude-md-management` |
| Codex | `kb-retriever`、`web-design-guidelines`、`frontend-design`、`ui-ux-pro-max`、`gsap-skills`、`context7` |

Claude 獨有的三個分別因 Codex 無 LSP plugin、hook schema 不同、目標檔是 CLAUDE.md 而不設 Codex 條目。正本以 `manifest/skills.json` 為準；`typescript-lsp` 另需 `npm install -g typescript-language-server typescript`。

### 倉庫結構

```
claude/
  CLAUDE.md                  Claude Code router → ~/.claude/CLAUDE.md
  statusline.sh              狀態列：repo·worktree、分支、模型、context、額度、token
  hooks/                     cleanup-orphans.{sh,ps1} → ~/.claude/hooks/
  skills/ai-global/          /ai-global 分派器 + commands/*.md
codex/AGENTS.md              Codex router → ~/.codex/AGENTS.md
governance/                  憲法本體 → ~/.ai-global/governance/
manifest/skills.json         第三方能力清單（名稱＋來源＋版本）
manifest/settings.json       settings 共用基準
manifest/sources.json        evolve 的核對來源與上次核對日期
docs/reference/              agent-runtime.md（工具機制）、governance-evaluation.md（驗收情境）
docs/reports/                evolve 產出的審查報告
setup/                       align.py、deploy.py、installers.py、capabilities.py、capabilities_tui.py、
                             check_governance.py、install-cleanup-*、test_*.py、requirements-tui.txt
.github/workflows/governance.yml  三 OS 跑 checker 與測試
```

`~/.ai-global/` 頂層只允許 `governance/` 與 `.deploy-state.json`，其他一律視為舊版殘留收進 trash。`~/.claude/skills|commands|agents` 底下只動 repo 自己的項目，第三方的原地不碰。

### 技術棧

| 元件 | 技術 | 為何 |
|---|---|---|
| 腳本 | Python 3.11+ 標準庫 | 一份實作三 OS 通用；可互相 import，不靠解析 stdout |
| 比對 | 位元組比對；hash 自算 git blob sha1 | 和 git blob 對得上，不依賴 git 執行檔 |
| 互動選單 | prompt_toolkit（專案 `.venv`，`align` 自動建） | 能力開關與對齊衝突共用；非 TTY 退回 `--resolve` |
| 測試 | `unittest`，隔離 fixture | 不碰真實家目錄 |
| 行尾 | `.gitattributes` 強制 LF | macOS 的 shebang 需要 |

### 從 symlink 時代升級（2026-09-07 前裝的機器，一次性）

`git pull` 後直接 `deploy.py`：symlink 會報 `STALE` 並被連結本身搬進 trash、舊 `~/.ai-global/manifest/` 自動收掉、`~/Developer/agent-governance` 不再使用。唯一手動步驟：`mv ~/.claude/skills/sync-check ~/.ai-trash/`。

---

## hooks 與記憶體回收（機器本地、手動接）

`claude/hooks/` 會部署到 `~/.claude/hooks/`，但**要不要啟用由各機器的 `~/.claude/settings.json` 決定**，manifest 不管 hooks。

| 腳本 | 接法 |
|---|---|
| `cleanup-orphans.sh`（macOS） | `SessionEnd`：`bash ~/.claude/hooks/cleanup-orphans.sh --scope session`；排程：`bash setup/install-cleanup-agent.sh`（launchd，每 2h；`--interval-hours N`、`--uninstall`） |
| `cleanup-orphans.ps1`（Windows） | 自 2026-09-08 改為手動：桌面「Claude 清理背景程序.cmd」或 `~/.claude/hooks/cleanup-orphans.ps1 -Scope global`；排程工作與 SessionEnd hook 已移除，不因部署重新掛載 |

global 模式只回報候選程序與 VM，不因名稱相似或父程序消失就終止；session 模式只處理可證明屬於該 session 的後代輔助程序。支援 `--dry-run`／`-DryRun`，log 在 `~/.claude/logs/cleanup.log`。

---

## 給 AI agent 的指引

**Claude Code 已部署過的機器**：用 `/ai-global`。

**全新機器（skill 還不存在）或 Codex**：
1. 確認 OS 與 clone，先跑 `python setup/check_governance.py` 與 `python setup/align.py --plan`；看清既有 router 差異。需要取代且既有授權未涵蓋時，告知影響與備份位置後取得同意。
2. 在授權內執行 `python setup/align.py --yes` 並以 `deploy.py check` 驗證；被取代內容保留至 `~/.ai-trash/`。
3. 衝突在對話中逐項請使用者決定，再以 `--resolve` 套用；不自動納管本機多出的能力。
4. 回報變更、證據、限制與分支。

**紅線（對 agent 強制）**：不直接編輯部署端（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.ai-global/**`）；禁止 `rm`／程式化刪除，一律 `mv` 進 `~/.ai-trash/`；push 須使用者對具體遠端／分支明確授權；任何真實憑證不進 repo；改 `governance/` 先讀 `governance/40-maintenance.md`。

---

## 已知邊界

- Markdown 是行為約定，不是隔離：checker 與 `--local` 只驗「檔在、內容對」，不驗「當次 session 真的載入或遵循」。真正的強制在 sandbox／permissions／hooks／CI；[驗收情境](docs/reference/governance-evaluation.md)、[執行環境參考](docs/reference/agent-runtime.md)。
- 能力清單只涵蓋可辨識的本機來源與設定；未知狀態不能當成已啟用或停用。Codex plugin 沒有可靠安裝登錄，安裝狀態顯示未知。
- manifest 的 `codex_config` 只共用 `personality`；`model`／`model_reasoning_effort` 各機器自己決定。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、真實 `.env`、API key）**永不進本倉庫**；無秘密的 `.env.example` 依 `governance/50-safety.md` 檢查後可追蹤。
- 本倉庫必須保持 **private**。
