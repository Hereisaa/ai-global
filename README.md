# ai-global

我給 AI 工具（Claude Code／Cowork、Codex）的**全域設定**，兩台電腦（macOS 主力、Windows 副機）共用同一份。

裡面有四種東西：

| 東西 | 是什麼 | 部署到哪 |
|---|---|---|
| router | `CLAUDE.md`、`AGENTS.md`，工具每次開 session 自動讀的入口 | `~/.claude/`、`~/.codex/` |
| 憲法（governance） | 委派、判斷、安全、工程等規則，router 依情境路由過去讀。有自己的索引 [governance/README.md](governance/README.md)，使用者手冊在 [governance/USER-GUIDE.md](governance/USER-GUIDE.md) | `~/.ai-global/governance/` |
| 自製能力 | `/ai-global` skill、hooks、statusline | `~/.claude/` |
| 第三方清單（manifest） | 該裝哪些 skills／plugins、版本多少 | 不部署，只用來對帳 |

運作方式一句話：**在 clone 裡改檔 → 跑 `align` → 它把檔複製到工具讀的位置**；另一台 `git pull` 再跑一次 `align` 就同步了。所有被換掉的檔都搬進 `~/.ai-trash/`，不刪東西。

---

## 環境需求

| 需要 | 說明 |
|---|---|
| git | clone、同步 |
| **Python 3.11 以上** | macOS 內建的 `python3` 是 3.9，太舊：`brew install python@3.12`，之後用 `python3.12` 這個指令。Windows 從 python.org 裝 |
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
2. 缺選單套件 → 問「建立 .venv 並安裝？[Y/n]」，Enter 就建好、裝好、重新執行自己。`.venv` 只在這個資料夾，刪掉就還原。
3. 部署 router、憲法、hooks、skill 到上表的位置。
4. 補裝 manifest 列的第三方 plugins／skills。
5. 有衝突（本機多出來的、版本不同的、重複的）就開選單讓你逐項選；沒有就結束。

> 電腦上本來就有自己的 `CLAUDE.md`／`AGENTS.md`？它會列成 `edited` 衝突讓你選「用 repo 的／把我的寫回 repo／先保留」，原檔一定先進 `~/.ai-trash/`。

---

## 平常怎麼用

六個動作，**在 Claude Code 裡說 `/ai-global <動作>`，或自己在終端跑同名腳本**，名字一樣、做的事一樣：

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
| `--only ID` | 只補裝這一項，ID 用 manifest 的 `id`；可重複 |
| `--resolve KEY=ACTION` | 指定某個衝突怎麼處理，KEY 和可用 ACTION 都印在 CONFLICT 表；可重複 |
| `--no-venv` | 缺選單套件時不問、不建 `.venv`，直接文字模式 |
| `--json` | 最後多印 JSON 摘要 |

輸出四張表：`DRIFT` 漂移、`DEPLOY` 部署了什麼、`INSTALL` 補裝結果、`CONFLICT` 要你決定的。回傳碼 `0` 完成、`2` 還有衝突、`1` 有失敗。

衝突七種，每種的預設都是最保守的：

| 類型 | 意思 | 可選 | 預設 |
|---|---|---|---|
| `edited` | 部署檔在 repo 外被改過 | overwrite 用 repo 的／writeback 寫回 repo／keep | overwrite |
| `extra` | 本機有、manifest 沒有 | keep／disable／trash | keep |
| `duplicate` | 獨立 skill 和 plugin 裡的同名 | trash／disable／keep | trash |
| `switch` | 本機開關和 manifest 建議相反 | enable／disable／keep | keep |
| `version` | 版本和 manifest 不同 | update／keep | update |
| `hook` | settings.json 指到不存在的 hook 腳本，或掛了只建議在別的平台掛的 hook | keep／unwire | keep |
| `hookmissing` | manifest 建議本平台掛的 hook，settings.json 沒掛 | keep／wire | keep |

### `deploy.py`

```
python setup/deploy.py [install | check]
```

`install`（預設）複製 router、憲法、hooks、statusline、skill 到位並記錄狀態；`check` 只報漂移。狀態：`OK`、`MISSING` 還沒部署、`BEHIND` repo 有新版、`EDITED` 部署端被改過、`EXTRA` repo 已移除但本機還在、`STALE` 舊版斷鏈。

### `capabilities.py`

