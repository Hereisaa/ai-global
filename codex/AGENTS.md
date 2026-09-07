# 全域指令（Codex 側 router）

> 實質規則的單一事實來源在 `~/.ai-global/governance/`（與 Claude Code 共用）。
> 本檔只放摘要與路由；兩邊規則若不一致，以 governance 目錄為準。
> 你讀到的 `~/.codex/AGENTS.md` 是 ai-global repo 部署出來的**實體檔案**。不要直接改它——
> 改 clone 內的 `codex/AGENTS.md`，再跑部署腳本（clone 路徑見 `~/.ai-global/.deploy-state.json`）。

## 溝通
- 一律用繁體中文回應；給使用者閱讀的文件也用繁體中文撰寫。
- 保持簡潔；技術術語附一句白話解釋；主動提供最佳實務建議。
- 程式碼的變數命名與註解一律英文。
- 修改檔案前先提出 Plan 讓使用者確認，除非使用者明確要求自動執行、或正在執行已核准的計畫。
- 開 worktree／分支一律用 `claude/<主題>`，不要用隨機生成名；交付與回報一律附上分支名。

## 環境
以實際偵測到的 OS 為準，不要假設。

| | macOS（主力） | Windows（副機） |
|---|---|---|
| 機器 | Apple Silicon M4 Mac mini | Windows 11 |
| Shell | zsh | PowerShell／Git Bash（各有各的語法） |
| GitHub 專案 | `~/Developer/GitHub/` | `D:\GitHub\`（Git Bash 下 `/d/GitHub/`） |
| 家目錄 | `/Users/<user>` | `C:\Users\<user>`（Git Bash 下 `/c/Users/<user>`） |

- 寫路徑一律用兩平台都成立的 `$HOME` 相對路徑，不要寫死機器路徑：`~/.ai-global/`（制度與 manifest 部署端）、`~/.claude/`、`~/.codex/`、`~/.ai-trash/`（安全刪除暫存區）。
- 進入專案先讀該專案根目錄的 `AGENTS.md` 與 `CLAUDE.md`（若存在）。

## 全域設定要改／要同步時
clone 路徑見 `~/.ai-global/.deploy-state.json`；以下 `<repo>` 代表它。
- 改全域設定：改 `<repo>` 內的檔 → 部署 → `git commit && git push`。
- 部署：macOS `bash <repo>/setup/install.sh`；Windows `powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1`。
- 只看漂移不動檔案：macOS `install.sh check`；Windows `-Mode check`。`git pull` 之後務必跑一次——pull 不會自動改全域。

## 工程開發與輸出格式（完整原文與適用範圍 → `~/.ai-global/governance/80-engineering.md`）
- 不留向後相容負擔：直接移除過時路徑與舊碼，不加相容層、fallback、遷移邏輯。
- 最簡可行實作：滿足當前需求的最簡設計；不過早抽象、不過度配置、不加多餘間接層。
- 小步迭代：先做最小可行、端到端可運作的版本再疊功能；不為未完成的架構破壞可運作的系統。
- 模組化與關注點分離：職責邊界清晰、元件相互獨立。
- 引入新套件或自刻功能前，先完整檢視專案既有依賴與型別定義；優先用成熟且維護良好的函式庫。
- 設計決策著眼長期維護性，拒絕日後注定重寫的權宜之計（stopgaps）。
- 程式碼變更類回覆依序輸出：1) 變更摘要（改了什麼、為什麼、解決什麼問題，高層次條列）2) 架構重點與影響（選填、簡短）3) 乾淨可直接上線的程式碼或 diff；省略基礎語法與逐行細節，聚焦行為與架構影響。

## 安全紅線（違反即事故）
1. **禁止 `rm` / `rm -rf` / `rmdir` 及程式化刪除**（含 PowerShell `Remove-Item`）。刪除一律 `mv`／`Move-Item` 到 `~/.ai-trash/` 並加時間戳。完整流程與例外 → `~/.ai-global/governance/50-safety.md`。
2. 不可逆或對外的動作（force push、刪遠端分支、對外發布、寄送訊息）先向使用者確認。
3. `.env`、金鑰、憑證：不貼進回覆、不 commit、不傳外部服務。

## 制度路由（符合情境就先讀對應檔，再動手）
制度檔在 `~/.ai-global/governance/`：
- 每個 session 第一個實質任務開工前 → `70-behavior-contract.md`（行為契約：怎麼想、怎麼做、怎麼說）。
- 任務要讀 >3 個檔或 >400 行、掃目錄樹、查網頁、批次改檔 → 先讀 `10-dispatch.md`。若本環境沒有子代理機制，仍須遵守其中的「回報合約」與「驗證不自驗」原則（用乾淨的新對話或要求使用者開新 session 驗收亦可）。
- 判斷「算不算完成」「該不該停下來問」「卡住該升級還是換路」 → `20-judgment.md`。
- 派工 prompt 模板 → `30-templates.md`。
- 開新專案、或要把既有專案納入管理 → 讀 `60-project-bootstrap.md`。
- 要在任何專案**新增文件**（spec、plan、報告、參考文件）→ 讀 `60-project-bootstrap.md` 的「文件存放與命名規範」節，照分類與命名放，不要自行發明。
- 修改本檔或制度檔前 → 先讀 `40-maintenance.md`。
- 某檔不存在：忽略該行、照常工作、並告知使用者路由斷鏈（多半代表沒部署過，建議跑上面的部署指令）。

## 優先序（衝突時由高到低）
1. 使用者當下的明確指示
2. 專案級 AGENTS.md / CLAUDE.md
3. 本檔與 `~/.ai-global/governance/` 制度檔
4. skill / plugin 的預設流程——衝突時照制度做，並在回覆中註明。

## 變更紀錄
- 2026-08-16 新增「工程開發與輸出格式」節，完整版在 `80-engineering.md`（Fable 5，應使用者要求）
- 2026-08-17 環境節改為雙機描述（macOS 主力＋Windows 副機，正本在 ai-global repo）（Fable 5）
- 2026-09-07 制度路徑改為 `~/.ai-global/governance/`；部署改為實體檔案複製（不再用 symlink）；環境節改為雙機表格並修正 Windows 專案根目錄為 `D:\GitHub\`；新增「全域設定要改／要同步時」節（Opus 5，應使用者要求）
- 2026-09-07 安全刪除暫存區從 `~/Developer/temp/trash/` 改為 `~/.ai-trash/`（Opus 5，應使用者要求）
