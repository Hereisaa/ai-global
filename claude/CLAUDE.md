# 全域指令（所有專案適用）

## 本檔的身分與改法
- 你讀到的 `~/.claude/CLAUDE.md` 是**實體檔案**，由 ai-global repo 部署產生（不是連結，不會斷鏈）。
- 實質規則的單一事實來源（SSOT）：`~/.ai-global/governance/`。本檔只放紅線與路由。
- 版本正本：ai-global git repo。本機 clone 的位置寫在 `~/.ai-global/.deploy-state.json` 的 `source_repo`。
- **不要直接編輯 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 或 `~/.ai-global/` 底下任何檔案。** 正確流程：改 clone 內對應檔 → 跑部署腳本 → `git commit && git push`。直接改部署端會在下次 check 被標成 `EDITED`，且下次部署時被覆蓋（舊檔進 `~/.ai-trash/`）。

## 環境
以實際偵測到的 OS 為準，不要假設。

| | macOS（主力） | Windows（副機） |
|---|---|---|
| 機器 | Apple Silicon M4 Mac mini | Windows 11 |
| Shell | zsh | PowerShell／Git Bash（各有各的語法） |
| GitHub 專案 | `~/Developer/GitHub/` | `D:\GitHub\`（Git Bash 下 `/d/GitHub/`） |
| 家目錄 | `/Users/<user>` | `C:\Users\<user>`（Git Bash 下 `/c/Users/<user>`） |

- 寫路徑一律用這些**兩平台都成立的 `$HOME` 相對路徑**，不要寫死機器路徑：
  - `~/.ai-global/`：制度檔與 manifest 的部署端
  - `~/.claude/`、`~/.codex/`：兩個工具的全域設定
  - `~/.ai-trash/`：安全刪除的暫存區
- 記憶體回收自動化兩台都已就位（macOS `cleanup-orphans.sh`＋launchd agent `com.claude.orphan-cleanup`；Windows `cleanup-orphans.ps1`＋排程工作 `ClaudeCodeOrphanCleanup`。皆為 SessionEnd hook＋每 2h；絕不殺 claude 主程序、跳過 remote-control、跳過 launchctl 受管服務）。使用者回報記憶體爆時先看 `~/.claude/logs/cleanup.log`，勿重複造輪子；詳見 ai-global README 對應平台節。
- 進入專案先讀該專案根目錄的 `CLAUDE.md` 與 `AGENTS.md`（若存在）。

## 全域設定要改／要同步時
clone 路徑見 `~/.ai-global/.deploy-state.json`；以下 `<repo>` 代表它。

- 改全域設定：改 `<repo>` 內的檔 → 部署 → `git commit && git push`（不 push 另一台拿不到）。
- 部署：macOS `bash <repo>/setup/install.sh`；Windows `powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1`。
- 只想看有沒有漂移（不動檔案）：同上加 `check`（macOS `install.sh check`／Windows `-Mode check`）。
- `git pull` 之後務必跑一次 check，決定要不要重新部署——pull 不會自動改全域。
- 完整對帳（含第三方 skills/plugins 與 settings 共用項）→ `/sync-check`。

## 多 session 並行（同一專案常有 3～5 個 session 在跑）
- 我自己開 worktree／分支時一律用 **`claude/<主題>`**（Codex 側用 `codex/<主題>`；前綴跟著工具走，這樣兩邊開的分支一眼分得出來）。系統自動生成的隨機字典名（`happy-snyder-98144c` 這種）開工前提議使用者改名，**不要自行 rename**——session metadata 會對不上。
- 交付與回報一律附上分支名；使用者問「哪個 session 對哪個分支」時查 session 清單的 branch 欄位與 `git worktree list`，不要憑印象答。

## 溝通
- 一律用繁體中文回應；給使用者閱讀的文件也用繁體中文撰寫。
- 保持簡潔；技術術語附一句白話解釋；主動提供最佳實務建議。
- 程式碼的變數命名與註解一律英文。
- 修改檔案前先提出 Plan 讓使用者確認，除非使用者明確要求自動執行、或正在執行已核准的計畫。

## 工程開發與輸出格式（完整原文與適用範圍 → `~/.ai-global/governance/80-engineering.md`）
- 不留向後相容負擔：直接移除過時路徑與舊碼，不加相容層、fallback、遷移邏輯。
- 最簡可行實作：滿足當前需求的最簡設計；不過早抽象、不過度配置、不加多餘間接層。
- 小步迭代：先做最小可行、端到端可運作的版本再疊功能；不為未完成的架構破壞可運作的系統。
- 模組化與關注點分離：職責邊界清晰、元件相互獨立。
- 引入新套件或自刻功能前，先完整檢視專案既有依賴與型別定義；優先用成熟且維護良好的函式庫。
- 設計決策著眼長期維護性，拒絕日後注定重寫的權宜之計（stopgaps）。
- 程式碼變更類回覆依序輸出：1) 變更摘要（改了什麼、為什麼、解決什麼問題，高層次條列）2) 架構重點與影響（選填、簡短）3) 乾淨可直接上線的程式碼或 diff；省略基礎語法與逐行細節，聚焦行為與架構影響。

## 安全紅線（違反即事故，無例外時不得便宜行事）
1. **禁止 `rm` / `rm -rf` / `rmdir` 及程式化刪除**（`os.remove`、`fs.unlink`、PowerShell `Remove-Item` 等）。刪除一律 `mv`／`Move-Item` 到 `~/.ai-trash/` 並加時間戳。完整流程與例外清單 → 讀 `~/.ai-global/governance/50-safety.md`。
2. 不可逆或對外的動作（force push、刪遠端分支、對外發布、寄送訊息）先向使用者確認。
3. `.env`、金鑰、憑證：不貼進回覆、不 commit、不傳給外部服務。

## 制度路由（符合情境就先讀對應檔，再動手）
制度檔在 `~/.ai-global/governance/`：
- 每個 session 第一個實質任務開工前 → 讀 `70-behavior-contract.md`（行為契約：怎麼想、怎麼做、怎麼說）。
- 任務預估要讀 **>3 個檔案或 >400 行**、掃目錄樹、查網頁、批次改檔 → 先讀 `10-dispatch.md`（委派規則、model/effort 選擇、驗證規範）。
- 要判斷「算不算完成」「該不該停下來問」「卡住該升級還是換路」 → 讀 `20-judgment.md`。
- 要寫派工 prompt 給 subagent → 用 `30-templates.md` 的模板。
- 開新專案、或要把既有專案納入管理 → 讀 `60-project-bootstrap.md`（三級制起手式與模板）。
- 要在任何專案**新增文件**（spec、plan、報告、參考文件）→ 讀 `60-project-bootstrap.md` 的「文件存放與命名規範」節，照分類與命名放，不要自行發明。
- 要修改本檔或任何制度檔 → 先讀 `40-maintenance.md`。
- 制度總覽 → `README.md`。

若上述某檔不存在：忽略該行、照常工作、並在回覆中告知使用者路由斷鏈（多半代表沒部署過，建議跑上面的部署指令）。

## 優先序（衝突時由高到低）
1. 使用者當下的明確指示
2. 專案級 CLAUDE.md / AGENTS.md
3. 本檔與 `~/.ai-global/governance/` 制度檔
4. plugin / skill 的預設流程——skill 與制度衝突時照制度做，並在回覆中註明略過了哪個 skill 流程。

## Cowork / 多端一致
本檔是 Claude Code CLI 與 Cowork（桌面版）之間使用者偏好的單一事實來源；Codex 側的對應檔為 `~/.codex/AGENTS.md`，兩者都只是 router，實質規則以 `~/.ai-global/governance/` 為準。

兩個 router **內容應保持對等，節次順序也刻意對齊**，方便逐節比對。只在「工具能力不同」處分歧，且分歧要寫明理由——例如分支前綴跟著工具走（`claude/` vs `codex/`）、`/sync-check` 只有 Claude Code 跑得動、子代理機制 Codex 未必有。改動任一邊時順手檢查另一邊要不要跟；照抄對面的工具專屬字眼（前綴、指令名）是最常見的錯。

## 變更紀錄
- 2026-07-31 新增「多 session 並行」節（Opus 5）
- 2026-08-16 新增「工程開發與輸出格式」節（完整版在 `80-engineering.md`）；制度目錄精簡，00/90/REPORT 歸檔（Fable 5，應使用者要求）
- 2026-08-17 環境節改為雙機描述（macOS 主力＋Windows 副機，正本在 ai-global repo）（Fable 5）
- 2026-08-28 環境節新增 Windows 記憶體回收自動化備忘（Fable 5，應使用者要求）
- 2026-08-28 記憶體回收自動化補上 macOS 版（Opus 5）
- 2026-09-07 制度路徑改為 `~/.ai-global/governance/`；部署改為實體檔案複製（不再用 symlink）；環境節改為雙機表格並修正 Windows 專案根目錄為 `D:\GitHub\`；新增「本檔的身分與改法」「全域設定要改／要同步時」兩節（Opus 5，應使用者要求）
- 2026-09-07 安全刪除暫存區從 `~/Developer/temp/trash/` 改為 `~/.ai-trash/`；`~/Developer` 是 macOS 形狀的路徑，不該在 Windows 上被建出來（Opus 5，應使用者要求）
- 2026-09-07 與 AGENTS.md 做對等稽核：分支前綴改為明示「跟著工具走」（`claude/` vs `codex/`），Cowork 節加上兩個 router 的對等契約與常見照抄錯誤（Opus 5，應使用者要求）
