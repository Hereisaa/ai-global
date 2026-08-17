# agent-governance — AI 代理制度目錄

跨 provider（Claude Code、Codex，含未來新增者）共用的工作制度。**單一事實來源在這裡**；`~/.claude/CLAUDE.md` 與 `~/.codex/AGENTS.md` 只是載入時的精簡 router。

建立背景：2026-07-03 由 Fable 5 一次性 session 建制，目的是把高階模型的判斷力外化成後續中階模型可執行的規則。

## 檔案索引（按需讀，不要一次全讀）

| 檔 | 內容 | 什麼時候讀 |
|---|---|---|
| [10-dispatch.md](10-dispatch.md) | 委派觸發表、派工三件套、model/effort 選擇、回報合約、升降級、驗證不自驗 | 任務要讀 >3 檔／掃 repo／查網頁／批次改檔／要驗收時 |
| [20-judgment.md](20-judgment.md) | 五個判斷 rubric：升級模型、算完成、該問使用者、方向錯訊號、品質底線 | 拿不定主意時，對號入座 |
| [30-templates.md](30-templates.md) | 派工 prompt 模板 ×5（搜尋/實作/重構/研究/審查） | 每次派工，複製填空 |
| [40-maintenance.md](40-maintenance.md) | 修改權限分級、教訓回寫格式、長度預算、兩側同步 | 想改任何制度檔或指令檔之前 |
| [50-safety.md](50-safety.md) | Safe Delete 完整流程、不可逆動作清單、憑證規則 | 要刪東西或做不可逆動作前 |
| [60-project-bootstrap.md](60-project-bootstrap.md) | 新專案 harness 三級制起手式、CLAUDE.md/CI/決策日誌模板、收尾儀式 | 開新專案或收編既有專案時 |
| [70-behavior-contract.md](70-behavior-contract.md) | 行為契約（Fable 5 蒸餾）：溝通/行動/驗證/程式碼四契約＋結尾自檢 | 每個 session 第一個實質任務開工前 |
| [80-engineering.md](80-engineering.md) | 工程開發原則與程式碼變更類回覆的輸出格式（完整版；router 載精簡版） | 精簡版與本檔不一致時，以本檔為準 |
| [USER-GUIDE.md](USER-GUIDE.md) | **給使用者本人**的手冊：口令表、環境強制層狀態、健康檢查 | 讀者是人不是模型 |
| `backups/` | 被修改檔案的原始備份，與已歸檔的歷史文件（`archived-*`：建制診斷 00、交接信 90、Fable/Opus 差異報告） | 需要回滾或查建制背景時 |

## 最短摘要（如果你只讀這一段）

1. 大量讀取派 subagent，主對話只進結論（10）。
2. 派工必附：目標動機、驗收條件、回報格式（30 有模板）。
3. 執行者不驗自己的活；驗收派 fresh-context agent 實跑實查（10）。
4. 拿不定主意查 rubric，不憑感覺（20）。
5. 改制度先備份、留變更紀錄；安全紅線與刪規則要先問使用者（40）。

## 變更紀錄
- 2026-07-03 建檔（Fable 5）
- 2026-07-05 新增 60-project-bootstrap.md 並掛上兩側路由（Fable 5）
- 2026-07-05 新增 USER-GUIDE.md（使用者手冊）；環境強制層：digrit CI 檔就緒、Stop hook 腳本就緒待掛載（Fable 5）
- 2026-07-08 新增 70-behavior-contract.md（行為契約，Fable 5 蒸餾）與 REPORT-fable5-vs-opus.md（差異分析報告），兩側路由同步掛載（Fable 5）
- 2026-08-16 新增 80-engineering.md；目錄精簡：00-diagnosis、90-letter、REPORT-fable5-vs-opus 歸檔至 `backups/archived-*`，相關引用已修（Fable 5，應使用者要求）
