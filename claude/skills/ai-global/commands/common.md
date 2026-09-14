# 共用背景

## 架構
- clone 是正本；`<repo>` 為 `~/.ai-global/.deploy-state.json` 的 `source_repo`。首次部署可使用已確認的目前 clone。
- governance、router、hooks、自製 skill 是部署副本；manifest 留在 clone。部署比對交給腳本。
- 被取代的檔案移到 `~/.ai-trash/<時間戳>/`，不刪除、不覆蓋備份。

**原則**：授權依 `governance/20-judgment.md`，安全依 `governance/50-safety.md`。已授權部署內的備份與可逆取代不重問；未涵蓋的既有內容衝突、第三方安裝、權限或模型改變才彙整一次裁決。check 與 list 只回報，不寫設定或 auto-memory。

## 部署腳本
- macOS/Linux：`bash <repo>/setup/install.sh [check]`
- Windows：`powershell -ExecutionPolicy Bypass -File <repo>\setup\install.ps1 [-Mode check]`

## check 狀態碼
| 狀態 | 意思 | 已授權部署時的處置 |
|---|---|---|
| `OK` | 與 repo 一致 | 無需處理 |
| `MISSING` | 尚未部署 | install |
| `STALE` | 舊連結 | install，保留原連結到 trash |
| `BEHIND` | 與部署時相同，repo 內容已不同 | 先確認 repo 含已確立決策，再 install |
| `EXTRA` | repo 已移除或改名 | install，舊檔到 trash |
| `EDITED` | 部署端在 repo 外被改過 | 看差異，依已授權處置；未涵蓋才詢問 |

`EDITED` 先比較對應檔案，只顯示不含秘密的差異。可回寫 clone 或以 repo 取代；不要將狀態碼當成政策新舊判斷。首次取代使用者既有 router 時，須明確告知影響與備份位置，既有授權未涵蓋才取得同意。僅授權部署不代表授權修改制度或 commit 其他工作。

回報 install 的 `WARN`／`DROP`／`NOTE` 及備份位置；相同狀態與內容已檢查過，不重跑。部署前後的 check 分別保護輸入與驗證結果，保留兩者。

## 能力對帳
執行 `python <repo>/setup/capabilities.py list`，區分專案預設與本機既有，列工具、類型、ID、安裝及啟用狀態。未列管能力預設保留，不逐項追問是否納管；缺項不自動安裝，偏好不因 sync 重設。只有使用者要求開關才接 [capabilities.md](capabilities.md)。

## settings 共用項對帳
先依 `check_governance.py --local` 輸出確認已覆蓋的欄位，不重做同一比對。其餘從 `<repo>/manifest/settings.json` 與本機設定做唯讀深度比對：Claude 的 `permissions`、`statusLine`、`extraKnownMarketplaces`，以及 manifest 宣告的 Codex 共用 key。checker 的白名單檢查未覆蓋這些欄位時，不能當成已對帳。`enabledPlugins` 已移出此共用基準，不整塊比對或覆寫。能力啟用狀態以 capabilities 清單為準，本機選擇不是必須修復的漂移。只顯示欄位名稱與影響，不輸出原始設定或秘密。修改依明確範圍備份後合併，保留其他 key；對帳本身不授權修改。

## 回報
結論先行，列具體變更、驗證、限制與分支。未安裝或本機停用不代表部署失敗。push 須對具體遠端／分支的明確授權。

## Codex 側
本 skill 的 slash command 屬 Claude Code；Codex 可直接使用 `<repo>/setup/` 中同一套 CLI。
