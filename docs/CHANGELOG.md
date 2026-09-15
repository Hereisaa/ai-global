# 變更紀錄（router）

兩個 router（`claude/CLAUDE.md`、`codex/AGENTS.md`）的變更紀錄集中在這裡，不放在 router 本體，避免每個 session 都載入歷史。制度檔（`governance/*.md`）的變更紀錄仍在各檔末尾。精確 diff 一律查 Git。

## claude/CLAUDE.md
- 2026-07-31 新增「多 session 並行」節（Opus 5）
- 2026-08-16 新增「工程開發與輸出格式」節（完整版在 `80-engineering.md`）；制度目錄精簡，00/90/REPORT 歸檔（Fable 5，應使用者要求）
- 2026-08-17 環境節改為雙機描述（macOS 主力＋Windows 副機，正本在 ai-global repo）（Fable 5）
- 2026-08-28 環境節新增 Windows 記憶體回收自動化備忘（Fable 5，應使用者要求）
- 2026-08-28 記憶體回收自動化補上 macOS 版（Opus 5）
- 2026-09-07 制度路徑改為 `~/.ai-global/governance/`；部署改為實體檔案複製（不再用 symlink）；環境節改為雙機表格並修正 Windows 專案根目錄為 `D:\GitHub\`；新增「本檔的身分與改法」「全域設定要改／要同步時」兩節（Opus 5，應使用者要求）
- 2026-09-07 安全刪除暫存區從 `~/Developer/temp/trash/` 改為 `~/.ai-trash/`；`~/Developer` 是 macOS 形狀的路徑，不該在 Windows 上被建出來（Opus 5，應使用者要求）
- 2026-09-07 與 AGENTS.md 做對等稽核：分支前綴改為明示「跟著工具走」（`claude/` vs `codex/`），Cowork 節加上兩個 router 的對等契約與常見照抄錯誤（Opus 5，應使用者要求）
- 2026-09-07 `sync-check` skill 改名為 `ai-global` 並擴充為完整生命週期（首次部署／更新／裁決／對帳）；`manifest/` 不再部署到 `~/.ai-global`（只有 skill 讀，直接讀 clone）（Fable 5.1，應使用者要求）
- 2026-09-07 部署狀態改記檔案雜湊（`files`）與管理清單（`managed`）：髒工作樹部署後仍正確判 BEHIND、改名的 skill 會自動收進 trash；`~/.ai-global` 頂層只允許 governance 與 state（Fable 5.1）
- 2026-09-07 合併 `claude/governance-refresh`（憲法優化）：授權／完成／驗收統一由 20 定義、push 需明確授權、委派不用檔數硬門檻、優先序加入平台層與同層衝突原則、補 50 與 80 路由、指向 `docs/reference/agent-runtime.md`；大綱維持本檔既有節次（Fable 5.1）
- 2026-09-14 縮小讀取範圍、對齊 80 工程規則、移除低風險重問與改名要求，補能力開關入口及 Windows 手動清理決策（Codex，使用者授權）。
- 2026-09-14 部署腳本改為單一 Python（`setup/deploy.py`），新增 `/ai-global align` 一鍵對齊（pull＋部署＋補裝＋衝突 TUI／對話裁決）與 `evolve`；install.sh／ps1 退役（Opus 5，使用者授權）
- 2026-09-14 `align` 加 Python 版本守門與 `.venv` 自動建置（缺 prompt_toolkit 問一句即建、重跑）；manifest 的 Codex `claude-plugins-official` 條目改為自動註冊 marketplace（Opus 5，使用者授權）
- 2026-09-15 skill 與腳本命名收斂：`check_governance.py` 改名 `govcheck.py`；`/ai-global` 收成 `check`（＝`align --plan`）／`align`（吸收 `sync`，`--only` 取代 `install`）／`deploy`／`govcheck`／`capabilities`／`evolve`；`install-cleanup-*` 退役（Fable 5.1，使用者授權）
- 2026-09-15 變更紀錄搬到 `docs/CHANGELOG.md`；同步節加入 SessionStart 漂移檢查 hook；安全紅線加入 PreToolUse 擋刪除 hook；全檔精簡回 60 行預算內（Fable 5.1，使用者授權）

## codex/AGENTS.md
- 2026-08-16 新增「工程開發與輸出格式」節，完整版在 `80-engineering.md`（Fable 5，應使用者要求）
- 2026-08-17 環境節改為雙機描述（macOS 主力＋Windows 副機，正本在 ai-global repo）（Fable 5）
- 2026-09-07 制度路徑改為 `~/.ai-global/governance/`；部署改為實體檔案複製（不再用 symlink）；環境節改為雙機表格並修正 Windows 專案根目錄為 `D:\GitHub\`；新增「全域設定要改／要同步時」節（Opus 5，應使用者要求）
- 2026-09-07 安全刪除暫存區從 `~/Developer/temp/trash/` 改為 `~/.ai-trash/`（Opus 5，應使用者要求）
- 2026-09-07 與 CLAUDE.md 做對等稽核：補上記憶體回收備忘、`/ai-global`（Codex 跑不了的適配寫法）、多 session 並行專節、制度總覽路由、「不要編輯部署端」的完整後果；節次順序對齊 CLAUDE.md 以利日後比對（Opus 5，應使用者要求）
- 2026-09-07 修正照抄錯誤：worktree／分支前綴從 `claude/<主題>` 改為 `codex/<主題>`（前綴跟著工具走）；`30-templates.md` 的派工對象改為不預設有子代理機制（Opus 5，使用者指出）
- 2026-09-07 `sync-check` skill 改名為 `ai-global`；`manifest/` 不再部署到 `~/.ai-global`（Fable 5.1，應使用者要求）
- 2026-09-07 部署狀態改記檔案雜湊（`files`）與管理清單（`managed`）；`~/.ai-global` 頂層只允許 governance 與 state（Fable 5.1）
- 2026-09-07 合併 `claude/governance-refresh`（憲法優化）：授權／完成／驗收統一由 20 定義、push 需明確授權、委派不用檔數硬門檻、優先序加入平台層與同層衝突原則、補 50 與 80 路由、指向 `docs/reference/agent-runtime.md`；大綱維持本檔既有節次（Fable 5.1）
- 2026-09-14 縮小讀取範圍、對齊 80 工程規則、移除低風險重問與改名要求，補能力開關入口及 Windows 手動清理決策（Codex，使用者授權）。
- 2026-09-14 部署腳本改為單一 Python（`setup/deploy.py`），新增 `align` 一鍵對齊與 `evolve`（Claude Code 的 skill；Codex 直接跑同一套 `setup/*.py`）；install.sh／ps1 退役（Opus 5，使用者授權）
- 2026-09-14 `align` 加 Python 版本守門與 `.venv` 自動建置（缺 prompt_toolkit 問一句即建、重跑）；manifest 的 Codex `claude-plugins-official` 條目改為自動註冊 marketplace（Opus 5，使用者授權）
- 2026-09-15 skill 與腳本命名收斂：`check_governance.py` 改名 `govcheck.py`；`/ai-global` 收成 `check`（＝`align --plan`）／`align`（吸收 `sync`，`--only` 取代 `install`）／`deploy`／`govcheck`／`capabilities`／`evolve`；`install-cleanup-*` 退役（Fable 5.1，使用者授權）
- 2026-09-15 變更紀錄搬到 `docs/CHANGELOG.md`；與 CLAUDE.md 同步精簡回 60 行預算內，hook 只在 Claude Code 生效、Codex 側註明沒有（Fable 5.1，使用者授權）
