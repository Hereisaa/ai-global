# capabilities（能力清單與本機開關）

在已確認的 `<repo>` 執行：

```bash
python setup/capabilities.py list
python setup/capabilities.py manage --demo
python setup/capabilities.py manage
python setup/capabilities.py disable --tool codex --kind plugin --id <ID>
python setup/capabilities.py enable --tool claude --kind skill --id <ID>
```

1. 無動作參數時用 list，唯讀列出專案預設、本機既有、工具、種類、ID、安裝與啟用狀態；保留未知狀態，不猜測已載入。
2. 開關只接受明確工具、類型與清單 ID。使用者已指定目標與動作即為授權，不再確認；歧義時先列匹配項目。
3. 使用 CLI 的原生設定更新或可逆停用機制，保留其餘本機設定。切換不等於卸載，不下載第三方，也不改 manifest。
4. 再 list 核對該項狀態並回報；若工具需要新工作階段才載入，明示目前只驗設定。CLI 不支援的項目回報限制，不自製另一套修改方法。

本機偏好保留在該機器，sync 不重設。更改專案預設屬另一次 manifest 變更；只有使用者要求才處理，不把本機選擇自動納管或寫入記憶。

清單僅涵蓋使用者全域層，不含 project/system 層；插件內 skills 隨插件開關。Codex 插件缺少可靠安裝登錄時顯示安裝未知，不把已設定 enabled 當成已安裝。Claude 插件用原生 enabledPlugins；Codex 用 config.toml 的 plugins 與 skills.config（Python 3.11+）；Claude 獨立能力停用至 `~/.claude/ai-global-disabled/{skills,commands}/<name>`。設定備份在 `~/.ai-trash/ai-global-settings-<唯一值>/`，不輸出內容。

設定參考：[Codex 設定參考](https://learn.chatgpt.com/docs/config-file/config-reference)、[Claude 插件參考](https://code.claude.com/docs/en/plugins-reference)。Codex 插件開關格式是本機已觀察並由 CLI 支援的格式，不宣稱是所有版本通用的官方 schema；不支援的格式回報限制。

使用者要方向鍵／空白鍵互動選單時，使用 manage，不以 list 代替。這需要真正的互動 Terminal 與 `setup/requirements-tui.txt` 套件；以 README 的 .venv 安裝方式準備，然後提供使用者啟動指令。不要在不支援互動的工具管線中等待鍵盤輸入。`--demo` 不讀寫本機能力設定；實際模式空白鍵只預選，Enter 才授權套用所選變更，Esc／Ctrl+C 放棄預選。未安裝或開關未知不可切換；套用失敗需交代已完成與未套用項目。
