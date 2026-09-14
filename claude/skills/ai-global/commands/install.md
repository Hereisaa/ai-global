# install <name>

按需讀 [common.md](common.md) 的「原則」。只安裝使用者明確指定的項目，不因 list 缺漏而觸發。`default_enabled` 是建議，不是改寫本機偏好的授權。要一次補齊全部缺項並處理衝突改走 [align.md](align.md)。

1. 在 `<repo>/manifest/skills.json` 以 `tool`、`type`、`id` 確認唯一項目，並先 `python <repo>/setup/capabilities.py list` 記下安裝、啟用狀態與實際路徑；名稱有歧義才詢問。
2. 執行 `python <repo>/setup/align.py --no-pull --yes --only <id>`（可多個 `--only`）。腳本依 manifest 的 `source` 型別處理：`repo:` 交給部署；`marketplace …` 用該工具的 plugin CLI（需要時先 `marketplace add`）；`github:owner/repo`＋`path` 淺 clone 後複製到 skill／command 目錄，並在目錄內寫 `.ai-global.json` 記來源與 commit。已停用（parked）的副本就地更新，不在啟用目錄另放一份；被取代的內容進 `~/.ai-trash/`。
3. `requires` 不在 PATH 時腳本只 WARN 並附 `requires_hint`；前置需求屬第三方安裝，彙整一次裁決後由使用者或授權下執行，不自動跑。
4. 再 `capabilities.py list` 核對該項狀態與既有啟用偏好未變；需要開關接 capabilities。工具需新工作階段才載入時明示目前只驗設定。
