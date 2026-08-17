# 全域指令（所有專案適用）

## 環境
- 兩台機器共用本設定（正本在 git repo `~/Developer/GitHub/ai-global`）：主力 macOS（Apple Silicon, M4 Mac mini，zsh）；副機 Windows（PowerShell／Git Bash）。以實際偵測到的 OS 為準。
- 主要工作區 `~/Developer/`；GitHub 專案在 `~/Developer/GitHub/`（兩平台同構，Windows 在 `%USERPROFILE%` 下）。
- 進入專案先讀該專案根目錄的 `CLAUDE.md` 與 `AGENTS.md`（若存在）。

## 多 session 並行（同一專案常有 3～5 個 session 在跑）
- 我自己開 worktree／分支時一律用 `claude/<主題>`。系統自動生成的隨機字典名（`happy-snyder-98144c` 這種）開工前提議使用者改名，**不要自行 rename**——session metadata 會對不上。
- 交付與回報一律附上分支名；使用者問「哪個 session 對哪個分支」時查 session 清單的 branch 欄位與 `git worktree list`，不要憑印象答。

## 溝通
- 一律用繁體中文回應；給使用者閱讀的文件也用繁體中文撰寫。
- 保持簡潔；技術術語附一句白話解釋；主動提供最佳實務建議。
- 程式碼的變數命名與註解一律英文。
- 修改檔案前先提出 Plan 讓使用者確認，除非使用者明確要求自動執行、或正在執行已核准的計畫。

## 工程開發與輸出格式（完整原文與適用範圍 → `~/Developer/agent-governance/80-engineering.md`）
- 不留向後相容負擔：直接移除過時路徑與舊碼，不加相容層、fallback、遷移邏輯。
- 最簡可行實作：滿足當前需求的最簡設計；不過早抽象、不過度配置、不加多餘間接層。
- 小步迭代：先做最小可行、端到端可運作的版本再疊功能；不為未完成的架構破壞可運作的系統。
- 模組化與關注點分離：職責邊界清晰、元件相互獨立。
- 引入新套件或自刻功能前，先完整檢視專案既有依賴與型別定義；優先用成熟且維護良好的函式庫。
- 設計決策著眼長期維護性，拒絕日後注定重寫的權宜之計（stopgaps）。
- 程式碼變更類回覆依序輸出：1) 變更摘要（改了什麼、為什麼、解決什麼問題，高層次條列）2) 架構重點與影響（選填、簡短）3) 乾淨可直接上線的程式碼或 diff；省略基礎語法與逐行細節，聚焦行為與架構影響。

## 安全紅線（違反即事故，無例外時不得便宜行事）
1. **禁止 `rm` / `rm -rf` / `rmdir` 及程式化刪除**（`os.remove`、`fs.unlink` 等）。刪除一律 `mv` 到 `~/Developer/temp/trash/` 並加時間戳。完整流程與例外清單 → 讀 `~/Developer/agent-governance/50-safety.md`。
2. 不可逆或對外的動作（force push、刪遠端分支、對外發布、寄送訊息）先向使用者確認。
3. `.env`、金鑰、憑證：不貼進回覆、不 commit、不傳給外部服務。

## 制度路由（符合情境就先讀對應檔，再動手）
制度檔在 `~/Developer/agent-governance/`：
- 每個 session 第一個實質任務開工前 → 讀 `70-behavior-contract.md`（行為契約：怎麼想、怎麼做、怎麼說）。
- 任務預估要讀 **>3 個檔案或 >400 行**、掃目錄樹、查網頁、批次改檔 → 先讀 `10-dispatch.md`（委派規則、model/effort 選擇、驗證規範）。
- 要判斷「算不算完成」「該不該停下來問」「卡住該升級還是換路」 → 讀 `20-judgment.md`。
- 要寫派工 prompt 給 subagent → 用 `30-templates.md` 的模板。
- 開新專案、或要把既有專案納入管理 → 讀 `60-project-bootstrap.md`（三級制起手式與模板）。
- 要在任何專案**新增文件**（spec、plan、報告、參考文件）→ 讀 `60-project-bootstrap.md` 的「文件存放與命名規範」節，照分類與命名放，不要自行發明。
- 要修改本檔或任何制度檔 → 先讀 `40-maintenance.md`。
- 制度總覽 → `README.md`。

若上述某檔不存在：忽略該行、照常工作、並在回覆中告知使用者路由斷鏈。

## 優先序（衝突時由高到低）
1. 使用者當下的明確指示
2. 專案級 CLAUDE.md / AGENTS.md
3. 本檔與 `~/Developer/agent-governance/` 制度檔
4. plugin / skill 的預設流程——skill 與制度衝突時照制度做，並在回覆中註明略過了哪個 skill 流程。

## Cowork / 多端一致
本檔是 Claude Code CLI 與 Cowork（桌面版）之間使用者偏好的單一事實來源；Codex 側的對應檔為 `~/.codex/AGENTS.md`，兩者都只是 router，實質規則以 `~/Developer/agent-governance/` 為準。

## 變更紀錄
- 2026-07-31 新增「多 session 並行」節（Opus 5）
- 2026-08-16 新增「工程開發與輸出格式」節（完整版在 `80-engineering.md`）；制度目錄精簡，00/90/REPORT 歸檔（Fable 5，應使用者要求）
- 2026-08-17 環境節改為雙機描述（macOS 主力＋Windows 副機，正本在 ai-global repo）（Fable 5）
