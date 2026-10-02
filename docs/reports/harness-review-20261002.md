# Harness 精簡與 eval 方法交付 2026-10-02

分支：`codex/harness-eval`；基準：`3f03aa6`。本次完成入口精簡、部署檢查狀態分層與 [eval方法設計](../reference/harness-eval-method.md)。不是模型行為實驗報告。

## 行為差異

- Codex入口由8284 bytes降為4302 bytes；Claude入口由8280 bytes降為4436 bytes。機器與維護背景移到按需參考；取消首次任務必讀完整70契約，其溝通原則留在入口、細節仍可查閱。授權、安全與制度路由保留。
- `deploy.py check` 保留內容一致時exit 0，另呈現記錄的部署來源與當前clone。hooks、當次載入與防護、remote明示未檢查／未驗證。部署state記是否含未提交變更。
- SessionStart hook明示比較的是clone，不把clone目前分支當成部署來源；一致不再暗示當次規則或安全防護已驗證。
- eval建議採實際任務、事件及成果檢查為主，模型裁判輔助，人工校準歧義。八題兩版本先16次預演、再累計48次；尚未建置runner或啟動模型測試。

## 驗證證據

- 離線govcheck：0失敗、0提醒。
- 本機govcheck --local：0失敗、2提醒。提醒是Claude本機settings.local.json優先序未判定，以及內容對帳不保證當次讀取／遵循與權限；不是新增失敗。
- 完整單元測試：122項，101通過、21略過（本次Python環境缺TUI依賴與PowerShell）。不得把略過計為通過。
- 已部署到本機，deploy.py check內容一致；沒有修改工具權限、plugin開關或真實憑證。
- 隔離上下文的獨立審查者讀回全部差異與新增文件，驗證相關fixture及結構檢查。發現hook來源措辭混淆，修正後由審查者重驗通過；未發現阻擋交付問題。

## 限制與回復

沒有模型安全／完成／效率成績；沒有Windows、桌面防護或另一台機器同步證據。入口文字減量不等於效能提升。eval開始前須先驗證隔離、規則載入、事件完整性及必要續談流程。

本機部署來源指向保留的 `ai-global-harness-eval` worktree；原clone的main未修改，不push也不合併。不要封存／搬移目前source_repo，除非先從要保留的clone重新部署並驗證。需要回復時可從原clone基準內容重新部署，既有替換檔已保存在本機 `~/.ai-trash/` 的唯一部署批次目錄。
