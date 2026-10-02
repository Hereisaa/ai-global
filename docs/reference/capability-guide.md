# 能力選配與工程工作環境

ai-global 管的是共用規則、設定部署和能力清單。日常開發先用基本能力；設計、研究或維護工作出現時才開對應選配。少裝能力不保證模型更快，是否有幫助仍要用實際任務驗證。

## 選哪一組

| 分組 | 適用工作 | 包含什麼 | 建議 |
|---|---|---|---|
| core 基本 | 多數程式開發 | ai-global 維護入口（Claude）、context7 文件查詢 | 新環境預設補裝；context7 仍只在需要文件時使用 |
| typescript 語言支援 | TypeScript／JavaScript 專案 | Claude typescript-lsp | 使用這些語言才開，另需 language server |
| frontend 前端 | 網站、介面、動畫 | frontend-design、web-design-guidelines、ui-ux-pro-max、gsap-skills | 按任務挑選，不必整組開；設計指南有重疊，先選一套主用 |
| research 研究 | 查本地 PDF、表格與文件知識庫 | kb-retriever | 有本地知識庫才開；純程式任務通常用不到 |
| maintenance 維護 | 編寫 Claude hook、整理 CLAUDE.md | hookify、claude-md-management | 維護時開；不要再建一套與 ai-global 重複的制度 |

`group` 只是清單分類，不會整組切換。`default_enabled` 表示一般 align 是否自動補裝缺項；不代表當次已載入，也不會重設既有本機開關。舊版 manifest 未標 group 的項目以 core 顯示，保持相容。

## 三個常用操作

在已確認的正本 clone 執行，Python 3.11+；macOS 可用 python3.12：

```bash
# 看前端選配；唯讀
python setup/capabilities.py list --group frontend
# 已安裝：指定工具及清單中的完整 ID 開啟
python setup/capabilities.py enable --tool claude --kind plugin --id frontend-design@claude-plugins-official
# 未安裝：明確補裝指定項目；ID 若同時列於兩工具，兩邊都會處理
python setup/align.py --no-pull --yes --only frontend-design@claude-plugins-official
```

停用用相同參數把 enable 改成 disable；原設定會備份，能力不卸載。開關由各機器自己保留，需在新工作階段確認載入。`--only` 仍會部署共用檔案，不是完全獨立的套件安裝器。

## 特定工具不必成為全域規則

動畫先沿用專案做法。小幅 hover、展開等效果通常用 CSS；專案需要時間軸、滾動或複雜 SVG 動畫時，可評估 GSAP 並開 gsap-skills。React 專案採用 GSAP 時沿用其 useGSAP 工作方式。套件選擇放在專案指令，避免每個後端或資料專案也載入動畫規範。

TUI 選單與 statusline 保留作為操作便利功能。程序清理 hook 是機器維護能力，有背景程序問題時再採用；部署腳本存在不代表已掛載或已驗證其防護。

## 三種工程環境各放什麼

| 環境 | ai-global 提供 | 專案或執行平台負責 |
|---|---|---|
| 工程師與程式 Agent 一起開發 | 共用授權、安全、交付原則及能力管理 | 建置、測試指令、架構限制、專案資料 |
| 自動執行的 agentic workflow | 相同基本規則與設定來源 | 任務狀態保存、重試上限、工具權限、取消、成本及事件紀錄 |
| 多人科技公司環境 | 可版本管理的共用基準與部署方法 | 身分、秘密管理、真正的隔離、審批、稽核及 CI |

不要把佇列、工作流引擎或團隊稽核系統塞進全域提示。要讓 Agent 跑公司任務，先在該專案記下：任務輸入與完成條件、可用工具與操作範圍、建置測試方式、失敗如何停下及保存成果。需要無人值守才由執行平台提供持久狀態與重試，不用文字規則冒充這些機制。

## 何時再維護

工具升級、能力失效或需求改變才查相關來源；日期過舊只是資訊。修改腳本跑對應測試；依變更影響選相關模型題，包含授權、安全、完成判斷與生效判讀。完整評估見 [harness-eval-method.md](harness-eval-method.md)，不要求每次小改都跑 48 次模型任務。
