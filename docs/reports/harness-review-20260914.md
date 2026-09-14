# Harness 審查報告 2026-09-14

- 觸發：GPT-6 Astra 發布（2026-09-08 起 Codex 端模型改為 `gpt-6-astra`），OpenAI 發表 skills／prompt 重審指南。
- 範圍：`manifest/sources.json` 全部 9 個來源；本次為 evolve 流程的第一份報告，部分結論已在同日以 `claude/skills-astra-review` 分支落實。
- 執行：Claude Code（Opus 5）；來源以 WebFetch／WebSearch 讀取，marketplace 以本機 CLI 對帳。

## 結論

需立即處理：0（本日已處理 3 項，見下）。可排入下次維護：2。只記錄：4。未核對：2。

## 逐來源

| 來源 | 結果 | 影響與分級 |
|---|---|---|
| openai-latest-model-guide | 變。Astra 指南：少 skill、description 寫成明確觸發、progressive disclosure、移除「每次先讀文件／先跑測試」類 scaffolding、明訂完成邊界 | **已處理**：manifest 由 11 項精簡為 10（去重疊：ui-styling、taste-skill、web-design-engineer；去方法論模板：三個內容產製 skill、superpowers）；`_readme` 補收錄準則 |
| openai-developers-blog | 變。`rethinking-skills-and-prompts-for-gpt-6-astra` | 同上；另 Codex 於 2026-09-14 已依此縮小 CLAUDE.md／AGENTS.md 讀取範圍（commit 9cbd60f） |
| codex-agents-md | 未核對（本次未重讀；agent-runtime.md 2026-09-06 的描述仍沿用） | 只記錄 |
| codex-config-reference | 變（本機驗證）。codex 0.152 `plugin add/remove`、`marketplace add` 可讀 Claude marketplace 格式；plugin `.mcp.json` 自動載入 `mcp_servers` | **已處理**：manifest 補 Codex 條目，兩側對齊；`capabilities.py` 對 Codex plugin 安裝狀態仍顯示「未知」——**可排入下次維護**：改用 `codex plugin list` 輸出判定安裝 |
| claude-skills-best-practices | 未變（與 Astra 指南一致：description 即路由、one skill one job、body < 500 行） | 只記錄 |
| claude-code-plugins-reference | 未核對（本次未重讀） | 只記錄 |
| claude-code-changelog | 本機 2.1.267。`claude plugin uninstall` 對已停用 plugin 回報 not found，需先 enable 或改原生設定 | 只記錄；capabilities.md 可補一句 |
| claude-plugins-official | 變。新納管 typescript-lsp、context7、hookify、claude-md-management、frontend-design；typescript-lsp 需全域 `typescript-language-server` | 已處理。**可排入下次維護**：hookify 尚未用來把 50-safety 紅線轉成 hook（目前只有 `rm` 走 permissions.deny） |
| vercel-agent-skills | 變。`web-design-guidelines` 取代靜態 command；同 repo 的 `react-best-practices` 對 React 19／Next 16 專案有用 | 已處理前者；後者為候選，未納入 |

## 建議動作

1. （下次維護）`capabilities.py`：Codex plugin 安裝狀態改由 `codex plugin list` 判定。
2. （下次維護）用 hookify 把 50-safety 的「push 需授權」「.env 不 commit」做成 PreToolUse hook，減少 prose 依賴。
3. （候選）評估 `react-best-practices` 是否納入 manifest（digrit 專案）。
4. 下次 evolve 補核對 codex-agents-md 與 claude-code-plugins-reference 兩個未核對來源。
