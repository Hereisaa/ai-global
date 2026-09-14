# 代理執行環境參考

核對日期：2026-09-06。下列官方機制已查閱來源全文；本機部署與實際工具行為仍須現場驗證。這是技術參考，授權與驗收依 [20](../../governance/20-judgment.md)，安全依 [50](../../governance/50-safety.md)。

## 以當前工具能力為準

先查看當前工作階段實際提供的工具、schema（參數格式）及權限，再選用能完成工作的最直接工具。不要假定某工具名、skill、模型或平台功能必然存在；官方文件用來釐清行為，不能代替本機能力探測。

本文件不指定推薦模型或固定 reasoning effort（推理投入程度）。OpenAI 的 Astra 指南明確建議審查 skills／AGENTS.md，因為不清楚或衝突的指令可能使工作提早停住；這是官方使用建議，不是本倉庫的模型效能實測。[官方指南](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra)

## Codex 指令載入

- 啟動一次 run 時建立指令鏈；全域先找 `AGENTS.override.md`，其次 `AGENTS.md`。
- 專案根目錄至目前工作目錄，每層依 override、AGENTS、設定中的 fallback 檔名順序，至多取一份；較近工作目錄的內容較晚載入。
- `project_doc_max_bytes` 預設限制合併內容為 32 KiB，不是每份檔案各有 32 KiB。
- 自訂 fallback 檔名或調整指令後，依客戶端方式重新載入並查日誌。單純在 router 寫一個其他檔案路徑，不代表探索機制會自動展開它。

來源：[AGENTS.md 官方說明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。實際工作階段若由宿主注入指令，另核對宿主提供的載入資訊。

## Claude Code 指令與記憶

- 載入 `CLAUDE.md`；共用 AGENTS 正本可用 `@AGENTS.md` 匯入。`@path` 的相對路徑依匯入檔位置解析，巢狀最多四次；匯入仍占上下文。
- 祖先目錄至工作目錄的內容串接，子目錄檔案按讀取載入。較晚出現不代表 JSON 設定式的強制覆寫。
- CLAUDE.md 建議低於 200 行；目前文件記載最多 4 MiB 可全文載入，超過略過。auto-memory 的 `MEMORY.md` 啟動時只載前 200 行或 25KB，以先達者為準。
- Claude Code 的同一 Git repository 各 worktree 共用機器本地 auto-memory；不是跨機器同步。Cowork 的載入與匯入限制另有差異，不能宣稱會自動共享這套治理。

來源：[Claude 記憶與載入官方說明](https://code.claude.com/docs/en/memory)。此處描述產品能力；本制度的記憶寫入授權仍依使用者明確要求。

## 強制控制的範圍

| 控制 | 能做什麼 | 不代表什麼 |
|---|---|---|
| 指令檔 | 提供專案慣例與判斷背景 | 不保證每次遵循 |
| Sandbox | 由作業系統限制命令的檔案與網路存取 | 不保證所有外部連接器受同一邊界控制 |
| Permissions | 控制工具是否允許執行或須核准 | 不應只看預設值，須核對實際有效設定 |
| 執行前 command hook | 在事件點檢查並拒絕動作 | 腳本規則仍要測試，覆蓋範圍可能有缺口 |
| 執行後 hook | 格式化、檢查或記錄結果 | 無法撤銷已執行動作 |
| Prompt／agent hook | 讓另一個模型評估條件 | 判斷並非確定性檢查 |
| CI 與合併保護 | 自動檢查並依遠端設定限制合併 | 只有工作流程檔案不代表保護已生效 |

Codex 區分 sandbox 的技術邊界與 approval policy 的核准時機；`danger-full-access` 移除 sandbox 限制，`never` 取消核准提示。不能把這些模式搭配文字紅線後描述為具備隔離。[Sandbox 官方說明](https://learn.chatgpt.com/docs/sandboxing)

Claude Code 的設定與 hooks 才是執行控制，CLAUDE.md 是指引。`PreToolUse` 可在執行前拒絕；hook 的 allow 不可覆蓋設定中的 deny。啟用後應測試允許及拒絕案例，不能只看檔案存在。[權限](https://code.claude.com/docs/en/permissions)、[Hooks](https://code.claude.com/docs/en/hooks-guide)

Astra 非同步安全監控可能在觸發行為之後才暫停，官方明言不取代 sandbox、permissions 或成果審查。[安全說明](https://learn.chatgpt.com/docs/agent-approvals-security)

## macOS／Windows 維護備忘

本倉庫的部署入口見 [README](../../README.md)。以下檔案已確認存在；本次沒有執行清理、驗證排程掛載或跨平台效果：

| 平台 | 清理腳本 |
|---|---|
| macOS | [cleanup-orphans.sh](../../claude/hooks/cleanup-orphans.sh) |
| Windows | [cleanup-orphans.ps1](../../claude/hooks/cleanup-orphans.ps1) |

排程安裝器（launchd／schtasks）已於 2026-09-15 退役：macOS 既有的 launchd agent 保留運作，重灌時手動掛 `--scope global`；Windows 為手動執行。

腳本提供 `--dry-run`／`-DryRun` 與 session／global 範圍選項。需使用時先讀當前程式、確認程序所有權與目標，再檢視預演及紀錄；預演也可能寫日誌。不要沿用舊 README 的記憶體門檻、Colima／WSL 行為或「停了就不會重啟」結論作為當前保證。此頁不授權終止程序或啟用排程。

## 變更紀錄
- 2026-09-06 建立；記錄官方載入與執行控制機制，將平台維護資訊與核心規則分開。