```
python setup/capabilities.py list    [--tool claude|codex] [--kind skill|plugin|command] [--id ID] [--json]
python setup/capabilities.py manage  [--demo]
python setup/capabilities.py enable  --tool claude|codex --kind skill|plugin|command --id ID
python setup/capabilities.py disable --tool claude|codex --kind skill|plugin|command --id ID
```

**第一個字（動作）一定要給**：

- `list`：表格列出每項能力的工具、種類、ID、來源、有沒有裝、開了沒。後面的 `--tool`／`--kind`／`--id` 是篩選，可不給。
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

檢查兩個 router 節次對齊、沒互抄對方的前綴、路由與連結有效、manifest 格式、`sources.json` 有沒有超過 45 天沒核對。`--local` 多對帳本機部署副本。CI 在 push／PR 時於三個 OS 跑。

### 測試

```bash
python -m unittest discover -s setup -p 'test_*.py'
```

---

## 它怎麼運作

**部署是複製，不是連結。** clone 在哪都行、可以搬、可以刪，電腦上的設定不受影響。（以前用 symlink，Windows 上 clone 換槽整條斷了好幾週，工具一聲不吭。）

**用狀態檔抓漂移。** `~/.ai-global/.deploy-state.json` 記 clone 在哪、每個檔部署時的 hash、部署了哪些項目。`BEHIND`／`EDITED` 靠 hash 判斷，所以沒 commit 的改動也判得準。

**兩個 router 平行但不逐字相同。** 節次刻意對齊，只在工具能力不同處分歧（分支前綴 `claude/` vs `codex/`、`/ai-global` 只有 Claude Code 能跑）。`govcheck` 把「節次不對齊」和「照抄對面前綴」直接判 FAIL。

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

正本是 `manifest/skills.json`。`typescript-lsp` 另需 `npm install -g typescript-language-server typescript`。

### 倉庫結構

```
claude/CLAUDE.md             Claude Code router      → ~/.claude/CLAUDE.md
claude/statusline.sh         狀態列                   → ~/.claude/statusline.sh
claude/hooks/                guard-delete.sh、ai-global-check.sh、cleanup-orphans.{sh,ps1} → ~/.claude/hooks/
claude/skills/ai-global/     /ai-global skill         → ~/.claude/skills/ai-global/
codex/AGENTS.md              Codex router             → ~/.codex/AGENTS.md
governance/                  憲法（README.md 是索引，USER-GUIDE.md 給使用者）→ ~/.ai-global/governance/
manifest/                    skills.json（第三方清單）、settings.json（共用設定）、sources.json（evolve 核對來源）
docs/CHANGELOG.md            兩個 router 的變更紀錄（不放在 router 本體）
docs/reference/              agent-runtime.md（工具機制）、governance-evaluation.md（驗收情境）
docs/reports/                evolve 產出的報告
setup/                       align.py、deploy.py、capabilities.py、govcheck.py 及各自的 test_*.py
```

`~/.ai-global/` 頂層只會有 `governance/` 和 `.deploy-state.json`，其他一律當舊版殘留收進 trash。`~/.claude/skills|commands|agents` 只動 repo 自己的項目，第三方的不碰。

---

## hooks

`claude/hooks/` 底下的腳本都會部署到 `~/.claude/hooks/`，但**要不要啟用由各機器自己的 `settings.json` 決定**，部署不會幫你掛。`manifest/settings.json` 的 `hooks` 區塊是建議接法：`align` 發現建議的 hook 沒掛會列成 `hookmissing` 衝突，選 `wire` 才掛（新 session 生效）；指到不存在腳本的 hook 列成 `hook`，選 `unwire` 才移除。

| 腳本 | 事件 | 做什麼 |
|---|---|---|
| `guard-delete.sh` | `PreToolUse`（matcher `Bash`） | 整條指令裡出現 `rm`／`rmdir`／`unlink`／`shred`／`find -delete`／`Remove-Item`／`git clean -f` 就擋下（exit 2）並把 50-safety 的替代做法回給模型。permissions 的 deny 只比對指令開頭，`cd x && rm -rf y` 擋不到，這支補上。`npm rm`、`git rm` 不擋。 |
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

Windows 的 Claude Code 也是用 `bash`（Git Bash）跑這些 `.sh`；guard 需要 `python3`／`python` 在 PATH，找不到就放行不擋。Windows 端尚未實測。

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
