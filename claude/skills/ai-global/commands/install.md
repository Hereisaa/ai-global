# install <name>

按需讀 [common.md](common.md) 的「原則」。只安裝使用者明確指定的項目，不因 list 缺漏而觸發。`default_enabled` 是建議，不是改寫本機偏好的授權。

1. 在 `<repo>/manifest/skills.json` 以 `tool`、`type`、`id` 確認唯一項目，並先執行 capabilities list 記下安裝、啟用狀態與實際路徑；名稱有歧義才詢問。
2. 依來源處理：`repo:` 是目前 clone 的自製能力（例如 ai-global），走既有部署流程並保留停用狀態，不當成 GitHub 來源或臆造版本；第三方才使用 manifest 的來源及可取得的 version/ref。未指定或無法解析版本時先回報可重現限制，不宣稱固定版本部署，也不改抓其他來源。
3. 依工具、種類及既有狀態選目標：
   - Claude 獨立 skill／command：已停用者只更新 `~/.claude/ai-global-disabled/skills/<id>/` 或 `~/.claude/ai-global-disabled/commands/<id>.md` 中的既有副本，不在啟用目錄另放一份；已啟用者更新 list 的既有路徑。若兩處皆有或狀態未知，先釐清，不任選一處覆蓋。
   - Codex 獨立 skill：更新已確認的安裝路徑，保留 `skills.config` 的既有停用設定；不得套用 Claude 路徑。
   - plugin：使用該工具支援的安裝入口及指定 marketplace；更新前後保留本機啟用設定，不以安裝推定同意啟用。
   - 首次安裝沒有偏好時，先說明安裝位置是否會被工具載入；使用者原授權已涵蓋便執行，未涵蓋的啟用選擇才確認。不要以 `default_enabled` 代替這項判斷。
4. 被取代內容依安全規則備份；核對版本與存在狀態，再 list 驗證既有啟用偏好未變。需要開關時接 capabilities，不把重新安裝當成啟用操作。
