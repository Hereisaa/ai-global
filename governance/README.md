# agent-governance — AI 代理制度索引

> 外部參考路徑：本檔的 `../` 連結以 ai-global clone 的 `governance/` 為基準；部署副本請先從 `~/.ai-global/.deploy-state.json` 取得 `source_repo` 再解析。只在任務需要時讀取，不遞迴載入。

跨 Claude Code、Codex 共用的工作制度。兩側入口為 [Claude router](../claude/CLAUDE.md) 與 [Codex router](../codex/AGENTS.md)；部署方式見 [倉庫 README](../README.md)。此頁只提供索引，規則以各責任檔為準。

## 按需閱讀

| 文件 | 職責與讀取時機 |
|---|---|
| [10-dispatch.md](10-dispatch.md) | 需要拆分任務、委派或獨立審查時的協作方式 |
| [20-judgment.md](20-judgment.md) | 授權、風險、完成與驗收標準的唯一責任檔 |
| [30-templates.md](30-templates.md) | 派工時使用的目標、驗收與回報模板 |
| [40-maintenance.md](40-maintenance.md) | 修改制度、全域指令及維護回復方式 |
| [50-safety.md](50-safety.md) | 安全規範的唯一責任檔 |
| [60-project-bootstrap.md](60-project-bootstrap.md) | 新專案配置、CI 與文件存放命名 |
| [70-behavior-contract.md](70-behavior-contract.md) | 工作與溝通方式；首個實質任務前讀取 |
| [80-engineering.md](80-engineering.md) | 工程設計、程式碼變更與交付格式 |
| [USER-GUIDE.md](USER-GUIDE.md) | 給使用者的日常操作、驗證與狀態判讀 |
| [agent-runtime.md](../docs/reference/agent-runtime.md) | 官方工具載入與權限機制、平台維護參考 |
| [backups/](backups/) | 回復與查考用的歷史快照，**不是生效指令** |

`backups/` 中的舊規則、模型比較與實測狀態，不代表現行制度或當前環境。查歷史時明確標示日期，不將整個備份目錄載入為規則。

## 變更紀錄
- 2026-07-03 建檔（Fable 5）
- 2026-07-05 新增 60-project-bootstrap.md 並掛上兩側路由（Fable 5）
- 2026-07-05 新增 USER-GUIDE.md（使用者手冊）；環境強制層：digrit CI 檔就緒、Stop hook 腳本就緒待掛載（Fable 5）
- 2026-07-08 新增 70-behavior-contract.md（行為契約，Fable 5 蒸餾）與 REPORT-fable5-vs-opus.md（差異分析報告），兩側路由同步掛載（Fable 5）
- 2026-08-16 新增 80-engineering.md；目錄精簡：00-diagnosis、90-letter、REPORT-fable5-vs-opus 歸檔至 `backups/archived-*`，相關引用已修（Fable 5，應使用者要求）
- 2026-09-06 精簡為職責索引；新增執行環境參考，明定備份只供歷史查考。
- 2026-09-14 外部參考按需從 source_repo 解析，避免部署端斷鏈與無關讀取（Codex，使用者授權）。
