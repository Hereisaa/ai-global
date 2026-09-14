# Harness 審查報告 2026-09-14（第 2 次）

- 觸發：驗證 `/ai-global evolve` 流程本身；補核對第 1 份報告列為「未核對」的兩個來源。
- 範圍：`codex-agents-md`、`claude-code-plugins-reference`（使用者指定；兩者 last_checked 皆 2026-09-06，距今 8 天，未超過 45 天）。
- 執行：Claude Code（Opus 5），WebFetch 讀官方頁面；本機 Claude Code 2.1.267、codex-cli 0.152.0。

## 結論

需立即處理：0。可排入下次維護：2。只記錄：2。未核對：0。

## 逐來源

| 來源 | 結果 | 影響與分級 |
|---|---|---|
| codex-agents-md | **未變**。官方：全域先 `~/.codex/AGENTS.override.md` 再 `AGENTS.md`；專案自 Git root 到 cwd 每層依 override → AGENTS → `project_doc_fallback_filenames` 至多取一份；由根向下串接，較近 cwd 者覆蓋；`project_doc_max_bytes` 預設 32 KiB 為**合併總量**；每次 run／TUI session 開始時重建指令鏈，無快取。與 `agent-runtime.md`「Codex 指令載入」節逐點一致。 | 只記錄。補充：官方明言「無快取、每次重建」，比 runtime 文「依客戶端方式重新載入並查日誌」更明確——可在下次維護時替換用語（不影響行為）。 |
| claude-code-plugins-reference | **變（相對於 last_seen）**。(a) 元件類型增至 10 種：skills、commands、agents、workflows、hooks、MCP、LSP、monitors（實驗）、themes（實驗）、output-styles。(b) `enabledPlugins` 可存在於 user／project／local／managed 四層。(c) 官方寫「可對已停用 plugin 直接 uninstall」，但本機 2.1.267 對 `superpowers`、`rust-analyzer-lsp` 兩個已停用 plugin 回報 not found，enable 後又報 not installed in user scope 並清掉登錄——**文件與觀察不符**。(d) `installed_plugins.json` 未在官方文件出現；`capabilities.py` 目前讀它判定安裝狀態，等於依賴未文件化格式。(e) `~/.claude/plugins/data/{id}/` 官方稱 uninstall 時自動刪除，但本機因 (c) 失敗而殘留，已手動清。 | **可排入下次維護** ×2：(1) `capabilities.py` 的 Claude 安裝判定加一層 `claude plugin list` 交叉驗證，並在 `capabilities.md` 記「已停用 plugin 先 enable 再 uninstall，或改原生設定」的繞行；(2) `check_governance.py` 對 `enabledPlugins` 只看 user 層，project／local 層可能覆蓋——現行 WARN「settings.local.json 存在」已涵蓋 local，project 層未涵蓋，評估是否加提示。其餘只記錄。 |

## 對 evolve 流程本身的驗證

| 步驟 | 結果 |
|---|---|
| 1 讀 sources 並算距今天數 | 正常；指定子集時只處理該兩筆 |
| 2 取回來源 | 兩頁皆可 WebFetch；無需 context7／gh |
| 3 影響判定 | 對照 `affects`（runtime 文、AGENTS.md、capabilities.py、skills.json）可落到具體檔案 |
| 4 寫報告 | 同日第二份，使用 `-2` 後綴，未覆蓋第 1 份 |
| 5 更新核對日期 | 兩筆 `last_checked` → 2026-09-14，`last_seen` 更新；`agent-runtime.md` 只有 Codex 節被核對，Claude 記憶節未重讀，故**不**更新其核對日期 |
| 6 回報 | 見對話 |

未覆蓋：evolve 不會自動判斷「文件與觀察不符」該信誰——本次以本機實測為準記錄，屬人工判斷。

## 建議動作

1. ~~（下次維護）`capabilities.py`：Claude 安裝狀態以 `claude plugin list` 交叉驗證；`capabilities.md` 補已停用 plugin 的卸載繞行。~~ **已處理（2026-09-14，同分支）**：`claude_cli_plugins()` 只在真實 home 且 CLI 可用時交叉驗證，隔離測試不受影響；note 明示「CLI 已列出／登錄有但 CLI 未列出／CLI 列出但登錄無」三種狀態。
2. ~~（下次維護）評估 checker 對 project 層 `enabledPlugins` 的提示。~~ **不改 checker**：project 層設定在各專案 repo 內，全域 checker 無從枚舉；改在 `capabilities.md` 明示進入專案時另看。
3. （下次 evolve）重讀 Claude memory 官方頁後再更新 `agent-runtime.md` 核對日期。
