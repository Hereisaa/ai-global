# install <name>

先讀 [common.md](common.md) 的「原則」。

1. 在 `<repo>/manifest/skills.json` 找 `<name>`；找不到 → 列出 manifest 清單請使用者重選。
2. 依 `type`：
   - `skill` → 從 `source` 標的 GitHub repo 抓對應目錄（有 `path` 欄位就抓那個子目錄）放到 `~/.claude/skills/<name>/`；抓不到就回報，不要硬湊替代品。
   - `plugin` → 引導使用者用 `/plugin` 從 manifest 記載的 marketplace 安裝。
   - `command` → 放到 `target` 路徑。
3. 核對存在與版本（manifest 的 `version`），回報。
